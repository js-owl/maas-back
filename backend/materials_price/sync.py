"""Materials price sync cycle: Excel + Bitrix → auto_price + MATERIALS catalog."""

from __future__ import annotations

import datetime
import gc
import re
import shutil
import statistics
import tempfile
from enum import Enum
from pathlib import Path
from typing import Any

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from backend.bitrix24.client import BitrixClient
from backend.core.config import (
    BITRIX_VERIFY_TLS,
    MATERIALS_CRM_NAME,
    MATERIALS_DISK_PATH,
    MATERIALS_PRICE_CRM_NAME,
    MATERIALS_SYNC_INTERVAL_SECONDS,
)
from backend.materials_price.catalog import publish_catalog_to_redis, upsert_catalog_to_db
from backend.materials_price.crm import BitrixCrmType, format_money, get_enum_dict, parse_money
from backend.materials_price.disk import download_files, list_files_at_path
from backend.materials_price.enums import (
    SERVICE_TYPE_BY_MATERIAL_MAIN,
    MaterialFamily,
    MaterialForm,
    MaterialNameMain,
)
from backend.materials_price.excel_source import PriceExcelSource
from backend.materials_price.field_map import M_REQ, P_REQ, enum_text_to_member
from backend.materials_price.synonyms import (
    GOST_PATTERNS,
    add_comma_point_syns,
    get_casefolded_syn_list,
    load_gost_forms,
)
from backend.utils.logging import get_logger

logger = get_logger(__name__)


def _uf(crm: BitrixCrmType, short_name: str) -> str:
    return crm.prefix + short_name


def _validate_field_names(crm: BitrixCrmType, req_dict: dict[str, dict[str, Any]]) -> bool:
    ok = True
    for req in req_dict.values():
        key = _uf(crm, str(req["bitrix_name"]))
        if key not in crm.fields:
            logger.error("CRM '%s' missing field '%s'", crm.title, req["bitrix_name"])
            ok = False
    return ok


def _build_materials_catalog(
    m_crm: BitrixCrmType,
    p_crm: BitrixCrmType,
    bitrix_enum_dict: dict[str, dict[str, str]],
    bitrix_text_rev_dict: dict[str, dict[str, Enum]],
) -> dict[str, Any]:
    """Build MATERIALS dict from Bitrix rows that have manual_price > 0."""
    materials_new: dict[str, Any] = {
        "other": {
            "label": "Другой",
            "family": "other",
            "electroplating_family": "other",
            "applicable_processes": [],
            "forms": {},
            "density": 0.0,
            "material_name": "other",
            "material_name_main": "other",
        }
    }

    parent_key = _uf(p_crm, str(P_REQ["parent"]["bitrix_name"]))
    price_key = _uf(p_crm, str(P_REQ["price"]["bitrix_name"]))
    form_key = _uf(p_crm, str(P_REQ["forms"]["bitrix_name"]))

    materials_by_id = {int(item["id"]): item for item in m_crm.items_list if "id" in item}

    for p_item in p_crm.items_list:
        manual_price = parse_money(p_item.get(price_key))
        if manual_price <= 0:
            continue
        parent_raw = p_item.get(parent_key)
        if parent_raw is None:
            continue
        try:
            parent_id = int(parent_raw)
        except (TypeError, ValueError):
            continue
        m_item = materials_by_id.get(parent_id)
        if m_item is None:
            continue

        materials_fields: dict[str, Any] = {}
        for m_key, req in M_REQ.items():
            raw = m_item.get(_uf(m_crm, str(req["bitrix_name"])))
            if req["bitrix_type"] == "enumeration":
                enum_map = bitrix_enum_dict.get(m_key) or {}
                rev = bitrix_text_rev_dict.get(m_key) or {}
                if req["is_multiple"] == "Y":
                    ids = raw if isinstance(raw, list) else ([raw] if raw is not None else [])
                    members = []
                    for eid in ids:
                        label = enum_map.get(str(eid))
                        if label is None:
                            continue
                        member = rev.get(label.casefold())
                        if member is not None:
                            members.append(member)
                    materials_fields[m_key] = members
                else:
                    if raw is None:
                        continue
                    label = enum_map.get(str(raw))
                    if label is None:
                        continue
                    member = rev.get(label.casefold())
                    if member is not None:
                        materials_fields[m_key] = member
            else:
                if raw is not None:
                    materials_fields[m_key] = raw

        form_raw = p_item.get(form_key)
        form_enum_map = bitrix_enum_dict.get("forms") or {}
        form_rev = bitrix_text_rev_dict.get("forms") or {}
        form_label = form_enum_map.get(str(form_raw)) if form_raw is not None else None
        form_member = form_rev.get(form_label.casefold()) if form_label else None
        if form_member is None:
            continue
        materials_fields["forms"] = form_member
        materials_fields["price"] = manual_price

        material_name = str(materials_fields.get("material_name") or "")
        main_enum = materials_fields.get("material_name_main")
        if not isinstance(main_enum, MaterialNameMain) or not material_name:
            continue
        item_id = f"{main_enum.value}_{material_name}"
        entry = materials_new.setdefault(item_id, {})

        main_label = M_REQ["material_name_main"]["bitrix_enum"][main_enum]
        entry["label"] = f"{main_label} {material_name}"
        entry["material_name"] = material_name
        entry["material_name_main"] = main_enum.value

        if "family" in materials_fields and isinstance(materials_fields["family"], Enum):
            entry["family"] = materials_fields["family"].value
            entry["electroplating_family"] = entry["family"]

        if "density" in materials_fields:
            try:
                entry["density"] = float(materials_fields["density"])
            except (TypeError, ValueError):
                pass

        if "material_group" in materials_fields and isinstance(materials_fields["material_group"], Enum):
            entry["material_group"] = materials_fields["material_group"].value

        if "material_name_group" in materials_fields:
            groups = materials_fields["material_name_group"]
            if isinstance(groups, list):
                entry["material_name_group"] = " ".join(
                    g.value if isinstance(g, Enum) else str(g) for g in groups
                )

        if "minimum_order_quantity" in materials_fields:
            try:
                entry["minimum_order_quantity"] = float(materials_fields["minimum_order_quantity"])
            except (TypeError, ValueError):
                pass

        processes = [s.value for s in SERVICE_TYPE_BY_MATERIAL_MAIN.get(main_enum, [])]
        entry["applicable_processes"] = processes

        forms = entry.setdefault("forms", {})
        form_payload: dict[str, Any] = {"price": round(manual_price, 2), "applicable_processes": processes}
        if "price_units" in materials_fields and isinstance(materials_fields["price_units"], list):
            form_payload["price_units"] = [
                u.value if isinstance(u, Enum) else str(u) for u in materials_fields["price_units"]
            ]
        if "one_layer_thickness" in materials_fields:
            try:
                form_payload["one_layer_thickness"] = float(materials_fields["one_layer_thickness"])
            except (TypeError, ValueError):
                pass
        forms[form_member.value] = form_payload

    return materials_new


async def run_materials_price_sync(
    client: BitrixClient,
    redis: Redis,
    db: AsyncSession,
) -> dict[str, Any]:
    """Run one sync cycle. Returns the MATERIALS catalog written to Redis/DB."""
    gost_forms = load_gost_forms()
    m_crm = BitrixCrmType(client, MATERIALS_CRM_NAME)
    p_crm = BitrixCrmType(client, MATERIALS_PRICE_CRM_NAME)
    await m_crm.update()
    await p_crm.update()

    if not _validate_field_names(m_crm, M_REQ) or not _validate_field_names(p_crm, P_REQ):
        raise ValueError("Bitrix materials/prices CRM field validation failed")

    mat_2_temp: dict[str, list[str]] = {}
    mat_id_name_dict: dict[str, int] = {}
    name_key = _uf(m_crm, str(M_REQ["material_name"]["bitrix_name"]))
    for p_item in m_crm.items_list:
        material_name_src = p_item.get(name_key)
        if material_name_src is None:
            continue
        material_name = str(material_name_src)
        mat_2_temp[material_name] = add_comma_point_syns(get_casefolded_syn_list(material_name))
        mat_id_name_dict[material_name] = int(p_item["id"])

    temp_2_mat = {t: m for m, temps in mat_2_temp.items() for t in temps}
    temp_2_mat = {
        k: temp_2_mat[k]
        for k in sorted(sorted(temp_2_mat.keys(), reverse=True), key=len, reverse=True)
    }

    form_2_temp: dict[str, list[str]] = {}
    for form in MaterialForm:
        form_search_text = P_REQ["forms"]["bitrix_enum"][form]
        form_2_temp[form_search_text] = get_casefolded_syn_list(form_search_text)
    temp_2_form = {t: f for f, temps in form_2_temp.items() for t in temps}
    temp_2_form = {
        k: temp_2_form[k]
        for k in sorted(sorted(temp_2_form.keys(), reverse=True), key=len, reverse=True)
    }

    materials_price_dict: dict[tuple[int, MaterialForm], list[tuple[datetime.datetime, float]]] = {}

    bitrix_enum_dict: dict[str, dict[str, str]] = {}
    bitrix_text_rev_dict: dict[str, dict[str, Enum]] = {}
    for m_k, b_req in (M_REQ | P_REQ).items():
        if b_req["bitrix_type"] != "enumeration":
            continue
        text_tmp: dict[str, Enum] = {}
        for member, label in b_req["bitrix_enum"].items():
            text_tmp[str(label).casefold()] = member
        bitrix_text_rev_dict[m_k] = text_tmp
        for crm in (p_crm, m_crm):
            enum_tmp = get_enum_dict(crm, str(b_req["bitrix_name"]))
            if enum_tmp:
                bitrix_enum_dict[m_k] = enum_tmp

    cache_dir = Path(tempfile.mkdtemp(prefix="materials_price_"))
    try:
        files = await list_files_at_path(client, MATERIALS_DISK_PATH)
        xls_files = [
            f for f in files if str(f.get("NAME", "")).endswith((".xls", ".xlsx"))
        ]
        downloaded = await download_files(xls_files, cache_dir, verify_tls=BITRIX_VERIFY_TLS)

        for path in downloaded:
            source = PriceExcelSource(str(path))
            try:
                for row in source.iter_rows():
                    name_ = row.get("name", "").casefold()
                    if not name_ or name_ == "none":
                        continue

                    form_scores: dict[str, int] = dict.fromkeys(form_2_temp, 0)
                    standards = [
                        gost
                        for pattern in GOST_PATTERNS
                        for gost in re.findall(pattern, name_, re.IGNORECASE)
                    ]
                    for std in standards:
                        for gost_form, stds in gost_forms.items():
                            if std.replace(" ", "").casefold() in stds and gost_form in temp_2_form:
                                form_scores[temp_2_form[gost_form]] += 1
                        name_ = name_.replace(std.casefold(), "")

                    for template in temp_2_form:
                        if re.search(r"\b" + re.escape(template), name_, re.IGNORECASE):
                            name_ = name_.replace(template, "")
                            form_scores[temp_2_form[template]] += 1

                    other_label = P_REQ["forms"]["bitrix_enum"][MaterialForm.OTHER]
                    form_scores[other_label] = 0

                    detected_form = ""
                    max_scores = 0
                    for form_label, score in form_scores.items():
                        if score > max_scores:
                            max_scores = score
                            detected_form = form_label

                    detected_material = ""
                    detected_material_id = -1
                    for template in temp_2_mat:
                        if re.search(r"\b" + re.escape(template), name_, re.IGNORECASE):
                            detected_material = temp_2_mat[template]
                            detected_material_id = mat_id_name_dict[detected_material]
                            break

                    if not detected_material:
                        continue
                    if not detected_form:
                        family_key = _uf(m_crm, str(M_REQ["family"]["bitrix_name"]))
                        for m in m_crm.items_list:
                            if str(m.get(name_key, "")).casefold() != detected_material.casefold():
                                continue
                            family_id = m.get(family_key)
                            bitrix_val = (bitrix_enum_dict.get("family") or {}).get(str(family_id))
                            if not bitrix_val:
                                break
                            member = (bitrix_text_rev_dict.get("family") or {}).get(bitrix_val.casefold())
                            if member == MaterialFamily.PLASTIC_3D:
                                detected_form = P_REQ["forms"]["bitrix_enum"][MaterialForm.THREAD]
                            break
                        if not detected_form:
                            continue

                    data_units_syns = get_casefolded_syn_list(row.get("meas", ""))
                    units_key = _uf(m_crm, str(M_REQ["price_units"]["bitrix_name"]))
                    valid_units = False
                    for m in m_crm.items_list:
                        if str(m.get(name_key, "")).casefold() != detected_material.casefold():
                            continue
                        src_val = m.get(units_key)
                        if not isinstance(src_val, list):
                            continue
                        unit_labels = [
                            (bitrix_enum_dict.get("price_units") or {}).get(str(uid), "")
                            for uid in src_val
                        ]
                        if set(u.casefold() for u in unit_labels if u).intersection(data_units_syns):
                            valid_units = True
                        break
                    if not valid_units:
                        continue

                    date_norm = re.sub(r"[./]", "-", row.get("date", ""))
                    price_date = None
                    found = re.findall(r"\d{2}-\d{2}-\d{4}", date_norm)
                    if found:
                        price_date = datetime.datetime.strptime(found[0], "%d-%m-%Y")
                    found = re.findall(r"\d{4}-\d{2}-\d{2}", date_norm)
                    if found:
                        price_date = datetime.datetime.strptime(found[0], "%Y-%m-%d")
                    if price_date is None:
                        continue

                    try:
                        price_val = float(str(row.get("price", "")).replace(",", "."))
                    except ValueError:
                        continue

                    form_member = enum_text_to_member("forms", detected_form)
                    if not isinstance(form_member, MaterialForm):
                        continue
                    price_key = (detected_material_id, form_member)
                    materials_price_dict.setdefault(price_key, []).append((price_date, price_val))
            finally:
                source.close()
                gc.collect()
    finally:
        shutil.rmtree(cache_dir, ignore_errors=True)

    # Aggregate + write auto_price
    auto_key = _uf(p_crm, str(P_REQ["auto_price"]["bitrix_name"]))
    form_field = _uf(p_crm, str(P_REQ["forms"]["bitrix_name"]))
    parent_field = _uf(p_crm, str(P_REQ["parent"]["bitrix_name"]))

    for (m_id, form), samples in list(materials_price_dict.items()):
        samples = sorted(samples, key=lambda t: t[0])
        values = [t[1] for t in samples]
        mean_val = statistics.mean(values) if values else 0.0
        samples = [t for t in samples if t[1] < (5 * mean_val)]
        if not samples:
            continue
        auto_price = statistics.mean([t[1] for t in samples])
        materials_price_dict[(m_id, form)] = samples

        # Find matching price CRM item(s) and update auto_price
        form_enum_id = None
        for eid, label in (bitrix_enum_dict.get("forms") or {}).items():
            member = (bitrix_text_rev_dict.get("forms") or {}).get(label.casefold())
            if member == form:
                form_enum_id = eid
                break
        if form_enum_id is None:
            continue
        for p_item in p_crm.items_list:
            try:
                parent_id = int(p_item.get(parent_field))
            except (TypeError, ValueError):
                continue
            if parent_id != m_id:
                continue
            if str(p_item.get(form_field)) != str(form_enum_id):
                continue
            await p_crm.item_update(int(p_item["id"]), {auto_key: format_money(auto_price)})

    # Refresh price CRM before building catalog (manual prices)
    await p_crm.update()
    catalog = _build_materials_catalog(m_crm, p_crm, bitrix_enum_dict, bitrix_text_rev_dict)
    await upsert_catalog_to_db(db, catalog)
    await publish_catalog_to_redis(redis, catalog)
    logger.info("Materials price sync finished: %s catalog materials", len(catalog))
    return catalog


async def run_loop(
    client: BitrixClient,
    redis: Redis,
    *,
    interval_seconds: int | None = None,
) -> None:
    import asyncio

    from backend.database import AsyncSessionLocal

    interval = interval_seconds if interval_seconds is not None else MATERIALS_SYNC_INTERVAL_SECONDS
    logger.info("Starting materials price sync loop (interval=%ss)", interval)
    while True:
        try:
            async with AsyncSessionLocal() as db:
                await run_materials_price_sync(client, redis, db)
        except Exception:
            logger.exception("Materials price sync run failed")
        await asyncio.sleep(interval)

"""Postgres + Redis persistence for MATERIALS catalog."""

from __future__ import annotations

import json
from typing import Any

from redis.asyncio import Redis
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Material, MaterialFormPrice
from backend.utils.logging import get_logger

logger = get_logger(__name__)

REDIS_CATALOG_KEY = "materials:catalog"


async def publish_catalog_to_redis(redis: Redis, catalog: dict[str, Any]) -> None:
    await redis.set(REDIS_CATALOG_KEY, json.dumps(catalog, ensure_ascii=False))
    logger.info("Published materials catalog to Redis (%s materials)", len(catalog))


async def load_catalog_from_redis(redis: Redis | None) -> dict[str, Any] | None:
    if redis is None:
        return None
    raw = await redis.get(REDIS_CATALOG_KEY)
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Invalid materials catalog JSON in Redis")
        return None
    if not isinstance(data, dict) or not data:
        return None
    return data


async def upsert_catalog_to_db(db: AsyncSession, catalog: dict[str, Any]) -> None:
    """Replace local material tables with the synced catalog."""
    await db.execute(delete(MaterialFormPrice))
    await db.execute(delete(Material))
    await db.flush()

    for material_id, info in catalog.items():
        if not isinstance(info, dict):
            continue
        mat = Material(
            id=material_id,
            label=str(info.get("label") or material_id),
            family=info.get("family"),
            electroplating_family=info.get("electroplating_family"),
            density=float(info["density"]) if info.get("density") is not None else None,
            minimum_order_quantity=(
                float(info["minimum_order_quantity"])
                if info.get("minimum_order_quantity") is not None
                else None
            ),
            material_name=info.get("material_name"),
            material_name_main=info.get("material_name_main"),
            material_group=info.get("material_group"),
            material_name_group=info.get("material_name_group"),
            applicable_processes=info.get("applicable_processes") or [],
            payload=info,
        )
        db.add(mat)
        forms = info.get("forms") or {}
        if isinstance(forms, dict):
            for form_id, form_info in forms.items():
                if not isinstance(form_info, dict):
                    continue
                db.add(
                    MaterialFormPrice(
                        material_id=material_id,
                        form=str(form_id),
                        price=float(form_info.get("price") or 0),
                        auto_price=None,
                        price_units=form_info.get("price_units"),
                        one_layer_thickness=(
                            float(form_info["one_layer_thickness"])
                            if form_info.get("one_layer_thickness") is not None
                            else None
                        ),
                        applicable_processes=form_info.get("applicable_processes"),
                    )
                )
    await db.commit()
    logger.info("Upserted %s materials into Postgres", len(catalog))


async def load_catalog_from_db(db: AsyncSession) -> dict[str, Any]:
    rows = (await db.execute(select(Material))).scalars().all()
    catalog: dict[str, Any] = {}
    for row in rows:
        if row.payload and isinstance(row.payload, dict):
            catalog[row.id] = row.payload
        else:
            catalog[row.id] = {
                "label": row.label,
                "family": row.family,
                "electroplating_family": row.electroplating_family,
                "density": row.density,
                "minimum_order_quantity": row.minimum_order_quantity,
                "material_name": row.material_name,
                "material_name_main": row.material_name_main,
                "material_group": row.material_group,
                "material_name_group": row.material_name_group,
                "applicable_processes": row.applicable_processes or [],
                "forms": {},
            }
    return catalog


def catalog_to_materials_list(
    catalog: dict[str, Any],
    process: str | None = None,
) -> list[dict[str, Any]]:
    """Build GET /materials list payload from MATERIALS-shaped catalog."""
    materials_list: list[dict[str, Any]] = []
    for material_id, info in catalog.items():
        if material_id == "other":
            continue
        if not isinstance(info, dict):
            continue
        processes = info.get("applicable_processes") or []
        if process and process not in processes:
            continue
        forms = info.get("forms") or {}
        form_ids = list(forms.keys()) if isinstance(forms, dict) else []
        materials_list.append(
            {
                "id": material_id,
                "label": info.get("label", ""),
                "family": info.get("family", ""),
                "density": info.get("density", 0.0),
                "forms": forms,
                "available_forms": form_ids,
                "applicable_processes": processes,
                "electroplating_family": info.get("electroplating_family"),
            }
        )
    materials_list.sort(key=lambda x: x["label"])
    return materials_list

"""Bitrix disk helpers for materials price Excel files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from backend.bitrix24.client import BitrixClient
from backend.utils.logging import get_logger

logger = get_logger(__name__)


async def _storage_get_entity_id(
    client: BitrixClient,
    method: str,
    name: str,
    parent_id: int | None = None,
) -> int:
    params: dict[str, Any] = {"filter": {"NAME": name}}
    if parent_id is not None:
        params["id"] = parent_id
    result = await client.call(method, params)
    # disk.* list methods return a list in result
    if isinstance(result, list) and len(result) == 1:
        return int(result[0].get("ID", -1))
    return -1


async def _list_files(client: BitrixClient, method: str, entity_id: int) -> list[dict[str, Any]]:
    start = 0
    files: list[dict[str, Any]] = []
    while True:
        data = await client.call_full(
            method,
            {"id": entity_id, "filter": {"TYPE": "file"}, "start": start},
        )
        result = data.get("result")
        if isinstance(result, list):
            files.extend(result)
        elif isinstance(result, dict):
            files.extend(result.get("files") or result.get("children") or [])
        start = int(data.get("next") or 0)
        if start == 0:
            break
    return files


async def list_files_at_path(client: BitrixClient, bitrix_path: str) -> list[dict[str, Any]]:
    """Walk disk path like 'Общий диск/materials_price' and return file records."""
    path_list = [p for p in bitrix_path.split("/") if p]
    if not path_list:
        raise ValueError(f"empty bitrix disk path: {bitrix_path}")

    ent_id = await _storage_get_entity_id(client, "disk.storage.getlist", path_list[0])
    if ent_id < 0:
        raise ValueError(f"Bitrix disk not found: {path_list[0]}")

    for i in range(1, len(path_list)):
        method = "disk.storage.getchildren" if i == 1 else "disk.folder.getchildren"
        folder_id = await _storage_get_entity_id(client, method, path_list[i], ent_id)
        if folder_id < 0:
            raise ValueError(f"Bitrix folder not found: {path_list[i]}")
        ent_id = folder_id

    if len(path_list) == 1:
        return await _list_files(client, "disk.storage.getchildren", ent_id)
    return await _list_files(client, "disk.folder.getchildren", ent_id)


async def download_files(
    files: list[dict[str, Any]],
    dest_dir: Path,
    *,
    verify_tls: bool = False,
) -> list[Path]:
    dest_dir.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []
    async with httpx.AsyncClient(timeout=120.0, verify=verify_tls) as http:
        for file_rec in files:
            name = file_rec.get("NAME") or ""
            url = file_rec.get("DOWNLOAD_URL") or ""
            if not name or not url:
                continue
            if not (name.endswith(".xls") or name.endswith(".xlsx")):
                continue
            local = dest_dir / name
            response = await http.get(url)
            response.raise_for_status()
            local.write_bytes(response.content)
            saved.append(local)
            logger.info("Downloaded materials price file %s", name)
    return saved

import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, text
from backend.models import Base, User, FileStorage
from backend.auth.service import get_password_hash
from backend.core.config import (
    ADMIN_DEFAULT_PASSWORD, ADMIN_USERNAME, DATABASE_URL, 
    UPLOAD_DIR, DEMO_FILE_IDS
)
from backend.utils.logging import get_logger
from backend.core.config import ADMIN_LOCATION_OVERRIDES_JSON, DEFAULT_LOCATION
import asyncio
from pathlib import Path
import shutil
from datetime import datetime, timezone
import json
from typing import Dict, Optional

logger = get_logger(__name__)


def _resolve_existing_path(path_value: Optional[str]) -> Optional[Path]:
    """Resolve stored relative/absolute file paths used inside and outside Docker.

    Existing records may contain either relative paths like ``uploads/name.stp``
    or absolute paths.  Docker deployments usually run from ``/app``, so for
    relative paths we also check ``/app/<path>``.
    """
    if not path_value:
        return None

    normalized = str(path_value).replace('\\', '/')
    path = Path(normalized)
    candidates = [path]

    if not path.is_absolute():
        candidates.append(Path("/app") / normalized)

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return None


engine = create_async_engine(
    DATABASE_URL, echo=False, future=True
)

AsyncSessionLocal = sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False, autocommit=False
)


async def ensure_schema() -> None:
    """Compare SQLAlchemy model definitions with the actual PostgreSQL schema.

    On every startup:
      1. Creates any tables that do not yet exist (IF NOT EXISTS semantics via
         SQLAlchemy create_all).
      2. For each table that already exists, adds any columns that are present in
         the model but absent from the database.  Uses PostgreSQL
         information_schema so no SQLite-specific PRAGMA calls remain.

    The function is idempotent and safe to run repeatedly.
    """
    # --- Step 1: create missing tables ---
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Schema check: all tables ensured")

    # --- Step 2: add missing columns to existing tables ---
    dialect = engine.dialect
    async with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            result = await conn.execute(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = current_schema()
                      AND table_name   = :tname
                    """
                ),
                {"tname": table.name},
            )
            existing_cols = {row[0] for row in result}

            for col in table.columns:
                if col.name in existing_cols:
                    continue

                # Compile the SQLAlchemy type to a PostgreSQL DDL string
                try:
                    col_type_str = col.type.compile(dialect=dialect)
                except Exception:
                    col_type_str = str(col.type)

                # PostgreSQL supports ADD COLUMN IF NOT EXISTS (≥ 9.6)
                alter_sql = (
                    f'ALTER TABLE "{table.name}" '
                    f'ADD COLUMN IF NOT EXISTS "{col.name}" {col_type_str}'
                )
                logger.info(
                    "Schema migration: adding %s.%s (%s)",
                    table.name, col.name, col_type_str,
                )
                await conn.execute(text(alter_sql))

    logger.info("Schema check: all columns ensured")


# ---------------------------------------------------------------------------
# Database session dependency
# ---------------------------------------------------------------------------

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        else:
            await session.commit()


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------

async def seed_admin():
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(
                User.__table__.select().where(User.username == ADMIN_USERNAME)
            )
            if result.first() is None:
                admin_user = User(
                    username=ADMIN_USERNAME,
                    hashed_password=get_password_hash(ADMIN_DEFAULT_PASSWORD),
                    is_admin=True,
                    must_change_password=True,
                )
                session.add(admin_user)
                await session.commit()
        except Exception:
            await session.rollback()
            raise


async def ensure_demo_files() -> None:
    """Ensure demo sample files exist in files table with fixed IDs and is_demo flag."""
    demo_mapping = [
        (1, "demo_printing_default.stp"),
        (2, "demo_lathe_default.stp"),
        (3, "sample_plate.stl"),
        (5, "sample_gear.stl"),
    ]
    special_id = 4
    special_filename = "demo_milling_default.stp"
    models_dir = Path(UPLOAD_DIR)
    models_dir.mkdir(parents=True, exist_ok=True)

    async with AsyncSessionLocal() as session:
        try:
            # Resolve an uploader user (prefer admin)
            uploader_id = None
            result = await session.execute(User.__table__.select().where(User.is_admin == True))
            row = result.first()
            if row and len(row) > 0:
                uploader_id = row.id
            else:
                result = await session.execute(User.__table__.select())
                row = result.first()
                uploader_id = (row.id if row and len(row) > 0 else None)

            now = datetime.now(timezone.utc).replace(tzinfo=None)

            async def upsert_demo(id_value: int, filename: str) -> None:
                file_path = models_dir / filename
                if filename == special_filename and not file_path.exists():
                    root_candidate = Path('.') / filename
                    if root_candidate.exists():
                        shutil.copyfile(str(root_candidate), str(file_path))
                if not file_path.exists():
                    return
                stat = file_path.stat()
                file_size = stat.st_size
                file_ext = file_path.suffix.lower()
                existing = await session.get(FileStorage, id_value)
                if existing:
                    existing.filename = filename
                    existing.original_filename = filename
                    existing.file_path = str(file_path)
                    existing.file_size = file_size
                    existing.file_type = file_ext
                    if uploader_id is not None:
                        existing.uploaded_by = uploader_id
                    existing.is_demo = True
                    existing.file_metadata = json.dumps({"file_size": file_size, "source": "demo_seed"})
                    session.add(existing)
                else:
                    new_file = FileStorage(
                        id=id_value,
                        filename=filename,
                        original_filename=filename,
                        file_path=str(file_path),
                        file_size=file_size,
                        file_type=file_ext,
                        uploaded_by=(uploader_id or 0),
                        uploaded_at=now,
                        file_metadata=json.dumps({"file_size": file_size, "source": "demo_seed"}),
                        is_demo=True,
                    )
                    session.add(new_file)
                await session.commit()

            for id_value, fname in demo_mapping:
                await upsert_demo(id_value, fname)
                logger.info(f"{fname} upsert")
            await upsert_demo(special_id, special_filename)
            logger.info(f"{special_filename} upsert")
        except Exception as e:
            logger.info(f"{e}")
            await session.rollback()


async def ensure_demo_file_previews() -> None:
    """Generate missing previews for demo files during service startup.

    A demo file is considered to already have a preview only when the database
    record points to a preview image that is actually present on disk. This is
    intentionally stricter than checking ``preview_generated`` alone, because a
    Docker volume may be recreated while old database rows still reference files
    that no longer exist.
    """
    # Local import avoids pulling the preview HTTP client into database module
    # initialization and keeps startup seed logic isolated.
    from backend.files.preview import preview_generator

    generated_count = 0
    fixed_metadata_count = 0
    skipped_count = 0
    failed_count = 0

    async with AsyncSessionLocal() as session:
        for file_id in DEMO_FILE_IDS:
            try:
                file_record = await session.get(FileStorage, file_id)
                if not file_record:
                    logger.info("Demo preview startup: file_id=%s is absent, skipped", file_id)
                    skipped_count += 1
                    continue

                file_record.is_demo = True

                existing_preview_path = _resolve_existing_path(file_record.preview_path)
                if existing_preview_path:
                    # If a preview file exists but flags/filename are stale, fix only DB metadata.
                    changed = False
                    if not file_record.preview_generated:
                        file_record.preview_generated = True
                        changed = True
                    if file_record.preview_path != str(existing_preview_path):
                        file_record.preview_path = str(existing_preview_path)
                        changed = True
                    if not file_record.preview_filename:
                        file_record.preview_filename = existing_preview_path.name
                        changed = True
                    if file_record.preview_generation_error:
                        file_record.preview_generation_error = None
                        changed = True

                    if changed:
                        session.add(file_record)
                        await session.commit()
                        fixed_metadata_count += 1
                        logger.info(
                            "Demo preview startup: fixed preview metadata for file_id=%s path=%s",
                            file_id,
                            existing_preview_path,
                        )
                    else:
                        skipped_count += 1
                        logger.info(
                            "Demo preview startup: preview already exists for file_id=%s path=%s",
                            file_id,
                            existing_preview_path,
                        )
                    continue

                model_path = _resolve_existing_path(file_record.file_path)
                if not model_path:
                    file_record.preview_generated = False
                    file_record.preview_generation_error = "Demo source file is not found on disk"
                    session.add(file_record)
                    await session.commit()
                    failed_count += 1
                    logger.warning(
                        "Demo preview startup: source model is not found for file_id=%s file_path=%s",
                        file_id,
                        file_record.file_path,
                    )
                    continue

                logger.info(
                    "Demo preview startup: generating missing preview for file_id=%s model_path=%s",
                    file_id,
                    model_path,
                )
                preview_data = await preview_generator.generate_preview(
                    model_path,
                    file_record.original_filename or file_record.filename,
                    fallback_to_placeholder=False,
                )

                if preview_data:
                    file_record.preview_filename = preview_data.get("preview_filename")
                    file_record.preview_path = preview_data.get("preview_path")
                    file_record.preview_generated = preview_data.get("preview_generated", False)
                    file_record.preview_generation_error = preview_data.get("preview_generation_error")
                    session.add(file_record)
                    await session.commit()

                    if file_record.preview_generated:
                        generated_count += 1
                        logger.info(
                            "Demo preview startup: preview generated for file_id=%s preview_path=%s",
                            file_id,
                            file_record.preview_path,
                        )
                    else:
                        failed_count += 1
                        logger.warning(
                            "Demo preview startup: preview generation failed for file_id=%s error=%s",
                            file_id,
                            file_record.preview_generation_error,
                        )
                else:
                    file_record.preview_generated = False
                    file_record.preview_generation_error = "Preview generator returned no data"
                    session.add(file_record)
                    await session.commit()
                    failed_count += 1
                    logger.warning(
                        "Demo preview startup: preview generator returned no data for file_id=%s",
                        file_id,
                    )

            except Exception as e:
                await session.rollback()
                failed_count += 1
                logger.warning(
                    "Demo preview startup: failed for file_id=%s: %s",
                    file_id,
                    e,
                    exc_info=True,
                )

    logger.info(
        "Demo preview startup completed: generated=%s fixed_metadata=%s skipped=%s failed=%s",
        generated_count,
        fixed_metadata_count,
        skipped_count,
        failed_count,
    )


# ---------------------------------------------------------------------------
# Location migration helpers (data backfill — not schema changes)
# ---------------------------------------------------------------------------


async def force_users_location_null():
    async with AsyncSessionLocal() as db:
        await db.execute(text("UPDATE users SET location = NULL"))
        logger.info("users location SET NULL value")
        await db.commit()

async def apply_admin_location_overrides(
        overrides: Dict[str, str],
        default_location: str = DEFAULT_LOCATION
    ):
    async with AsyncSessionLocal() as db:
        if not overrides:
            logger.info("DB migrate: no ADMIN_LOCATION_OVERRIDES_JSON provided")
        else:
            for username, location in overrides.items():
                loc = (location or "").strip()
                if not loc:
                    continue
                elif loc=='None':
                    loc=None
                await db.execute(
                    text("UPDATE users SET location = :loc WHERE username = :u"),
                    {"loc": loc, "u": username},
                )
                logger.info("DB migrate: applying admin location override for %s", username)

        logger.info("DB migrate: setting default location %s for users without location", default_location)
        await db.execute(
            text(
                """
                UPDATE users
                SET location = :default_loc
                WHERE location IS NULL OR TRIM(location) = ''
                """
            ),
            {"default_loc": default_location},
        )
        await db.commit()


# ---------------------------------------------------------------------------
# Config helper
# ---------------------------------------------------------------------------

def _env_json_dict(var_name: str) -> Dict[str, str]:
    raw = os.getenv(var_name, "").strip()
    if not raw:
        logger.info("Failed to parse %s from env", var_name)
        try:
            raw = ADMIN_LOCATION_OVERRIDES_JSON.strip()
        except Exception:
            logger.info("Failed to parse %s from config", var_name)

    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items() if v is not None}
    except Exception:
        logger.info("Failed to parse %s finally", var_name)
    return {}

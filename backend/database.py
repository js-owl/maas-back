import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, text
from backend.models import Base, User, FileStorage, utcnow
from backend.auth.service import get_password_hash
from backend.core.config import (
    ADMIN_DEFAULT_PASSWORD,
    ADMIN_EMAIL,
    ADMIN_PERSONAL_EMAIL,
    DATABASE_URL,
    UPLOAD_DIR,
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
            personal_email = ADMIN_PERSONAL_EMAIL.strip().lower()
            result = await session.execute(
                User.__table__.select().where(User.personal_email == personal_email)
            )
            if result.first() is None:
                now = utcnow()
                admin_user = User(
                    personal_email=personal_email,
                    email=ADMIN_EMAIL,
                    email_verified=True,
                    email_verified_at=now,
                    password_changed_at=now,
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
            for personal_email, location in overrides.items():
                loc = (location or "").strip()
                if not loc:
                    continue
                elif loc=='None':
                    loc=None
                await db.execute(
                    text("UPDATE users SET location = :loc WHERE personal_email = :personal_email"),
                    {"loc": loc, "personal_email": personal_email.strip().lower()},
                )
                logger.info("DB migrate: applying admin location override for %s", personal_email)

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

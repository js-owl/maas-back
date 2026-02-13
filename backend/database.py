import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, text
from backend.models import (
    Base,
    User,
    FileStorage,
    MaasBitrixIdsMapping,
    BitrixCategory,
    BitrixStatus,
    BitrixUserfield,
    BitrixUserfieldEnum,
    BitrixProductProperty,
    BitrixProductPropertyEnum,
)
from backend.auth.service import get_password_hash
from backend.core.config import ADMIN_DEFAULT_PASSWORD, ADMIN_USERNAME, DATABASE_URL, UPLOAD_DIR
from backend.utils.logging import get_logger
from backend.core.config import ADMIN_LOCATION_OVERRIDES_JSON
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

async def seed_admin():
    async with AsyncSessionLocal() as session:
        try:
            admin_username = ADMIN_USERNAME
            admin_password = ADMIN_DEFAULT_PASSWORD
            
            result = await session.execute(
                User.__table__.select().where(User.username == admin_username)
            )
            admin = result.first()
            if not admin:
                admin_user = User(
                    username=admin_username,
                    hashed_password=get_password_hash(admin_password),
                    is_admin=True,
                    must_change_password=True
                )
                session.add(admin_user)
                await session.commit()
        except Exception as e:
            await session.rollback()
            raise

# Dependency to get async DB session
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        else:
            await session.commit() 


async def ensure_order_new_columns() -> None:
    """Ensure newly added order columns exist on existing SQLite databases.
    Adds columns: length INTEGER, width INTEGER, height INTEGER, composite_rig TEXT,
    bitrix_contact_id INTEGER on users, bitrix_deal_id INTEGER on orders if missing.
    Also adds calculator result columns on orders: mat_volume REAL, detail_price REAL,
    mat_weight REAL, mat_price REAL, work_price REAL, k_quantity REAL, total_time REAL.
    """
    async with AsyncSessionLocal() as session:
        try:
            # Orders table columns
            result = await session.execute(text("PRAGMA table_info('orders')"))
            order_cols = {row[1] for row in result}
            order_alters = []
            if 'length' not in order_cols:
                order_alters.append("ALTER TABLE orders ADD COLUMN length INTEGER")
            if 'width' not in order_cols:
                order_alters.append("ALTER TABLE orders ADD COLUMN width INTEGER")
            if 'height' not in order_cols:
                order_alters.append("ALTER TABLE orders ADD COLUMN height INTEGER")
            if 'composite_rig' not in order_cols:
                order_alters.append("ALTER TABLE orders ADD COLUMN composite_rig TEXT")
            if 'bitrix_deal_id' not in order_cols:
                order_alters.append("ALTER TABLE orders ADD COLUMN bitrix_deal_id INTEGER")
            # Calculator result columns
            if 'mat_volume' not in order_cols:
                order_alters.append("ALTER TABLE orders ADD COLUMN mat_volume REAL")
            if 'detail_price' not in order_cols:
                order_alters.append("ALTER TABLE orders ADD COLUMN detail_price REAL")
            if 'mat_weight' not in order_cols:
                order_alters.append("ALTER TABLE orders ADD COLUMN mat_weight REAL")
            if 'mat_price' not in order_cols:
                order_alters.append("ALTER TABLE orders ADD COLUMN mat_price REAL")
            if 'work_price' not in order_cols:
                order_alters.append("ALTER TABLE orders ADD COLUMN work_price REAL")
            if 'k_quantity' not in order_cols:
                order_alters.append("ALTER TABLE orders ADD COLUMN k_quantity REAL")
            if 'total_time' not in order_cols:
                order_alters.append("ALTER TABLE orders ADD COLUMN total_time REAL")
            # New identifier columns (strings) replacing k_*
            if 'tolerance_id' not in order_cols:
                order_alters.append("ALTER TABLE orders ADD COLUMN tolerance_id TEXT")
            if 'finish_id' not in order_cols:
                order_alters.append("ALTER TABLE orders ADD COLUMN finish_id TEXT")
            if 'id_cover' not in order_cols:
                order_alters.append("ALTER TABLE orders ADD COLUMN id_cover TEXT")
            if 'thickness' not in order_cols:
                order_alters.append("ALTER TABLE orders ADD COLUMN thickness INTEGER")
            if 'dia' not in order_cols:
                order_alters.append("ALTER TABLE orders ADD COLUMN dia INTEGER")
            if 'k_cert' not in order_cols:
                order_alters.append("ALTER TABLE orders ADD COLUMN k_cert TEXT")
            if 'detail_time' not in order_cols:
                order_alters.append("ALTER TABLE orders ADD COLUMN detail_time REAL")
            if 'total_price_breakdown' not in order_cols:
                order_alters.append("ALTER TABLE orders ADD COLUMN total_price_breakdown TEXT")
            if 'invoice_ids' not in order_cols:
                order_alters.append("ALTER TABLE orders ADD COLUMN invoice_ids TEXT")
            if 'location' not in order_cols:
                order_alters.append("ALTER TABLE orders ADD COLUMN location TEXT")
            if 'order_name' not in order_cols:
                order_alters.append(text("ALTER TABLE orders ADD COLUMN order_name TEXT"))
            if 'order_code' not in order_cols:
                order_alters.append(text("ALTER TABLE orders ADD COLUMN order_code TEXT"))
            if 'kit_id' not in order_cols:
                order_alters.append("ALTER TABLE orders ADD COLUMN kit_id INTEGER")
            if 'location' not in order_cols:
                order_alters.append("ALTER TABLE orders ADD COLUMN location TEXT")
            if 'order_name' not in order_cols:
                order_alters.append(text("ALTER TABLE orders ADD COLUMN order_name TEXT"))
            if 'order_code' not in order_cols:
                order_alters.append(text("ALTER TABLE orders ADD COLUMN order_code TEXT"))
            if 'kit_id' not in order_cols:
                order_alters.append("ALTER TABLE orders ADD COLUMN kit_id INTEGER")
            for stmt in order_alters:
                if isinstance(stmt, str):
                    await session.execute(text(stmt))
                else:
                    await session.execute(stmt)
            if order_alters:
                await session.commit()
                # Backfill newly added identifier columns to "1" for consistency
                try:
                    await session.execute("UPDATE orders SET tolerance_id = '1' WHERE tolerance_id IS NULL")
                    await session.execute("UPDATE orders SET finish_id = '1' WHERE finish_id IS NULL")
                    await session.execute("UPDATE orders SET id_cover = '1' WHERE id_cover IS NULL")
                    await session.commit()
                except Exception:
                    await session.rollback()
            
            # Migration: Convert id_cover from string to JSON array
            try:
                # Check if id_cover column exists and has string values that need conversion
                result = await session.execute("SELECT COUNT(*) FROM orders WHERE id_cover IS NOT NULL AND id_cover NOT LIKE '[%'")
                count = result.scalar()
                if count > 0:
                    # Convert string values to JSON arrays
                    await session.execute("UPDATE orders SET id_cover = '[\"' || id_cover || '\"]' WHERE id_cover IS NOT NULL AND id_cover NOT LIKE '[%'")
                    await session.commit()
            except Exception as e:
                await session.rollback()
            
            # Orders table: make dimensions column nullable
            try:
                result = await session.execute("PRAGMA table_info('orders')")
                order_cols = {row[1] for row in result}
                if 'dimensions' in order_cols:
                    # Check if dimensions column is nullable
                    result = await session.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='orders'")
                    table_sql = result.scalar()
                    if table_sql and 'dimensions' in table_sql and 'NOT NULL' in table_sql:
                        # Make dimensions nullable by recreating the table
                        # This is a complex operation for SQLite, so we'll handle it gracefully
                        # For now, we'll just continue
                        pass
            except Exception as e:
                pass

            # is_demo is now managed via Alembic migration
        except Exception:
            # Best-effort; avoid blocking startup if this fails
            await session.rollback()


async def ensure_invoices_table() -> None:
    """Ensure invoices table exists and has all required columns"""
    async with AsyncSessionLocal() as session:
        try:
            # Check if invoices table exists
            result = await session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='invoices'"))
            table_exists = result.first() is not None
            
            if not table_exists:
                # Create invoices table using SQLAlchemy metadata
                from backend.models import InvoiceStorage
                async with engine.begin() as conn:
                    await conn.run_sync(InvoiceStorage.__table__.create)
                logger.info("Created invoices table")
            else:
                # Check if all columns exist
                result = await session.execute(text("PRAGMA table_info('invoices')"))
                invoice_cols = {row[1] for row in result}
                invoice_alters = []
                
                required_columns = {
                    'id': 'INTEGER PRIMARY KEY',
                    'filename': 'VARCHAR',
                    'original_filename': 'VARCHAR',
                    'file_path': 'VARCHAR',
                    'file_size': 'INTEGER',
                    'file_type': 'VARCHAR',
                    'order_id': 'INTEGER',
                    'bitrix_document_id': 'INTEGER',
                    'generated_at': 'DATETIME',
                    'created_at': 'DATETIME',
                    'updated_at': 'DATETIME'
                }
                
                for col_name, col_type in required_columns.items():
                    if col_name not in invoice_cols:
                        if col_name == 'id':
                            continue  # Skip primary key
                        alter_stmt = f"ALTER TABLE invoices ADD COLUMN {col_name} {col_type}"
                        if col_name == 'order_id':
                            alter_stmt += " NOT NULL"
                        invoice_alters.append(alter_stmt)
                
                for stmt in invoice_alters:
                    await session.execute(text(stmt))
                
                if invoice_alters:
                    await session.commit()
                    logger.info(f"Added {len(invoice_alters)} columns to invoices table")
        except Exception as e:
            await session.rollback()
            logger.error(f"Error ensuring invoices table: {e}", exc_info=True)


async def ensure_demo_files() -> None:
    """Ensure demo sample files exist in files table with fixed IDs and is_demo flag.
    Maps IDs 1-5 (excluding 4 for samples) and ID 4 to specific demo files.
    IDs 1, 2, 4 use STP files, IDs 3, 5 use STL files.
    """
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
                uploader_id = row[0].id
            else:
                # Fallback to any user
                result = await session.execute(User.__table__.select())
                row = result.first()
                uploader_id = (row[0].id if row and len(row) > 0 else None)

            now = datetime.now(timezone.utc)

            async def upsert_demo(id_value: int, filename: str) -> None:
                file_path = models_dir / filename
                # If file is the special one and not in uploads yet, copy from project root
                if filename == special_filename and not file_path.exists():
                    root_candidate = Path('.') / filename
                    if root_candidate.exists():
                        shutil.copyfile(str(root_candidate), str(file_path))
                # Skip if file doesn't exist
                if not file_path.exists():
                    return
                # Gather stats
                stat = file_path.stat()
                file_size = stat.st_size
                file_ext = file_path.suffix.lower()
                # Fetch existing by id
                existing = await session.get(FileStorage, id_value)
                if existing:
                    # Update fields and mark demo
                    existing.filename = filename
                    existing.original_filename = filename
                    existing.file_path = str(file_path)
                    existing.file_size = file_size
                    existing.file_type = file_ext
                    if uploader_id is not None:
                        existing.uploaded_by = uploader_id
                    existing.is_demo = True
                    existing.file_metadata = json.dumps({
                        "file_size": file_size,
                        "source": "demo_seed",
                    })
                    session.add(existing)
                else:
                    # Create new with explicit id
                    new_file = FileStorage(
                        id=id_value,
                        filename=filename,
                        original_filename=filename,
                        file_path=str(file_path),
                        file_size=file_size,
                        file_type=file_ext,
                        uploaded_by=(uploader_id or 0),
                        uploaded_at=now,
                        file_metadata=json.dumps({
                            "file_size": file_size,
                            "source": "demo_seed",
                        }),
                        is_demo=True,
                    )
                    session.add(new_file)
                await session.commit()

            # Upsert normal demo samples (1,2,3,5)
            for id_value, fname in demo_mapping:
                await upsert_demo(id_value, fname)
            # Upsert special id 4
            await upsert_demo(special_id, special_filename)
        except Exception:
            await session.rollback()

async def ensure_kits_table() -> None:
    """Ensure kits table exists and has required columns (SQLite friendly)."""
    async with AsyncSessionLocal() as session:
        try:
            # Check if kits table exists
            result = await session.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name='kits'")
            )
            table_exists = result.first() is not None

            if not table_exists:
                from backend.models import Kit
                async with engine.begin() as conn:
                    await conn.run_sync(Kit.__table__.create)
                logger.info("Created kits table")
                return

            # If exists — ensure columns (future-proof pattern)
            result = await session.execute(text("PRAGMA table_info('kits')"))
            cols = {row[1] for row in result}
            alters = []

            required = {
                "order_ids": "TEXT",
                "user_id": "INTEGER",
                "kit_name": "VARCHAR",
                "quantity": "INTEGER",
                "kit_price": "REAL",
                "delivery_price": "REAL",
                "status": "VARCHAR",
                "created_at": "DATETIME",
                "updated_at": "DATETIME",
                "bitrix_deal_id": "INTEGER",
                "location": "TEXT",
            }

            for col_name, col_type in required.items():
                if col_name not in cols:
                    alters.append(f"ALTER TABLE kits ADD COLUMN {col_name} {col_type}")

            for stmt in alters:
                await session.execute(text(stmt))

            if alters:
                await session.commit()
                logger.info(f"Added {len(alters)} columns to kits table")
        except Exception as e:
            await session.rollback()
            logger.error(f"Error ensuring kits table: {e}", exc_info=True)

async def ensure_users_new_columns() -> None:
    """Ensure users table exists and has required columns (SQLite friendly)."""
    async with AsyncSessionLocal() as session:
        try:
            # ensure columns
            result = await session.execute(text("PRAGMA table_info('users')"))
            cols = {row[1] for row in result}
            alters = []

            required = {
                "bitrix_contact_id": "INTEGER",
                "created_at": "DATETIME",
                "updated_at": "DATETIME",
                "personal_phone_number": "VARCHAR",
            }

            for col_name, col_type in required.items():
                if col_name not in cols:
                    alters.append(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")

            for stmt in alters:
                await session.execute(text(stmt))

            if alters:
                await session.commit()
                logger.info(f"Added {len(alters)} columns to users table")
                # Backfill timestamp columns for existing users
                try:
                    now = datetime.now(timezone.utc)
                    await session.execute("UPDATE users SET created_at = ? WHERE created_at IS NULL", (now,))
                    await session.execute("UPDATE users SET updated_at = ? WHERE updated_at IS NULL", (now,))
                    await session.commit()
                except Exception:
                    await session.rollback()
        except Exception as e:
            await session.rollback()
            logger.error(f"Error ensuring users table: {e}", exc_info=True)

def _env_json_dict(var_name: str) -> Dict[str, str]:
    raw = os.getenv(var_name, "").strip()
    if not raw:
        logger.info(f"Failed to parse {var_name} from env")
        try: 
            raw = ADMIN_LOCATION_OVERRIDES_JSON.strip()
        except:
            logger.info(f"Failed to parse {var_name} from config")

    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items() if v is not None}
    except Exception:
        logger.info(f"Failed to parse {var_name} finally")
    return {}


async def ensure_users_location_column():
    async with AsyncSessionLocal() as db:
        cols = await db.execute(text("PRAGMA table_info(users)"))
        colnames = {row[1] for row in cols.fetchall()}  # row: (cid, name, type, notnull, dflt_value, pk)
        if "location" not in colnames:
            logger.info("DB migrate: adding users.location column")
            await db.execute(text("ALTER TABLE users ADD COLUMN location TEXT"))
            await db.commit()

async def backfill_users_location_from_kits():
    async with AsyncSessionLocal() as db:
        # Берём последнее известное значение location по китам пользователя
        # updated_at/created_at в kits есть :contentReference[oaicite:15]{index=15}
        logger.info("DB migrate: backfilling users.location from kits.location")
        await db.execute(text("""
            UPDATE users
            SET location = (
                SELECT k.location
                FROM kits k
                WHERE k.user_id = users.id
                AND k.location IS NOT NULL AND TRIM(k.location) <> ''
                ORDER BY COALESCE(k.updated_at, k.created_at) DESC
                LIMIT 1
            )
            WHERE (location IS NULL OR TRIM(location) = '')
            AND EXISTS (
                SELECT 1 FROM kits k2
                WHERE k2.user_id = users.id
                AND k2.location IS NOT NULL AND TRIM(k2.location) <> ''
            )
        """))
        await db.commit()


async def apply_admin_location_overrides(
        overrides: Dict[str, str],
        default_location: str = "location_1"
    ):
    async with AsyncSessionLocal() as db:
        if not overrides:
            logger.info("DB migrate: no ADMIN_LOCATION_OVERRIDES_JSON provided")
        else:
            for username, location in overrides.items():
                loc = (location or "").strip()
                if not loc:
                    continue
                await db.execute(
                    text("UPDATE users SET location = :loc WHERE username = :u"),
                    {"loc": loc, "u": username}
                )
                logger.info(f"DB migrate: applying admin location overrides by {username}")

        logger.info(f"DB migrate: setting default location {default_location} for users without location")
        await db.execute(
            text(
                """
                UPDATE users
                SET location = :default_loc
                WHERE location IS NULL OR TRIM(location) = ''
                """
            ),
            {"default_loc": default_location}
        )
        await db.commit()

async def ensure_maas_bitrix_ids_mapping_table() -> None:
    """Ensure maas_bitrix_ids_mapping table exists and has all required columns"""
    async with AsyncSessionLocal() as session:
        try:
            # Check if table exists
            result = await session.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name='maas_bitrix_ids_mapping'")
            )
            table_exists = result.first() is not None
            
            if not table_exists:
                # Create table using SQLAlchemy metadata
                async with engine.begin() as conn:
                    await conn.run_sync(MaasBitrixIdsMapping.__table__.create)
                logger.info("Created maas_bitrix_ids_mapping table")
            else:
                # Check if all columns exist
                result = await session.execute(text("PRAGMA table_info('maas_bitrix_ids_mapping')"))
                mapping_cols = {row[1] for row in result}
                mapping_alters = []
                
                required_columns = {
                    'id': 'INTEGER PRIMARY KEY',
                    'maas_id': 'INTEGER NOT NULL',
                    'bitrix_id': 'INTEGER NOT NULL',
                    'entity_type': 'VARCHAR(32) NOT NULL',
                    'buffer': 'JSON',
                    'created_at': 'DATETIME',
                    'updated_at': 'DATETIME'
                }
                
                for col_name, col_type in required_columns.items():
                    if col_name not in mapping_cols:
                        if col_name == 'id':
                            continue  # Skip primary key
                        alter_stmt = f"ALTER TABLE maas_bitrix_ids_mapping ADD COLUMN {col_name} {col_type}"
                        mapping_alters.append(alter_stmt)
                
                for stmt in mapping_alters:
                    await session.execute(text(stmt))
                
                if mapping_alters:
                    await session.commit()
                    logger.info(f"Added {len(mapping_alters)} columns to maas_bitrix_ids_mapping table")
        except Exception as e:
            await session.rollback()
            logger.error(f"Error ensuring maas_bitrix_ids_mapping table: {e}", exc_info=True)


async def ensure_constant_entity_tables() -> None:
    """Ensure Bitrix24 constant-entity source-of-truth tables exist (bitrix_category, bitrix_status, bitrix_userfield, bitrix_userfield_enum, bitrix_product_property, bitrix_product_property_enum)."""
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name='bitrix_category'")
            )
            if result.first() is not None:
                return
            async with engine.begin() as conn:
                await conn.run_sync(BitrixCategory.__table__.create)
                await conn.run_sync(BitrixStatus.__table__.create)
                await conn.run_sync(BitrixUserfield.__table__.create)
                await conn.run_sync(BitrixUserfieldEnum.__table__.create)
                await conn.run_sync(BitrixProductProperty.__table__.create)
                await conn.run_sync(BitrixProductPropertyEnum.__table__.create)
            logger.info("Created constant-entity tables: bitrix_category, bitrix_status, bitrix_userfield, bitrix_userfield_enum, bitrix_product_property, bitrix_product_property_enum")
        except Exception as e:
            await session.rollback()
            logger.error(f"Error ensuring constant-entity tables: {e}", exc_info=True)

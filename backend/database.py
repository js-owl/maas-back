from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, text
from backend.models import Base, User, FileStorage
from backend.auth.service import get_password_hash
import asyncio
import os
from pathlib import Path
import shutil
from datetime import datetime, timezone
import json

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/shop.db")

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL, echo=False, future=True
)

AsyncSessionLocal = sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False, autocommit=False
)

async def seed_admin():
    async with AsyncSessionLocal() as session:
        try:
            admin_username = os.getenv("ADMIN_USERNAME", "admin")
            admin_password = os.getenv("ADMIN_DEFAULT_PASSWORD", "admin")
            
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
                order_alters.append(text("ALTER TABLE orders ADD COLUMN total_price_breakdown TEXT"))
            for stmt in order_alters:
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

            # Users table columns
            result = await session.execute("PRAGMA table_info('users')")
            user_cols = {row[1] for row in result}
            user_alters = []
            if 'bitrix_contact_id' not in user_cols:
                user_alters.append("ALTER TABLE users ADD COLUMN bitrix_contact_id INTEGER")
            if 'created_at' not in user_cols:
                user_alters.append("ALTER TABLE users ADD COLUMN created_at DATETIME")
            if 'updated_at' not in user_cols:
                user_alters.append("ALTER TABLE users ADD COLUMN updated_at DATETIME")
            for stmt in user_alters:
                await session.execute(stmt)
            if user_alters:
                await session.commit()
                # Backfill timestamp columns for existing users
                try:
                    now = datetime.now(timezone.utc)
                    await session.execute("UPDATE users SET created_at = ? WHERE created_at IS NULL", (now,))
                    await session.execute("UPDATE users SET updated_at = ? WHERE updated_at IS NULL", (now,))
                    await session.commit()
                except Exception:
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
    models_dir = Path(os.getenv("UPLOAD_DIR", "uploads/3d_models"))
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
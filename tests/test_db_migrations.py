"""
DB migration & persistence tests

Goal:
- Validate that ensure_* migrations correctly upgrade an "old" SQLite schema.
- Validate idempotency (running migrations twice is safe).
- Validate that kits/orders can be persisted after migrations.

Run via scripts/run_all_tests.py
"""

import asyncio
import os
import tempfile
from pathlib import Path
import importlib
from sqlalchemy import text


class DatabaseMigrationsTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        # base_url is unused; kept for compatibility with runner signature
        self.base_url = base_url
        self.tmp_dir = None
        self.db_path = None
        self.db_url = None

        self.db_mod = None  # backend.database (reloaded with env DATABASE_URL)
        self.models_mod = None  # backend.models

    async def __aenter__(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_shop.db"
        self.db_url = f"sqlite+aiosqlite:///{self.db_path}"

        # IMPORTANT: set DATABASE_URL before importing backend.database
        os.environ["DATABASE_URL"] = self.db_url

        # Reload modules to ensure engine/session use this temp DB
        import backend.models as models_mod
        import backend.database as db_mod
        self.models_mod = importlib.reload(models_mod)
        self.db_mod = importlib.reload(db_mod)

        return self

    async def __aexit__(self, exc_type, exc, tb):
        try:
            if self.db_mod and getattr(self.db_mod, "engine", None):
                await self.db_mod.engine.dispose()
        finally:
            if self.tmp_dir:
                self.tmp_dir.cleanup()

    async def _exec(self, sql: str, params: dict | None = None):
        async with self.db_mod.AsyncSessionLocal() as session:
            await session.execute(text(sql), params or {})
            await session.commit()

    async def _fetchall(self, sql: str, params: dict | None = None):
        async with self.db_mod.AsyncSessionLocal() as session:
            res = await session.execute(text(sql), params or {})
            return res.fetchall()

    async def _create_old_schema(self):
        """
        Create a deliberately "old" schema:
        - users table exists but minimal
        - orders table exists but WITHOUT kit_id and WITHOUT many new columns
        - kits table does NOT exist
        """
        await self._exec("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE,
                hashed_password TEXT,
                is_admin BOOLEAN DEFAULT 0
            )
        """)
        await self._exec("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id INTEGER PRIMARY KEY,
                user_id INTEGER,
                service_id TEXT,
                file_id INTEGER,
                status TEXT
            )
        """)
        # files table minimal (some flows need it; migrations shouldn't depend on it)
        await self._exec("""
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY,
                filename TEXT,
                original_filename TEXT,
                file_path TEXT
            )
        """)

    async def _assert_table_has_columns(self, table: str, expected_cols: set[str]):
        rows = await self._fetchall(f"PRAGMA table_info('{table}')")
        got = {r[1] for r in rows}
        missing = expected_cols - got
        assert not missing, f"Table '{table}' missing columns: {sorted(missing)}; got={sorted(got)}"

    async def test_migrations_upgrade_old_schema(self):
        print(" Testing DB: migrations upgrade old schema.")
        await self._create_old_schema()

        # Run migrations
        await self.db_mod.ensure_order_new_columns()
        await self.db_mod.ensure_kits_table()

        # Assert kits table exists and key columns exist
        await self._assert_table_has_columns("kits", {
            "kit_id",
            "order_ids",
            "user_id",
            "kit_name",
            "quantity",
            "status",
            "created_at",
            "updated_at",
            "bitrix_deal_id",
            "location",
        })

        # Assert orders got kit_id at least (plus others are ok if present)
        await self._assert_table_has_columns("orders", {"kit_id"})

        print(" DB upgrade path passed")

    async def test_migrations_idempotent(self):
        print(" Testing DB: migrations are idempotent.")
        await self._create_old_schema()

        # Run twice: should not crash
        await self.db_mod.ensure_order_new_columns()
        await self.db_mod.ensure_kits_table()
        await self.db_mod.ensure_order_new_columns()
        await self.db_mod.ensure_kits_table()

        # Still valid
        await self._assert_table_has_columns("orders", {"kit_id"})
        await self._assert_table_has_columns("kits", {"kit_id", "order_ids", "user_id"})
        print(" DB idempotency passed")

    async def test_persistence_kits_and_orders(self):
        print(" Testing DB: persistence of kits and orders after migrations.")
        await self._create_old_schema()
        await self.db_mod.ensure_order_new_columns()
        await self.db_mod.ensure_kits_table()

        # Insert user
        await self._exec("""
            INSERT INTO users (id, username, hashed_password, is_admin)
            VALUES (1001, 'db_test_user', 'hash', 0)
        """)

        # Insert kit
        await self._exec("""
            INSERT INTO kits (kit_id, order_ids, user_id, kit_name, quantity, status, location)
            VALUES (2001, '[]', 1001, 'kit-db', 2, 'NEW', 'test')
        """)

        # Insert order with kit_id (simulate app behavior)
        await self._exec("""
            INSERT INTO orders (order_id, user_id, service_id, file_id, status, kit_id)
            VALUES (3001, 1001, 'cnc-milling', 1, 'NEW', 2001)
        """)

        # Update kit.order_ids to include order
        await self._exec("""
            UPDATE kits SET order_ids='[3001]' WHERE kit_id=2001
        """)

        # Verify readback
        rows = await self._fetchall("SELECT order_ids, user_id, kit_name, quantity FROM kits WHERE kit_id=2001")
        assert rows, "Kit not found after insert"
        order_ids, user_id, kit_name, qty = rows[0]
        assert order_ids == "[3001]"
        assert user_id == 1001
        assert kit_name == "kit-db"
        assert qty == 2

        # Verify order links to kit_id
        rows = await self._fetchall("SELECT kit_id FROM orders WHERE order_id=3001")
        assert rows and rows[0][0] == 2001, f"Order.kit_id not persisted correctly: {rows}"

        print(" DB persistence passed")

    async def run_all_tests(self):
        print(" Starting DB migration & persistence tests.\n")
        await self.test_migrations_upgrade_old_schema()
        print()
        await self.test_migrations_idempotent()
        print()
        await self.test_persistence_kits_and_orders()
        print()
        print(" All DB migration tests completed successfully!")


async def main():
    async with DatabaseMigrationsTester() as tester:
        await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())

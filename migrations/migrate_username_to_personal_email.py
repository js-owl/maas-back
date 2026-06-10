"""
One-time PostgreSQL migration for the user identity model:

- Adds email verification columns from the superseded email verification migration.
- Adds password_changed_at and backfills it from updated_at/created_at.
- Adds unique personal_email and backfills it from the existing email where possible.
- Keeps email nullable and non-unique as the company email field.
- Drops username and its related indexes/constraints.

Run from repo root (DATABASE_URL must point at the target database):

    python migrations/migrate_username_to_personal_email.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from backend.database import engine


async def migrate() -> None:
    async with engine.begin() as conn:
        # --- Email verification / password timestamp columns (idempotent) ---
        await conn.execute(
            text(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS "
                "email_verified BOOLEAN NOT NULL DEFAULT FALSE"
            )
        )
        await conn.execute(
            text(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS "
                "email_verified_at TIMESTAMP WITHOUT TIME ZONE"
            )
        )
        await conn.execute(
            text(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS "
                "password_changed_at TIMESTAMP WITHOUT TIME ZONE"
            )
        )

        await conn.execute(
            text("UPDATE users SET email_verified = FALSE WHERE email_verified IS NULL")
        )
        await conn.execute(
            text("ALTER TABLE users ALTER COLUMN email_verified SET NOT NULL")
        )
        await conn.execute(
            text("ALTER TABLE users ALTER COLUMN email_verified SET DEFAULT FALSE")
        )

        await conn.execute(
            text(
                """
                UPDATE users
                SET password_changed_at = COALESCE(updated_at, created_at, NOW())
                WHERE password_changed_at IS NULL
                """
            )
        )

        # --- Account identity migration ---
        await conn.execute(
            text("ALTER TABLE users ADD COLUMN IF NOT EXISTS personal_email VARCHAR")
        )

        await conn.execute(
            text(
                """
                UPDATE users
                SET personal_email = lower(trim(email))
                WHERE (personal_email IS NULL OR trim(personal_email) = '')
                  AND email IS NOT NULL
                  AND trim(email) <> ''
                """
            )
        )

        await conn.execute(
            text(
                """
                UPDATE users
                SET personal_email = 'migration-personal-' || id::text || '@invalid.local'
                WHERE personal_email IS NULL OR trim(personal_email) = ''
                """
            )
        )

        # If company email values were duplicated before this migration, keep the first
        # personal_email and synthesize deterministic unique identities for the rest.
        await conn.execute(
            text(
                """
                UPDATE users AS u
                SET personal_email = 'migration-personal-' || u.id::text || '@invalid.local'
                FROM (
                    SELECT id,
                           ROW_NUMBER() OVER (
                               PARTITION BY lower(trim(personal_email))
                               ORDER BY id
                           ) AS rn
                    FROM users
                    WHERE personal_email IS NOT NULL AND trim(personal_email) <> ''
                ) AS d
                WHERE u.id = d.id AND d.rn > 1
                """
            )
        )

        await conn.execute(
            text("UPDATE users SET personal_email = lower(trim(personal_email))")
        )
        await conn.execute(text("ALTER TABLE users ALTER COLUMN personal_email SET NOT NULL"))
        await conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS "
                "uq_users_personal_email ON users (personal_email)"
            )
        )

        await conn.execute(text("DROP INDEX IF EXISTS uq_users_email"))
        await conn.execute(text("DROP INDEX IF EXISTS ix_users_email"))
        await conn.execute(
            text(
                """
                ALTER TABLE users
                DROP CONSTRAINT IF EXISTS users_email_key
                """
            )
        )
        await conn.execute(text("ALTER TABLE users ALTER COLUMN email DROP NOT NULL"))

        await conn.execute(text("DROP INDEX IF EXISTS ix_users_username"))
        await conn.execute(
            text(
                """
                ALTER TABLE users
                DROP CONSTRAINT IF EXISTS users_username_key
                """
            )
        )
        await conn.execute(text("ALTER TABLE users DROP COLUMN IF EXISTS username"))

    print("Migration migrate_username_to_personal_email completed successfully.")


def main() -> None:
    asyncio.run(migrate())


if __name__ == "__main__":
    main()

# pgAdmin pre-config for local Docker

- **servers.json** – Pre-loads the "Postgres (local)" server so it appears in pgAdmin on first open.
- **pgpass** – Supplies the Postgres password so you don't have to type it (format: `host:port:database:user:password`).

If you override `POSTGRES_PASSWORD` (or `POSTGRES_USER`) in `.env.local` or the compose env, update **pgpass** to use the same password (and user), otherwise pgAdmin will prompt for it when connecting.

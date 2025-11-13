# PostgreSQL Migration Guide

This guide provides step-by-step instructions for migrating the Manufacturing Service Backend from SQLite to PostgreSQL.

## 🎯 Overview

The migration from SQLite to PostgreSQL will provide:
- **Better Concurrency** - Multiple simultaneous database connections
- **Improved Performance** - Advanced query optimization and indexing
- **Production Readiness** - Enterprise-grade database features
- **Scalability** - Support for larger datasets and higher loads
- **Advanced Features** - Full-text search, JSON support, and more

## 📋 Prerequisites

### Required Software

1. **PostgreSQL 13+**
   ```bash
   # Ubuntu/Debian
   sudo apt update
   sudo apt install postgresql postgresql-contrib
   
   # CentOS/RHEL
   sudo yum install postgresql-server postgresql-contrib
   
   # macOS (Homebrew)
   brew install postgresql
   
   # Windows
   # Download from https://www.postgresql.org/download/windows/
   ```

2. **pgAdmin (Optional)**
   ```bash
   # Download from https://www.pgadmin.org/download/
   ```

3. **Python Dependencies**
   ```bash
   pip install psycopg2-binary alembic
   ```

### Database Setup

1. **Create PostgreSQL Database**
   ```sql
   -- Connect to PostgreSQL as superuser
   sudo -u postgres psql
   
   -- Create database and user
   CREATE DATABASE maas_backend;
   CREATE USER maas_user WITH PASSWORD 'your_secure_password';
   GRANT ALL PRIVILEGES ON DATABASE maas_backend TO maas_user;
   
   -- Exit PostgreSQL
   \q
   ```

2. **Test Connection**
   ```bash
   psql -h localhost -U maas_user -d maas_backend
   ```

## 🔧 Migration Steps

### Step 1: Update Dependencies

1. **Update requirements.txt**
   ```txt
   # Database & ORM
   sqlalchemy==2.0.23
   alembic==1.12.1
   psycopg2-binary==2.9.9
   asyncpg==0.29.0
   
   # Remove SQLite-specific dependencies
   # aiosqlite==0.19.0  # Remove this line
   ```

2. **Install New Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

### Step 2: Configure Alembic

1. **Initialize Alembic**
   ```bash
   alembic init alembic
   ```

2. **Update alembic.ini**
   ```ini
   # Replace the sqlalchemy.url line with:
   sqlalchemy.url = postgresql+asyncpg://maas_user:your_secure_password@localhost/maas_backend
   ```

3. **Update alembic/env.py**
   ```python
   import os
   from sqlalchemy import engine_from_config, pool
   from sqlalchemy.ext.asyncio import AsyncEngine
   from alembic import context
   from backend.models import Base
   from backend.core.config import settings
   
   # Set the SQLAlchemy URL from environment
   config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
   
   # Target metadata
   target_metadata = Base.metadata
   
   def run_migrations_online():
       """Run migrations in 'online' mode."""
       connectable = engine_from_config(
           config.get_section(config.config_ini_section),
           prefix="sqlalchemy.",
           poolclass=pool.NullPool,
       )
       
       with connectable.connect() as connection:
           context.configure(
               connection=connection,
               target_metadata=target_metadata
           )
           
           with context.begin_transaction():
               context.run_migrations()
   
   run_migrations_online()
   ```

### Step 3: Update Database Configuration

1. **Update backend/core/config.py**
   ```python
   from pydantic_settings import BaseSettings
   
   class Settings(BaseSettings):
       # Database configuration
       DATABASE_URL: str = "postgresql+asyncpg://maas_user:your_secure_password@localhost/maas_backend"
       
       # ... other settings
   
   settings = Settings()
   ```

2. **Update backend/database.py**
   ```python
   from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
   from backend.core.config import settings
   
   # Create async engine
   engine = create_async_engine(
       settings.DATABASE_URL,
       echo=True,  # Set to False in production
       future=True
   )
   
   # Create async session factory
   async_session = async_sessionmaker(
       engine,
       class_=AsyncSession,
       expire_on_commit=False
   )
   
   async def get_db() -> AsyncSession:
       async with async_session() as session:
           yield session
   ```

### Step 4: Create Initial Migration

1. **Generate Initial Migration**
   ```bash
   alembic revision --autogenerate -m "Initial migration"
   ```

2. **Review Generated Migration**
   ```bash
   # Check the generated migration file in alembic/versions/
   cat alembic/versions/XXXX_initial_migration.py
   ```

3. **Apply Migration**
   ```bash
   alembic upgrade head
   ```

### Step 5: Data Migration

1. **Create Data Migration Script**
   ```python
   # scripts/migrate_data.py
   import asyncio
   import sqlite3
   import asyncpg
   from backend.core.config import settings
   
   async def migrate_data():
       # Connect to SQLite
       sqlite_conn = sqlite3.connect('data/shop.db')
       sqlite_cursor = sqlite_conn.cursor()
       
       # Connect to PostgreSQL
       pg_conn = await asyncpg.connect(settings.DATABASE_URL)
       
       try:
           # Migrate users
           sqlite_cursor.execute("SELECT * FROM users")
           users = sqlite_cursor.fetchall()
           
           for user in users:
               await pg_conn.execute("""
                   INSERT INTO users (id, username, email, hashed_password, is_admin, user_type, created_at, updated_at)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                   ON CONFLICT (id) DO NOTHING
               """, *user)
           
           # Migrate files
           sqlite_cursor.execute("SELECT * FROM files")
           files = sqlite_cursor.fetchall()
           
           for file in files:
               await pg_conn.execute("""
                   INSERT INTO files (id, filename, file_path, file_type, file_size, uploaded_by, created_at, updated_at)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                   ON CONFLICT (id) DO NOTHING
               """, *file)
           
           # Migrate orders
           sqlite_cursor.execute("SELECT * FROM orders")
           orders = sqlite_cursor.fetchall()
           
           for order in orders:
               await pg_conn.execute("""
                   INSERT INTO orders (order_id, user_id, service_id, material_id, material_form, quantity, 
                                     length, width, height, thickness, dia, n_dimensions, file_id, 
                                     cover_id, tolerance_id, finish_id, k_otk, k_cert, total_price, 
                                     status, created_at, updated_at, bitrix_contact_id, bitrix_deal_id)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24)
                   ON CONFLICT (order_id) DO NOTHING
               """, *order)
           
           # Migrate other tables...
           
           print("Data migration completed successfully!")
           
       finally:
           sqlite_conn.close()
           await pg_conn.close()
   
   if __name__ == "__main__":
       asyncio.run(migrate_data())
   ```

2. **Run Data Migration**
   ```bash
   python scripts/migrate_data.py
   ```

### Step 6: Update Environment Variables

1. **Update .env file**
   ```env
   # Database
   DATABASE_URL=postgresql+asyncpg://maas_user:your_secure_password@localhost/maas_backend
   
   # Other settings remain the same
   SECRET_KEY=your-secret-key-here
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   CALCULATOR_SERVICE_URL=http://localhost:7000
   ```

2. **Update Docker Compose (if using)**
   ```yaml
   services:
     backend:
       environment:
         - DATABASE_URL=postgresql+asyncpg://maas_user:your_secure_password@postgres:5432/maas_backend
     
     postgres:
       image: postgres:15
       environment:
         - POSTGRES_DB=maas_backend
         - POSTGRES_USER=maas_user
         - POSTGRES_PASSWORD=your_secure_password
       volumes:
         - postgres_data:/var/lib/postgresql/data
       ports:
         - "5432:5432"
   
   volumes:
     postgres_data:
   ```

### Step 7: Testing

1. **Run Tests**
   ```bash
   python scripts/run_all_tests.py
   ```

2. **Verify Data Integrity**
   ```python
   # scripts/verify_migration.py
   import asyncio
   import asyncpg
   from backend.core.config import settings
   
   async def verify_migration():
       conn = await asyncpg.connect(settings.DATABASE_URL)
       
       try:
           # Check user count
           user_count = await conn.fetchval("SELECT COUNT(*) FROM users")
           print(f"Users migrated: {user_count}")
           
           # Check file count
           file_count = await conn.fetchval("SELECT COUNT(*) FROM files")
           print(f"Files migrated: {file_count}")
           
           # Check order count
           order_count = await conn.fetchval("SELECT COUNT(*) FROM orders")
           print(f"Orders migrated: {order_count}")
           
           # Verify relationships
           orders_with_files = await conn.fetchval("""
               SELECT COUNT(*) FROM orders o 
               JOIN files f ON o.file_id = f.id
           """)
           print(f"Orders with files: {orders_with_files}")
           
       finally:
           await conn.close()
   
   if __name__ == "__main__":
       asyncio.run(verify_migration())
   ```

## 🚀 Production Deployment

### Performance Optimization

1. **Connection Pooling**
   ```python
   # backend/database.py
   engine = create_async_engine(
       settings.DATABASE_URL,
       pool_size=20,
       max_overflow=30,
       pool_pre_ping=True,
       pool_recycle=3600
   )
   ```

2. **Indexing Strategy**
   ```sql
   -- Create indexes for common queries
   CREATE INDEX idx_users_username ON users(username);
   CREATE INDEX idx_users_email ON users(email);
   CREATE INDEX idx_orders_user_id ON orders(user_id);
   CREATE INDEX idx_orders_status ON orders(status);
   CREATE INDEX idx_files_uploaded_by ON files(uploaded_by);
   CREATE INDEX idx_bitrix_sync_queue_status ON bitrix_sync_queue(status);
   ```

3. **Query Optimization**
   ```python
   # Use select_related for foreign keys
   result = await session.execute(
       select(Order)
       .options(selectinload(Order.user))
       .options(selectinload(Order.file))
       .where(Order.user_id == user_id)
   )
   ```

### Monitoring and Maintenance

1. **Database Monitoring**
   ```sql
   -- Check database size
   SELECT pg_size_pretty(pg_database_size('maas_backend'));
   
   -- Check table sizes
   SELECT 
       schemaname,
       tablename,
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
   FROM pg_tables 
   WHERE schemaname = 'public'
   ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
   
   -- Check slow queries
   SELECT query, mean_time, calls 
   FROM pg_stat_statements 
   ORDER BY mean_time DESC 
   LIMIT 10;
   ```

2. **Backup Strategy**
   ```bash
   # Create backup
   pg_dump -h localhost -U maas_user -d maas_backend > backup_$(date +%Y%m%d_%H%M%S).sql
   
   # Restore backup
   psql -h localhost -U maas_user -d maas_backend < backup_20240115_120000.sql
   ```

3. **Automated Backups**
   ```bash
   # Add to crontab
   0 2 * * * pg_dump -h localhost -U maas_user -d maas_backend | gzip > /backups/maas_backend_$(date +\%Y\%m\%d_\%H\%M\%S).sql.gz
   ```

## 🔄 Rollback Procedures

### Emergency Rollback

1. **Stop Application**
   ```bash
   # Stop the backend service
   sudo systemctl stop maas-backend
   # or
   docker-compose down
   ```

2. **Restore SQLite**
   ```bash
   # Restore from backup
   cp backup_maas_backend_YYYYMMDD_HHMMSS.zip .
   unzip backup_maas_backend_YYYYMMDD_HHMMSS.zip
   ```

3. **Update Configuration**
   ```env
   DATABASE_URL=sqlite+aiosqlite:///./data/shop.db
   ```

4. **Restart Application**
   ```bash
   # Start the backend service
   sudo systemctl start maas-backend
   # or
   docker-compose up -d
   ```

### Data Recovery

1. **Export PostgreSQL Data**
   ```bash
   pg_dump -h localhost -U maas_user -d maas_backend --data-only > data_export.sql
   ```

2. **Import to SQLite**
   ```python
   # scripts/export_to_sqlite.py
   import sqlite3
   import asyncpg
   from backend.core.config import settings
   
   async def export_to_sqlite():
       # Connect to PostgreSQL
       pg_conn = await asyncpg.connect(settings.DATABASE_URL)
       
       # Connect to SQLite
       sqlite_conn = sqlite3.connect('data/shop.db')
       sqlite_cursor = sqlite_conn.cursor()
       
       try:
           # Export users
           users = await pg_conn.fetch("SELECT * FROM users")
           for user in users:
               sqlite_cursor.execute("""
                   INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               """, user)
           
           # Export other tables...
           
           sqlite_conn.commit()
           print("Data exported to SQLite successfully!")
           
       finally:
           await pg_conn.close()
           sqlite_conn.close()
   
   if __name__ == "__main__":
       asyncio.run(export_to_sqlite())
   ```

## 📊 Performance Comparison

### Expected Improvements

| Metric | SQLite | PostgreSQL | Improvement |
|--------|--------|------------|-------------|
| Concurrent Connections | 1 | 100+ | 100x |
| Query Performance | Good | Excellent | 2-5x |
| Memory Usage | Low | Medium | Acceptable |
| Disk Usage | Low | Medium | Acceptable |
| Backup/Recovery | Manual | Automated | Significant |
| Monitoring | Basic | Advanced | Significant |

### Monitoring Queries

```sql
-- Connection monitoring
SELECT count(*) as active_connections 
FROM pg_stat_activity 
WHERE state = 'active';

-- Query performance
SELECT 
    query,
    mean_time,
    calls,
    total_time
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;

-- Database size
SELECT pg_size_pretty(pg_database_size('maas_backend'));

-- Table statistics
SELECT 
    schemaname,
    tablename,
    n_tup_ins as inserts,
    n_tup_upd as updates,
    n_tup_del as deletes
FROM pg_stat_user_tables
ORDER BY n_tup_ins DESC;
```

## 🛠️ Troubleshooting

### Common Issues

1. **Connection Errors**
   ```bash
   # Check PostgreSQL status
   sudo systemctl status postgresql
   
   # Check connection
   psql -h localhost -U maas_user -d maas_backend
   ```

2. **Migration Errors**
   ```bash
   # Check Alembic status
   alembic current
   
   # Check migration history
   alembic history
   
   # Rollback if needed
   alembic downgrade -1
   ```

3. **Performance Issues**
   ```sql
   -- Check slow queries
   SELECT query, mean_time, calls 
   FROM pg_stat_statements 
   WHERE mean_time > 1000
   ORDER BY mean_time DESC;
   
   -- Check locks
   SELECT * FROM pg_locks WHERE NOT granted;
   ```

### Support Resources

- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [AsyncPG Documentation](https://magicstack.github.io/asyncpg/)

---

This migration guide provides comprehensive instructions for moving from SQLite to PostgreSQL. For additional support or questions, refer to the [DEVELOPMENT.md](DEVELOPMENT.md) or create an issue in the repository.

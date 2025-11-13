#!/usr/bin/env python3
"""
Database migration script to add created_at and updated_at columns to users table
"""
import asyncio
import sqlite3
from datetime import datetime, timezone

async def migrate_database():
    """Add created_at and updated_at columns to users table"""
    db_path = "data/shop.db"
    
    # Connect to SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info('users')")
        columns = [row[1] for row in cursor.fetchall()]
        
        print(f"Existing columns: {columns}")
        
        # Add created_at column if it doesn't exist
        if 'created_at' not in columns:
            print("Adding created_at column...")
            cursor.execute("ALTER TABLE users ADD COLUMN created_at DATETIME")
        else:
            print("created_at column already exists")
            
        # Add updated_at column if it doesn't exist
        if 'updated_at' not in columns:
            print("Adding updated_at column...")
            cursor.execute("ALTER TABLE users ADD COLUMN updated_at DATETIME")
        else:
            print("updated_at column already exists")
        
        # Commit changes
        conn.commit()
        
        # Backfill existing users with current timestamp
        now = datetime.now(timezone.utc)
        print(f"Backfilling timestamps with: {now}")
        
        cursor.execute("UPDATE users SET created_at = ? WHERE created_at IS NULL", (now,))
        cursor.execute("UPDATE users SET updated_at = ? WHERE updated_at IS NULL", (now,))
        
        conn.commit()
        
        # Verify the changes
        cursor.execute("PRAGMA table_info('users')")
        new_columns = [row[1] for row in cursor.fetchall()]
        print(f"Updated columns: {new_columns}")
        
        # Check if timestamps were set
        cursor.execute("SELECT id, username, created_at, updated_at FROM users LIMIT 3")
        users = cursor.fetchall()
        print("Sample users with timestamps:")
        for user in users:
            print(f"  ID: {user[0]}, Username: {user[1]}, Created: {user[2]}, Updated: {user[3]}")
        
        print("✅ Database migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    asyncio.run(migrate_database())

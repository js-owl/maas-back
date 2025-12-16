"""
Add invoice_ids column to orders table
"""
import asyncio
import sqlite3
from pathlib import Path

async def add_columns():
    """Add invoice_ids column to orders table"""
    db_path = Path("data/shop.db")
    
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return
    
    # Connect to SQLite database
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info('orders')")
        columns = [row[1] for row in cursor.fetchall()]
        
        print(f"Existing columns: {columns}")
        
        # Add invoice_ids column if it doesn't exist
        if 'invoice_ids' not in columns:
            print("Adding invoice_ids column...")
            cursor.execute("ALTER TABLE orders ADD COLUMN invoice_ids TEXT")
            conn.commit()
            print("✓ invoice_ids column added successfully")
        else:
            print("invoice_ids column already exists")
        
        # Add location column
        if 'location' not in columns:
            print("Adding location column...")
            cursor.execute("ALTER TABLE orders ADD COLUMN location TEXT")
            conn.commit()
            print("✓ location column added successfully")
        else:
            print("location column already exists")
        
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    asyncio.run(add_columns())



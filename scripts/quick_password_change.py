#!/usr/bin/env python3
"""
Quick Password Change Script
===========================

Simple script for quickly changing user passwords.
Use this for emergency password changes or when you need a quick solution.

Usage:
    python scripts/quick_password_change.py <username> <new_password>
    python scripts/quick_password_change.py <user_id> <new_password>
"""

import sys
import os
import sqlite3
import bcrypt

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def main():
    if len(sys.argv) != 3:
        print("Usage: python scripts/quick_password_change.py <username_or_id> <new_password>")
        print("Examples:")
        print("  python scripts/quick_password_change.py admin newpass123")
        print("  python scripts/quick_password_change.py 1 newpass123")
        sys.exit(1)
    
    identifier = sys.argv[1]
    new_password = sys.argv[2]
    
    # Find database
    db_paths = ['data/shop.db', 'shop.db', '../data/shop.db', '../../data/shop.db']
    db_path = None
    
    for path in db_paths:
        if os.path.exists(path):
            db_path = path
            break
    
    if not db_path:
        print("❌ Database not found")
        sys.exit(1)
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Determine if identifier is username or ID
        if identifier.isdigit():
            # It's a user ID
            cursor.execute('SELECT id, username FROM users WHERE id = ?', (int(identifier),))
        else:
            # It's a username
            cursor.execute('SELECT id, username FROM users WHERE username = ?', (identifier,))
        
        user = cursor.fetchone()
        
        if not user:
            print(f"❌ User not found: {identifier}")
            sys.exit(1)
        
        user_id, username = user
        print(f"Changing password for user: {username} (ID: {user_id})")
        
        # Hash and update password
        hashed_password = hash_password(new_password)
        cursor.execute('UPDATE users SET hashed_password = ? WHERE id = ?', (hashed_password, user_id))
        
        if cursor.rowcount > 0:
            conn.commit()
            print("✅ Password changed successfully")
        else:
            print("❌ Failed to change password")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    main()

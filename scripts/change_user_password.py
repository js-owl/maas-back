#!/usr/bin/env python3
"""
User Management Script
=====================

This script allows managing users in the MaaS backend database.
It can change passwords, delete users, and list all users.
Useful for production server user management.

Usage:
    python scripts/change_user_password.py --list-users
    python scripts/change_user_password.py --username <username> --new-password <password>
    python scripts/change_user_password.py --user-id <id> --new-password <password>
    python scripts/change_user_password.py --username <username> --delete-user
    python scripts/change_user_password.py --user-id <id> --delete-user --force
    python scripts/change_user_password.py --help

Security Notes:
- Passwords are hashed using bcrypt before storage
- The script requires database access
- Use strong passwords for production
- Admin users require --force flag to delete
- Users with orders require --force flag to delete
- Consider using environment variables for sensitive operations
"""

import argparse
import sys
import os
import sqlite3
import bcrypt
from pathlib import Path

# Add backend to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def get_database_path():
    """Get the database path, checking multiple possible locations"""
    possible_paths = [
        #'data/shop.db',
        'shop.db',
        #'../data/shop.db',
        #'../../data/shop.db'
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    raise FileNotFoundError("Database not found. Checked paths: " + ", ".join(possible_paths))

def list_users(db_path: str):
    """List all users in the database"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT id, username, is_admin, email, full_name
            FROM users 
            ORDER BY id
        ''')
        users = cursor.fetchall()
        
        print("Users in database:")
        print("=" * 80)
        print(f"{'ID':<4} {'Username':<15} {'Admin':<6} {'Email':<25} {'Full Name':<20}")
        print("-" * 80)
        
        for user_id, username, is_admin, email, full_name in users:
            admin_status = "Yes" if is_admin else "No"
            email_display = email[:22] + "..." if email and len(email) > 25 else email or "N/A"
            name_display = full_name[:17] + "..." if full_name and len(full_name) > 20 else full_name or "N/A"
            
            print(f"{user_id:<4} {username:<15} {admin_status:<6} {email_display:<25} {name_display:<20}")
        
        print(f"\nTotal users: {len(users)}")
        
    except Exception as e:
        print(f"Error listing users: {e}")
    finally:
        conn.close()

def find_user(db_path: str, username: str = None, user_id: int = None):
    """Find a user by username or ID"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        if username:
            cursor.execute('SELECT id, username, is_admin, email, full_name FROM users WHERE username = ?', (username,))
        elif user_id:
            cursor.execute('SELECT id, username, is_admin, email, full_name FROM users WHERE id = ?', (user_id,))
        else:
            return None
        
        user = cursor.fetchone()
        return user
        
    except Exception as e:
        print(f"Error finding user: {e}")
        return None
    finally:
        conn.close()

def change_password(db_path: str, username: str = None, user_id: int = None, new_password: str = None):
    """Change a user's password"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Find the user
        user = find_user(db_path, username, user_id)
        if not user:
            print(f"❌ User not found")
            return False
        
        user_id, username, is_admin, email, full_name = user
        print(f"Found user: {username} (ID: {user_id})")
        print(f"Admin: {'Yes' if is_admin else 'No'}")
        print(f"Email: {email or 'N/A'}")
        print(f"Full Name: {full_name or 'N/A'}")
        
        # Hash the new password
        hashed_password = hash_password(new_password)
        
        # Update the password
        cursor.execute('UPDATE users SET hashed_password = ? WHERE id = ?', (hashed_password, user_id))
        
        if cursor.rowcount > 0:
            conn.commit()
            print(f"✅ Password successfully changed for user '{username}'")
            
            # Verify the password change
            if verify_password(new_password, hashed_password):
                print("✅ Password verification successful")
            else:
                print("❌ Password verification failed")
                return False
                
            return True
        else:
            print("❌ Failed to update password")
            return False
            
    except Exception as e:
        print(f"❌ Error changing password: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def delete_user(db_path: str, username: str = None, user_id: int = None, force: bool = False):
    """Delete a user from the database"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Find the user
        user = find_user(db_path, username, user_id)
        if not user:
            print(f"❌ User not found")
            return False
        
        user_id, username, is_admin, email, full_name = user
        print(f"Found user: {username} (ID: {user_id})")
        print(f"Admin: {'Yes' if is_admin else 'No'}")
        print(f"Email: {email or 'N/A'}")
        print(f"Full Name: {full_name or 'N/A'}")
        
        # Safety check for admin users
        if is_admin and not force:
            print("❌ Cannot delete admin user without --force flag")
            print("Use --force to delete admin users (use with extreme caution)")
            return False
        
        # Check if user has orders
        cursor.execute('SELECT COUNT(*) FROM orders WHERE user_id = ?', (user_id,))
        order_count = cursor.fetchone()[0]
        
        if order_count > 0:
            print(f"⚠️  Warning: User has {order_count} orders in the database")
            if not force:
                print("Use --force to delete user with orders")
                return False
        
        # Confirm deletion
        if not force:
            confirm = input(f"Are you sure you want to delete user '{username}'? (yes/no): ")
            if confirm.lower() != 'yes':
                print("❌ Deletion cancelled")
                return False
        
        # Delete the user
        cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
        
        if cursor.rowcount > 0:
            conn.commit()
            print(f"✅ User '{username}' successfully deleted")
            return True
        else:
            print("❌ Failed to delete user")
            return False
            
    except Exception as e:
        print(f"❌ Error deleting user: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def validate_password(password: str) -> bool:
    """Validate password strength"""
    if len(password) < 8:
        print("❌ Password must be at least 8 characters long")
        return False
    
    if len(password) > 128:
        print("❌ Password must be less than 128 characters long")
        return False
    
    # Check for common weak passwords
    weak_passwords = ['password', '12345678', 'admin123', 'test123', 'user123']
    if password.lower() in weak_passwords:
        print("⚠️  Warning: This password is commonly used and may be insecure")
    
    return True

def main():
    parser = argparse.ArgumentParser(
        description="Manage users in MaaS backend database (change passwords, delete users)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/change_user_password.py --list-users
  python scripts/change_user_password.py --username admin --new-password newpass123
  python scripts/change_user_password.py --user-id 1 --new-password newpass123
  python scripts/change_user_password.py --username testuser --new-password "StrongP@ssw0rd!"
  python scripts/change_user_password.py --username testuser --delete-user
  python scripts/change_user_password.py --user-id 5 --delete-user --force
        """
    )
    
    parser.add_argument('--username', help='Username to change password for or delete')
    parser.add_argument('--user-id', type=int, help='User ID to change password for or delete')
    parser.add_argument('--new-password', help='New password')
    parser.add_argument('--delete-user', action='store_true', help='Delete user instead of changing password')
    parser.add_argument('--list-users', action='store_true', help='List all users')
    parser.add_argument('--database', help='Path to database file (default: auto-detect)')
    parser.add_argument('--force', action='store_true', help='Skip validation and confirmations')
    
    args = parser.parse_args()
    
    # Get database path
    try:
        db_path = args.database or get_database_path()
        print(f"Using database: {db_path}")
    except FileNotFoundError as e:
        print(f"❌ {e}")
        return 1
    
    # List users if requested
    if args.list_users:
        list_users(db_path)
        return 0
    
    # Validate arguments
    if not args.username and not args.user_id:
        print("❌ Error: Must specify either --username or --user-id")
        parser.print_help()
        return 1
    
    # Handle delete user
    if args.delete_user:
        success = delete_user(db_path, args.username, args.user_id, args.force)
        return 0 if success else 1
    
    # Handle change password
    if not args.new_password:
        print("❌ Error: Must specify --new-password for password change")
        parser.print_help()
        return 1
    
    # Validate password strength
    if not args.force and not validate_password(args.new_password):
        print("Use --force to skip password validation")
        return 1
    
    # Change password
    success = change_password(db_path, args.username, args.user_id, args.new_password)
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())

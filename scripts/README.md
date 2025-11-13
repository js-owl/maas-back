# Scripts Directory

This directory contains utility scripts for managing the MaaS backend system.

## Password Management Scripts

### 1. `change_user_password.py` - Full-Featured User Management

**Purpose**: Comprehensive script for managing users with password changes, user deletion, and validation features.

**Features**:
- List all users in the database
- Change passwords by username or user ID
- Delete users by username or user ID
- Password strength validation
- Detailed user information display
- Safety checks for admin users and users with orders
- Interactive confirmation for deletions
- Error handling and rollback
- Production-ready with security considerations

**Usage**:
```bash
# List all users
python scripts/change_user_password.py --list-users

# Change password by username
python scripts/change_user_password.py --username admin --new-password "NewSecurePass123!"

# Change password by user ID
python scripts/change_user_password.py --user-id 1 --new-password "NewSecurePass123!"

# Skip password validation (use with caution)
python scripts/change_user_password.py --username admin --new-password "weakpass" --force

# Delete user (with confirmation)
python scripts/change_user_password.py --username testuser --delete-user

# Delete user by ID (force mode, no confirmation)
python scripts/change_user_password.py --user-id 5 --delete-user --force

# Specify custom database path
python scripts/change_user_password.py --username admin --new-password "NewPass123!" --database /path/to/shop.db
```

**Options**:
- `--username <username>`: Username to change password for or delete
- `--user-id <id>`: User ID to change password for or delete
- `--new-password <password>`: New password
- `--delete-user`: Delete user instead of changing password
- `--list-users`: List all users in the database
- `--database <path>`: Custom database path (default: auto-detect)
- `--force`: Skip validation and confirmations
- `--help`: Show help message

### 2. `quick_password_change.py` - Quick Password Change

**Purpose**: Simple script for quick password changes without validation.

**Usage**:
```bash
# Change password by username
python scripts/quick_password_change.py admin newpass123

# Change password by user ID
python scripts/quick_password_change.py 1 newpass123
```

## Security Notes

### Password Requirements
- Minimum 8 characters
- Maximum 128 characters
- Avoid common weak passwords
- Use strong, unique passwords for production

### Database Access
- Scripts automatically detect database location
- Supports multiple database path configurations
- Uses bcrypt for secure password hashing
- Includes transaction rollback on errors

### Production Usage
1. **Test first**: Always test password changes in development
2. **Backup database**: Create backup before making changes
3. **Use strong passwords**: Avoid weak or common passwords
4. **Verify changes**: Test login after password change
5. **Monitor logs**: Check application logs for any issues

## Examples

### Emergency Password Reset
```bash
# Quick reset for admin user
python scripts/quick_password_change.py admin EmergencyPass123!

# Verify the change worked
python scripts/change_user_password.py --list-users
```

### Production Password Management
```bash
# List all users first
python scripts/change_user_password.py --list-users

# Change specific user password with validation
python scripts/change_user_password.py --username testuser --new-password "StrongP@ssw0rd2024!"

# Verify the change
python scripts/change_user_password.py --list-users
```

### Database Maintenance
```bash
# Check database location
python scripts/change_user_password.py --list-users

# Use custom database path
python scripts/change_user_password.py --username admin --new-password "NewPass123!" --database /backup/shop.db
```

## Troubleshooting

### Common Issues

1. **Database not found**
   - Check if you're in the correct directory
   - Verify database file exists
   - Use `--database` option to specify path

2. **User not found**
   - Use `--list-users` to see available users
   - Check username spelling
   - Verify user ID is correct

3. **Permission denied**
   - Ensure you have write access to database
   - Check file permissions
   - Run with appropriate user privileges

4. **Password validation failed**
   - Use stronger password
   - Use `--force` to skip validation (not recommended for production)

### Error Messages

- `❌ Database not found`: Database file not located
- `❌ User not found`: Username or ID doesn't exist
- `❌ Password must be at least 8 characters`: Password too short
- `❌ Failed to update password`: Database update failed
- `✅ Password successfully changed`: Success message

## Dependencies

- Python 3.7+
- bcrypt library
- sqlite3 (built-in)

Install dependencies:
```bash
pip install bcrypt
```

## Demo Model Management

### 3. `replace_demo_models.py` - Replace Demo 3D Models

**Purpose**: Replace demo 3D models (IDs 1, 2, 4) with new STP files, updating both file system and database records, and generating preview images.

**Features**:
- Replace demo models with new STP files from specified directory
- Backup existing demo files with timestamps
- Update database FileStorage records with new filenames, paths, sizes, and file types
- Generate preview images for replaced models using backend preview system
- Update preview-related fields in database (preview_filename, preview_path, preview_generated)
- Atomic database updates with rollback capability
- Detailed logging and progress output
- Verification of successful replacement

**Usage**:
```bash
# Replace demo models with new STP files
python scripts/replace_demo_models.py --db-path data/shop.db --uploads-dir uploads/3d_models --new-models-dir /path/to/new_demo_models

# Dry run to see what would be changed
python scripts/replace_demo_models.py --db-path data/shop.db --uploads-dir uploads/3d_models --new-models-dir /path/to/new_demo_models --dry-run
```

**Options**:
- `--db-path <path>`: Path to SQLite database file (required)
- `--uploads-dir <path>`: Path to uploads directory (required)
- `--new-models-dir <path>`: Path to directory containing new model files (required)
- `--dry-run`: Perform a dry run without making changes

**File Mappings**:
- ID 1: `file_id_1.stp` → `demo_printing_default.stp`
- ID 2: `file_id_2.stp` → `demo_lathe_default.stp`
- ID 4: `file_id_4.stp` → `demo_milling_default.stp`

**Process**:
1. Validates environment and file existence
2. Creates timestamped backups of existing demo files
3. Copies new STP files to uploads directory with proper naming
4. Generates preview images using backend preview system
5. Updates database records with new file information and preview data
6. Verifies successful replacement
7. Provides rollback capability on failure

**Backup Files**:
- Backups are stored in `uploads/3d_models/backups/`
- Format: `original_filename.backup.YYYYMMDD_HHMMSS`
- Automatic rollback on failure

## File Structure

```
scripts/
├── README.md                    # This file
├── change_user_password.py      # Full-featured password change script
├── quick_password_change.py     # Quick password change script
├── replace_demo_models.py       # Demo model replacement script
└── run_all_tests.py            # Test runner script
```
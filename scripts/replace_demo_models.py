#!/usr/bin/env python3
"""
Replace Demo Models Script

This script replaces demo 3D models (IDs 1, 2, 4) on the remote server with new STP files,
updating both file system and database records, and generating preview images.

Usage:
    python scripts/replace_demo_models.py --db-path data/shop.db --uploads-dir uploads/3d_models --new-models-dir /path/to/new_demo_models
"""

import os
import sys
import sqlite3
import shutil
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import json

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('replace_demo_models.log')
    ]
)
logger = logging.getLogger(__name__)

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import preview generation utilities
try:
    from backend.files.preview import PreviewGenerator
    from backend.utils.helpers import generate_placeholder_preview
    PREVIEW_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Preview generation not available: {e}")
    PREVIEW_AVAILABLE = False

class DemoModelReplacer:
    """Handles replacement of demo models with new STP files"""
    
    def __init__(self, db_path: str, uploads_dir: str, new_models_dir: str):
        self.db_path = Path(db_path)
        self.uploads_dir = Path(uploads_dir)
        self.new_models_dir = Path(new_models_dir)
        self.preview_generator = PreviewGenerator() if PREVIEW_AVAILABLE else None
        
        # Mapping of file IDs to target filenames in uploads directory
        # ID 1: Printing, ID 2: Lathe, ID 4: Milling
        self.file_mappings = {
            1: "demo_printing_default.stp",
            2: "demo_lathe_default.stp",
            4: "demo_milling_default.stp"
        }
        
        # Source files in new_models_dir (all IDs being replaced)
        self.source_files = {
            1: "file_id_1.stp",
            2: "file_id_2.stp",
            4: "file_id_4_ok.stp"
        }
        
        # Backup directory
        self.backup_dir = self.uploads_dir / "backups"
        self.backup_dir.mkdir(exist_ok=True)
    
    def validate_environment(self) -> bool:
        """Validate that all required files and directories exist"""
        logger.info("Validating environment...")
        
        # Check database
        if not self.db_path.exists():
            logger.error(f"Database not found: {self.db_path}")
            return False
        
        # Check uploads directory
        if not self.uploads_dir.exists():
            logger.error(f"Uploads directory not found: {self.uploads_dir}")
            return False
        
        # Check new models directory and files
        if not self.new_models_dir.exists():
            logger.error(f"New models directory not found: {self.new_models_dir}")
            return False
        
        # Only validate source files that we're actually replacing
        for file_id, source_file in self.source_files.items():
            source_path = self.new_models_dir / source_file
            if not source_path.exists():
                logger.error(f"Source file not found: {source_path}")
                return False
        
        logger.info("Environment validation passed")
        logger.info(f"Will replace files for IDs: {list(self.source_files.keys())}")
        return True
    
    def backup_existing_files(self) -> Dict[int, str]:
        """Backup existing demo files to both backups directory and new_demo_models directory"""
        logger.info("Creating backups of existing demo files...")
        backup_paths = {}
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Only backup files that will be replaced
        for file_id in self.source_files.keys():
            # Try to find existing file (might be .stp or .stl)
            current_path = None
            original_ext = None
            target_filename = self.file_mappings[file_id]
            for ext in ['.stp', '.stl']:
                # Try with target extension and also try alternative extension
                current_filename = target_filename.replace('.stp', ext).replace('.stl', ext)
                test_path = self.uploads_dir / current_filename
                
                if test_path.exists():
                    current_path = test_path
                    original_ext = ext
                    break
            
            if current_path and original_ext:
                # Backup 1: Timestamped backup to uploads/backups/
                backup_filename = f"{current_path.name}.backup.{timestamp}"
                backup_path = self.backup_dir / backup_filename
                shutil.copy2(current_path, backup_path)
                backup_paths[file_id] = str(backup_path)
                logger.info(f"Backed up {current_path.name} to {backup_filename}")
                
                # Backup 2: Simple backup to new_demo_models/ with _old suffix
                old_backup_filename = f"file_id_{file_id}_old{original_ext}"
                old_backup_path = self.new_models_dir / old_backup_filename
                shutil.copy2(current_path, old_backup_path)
                logger.info(f"Backed up {current_path.name} to {old_backup_filename} in new_demo_models/")
            else:
                logger.warning(f"Existing file not found for backup (file_id {file_id})")
        
        return backup_paths
    
    def copy_new_files(self) -> Dict[int, Path]:
        """Copy new demo files to uploads directory (only for files being replaced)"""
        logger.info("Copying new demo files...")
        copied_files = {}
        
        # Only copy files that have source files available
        for file_id in self.source_files.keys():
            source_file = self.source_files[file_id]
            target_file = self.file_mappings[file_id]
            
            source_path = self.new_models_dir / source_file
            target_path = self.uploads_dir / target_file
            
            try:
                shutil.copy2(source_path, target_path)
                copied_files[file_id] = target_path
                logger.info(f"Copied {source_file} to {target_file}")
            except Exception as e:
                logger.error(f"Failed to copy {source_file}: {e}")
                raise
        
        return copied_files
    
    async def generate_preview(self, file_id: int, model_path: Path, original_filename: str) -> Optional[Dict[str, Any]]:
        """Generate preview image for a model file"""
        try:
            logger.info(f"Generating preview for file {file_id}: {original_filename}")
            
            if not PREVIEW_AVAILABLE or not self.preview_generator:
                logger.warning("Preview generation not available, will use placeholder")
                return None
            
            # Use the preview generator
            preview_data = await self.preview_generator.generate_preview(model_path, original_filename)
            
            if preview_data:
                logger.info(f"Preview generated successfully for file {file_id}")
                return preview_data
            else:
                logger.warning(f"Preview generation failed for file {file_id}, will use placeholder")
                return None
                
        except Exception as e:
            logger.error(f"Error generating preview for file {file_id}: {e}")
            return None
    
    async def update_database(self, copied_files: Dict[int, Path]) -> bool:
        """Update database records for replaced demo files"""
        logger.info("Updating database records...")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Only update database for files that were actually copied
            for file_id in copied_files.keys():
                model_path = copied_files[file_id]
                filename = self.file_mappings[file_id]
                
                # Get file stats
                stat = model_path.stat()
                file_size = stat.st_size
                # Extract file type - ensure it's correctly extracted (should be .stp)
                file_type = model_path.suffix.lower()
                if not file_type.startswith('.'):
                    file_type = '.' + file_type
                
                # Verify file_type is .stp (expected for demo models)
                if file_type != '.stp':
                    logger.warning(f"File type is {file_type}, expected .stp for file {file_id}")
                
                # Get current database record to preserve uploaded_by and uploaded_at
                cursor.execute("SELECT uploaded_by, uploaded_at FROM files WHERE id = ?", (file_id,))
                existing_row = cursor.fetchone()
                uploaded_by = existing_row[0] if existing_row else None
                uploaded_at = existing_row[1] if existing_row else None
                
                # Generate preview
                preview_data = await self.generate_preview(file_id, model_path, filename)
                
                # Prepare update data - ALL columns that need updating
                # Calculate relative path from uploads directory for database storage
                # This ensures paths work in both local and containerized environments
                # Database expects: uploads/3d_models/filename.stp
                try:
                    # Try to get relative path from current working directory
                    # This preserves the full path structure (uploads/3d_models/...)
                    cwd = Path.cwd()
                    relative_path = model_path.relative_to(cwd)
                    # Convert to forward slashes for cross-platform compatibility
                    file_path_value = str(relative_path).replace('\\', '/')
                    
                    # Ensure it starts with uploads/ for consistency
                    if not file_path_value.startswith('uploads/'):
                        # If it doesn't, try a different approach
                        if 'uploads' in str(model_path):
                            # Extract everything from uploads onwards
                            parts = str(model_path).split('uploads')
                            if len(parts) > 1:
                                file_path_value = 'uploads' + parts[1].replace('\\', '/')
                            else:
                                file_path_value = f"uploads/3d_models/{filename}"
                        else:
                            file_path_value = f"uploads/3d_models/{filename}"
                except ValueError:
                    # If relative_to fails, check if model_path is already inside uploads_dir
                    if str(self.uploads_dir) in str(model_path):
                        # Extract path starting from uploads
                        model_str = str(model_path).replace('\\', '/')
                        uploads_idx = model_str.find('uploads/')
                        if uploads_idx >= 0:
                            file_path_value = model_str[uploads_idx:]
                        else:
                            # Fallback: construct from uploads_dir name and filename
                            uploads_dir_name = self.uploads_dir.name
                            parent_name = self.uploads_dir.parent.name
                            file_path_value = f"{parent_name}/{uploads_dir_name}/{filename}"
                    else:
                        # Last fallback: use standard path
                        file_path_value = f"uploads/3d_models/{filename}"
                
                update_data = {
                    'filename': filename,
                    'original_filename': filename,
                    'file_path': file_path_value,  # Use relative path for cross-platform compatibility
                    'file_size': file_size,
                    'file_type': file_type,  # Should be .stp
                    'is_demo': True,
                    'file_metadata': json.dumps({
                        "file_size": file_size,
                        "source": "demo_replacement",
                        "replaced_at": datetime.now().isoformat()
                    })
                }
                
                # Preserve uploaded_by if it exists, otherwise leave as None (won't update)
                if uploaded_by is not None:
                    update_data['uploaded_by'] = uploaded_by
                # uploaded_at is preserved automatically by not including it in update
                
                # Add preview data if available
                if preview_data:
                    update_data.update({
                        'preview_filename': preview_data.get('preview_filename'),
                        'preview_path': preview_data.get('preview_path'),
                        'preview_generated': preview_data.get('preview_generated', False),
                        'preview_generation_error': preview_data.get('preview_generation_error')
                    })
                else:
                    # Generate placeholder preview
                    try:
                        if PREVIEW_AVAILABLE:
                            placeholder_data = generate_placeholder_preview(filename)
                            placeholder_filename = f"{Path(filename).stem}_placeholder_preview.png"
                            placeholder_path = self.preview_generator.preview_dir / placeholder_filename
                            
                            with open(placeholder_path, 'wb') as f:
                                f.write(placeholder_data)
                            
                            update_data.update({
                                'preview_filename': placeholder_filename,
                                'preview_path': str(placeholder_path),
                                'preview_generated': True,
                                'preview_generation_error': None
                            })
                        else:
                            # Simple placeholder without backend dependencies
                            placeholder_filename = f"{Path(filename).stem}_placeholder_preview.png"
                            update_data.update({
                                'preview_filename': placeholder_filename,
                                'preview_path': f"uploads/previews/{placeholder_filename}",
                                'preview_generated': False,
                                'preview_generation_error': "Preview generation not available"
                            })
                    except Exception as e:
                        logger.warning(f"Failed to generate placeholder for file {file_id}: {e}")
                        update_data.update({
                            'preview_generated': False,
                            'preview_generation_error': str(e)
                        })
                
                # Update database
                set_clause = ', '.join([f"{key} = ?" for key in update_data.keys()])
                values = list(update_data.values()) + [file_id]
                
                cursor.execute(f"""
                    UPDATE files 
                    SET {set_clause}
                    WHERE id = ?
                """, values)
                
                logger.info(f"Updated database record for file ID {file_id}")
                
                # Verify the update was successful by reading back all columns
                cursor.execute("""
                    SELECT filename, original_filename, file_path, file_size, file_type, is_demo,
                           preview_filename, preview_path, preview_generated, uploaded_by, uploaded_at
                    FROM files WHERE id = ?
                """, (file_id,))
                verify_row = cursor.fetchone()
                
                if verify_row:
                    logger.info(f"Verification for ID {file_id}:")
                    logger.info(f"  filename: {verify_row[0]}")
                    logger.info(f"  original_filename: {verify_row[1]}")
                    logger.info(f"  file_path: {verify_row[2]}")
                    logger.info(f"  file_size: {verify_row[3]}")
                    logger.info(f"  file_type: {verify_row[4]} (expected: .stp)")
                    logger.info(f"  is_demo: {verify_row[5]}")
                    logger.info(f"  preview_generated: {verify_row[8]}")
                    
                    # Verify critical fields
                    if verify_row[0] != filename:
                        logger.error(f"  ERROR: filename mismatch - expected {filename}, got {verify_row[0]}")
                    if verify_row[4] != '.stp':
                        logger.warning(f"  WARNING: file_type is {verify_row[4]}, expected .stp")
                    if verify_row[5] != 1:
                        logger.error(f"  ERROR: is_demo is not True")
                else:
                    logger.error(f"Failed to verify update for file ID {file_id}")
            
            conn.commit()
            conn.close()
            
            logger.info("Database update completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Database update failed: {e}")
            return False
    
    def get_current_demo_files(self) -> Dict[int, Dict[str, Any]]:
        """Get current demo files from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            current_files = {}
            for file_id in [1, 2, 4]:
                cursor.execute("""
                    SELECT id, filename, file_path, file_size, file_type, is_demo
                    FROM files WHERE id = ?
                """, (file_id,))
                
                row = cursor.fetchone()
                if row:
                    current_files[file_id] = {
                        'id': row['id'],
                        'filename': row['filename'],
                        'file_path': row['file_path'],
                        'file_size': row['file_size'],
                        'file_type': row['file_type'],
                        'is_demo': bool(row['is_demo'])
                    }
            
            conn.close()
            return current_files
        except Exception as e:
            logger.error(f"Failed to get current demo files: {e}")
            return {}
    
    def display_current_files(self) -> None:
        """Display current demo files in database"""
        print("\n" + "="*80)
        print("CURRENT DEMO FILES IN DATABASE")
        print("="*80)
        
        current_files = self.get_current_demo_files()
        if not current_files:
            print("No demo files found in database.")
            return
        
        for file_id in sorted(current_files.keys()):
            info = current_files[file_id]
            print(f"\n  ID {file_id}: {info['filename']}")
            print(f"    Path: {info['file_path']}")
            print(f"    Size: {info['file_size']:,} bytes")
            print(f"    Type: {info['file_type']}")
            print(f"    Is Demo: {info['is_demo']}")
        print()
    
    def display_available_new_files(self) -> None:
        """Display available new files from new_demo_models directory"""
        print("\n" + "="*80)
        print("AVAILABLE NEW FILES")
        print("="*80)
        
        for file_id in sorted(self.source_files.keys()):
            source_file = self.source_files[file_id]
            source_path = self.new_models_dir / source_file
            target_file = self.file_mappings[file_id]
            
            if source_path.exists():
                size = source_path.stat().st_size
                print(f"\n  ID {file_id}: {source_file} → {target_file}")
                print(f"    Size: {size:,} bytes")
            else:
                print(f"\n  ID {file_id}: {source_file} (NOT FOUND)")
        print()
    
    def display_mapping_summary(self, selected_ids: List[int]) -> None:
        """Display mapping summary for selected files"""
        print("\n" + "="*80)
        print("REPLACEMENT SUMMARY")
        print("="*80)
        
        current_files = self.get_current_demo_files()
        
        for file_id in sorted(selected_ids):
            source_file = self.source_files[file_id]
            target_file = self.file_mappings[file_id]
            current_info = current_files.get(file_id, {})
            
            print(f"\n  ID {file_id}:")
            print(f"    Source: {source_file}")
            print(f"    Target: {target_file}")
            if current_info:
                print(f"    Current: {current_info.get('filename', 'N/A')} ({current_info.get('file_size', 0):,} bytes)")
            else:
                print(f"    Current: Not found in database")
        print()
    
    def interactive_select_files(self) -> List[int]:
        """Interactive menu for selecting which files to replace"""
        print("\n" + "="*80)
        print("INTERACTIVE DEMO MODEL REPLACEMENT")
        print("="*80)
        
        self.display_current_files()
        self.display_available_new_files()
        
        while True:
            print("\nSelect files to replace:")
            print("  [1] Replace all (IDs 1, 2, 4)")
            print("  [2] Replace ID 1 only (demo_printing_default.stp)")
            print("  [3] Replace ID 2 only (demo_lathe_default.stp)")
            print("  [4] Replace ID 4 only (demo_milling_default.stp)")
            print("  [5] Custom selection")
            print("  [Q] Quit")
            
            choice = input("\nEnter your choice: ").strip().upper()
            
            if choice == 'Q':
                return []
            elif choice == '1':
                selected = [1, 2, 4]
                break
            elif choice == '2':
                selected = [1]
                break
            elif choice == '3':
                selected = [2]
                break
            elif choice == '4':
                selected = [4]
                break
            elif choice == '5':
                selected = self.custom_selection()
                if selected:
                    break
            else:
                print("Invalid choice. Please try again.")
        
        if selected:
            self.display_mapping_summary(selected)
            confirm = input("\nProceed with replacement? (yes/no): ").strip().lower()
            if confirm not in ['yes', 'y']:
                print("Cancelled by user.")
                return []
        
        return selected
    
    def custom_selection(self) -> List[int]:
        """Custom file selection"""
        print("\nAvailable file IDs: 1, 2, 4")
        print("Enter file IDs separated by commas (e.g., '1,2,4' or '1'):")
        
        try:
            user_input = input("Selection: ").strip()
            selected = [int(x.strip()) for x in user_input.split(',')]
            
            # Validate selection
            valid_ids = [1, 2, 4]
            invalid = [x for x in selected if x not in valid_ids]
            if invalid:
                print(f"Invalid IDs: {invalid}. Valid IDs are: {valid_ids}")
                return []
            
            return sorted(selected)
        except ValueError:
            print("Invalid input. Please enter comma-separated numbers.")
            return []
    
    def confirm_step(self, step_name: str, description: str) -> bool:
        """Confirm a step before proceeding"""
        print(f"\n{step_name}: {description}")
        response = input("Continue? (yes/no): ").strip().lower()
        return response in ['yes', 'y']
    
    def verify_replacement(self, replaced_ids: List[int]) -> bool:
        """Verify that the replacement was successful - check ALL columns"""
        logger.info("Verifying replacement...")
        print("\nVerifying all updated columns...")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            all_verified = True
            # Only verify the files that were actually replaced
            for file_id in replaced_ids:
                cursor.execute("""
                    SELECT filename, original_filename, file_path, file_size, file_type, is_demo,
                           preview_filename, preview_path, preview_generated, preview_generation_error
                    FROM files WHERE id = ?
                """, (file_id,))
                
                row = cursor.fetchone()
                if not row:
                    logger.error(f"File ID {file_id} not found in database")
                    print(f"  [ERROR] ID {file_id}: Not found in database")
                    all_verified = False
                    continue
                
                (filename, original_filename, file_path, file_size, file_type, is_demo,
                 preview_filename, preview_path, preview_generated, preview_error) = row
                
                expected_filename = self.file_mappings[file_id]
                file_path_obj = Path(file_path)
                
                # Verify all columns
                checks = []
                
                # filename check
                if filename == expected_filename:
                    checks.append(f"[OK] filename: {filename}")
                else:
                    checks.append(f"[ERROR] filename: expected {expected_filename}, got {filename}")
                    all_verified = False
                
                # original_filename check
                if original_filename == expected_filename:
                    checks.append(f"[OK] original_filename: {original_filename}")
                else:
                    checks.append(f"[ERROR] original_filename: expected {expected_filename}, got {original_filename}")
                    all_verified = False
                
                # file_path check
                if file_path_obj.exists():
                    checks.append(f"[OK] file_path exists: {file_path}")
                else:
                    checks.append(f"[ERROR] file_path not found: {file_path}")
                    all_verified = False
                
                # file_size check (verify it matches actual file)
                if file_path_obj.exists():
                    actual_size = file_path_obj.stat().st_size
                    if file_size == actual_size:
                        checks.append(f"[OK] file_size: {file_size:,} bytes")
                    else:
                        checks.append(f"[ERROR] file_size mismatch: DB={file_size}, actual={actual_size}")
                        all_verified = False
                
                # file_type check (must be .stp)
                if file_type == '.stp':
                    checks.append(f"[OK] file_type: {file_type}")
                else:
                    checks.append(f"[ERROR] file_type: expected .stp, got {file_type}")
                    all_verified = False
                
                # is_demo check
                if is_demo:
                    checks.append(f"[OK] is_demo: True")
                else:
                    checks.append(f"[ERROR] is_demo: expected True, got {is_demo}")
                    all_verified = False
                
                # preview checks
                if preview_filename:
                    checks.append(f"[OK] preview_filename: {preview_filename}")
                else:
                    checks.append(f"[WARN] preview_filename: None")
                
                if preview_path:
                    checks.append(f"[OK] preview_path: {preview_path}")
                else:
                    checks.append(f"[WARN] preview_path: None")
                
                checks.append(f"[{'OK' if preview_generated else 'WARN'}] preview_generated: {preview_generated}")
                
                print(f"\n  ID {file_id}: {expected_filename}")
                for check in checks:
                    print(f"    {check}")
            
            conn.close()
            
            if all_verified:
                logger.info("Replacement verification completed successfully")
                print("\n[OK] All verifications passed!")
                return True
            else:
                logger.error("Some verification checks failed")
                print("\n[ERROR] Some verification checks failed - see details above")
                return False
            
        except Exception as e:
            logger.error(f"Verification failed: {e}")
            print(f"\n[ERROR] Verification error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def run(self, selected_ids: Optional[List[int]] = None) -> bool:
        """Execute the complete replacement process"""
        logger.info("Starting demo model replacement process...")
        
        try:
            # Step 1: Validate environment
            if not self.validate_environment():
                return False
            
            # Step 2: Interactive file selection (if not provided)
            if selected_ids is None:
                selected_ids = self.interactive_select_files()
            
            if not selected_ids:
                logger.info("No files selected for replacement.")
                return False
            
            # Filter source_files to only include selected IDs
            original_source_files = self.source_files.copy()
            self.source_files = {k: v for k, v in self.source_files.items() if k in selected_ids}
            
            # Step 3: Backup existing files
            print("\n" + "="*80)
            print("STEP 1: BACKUP EXISTING FILES")
            print("="*80)
            if not self.confirm_step("Backup", f"Create backups for IDs: {selected_ids}"):
                print("Backup cancelled by user.")
                return False
            
            backup_paths = self.backup_existing_files()
            print(f"[OK] Backed up {len(backup_paths)} files")
            
            # Step 4: Copy new files
            print("\n" + "="*80)
            print("STEP 2: COPY NEW FILES")
            print("="*80)
            if not self.confirm_step("Copy", f"Copy new files to uploads directory for IDs: {selected_ids}"):
                print("Copy cancelled by user.")
                return False
            
            copied_files = self.copy_new_files()
            print(f"[OK] Copied {len(copied_files)} files")
            
            # Step 5: Update database
            print("\n" + "="*80)
            print("STEP 3: UPDATE DATABASE")
            print("="*80)
            if not self.confirm_step("Database Update", f"Update database records for IDs: {selected_ids}"):
                print("Database update cancelled by user. Rolling back...")
                self.rollback(copied_files, backup_paths)
                return False
            
            if not await self.update_database(copied_files):
                logger.error("Database update failed, rolling back...")
                self.rollback(copied_files, backup_paths)
                return False
            print(f"[OK] Updated {len(copied_files)} database records")
            
            # Step 6: Verify replacement
            print("\n" + "="*80)
            print("STEP 4: VERIFICATION")
            print("="*80)
            if not self.verify_replacement(list(copied_files.keys())):
                logger.error("Verification failed, rolling back...")
                self.rollback(copied_files, backup_paths)
                return False
            print("[OK] All replacements verified successfully")
            
            # Restore original source_files
            self.source_files = original_source_files
            
            # Final summary
            print("\n" + "="*80)
            print("REPLACEMENT COMPLETED SUCCESSFULLY!")
            print("="*80)
            print(f"\nReplaced {len(copied_files)} demo model(s):")
            for file_id in sorted(copied_files.keys()):
                print(f"  - ID {file_id}: {self.file_mappings[file_id]}")
            print(f"\nBackups created:")
            for file_id in sorted(backup_paths.keys()):
                print(f"  - ID {file_id}: {Path(backup_paths[file_id]).name}")
            print()
            
            logger.info("Demo model replacement completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Replacement process failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def rollback(self, copied_files: Dict[int, Path], backup_paths: Dict[int, str]):
        """Rollback changes in case of failure"""
        logger.info("Rolling back changes...")
        
        try:
            # Remove copied files
            for file_id, file_path in copied_files.items():
                if file_path.exists():
                    file_path.unlink()
                    logger.info(f"Removed copied file: {file_path}")
            
            # Restore from backups
            for file_id, backup_path in backup_paths.items():
                if Path(backup_path).exists():
                    # Get the original extension from the backup filename
                    backup_filename = Path(backup_path).name
                    original_filename = backup_filename.split('.backup.')[0]
                    target_path = self.uploads_dir / original_filename
                    shutil.copy2(backup_path, target_path)
                    logger.info(f"Restored from backup: {original_filename}")
            
            logger.info("Rollback completed")
            
        except Exception as e:
            logger.error(f"Rollback failed: {e}")

async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Replace demo 3D models with new STP files")
    parser.add_argument("--db-path", required=True, help="Path to SQLite database file")
    parser.add_argument("--uploads-dir", required=True, help="Path to uploads directory")
    parser.add_argument("--new-models-dir", required=True, help="Path to directory containing new model files")
    parser.add_argument("--dry-run", action="store_true", help="Perform a dry run without making changes")
    
    args = parser.parse_args()
    
    if args.dry_run:
        logger.info("DRY RUN MODE - No changes will be made")
        # TODO: Implement dry run logic
        return 0
    
    replacer = DemoModelReplacer(
        db_path=args.db_path,
        uploads_dir=args.uploads_dir,
        new_models_dir=args.new_models_dir
    )
    
    success = await replacer.run()
    return 0 if success else 1

if __name__ == "__main__":
    import asyncio
    sys.exit(asyncio.run(main()))

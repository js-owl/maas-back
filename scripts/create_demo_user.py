#!/usr/bin/env python3
"""
Create diam-aero user with demo orders
Based on screenshots showing 3 orders with specific prices and materials
"""

import asyncio
import os
import sys
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

# Add parent directory to path to import backend modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

# Import backend modules
from backend.models import User, FileStorage, Order
from backend.auth.service import get_password_hash
from backend.calculations.service import call_calculator_service
from backend.utils.logging import get_logger

logger = get_logger(__name__)

# Database configuration
DATABASE_URL = "sqlite+aiosqlite:///./data/shop.db"
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# API configuration
API_BASE_URL = "http://localhost:8001"

class DemoUserCreator:
    def __init__(self):
        self.uploads_dir = Path("uploads/3d_models")
        self.demo_dir = Path("demo")
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        
    async def get_available_materials(self) -> Dict[str, str]:
        """Fetch available materials from calculator API"""
        try:
            response = requests.get(f"{API_BASE_URL}/materials?process=cnc-milling", timeout=10)
            if response.status_code == 200:
                materials_data = response.json()
                materials = materials_data.get("materials", [])
                
                # Create mapping of material names/IDs
                material_map = {}
                for material in materials:
                    if isinstance(material, dict):
                        mat_id = material.get("id", "")
                        mat_name = material.get("name", "")
                        if mat_id:
                            material_map[mat_id] = mat_id
                            if mat_name:
                                material_map[mat_name] = mat_id
                    elif isinstance(material, str):
                        material_map[material] = material
                
                logger.info(f"Fetched {len(material_map)} materials from API")
                return material_map
            else:
                logger.warning(f"Failed to fetch materials: {response.status_code}")
                return {"alum_D16": "alum_D16", "alum_AMG5": "alum_AMG5"}
        except Exception as e:
            logger.error(f"Error fetching materials: {e}")
            return {"alum_D16": "alum_D16", "alum_AMG5": "alum_AMG5"}
    
    async def create_user(self, db: AsyncSession) -> User:
        """Create diam-aero user"""
        username = "diam-aero"
        password = "112233"
        
        # Check if user already exists
        result = await db.execute(select(User).where(User.username == username))
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            logger.info(f"User {username} already exists with ID {existing_user.id}")
            return existing_user
        
        # Create new user
        hashed_password = get_password_hash(password)
        user = User(
            username=username,
            hashed_password=hashed_password,
            is_admin=False,
            user_type="individual",
            email="diam-aero@example.com",
            full_name="Diam Aero User",
            created_at=datetime(2025, 10, 23, 12, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2025, 10, 23, 12, 0, 0, tzinfo=timezone.utc)
        )
        
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"Created user {username} with ID {user.id}")
        return user
    
    async def upload_file(self, db: AsyncSession, user_id: int, source_path: Path, original_filename: str) -> FileStorage:
        """Upload STL file and create FileStorage record"""
        
        # Generate unique filename
        file_extension = source_path.suffix
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        target_path = self.uploads_dir / unique_filename
        
        # Copy file to uploads directory
        shutil.copy2(source_path, target_path)
        
        # Get file size
        file_size = target_path.stat().st_size
        
        # Create FileStorage record
        upload_date = datetime(2025, 10, 23, 12, 0, 0, tzinfo=timezone.utc)
        file_record = FileStorage(
            filename=unique_filename,
            original_filename=original_filename,
            file_path=str(target_path),
            file_size=file_size,
            file_type=file_extension[1:],  # Remove the dot
            uploaded_by=user_id,
            is_demo=False,
            uploaded_at=upload_date
        )
        
        db.add(file_record)
        await db.commit()
        await db.refresh(file_record)
        
        logger.info(f"Uploaded file {original_filename} as {unique_filename} (ID: {file_record.id})")
        return file_record
    
    async def calculate_price_for_file(self, file_record: FileStorage, material_id: str) -> Dict[str, Any]:
        """Calculate price for uploaded file"""
        try:
            # Get file data as base64
            with open(file_record.file_path, 'rb') as f:
                file_data = f.read()
            import base64
            base64_data = base64.b64encode(file_data).decode('utf-8')
            
            # Call calculator service with correct signature
            result = await call_calculator_service(
                service_id="cnc-milling",
                material_id=material_id,
                material_form="rod",
                quantity=1,
                length=None,
                width=None,
                height=None,
                n_dimensions=1,
                tolerance_id="1",
                finish_id="1",
                cover_id=["1"],
                k_otk="1",
                k_cert=["a", "f"],
                file_data=base64_data,
                file_name=file_record.original_filename,
                file_type=file_record.file_type
            )
            logger.info(f"Calculation result for file {file_record.id}: price={result.get('total_price', 'N/A')}")
            return result
            
        except Exception as e:
            logger.error(f"Error calculating price for file {file_record.id}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Return default values if calculation fails
            return {
                "total_price": 10000.0,
                "detail_price": 10000.0,
                "calculation_type": "rule_based"
            }
    
    async def create_order(self, db: AsyncSession, user_id: int, file_record: FileStorage, 
                          material_id: str, expected_price: float, order_date: datetime) -> Order:
        """Create order with calculation"""
        
        # Calculate price
        calc_result = await self.calculate_price_for_file(file_record, material_id)
        
        # Create order
        order = Order(
            user_id=user_id,
            file_id=file_record.id,
            service_id="cnc-milling",
            quantity=1,
            material_id=material_id,
            material_form="rod",
            tolerance_id="1",
            finish_id="1",
            cover_id=["1"],
            k_otk="1",
            k_cert=["a", "f"],
            n_dimensions=1,
            status="completed",
            created_at=order_date,
            updated_at=order_date,
            # Calculation results
            total_price=calc_result.get("total_price"),
            detail_price=calc_result.get("detail_price"),
            detail_price_one=calc_result.get("detail_price_one"),
            mat_volume=calc_result.get("mat_volume"),
            mat_weight=calc_result.get("mat_weight"),
            mat_price=calc_result.get("mat_price"),
            work_price=calc_result.get("work_price"),
            k_quantity=calc_result.get("k_quantity"),
            detail_time=calc_result.get("detail_time"),
            total_time=calc_result.get("total_time"),
            manufacturing_cycle=calc_result.get("manufacturing_cycle"),
            calculation_type=calc_result.get("calculation_type"),
            ml_model=calc_result.get("ml_model"),
            ml_confidence=calc_result.get("ml_confidence"),
            calculation_time=calc_result.get("calculation_time"),
            total_calculation_time=calc_result.get("total_calculation_time")
        )
        
        db.add(order)
        await db.commit()
        await db.refresh(order)
        
        logger.info(f"Created order {order.order_id} with price {order.total_price} (expected: {expected_price})")
        return order
    
    async def run(self):
        """Main execution function"""
        logger.info("=" * 60)
        logger.info("Starting demo user creation for diam-aero")
        logger.info("=" * 60)
        
        # File mappings from the screenshot
        # Order 9 → ДМРЕ.1.00.6151.002.stl
        # Order 10 → ДМРЕ.1.00.6151.001.stl
        # Order 11 → ДМРЕ.2.00.3202.005.stl
        file_mappings = [
            {
                "source": "ДМРЕ.1.00.6151.002.stl",
                "material": "alum_D16",
                "expected_price": 44652.43,
                "order_num": 9
            },
            {
                "source": "ДМРЕ.1.00.6151.001.stl", 
                "material": "alum_AMG5",
                "expected_price": 29341.98,
                "order_num": 10
            },
            {
                "source": "ДМРЕ.2.00.3202.005.stl",
                "material": "alum_D16", 
                "expected_price": 35343.3,
                "order_num": 11
            }
        ]
        
        # Set order date to 2025-10-23
        order_date = datetime(2025, 10, 23, 12, 0, 0, tzinfo=timezone.utc)
        
        async with AsyncSessionLocal() as db:
            try:
                # Get available materials
                logger.info("\n[1/5] Fetching available materials from API...")
                materials = await self.get_available_materials()
                logger.info(f"Available materials: {list(materials.keys())[:10]}")
                
                # Create user
                logger.info("\n[2/5] Creating user 'diam-aero'...")
                user = await self.create_user(db)
                logger.info(f"User created/found with ID: {user.id}")
                
                # Process each file
                logger.info(f"\n[3/5] Processing {len(file_mappings)} STL files...")
                for idx, mapping in enumerate(file_mappings, 1):
                    source_path = self.demo_dir / mapping["source"]
                    
                    logger.info(f"\n  Processing file {idx}/{len(file_mappings)}: {mapping['source']}")
                    
                    if not source_path.exists():
                        logger.error(f"  ERROR: Source file not found: {source_path}")
                        continue
                    
                    # Upload file
                    logger.info(f"  Uploading file...")
                    file_record = await self.upload_file(db, user.id, source_path, mapping["source"])
                    logger.info(f"  File uploaded with ID: {file_record.id}")
                    
                    # Map material
                    material_id = materials.get(mapping["material"], mapping["material"])
                    if not material_id:
                        material_id = "alum_D16"  # Default fallback
                        logger.warning(f"  Material {mapping['material']} not found, using {material_id}")
                    else:
                        logger.info(f"  Using material: {material_id}")
                    
                    # Create order
                    logger.info(f"  Creating order (expected price: {mapping['expected_price']})...")
                    order = await self.create_order(
                        db, user.id, file_record, material_id, 
                        mapping["expected_price"], order_date
                    )
                    
                    logger.info(f"  Order {order.order_id} created successfully!")
                    logger.info(f"  Status: {order.status}, Price: {order.total_price}")
                
                # Verification
                logger.info("\n[4/5] Verifying created data...")
                result = await db.execute(select(User).where(User.username == "diam-aero"))
                user = result.scalar_one_or_none()
                
                if user:
                    result = await db.execute(select(FileStorage).where(FileStorage.uploaded_by == user.id))
                    files = result.scalars().all()
                    
                    result = await db.execute(select(Order).where(Order.user_id == user.id))
                    orders = result.scalars().all()
                    
                    logger.info(f"  User: {user.username} (ID: {user.id})")
                    logger.info(f"  Files: {len(files)} uploaded")
                    logger.info(f"  Orders: {len(orders)} created")
                    
                    for order in orders:
                        logger.info(f"    Order {order.order_id}: {order.service_id}, price={order.total_price}, status={order.status}")
                
                logger.info("\n[5/5] Demo user creation completed successfully!")
                logger.info("=" * 60)
                
            except Exception as e:
                logger.error(f"\nERROR: Failed to create demo user: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                await db.rollback()
                raise

async def main():
    """Main function"""
    creator = DemoUserCreator()
    await creator.run()

if __name__ == "__main__":
    asyncio.run(main())

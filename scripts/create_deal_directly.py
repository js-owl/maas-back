"""Create order 38 deal directly in Bitrix and check for errors"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.database import AsyncSessionLocal
from backend import models
from backend.bitrix.client import bitrix_client
from backend.bitrix.funnel_manager import funnel_manager
from backend.bitrix.service import create_deal_from_order
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as db:
        # Get order 38
        result = await db.execute(
            select(models.Order).where(models.Order.order_id == 38)
        )
        order = result.scalar_one_or_none()
        
        if not order:
            print("Order 38 not found!")
            return
        
        print("="*60)
        print(f"Order 38 Details:")
        print("="*60)
        print(f"Order ID: {order.order_id}")
        print(f"User ID: {order.user_id}")
        print(f"Service ID: {order.service_id}")
        print(f"Status: {order.status}")
        print(f"Bitrix Deal ID: {order.bitrix_deal_id}")
        print(f"Total Price: {order.total_price}")
        
        # Get user
        user_result = await db.execute(
            select(models.User).where(models.User.id == order.user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            print("\nUser not found!")
            return
        
        print(f"\nUser Details:")
        print(f"  Username: {user.username}")
        print(f"  Email: {user.email}")
        print(f"  Full Name: {user.full_name}")
        print(f"  Bitrix Contact ID: {user.bitrix_contact_id}")
        
        # Ensure funnel is initialized
        print("\n" + "="*60)
        print("Initializing MaaS funnel...")
        print("="*60)
        try:
            success = await funnel_manager.ensure_maas_funnel()
            if success:
                print(f"✓ MaaS funnel initialized with category ID: {funnel_manager.get_category_id()}")
            else:
                print("✗ Failed to initialize MaaS funnel")
                return
        except Exception as e:
            print(f"✗ Error initializing funnel: {e}")
            import traceback
            traceback.print_exc()
            return
        
        # Get stage ID for order status
        stage_id = funnel_manager.get_stage_id_for_status(order.status)
        category_id = funnel_manager.get_category_id()
        
        print(f"\nFunnel Details:")
        print(f"  Category ID: {category_id}")
        print(f"  Stage ID for status '{order.status}': {stage_id}")
        
        # Get file if available
        file_record = None
        if order.file_id:
            from backend.files.service import get_file_by_id
            file_record = await get_file_by_id(db, order.file_id)
            if file_record:
                print(f"\nFile Details:")
                print(f"  Filename: {file_record.filename}")
                print(f"  File Path: {file_record.file_path}")
        
        # Get documents if available
        documents = []
        document_ids = order.document_ids
        if document_ids:
            # Parse if it's a JSON string
            if isinstance(document_ids, str):
                import json
                try:
                    document_ids = json.loads(document_ids)
                except:
                    document_ids = []
            
            # Only fetch if we have actual IDs
            if isinstance(document_ids, list) and len(document_ids) > 0:
                from backend.documents.service import get_documents_by_ids
                documents = await get_documents_by_ids(db, document_ids)
                if documents:
                    print(f"\nDocuments: {len(documents)} found")
            else:
                print(f"\nDocuments: None (document_ids is empty)")
        else:
            print(f"\nDocuments: None (document_ids is None)")
        
        # Try to create deal directly
        print("\n" + "="*60)
        print("Creating deal directly in Bitrix...")
        print("="*60)
        try:
            deal_id = await create_deal_from_order(order, file_record, documents)
            if deal_id:
                print(f"✓ Deal created successfully! Deal ID: {deal_id}")
                
                # Update order with deal ID
                order.bitrix_deal_id = deal_id
                await db.commit()
                print(f"✓ Order 38 updated with Bitrix Deal ID: {deal_id}")
            else:
                print("✗ Deal creation returned None (no error, but no deal ID)")
        except Exception as e:
            print(f"✗ Error creating deal: {e}")
            import traceback
            traceback.print_exc()
            
            # Try to get more details about the error
            print("\n" + "="*60)
            print("Checking Bitrix client configuration...")
            print("="*60)
            print(f"Bitrix configured: {bitrix_client.is_configured()}")
            if bitrix_client.is_configured():
                print(f"Bitrix URL: {bitrix_client.base_url}")

if __name__ == "__main__":
    asyncio.run(main())


"""Check sync errors by examining logs and testing a few orders"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.database import AsyncSessionLocal
from backend import models
from backend.bitrix.deal_sync_service import deal_sync_service
from backend.bitrix.client import bitrix_client
from backend.bitrix.funnel_manager import funnel_manager
from sqlalchemy import select
from backend.utils.logging import get_logger

logger = get_logger(__name__)


async def check_errors():
    """Check what errors are occurring during sync"""
    async with AsyncSessionLocal() as db:
        # Get a few orders with Bitrix deals
        result = await db.execute(
            select(models.Order)
            .where(models.Order.bitrix_deal_id.isnot(None))
            .limit(5)
        )
        orders = result.scalars().all()
        
        print("=" * 60)
        print("SYNC ERROR ANALYSIS")
        print("=" * 60)
        print(f"\nChecking {len(orders)} sample orders...\n")
        
        # Check funnel manager
        print("1. Funnel Manager Status:")
        if funnel_manager.is_initialized():
            print("   ✓ Funnel manager is initialized")
        else:
            print("   ✗ Funnel manager is NOT initialized - this will cause stage mapping errors")
        
        # Test each order
        for order in orders:
            print(f"\n{'='*60}")
            print(f"Order {order.order_id} (Deal {order.bitrix_deal_id})")
            print(f"{'='*60}")
            
            # Test getting deal
            try:
                deal_data = await bitrix_client.get_deal(order.bitrix_deal_id)
                if deal_data:
                    stage_id = deal_data.get("STAGE_ID") or deal_data.get("stage_id")
                    stage_name = deal_data.get("STAGE_NAME") or deal_data.get("stageName", "")
                    print(f"  ✓ Deal found in Bitrix")
                    print(f"    Stage ID: {stage_id}")
                    print(f"    Stage Name: {stage_name}")
                    
                    # Check stage mapping
                    if stage_id:
                        if funnel_manager.is_initialized():
                            mapped_status = funnel_manager.get_status_for_stage_id(stage_id)
                            if mapped_status:
                                print(f"    ✓ Mapped to order status: {mapped_status}")
                            else:
                                print(f"    ✗ No mapping found for stage {stage_id}")
                                print(f"      Current order status: {order.status}")
                        else:
                            print(f"    ✗ Cannot map (funnel manager not initialized)")
                    else:
                        print(f"    ✗ No STAGE_ID in deal data")
                else:
                    print(f"  ✗ Deal {order.bitrix_deal_id} not found in Bitrix")
            except Exception as e:
                print(f"  ✗ Error getting deal: {e}")
            
            # Test invoice check
            try:
                documents = await bitrix_client.list_document_generator_documents(order.bitrix_deal_id)
                if documents:
                    print(f"  ✓ Found {len(documents)} document(s) for deal")
                    for doc in documents[:3]:  # Show first 3
                        doc_id = doc.get("id") or doc.get("documentId", "N/A")
                        doc_title = doc.get("title") or doc.get("name", "N/A")
                        print(f"    - Document {doc_id}: {doc_title}")
                else:
                    print(f"  ✗ No documents found for deal (this is normal if no invoice generated yet)")
            except Exception as e:
                print(f"  ✗ Error checking documents: {e}")
        
        print(f"\n{'='*60}")
        print("SUMMARY")
        print(f"{'='*60}")
        print("\nCommon error causes:")
        print("1. Funnel manager not initialized → stage mapping fails")
        print("2. No STAGE_ID in deal → cannot determine order status")
        print("3. No documents in Bitrix → invoice download fails (normal)")
        print("4. Deal not found → 400 Bad Request from Bitrix API")
        print("\nNote: 'invoice_errors' and 'stage_errors' are expected for:")
        print("  - Orders without invoices yet (normal)")
        print("  - Orders with unmapped stages (may need funnel initialization)")
        print("  - Orders with deals that no longer exist in Bitrix")


if __name__ == "__main__":
    asyncio.run(check_errors())



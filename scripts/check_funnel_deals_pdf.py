"""Check funnel initialization, problematic deal IDs, and PDF storage"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.database import AsyncSessionLocal
from backend import models
from backend.bitrix.client import bitrix_client
from backend.bitrix.funnel_manager import funnel_manager
from backend.documents.service import get_documents_by_ids
from sqlalchemy import select
import json

async def check_all():
    """Check funnel, deal IDs, and PDF storage"""
    print("=" * 80)
    print("COMPREHENSIVE CHECK: FUNNEL, DEAL IDs, AND PDF STORAGE")
    print("=" * 80)
    
    # 1. Check and initialize funnel manager
    print("\n" + "=" * 80)
    print("1. FUNNEL MANAGER STATUS")
    print("=" * 80)
    print(f"Initialized: {funnel_manager.is_initialized()}")
    print(f"Category ID: {funnel_manager.get_category_id()}")
    
    if not funnel_manager.is_initialized():
        print("\n⚠ Funnel manager is NOT initialized. Initializing now...")
        try:
            success = await funnel_manager.ensure_maas_funnel()
            if success:
                print(f"✓ Funnel initialized successfully!")
                print(f"  Category ID: {funnel_manager.get_category_id()}")
                print(f"  Stage mapping: {funnel_manager.get_stage_mapping()}")
                print(f"  Status mapping: {funnel_manager.get_status_mapping()}")
            else:
                print("✗ Failed to initialize funnel")
        except Exception as e:
            print(f"✗ Error initializing funnel: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"\n✓ Funnel manager is initialized")
        print(f"  Category ID: {funnel_manager.get_category_id()}")
        print(f"  Stage mapping: {funnel_manager.get_stage_mapping()}")
        print(f"  Status mapping: {funnel_manager.get_status_mapping()}")
    
    # 2. Check all orders with Bitrix deals and find problematic ones
    print("\n" + "=" * 80)
    print("2. CHECKING DEAL IDs FOR ERRORS")
    print("=" * 80)
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(models.Order)
            .where(models.Order.bitrix_deal_id.isnot(None))
        )
        orders = result.scalars().all()
        
        print(f"\nTotal orders with Bitrix deals: {len(orders)}")
        
        problematic_deals = []
        valid_deals = []
        
        # Test first 10 deals to find patterns
        test_orders = orders[:10] if len(orders) > 10 else orders
        
        for order in test_orders:
            try:
                deal_data = await bitrix_client.get_deal(order.bitrix_deal_id)
                if deal_data:
                    valid_deals.append({
                        "order_id": order.order_id,
                        "deal_id": order.bitrix_deal_id,
                        "stage_id": deal_data.get("STAGE_ID") or deal_data.get("stage_id", "N/A")
                    })
                else:
                    problematic_deals.append({
                        "order_id": order.order_id,
                        "deal_id": order.bitrix_deal_id,
                        "error": "Deal not found (returned None)"
                    })
            except Exception as e:
                error_msg = str(e)
                if "400" in error_msg or "Bad Request" in error_msg:
                    problematic_deals.append({
                        "order_id": order.order_id,
                        "deal_id": order.bitrix_deal_id,
                        "error": f"400 Bad Request: {error_msg[:100]}"
                    })
                else:
                    problematic_deals.append({
                        "order_id": order.order_id,
                        "deal_id": order.bitrix_deal_id,
                        "error": f"Error: {error_msg[:100]}"
                    })
        
        print(f"\n✓ Valid deals: {len(valid_deals)}")
        if valid_deals:
            print("  Sample valid deals:")
            for deal in valid_deals[:3]:
                print(f"    Order {deal['order_id']} → Deal {deal['deal_id']} (Stage: {deal['stage_id']})")
        
        print(f"\n✗ Problematic deals: {len(problematic_deals)}")
        if problematic_deals:
            print("  Problematic deals:")
            for deal in problematic_deals[:5]:
                print(f"    Order {deal['order_id']} → Deal {deal['deal_id']}")
                print(f"      Error: {deal['error']}")
        
        # Check all problematic deals
        if len(orders) > 10:
            print(f"\nChecking remaining {len(orders) - 10} orders...")
            for order in orders[10:]:
                try:
                    deal_data = await bitrix_client.get_deal(order.bitrix_deal_id)
                    if not deal_data:
                        problematic_deals.append({
                            "order_id": order.order_id,
                            "deal_id": order.bitrix_deal_id,
                            "error": "Deal not found"
                        })
                except Exception as e:
                    error_msg = str(e)
                    if "400" in error_msg:
                        problematic_deals.append({
                            "order_id": order.order_id,
                            "deal_id": order.bitrix_deal_id,
                            "error": f"400 Bad Request"
                        })
        
        print(f"\nTotal problematic deals: {len(problematic_deals)}")
        if problematic_deals:
            print("\nSummary of problematic deal IDs:")
            deal_ids = [d['deal_id'] for d in problematic_deals]
            print(f"  Deal IDs: {deal_ids[:10]}{'...' if len(deal_ids) > 10 else ''}")
    
    # 3. Check PDF storage for order 41
    print("\n" + "=" * 80)
    print("3. PDF STORAGE AND API ACCESS CHECK (Order 41)")
    print("=" * 80)
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(models.Order).where(models.Order.order_id == 41)
        )
        order = result.scalar_one_or_none()
        
        if not order:
            print("✗ Order 41 not found")
        else:
            print(f"\nOrder 41 Details:")
            print(f"  Invoice file path: {order.invoice_file_path}")
            print(f"  Invoice IDs: {order.invoice_ids}")
            print(f"  Invoice URL: {order.invoice_url}")
            
            # Check if PDF file exists
            if order.invoice_file_path:
                pdf_path = Path(order.invoice_file_path)
                if pdf_path.exists():
                    print(f"\n✓ PDF file exists: {pdf_path}")
                    print(f"  Size: {pdf_path.stat().st_size} bytes")
                    print(f"  Extension: {pdf_path.suffix}")
                else:
                    print(f"\n✗ PDF file not found: {pdf_path}")
            
            # Check invoice document in database
            if order.invoice_ids:
                invoice_doc_ids = []
                if isinstance(order.invoice_ids, str):
                    try:
                        invoice_doc_ids = json.loads(order.invoice_ids)
                    except:
                        pass
                elif isinstance(order.invoice_ids, list):
                    invoice_doc_ids = order.invoice_ids
                
                if invoice_doc_ids:
                    invoices = await get_documents_by_ids(db, invoice_doc_ids)
                    if invoices:
                        invoice_doc = invoices[0]
                        print(f"\n✓ Invoice document in database:")
                        print(f"  Document ID: {invoice_doc.id}")
                        print(f"  File path: {invoice_doc.file_path}")
                        print(f"  Original filename: {invoice_doc.original_filename}")
                        print(f"  Category: {invoice_doc.document_category}")
                        print(f"  User ID: {invoice_doc.uploaded_by}")
                        
                        # Check if document file exists
                        doc_path = Path(invoice_doc.file_path)
                        if doc_path.exists():
                            print(f"  ✓ Document file exists: {doc_path}")
                            print(f"    Size: {doc_path.stat().st_size} bytes")
                        else:
                            print(f"  ✗ Document file not found: {doc_path}")
                    else:
                        print(f"\n✗ Invoice document not found in database")
                else:
                    print(f"\n⚠ No invoice document IDs found")
            else:
                print(f"\n⚠ No invoice_ids set")
            
            # Check API endpoint availability
            print(f"\nAPI Endpoints:")
            print(f"  GET /orders/41/invoices - Returns invoice documents")
            print(f"  GET /orders/41/invoice - Downloads invoice file")
            print(f"  GET /documents/{invoice_doc.id if order.invoice_ids else 'N/A'} - Downloads document")
    
    print("\n" + "=" * 80)
    print("CHECK COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(check_all())


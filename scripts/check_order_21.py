"""Check order 21 for updates and invoice files"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.database import AsyncSessionLocal
from backend import models
from backend.documents.service import get_documents_by_ids
from sqlalchemy import select
import json

async def check():
    """Check order 21"""
    print("=" * 80)
    print("ORDER 21 CHECK")
    print("=" * 80)
    
    async with AsyncSessionLocal() as db:
        # Get order 21
        result = await db.execute(
            select(models.Order).where(models.Order.order_id == 21)
        )
        order = result.scalar_one_or_none()
        
        if not order:
            print("\n✗ Order 21 not found")
            return
        
        print(f"\n1. Order 21 Basic Info:")
        print(f"   Order ID: {order.order_id}")
        print(f"   User ID: {order.user_id}")
        print(f"   Status: {order.status}")
        print(f"   Bitrix Deal ID: {order.bitrix_deal_id}")
        print(f"   Created: {order.created_at}")
        print(f"   Updated: {order.updated_at}")
        
        print(f"\n2. Invoice Information:")
        print(f"   invoice_file_path: {order.invoice_file_path}")
        print(f"   invoice_ids: {order.invoice_ids}")
        print(f"   invoice_url: {order.invoice_url}")
        print(f"   invoice_generated_at: {order.invoice_generated_at}")
        
        # Check invoice files on disk
        if order.invoice_file_path:
            invoice_path = Path(order.invoice_file_path)
            print(f"\n3. Invoice File on Disk:")
            if invoice_path.exists():
                print(f"   ✓ File exists: {invoice_path}")
                print(f"     Size: {invoice_path.stat().st_size} bytes")
                print(f"     Extension: {invoice_path.suffix}")
            else:
                print(f"   ✗ File NOT found: {invoice_path}")
            
            # Check for DOCX version
            docx_path = invoice_path.with_suffix('.docx')
            if docx_path.exists():
                print(f"   ✓ DOCX version exists: {docx_path}")
                print(f"     Size: {docx_path.stat().st_size} bytes")
            else:
                print(f"   ✗ DOCX version NOT found: {docx_path}")
        
        # Check invoice documents in database
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
                print(f"\n4. Invoice Documents in Database (IDs: {invoice_doc_ids}):")
                invoices = await get_documents_by_ids(db, invoice_doc_ids)
                if invoices:
                    for invoice in invoices:
                        print(f"\n   Document ID {invoice.id}:")
                        print(f"     filename: {invoice.filename}")
                        print(f"     original_filename: {invoice.original_filename}")
                        print(f"     file_path: {invoice.file_path}")
                        print(f"     file_size: {invoice.file_size} bytes")
                        print(f"     file_type: {invoice.file_type}")
                        print(f"     document_category: {invoice.document_category}")
                        print(f"     uploaded_at: {invoice.uploaded_at}")
                        
                        # Check if file exists
                        if invoice.file_path:
                            file_path = Path(invoice.file_path)
                            if file_path.exists():
                                print(f"     ✓ File exists on disk")
                            else:
                                print(f"     ✗ File NOT found on disk")
                else:
                    print("   ✗ No invoice documents found")
            else:
                print("\n4. No invoice document IDs found")
        else:
            print("\n4. No invoice_ids set - no invoices downloaded yet")
        
        # Check for any invoice files in the uploads/invoices directory for order 21
        print(f"\n5. Checking for invoice files in uploads/invoices/ for order 21:")
        invoice_dir = Path("uploads/invoices")
        if invoice_dir.exists():
            order_21_files = list(invoice_dir.glob(f"*order_21*"))
            if order_21_files:
                print(f"   Found {len(order_21_files)} file(s):")
                for file in order_21_files:
                    print(f"     - {file.name} ({file.stat().st_size} bytes, {file.suffix})")
            else:
                print(f"   ✗ No files found matching *order_21*")
        else:
            print(f"   ✗ Invoice directory not found")
        
        print("\n" + "=" * 80)
        print("SUMMARY:")
        print("=" * 80)
        if order.invoice_file_path or order.invoice_ids:
            print("✓ Order 21 has invoice information")
            if order.invoice_file_path:
                path = Path(order.invoice_file_path)
                if path.exists():
                    print(f"  ✓ PDF file exists: {path.suffix}")
                else:
                    print(f"  ✗ PDF file missing")
        else:
            print("✗ Order 21 has no invoice information yet")

if __name__ == "__main__":
    asyncio.run(check())



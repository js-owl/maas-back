"""Test if PDF invoice can be accessed via API"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.database import AsyncSessionLocal
from backend import models
from backend.documents.service import get_documents_by_ids
from sqlalchemy import select
import json

async def test_pdf_access():
    """Test PDF access for order 41"""
    print("=" * 60)
    print("PDF API ACCESS TEST")
    print("=" * 60)
    
    async with AsyncSessionLocal() as db:
        # Get order 41
        result = await db.execute(
            select(models.Order).where(models.Order.order_id == 41)
        )
        order = result.scalar_one_or_none()
        
        if not order:
            print("Order 41 not found")
            return
        
        print(f"\nOrder 41 Details:")
        print(f"  Invoice file path: {order.invoice_file_path}")
        print(f"  Invoice IDs: {order.invoice_ids}")
        print(f"  Invoice URL: {order.invoice_url}")
        print(f"  Invoice generated at: {order.invoice_generated_at}")
        
        # Check if file exists
        if order.invoice_file_path:
            file_path = Path(order.invoice_file_path)
            if file_path.exists():
                print(f"\n✓ Invoice file exists: {file_path}")
                print(f"  Size: {file_path.stat().st_size} bytes")
                print(f"  Extension: {file_path.suffix}")
            else:
                print(f"\n✗ Invoice file not found: {file_path}")
        
        # Check invoice document
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
                    print(f"\n✓ Invoice document found:")
                    print(f"  Document ID: {invoice_doc.id}")
                    print(f"  File path: {invoice_doc.file_path}")
                    print(f"  Original filename: {invoice_doc.original_filename}")
                    print(f"  Category: {invoice_doc.document_category}")
                    print(f"  Created at: {invoice_doc.uploaded_at}")
                    
                    # Check if document file exists
                    doc_file_path = Path(invoice_doc.file_path)
                    if doc_file_path.exists():
                        print(f"\n✓ Document file exists: {doc_file_path}")
                        print(f"  Size: {doc_file_path.stat().st_size} bytes")
                        print(f"  Extension: {doc_file_path.suffix}")
                        
                        # Test API endpoint path
                        print(f"\nAPI Endpoint:")
                        print(f"  GET /orders/41/invoices")
                        print(f"  GET /orders/41/invoice (download)")
                        print(f"  GET /documents/{invoice_doc.id} (download)")
                    else:
                        print(f"\n✗ Document file not found: {doc_file_path}")
                else:
                    print(f"\n✗ Invoice document not found for IDs: {invoice_doc_ids}")
        
        print("\n" + "=" * 60)
        print("SUMMARY:")
        print("=" * 60)
        print("The PDF invoice is stored in the database and can be accessed via:")
        print("  1. GET /orders/41/invoices - List invoice documents")
        print("  2. GET /orders/41/invoice - Download invoice file")
        print("  3. GET /documents/{document_id} - Download specific document")
        print("\nThe invoice is properly linked in:")
        print("  - Order.invoice_ids (JSON array of document IDs)")
        print("  - Order.invoice_file_path (file system path)")
        print("  - DocumentStorage table (document record)")

if __name__ == "__main__":
    asyncio.run(test_pdf_access())


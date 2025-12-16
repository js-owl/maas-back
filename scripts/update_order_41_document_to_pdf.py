"""Update order 41 invoice document to point to PDF instead of DOCX"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.database import AsyncSessionLocal
from backend import models
from backend.documents.service import get_documents_by_ids
from sqlalchemy import select, update
import json

async def update_document():
    """Update invoice document to point to PDF"""
    async with AsyncSessionLocal() as db:
        # Get order 41
        result = await db.execute(
            select(models.Order).where(models.Order.order_id == 41)
        )
        order = result.scalar_one_or_none()
        
        if not order:
            print("Order 41 not found")
            return
        
        print("=" * 60)
        print("Updating Order 41 Invoice Document")
        print("=" * 60)
        print(f"Invoice IDs: {order.invoice_ids}")
        print(f"Invoice file path: {order.invoice_file_path}")
        
        if not order.invoice_ids:
            print("No invoice_ids found")
            return
        
        # Parse invoice_ids
        invoice_doc_ids = []
        if isinstance(order.invoice_ids, str):
            try:
                invoice_doc_ids = json.loads(order.invoice_ids)
            except:
                pass
        elif isinstance(order.invoice_ids, list):
            invoice_doc_ids = order.invoice_ids
        
        if not invoice_doc_ids:
            print("No invoice document IDs found")
            return
        
        # Get the invoice document
        invoices = await get_documents_by_ids(db, invoice_doc_ids)
        if not invoices:
            print("Invoice document not found")
            return
        
        invoice_doc = invoices[0]
        print(f"\nCurrent document:")
        print(f"  ID: {invoice_doc.id}")
        print(f"  File path: {invoice_doc.file_path}")
        print(f"  Original filename: {invoice_doc.original_filename}")
        
        # Update to PDF
        pdf_path = "uploads/invoices/invoice_order_41_deal_65.pdf"
        pdf_filename = "invoice_order_41.pdf"
        
        if Path(pdf_path).exists():
            await db.execute(
                update(models.DocumentStorage)
                .where(models.DocumentStorage.id == invoice_doc.id)
                .values(
                    file_path=pdf_path,
                    original_filename=pdf_filename
                )
            )
            await db.commit()
            print(f"\n✓ Updated document to PDF:")
            print(f"  File path: {pdf_path}")
            print(f"  Original filename: {pdf_filename}")
        else:
            print(f"\n✗ PDF file not found: {pdf_path}")


if __name__ == "__main__":
    asyncio.run(update_document())


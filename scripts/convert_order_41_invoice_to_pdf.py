"""Convert existing invoice for order 41 from DOCX to PDF"""
import asyncio
import sys
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.database import AsyncSessionLocal
from backend import models
from backend.documents.service import get_documents_by_ids, create_document_from_file_path
from sqlalchemy import select, update
import json

async def convert_order_41_invoice():
    """Convert order 41 invoice from DOCX to PDF"""
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
        print(f"Order 41 Invoice Conversion")
        print("=" * 60)
        print(f"Invoice file path: {order.invoice_file_path}")
        print(f"Invoice IDs: {order.invoice_ids}")
        
        # Check if invoice file exists
        if not order.invoice_file_path:
            print("No invoice file path found")
            return
        
        invoice_path = Path(order.invoice_file_path)
        if not invoice_path.exists():
            print(f"Invoice file not found: {invoice_path}")
            return
        
        print(f"Found invoice file: {invoice_path} ({invoice_path.stat().st_size} bytes)")
        
        # Check if it's DOCX
        if invoice_path.suffix.lower() != ".docx":
            print(f"File is not DOCX (it's {invoice_path.suffix}), skipping conversion")
            return
        
        # Convert to PDF
        pdf_path = invoice_path.with_suffix('.pdf')
        print(f"\nConverting to PDF: {pdf_path}")
        
        try:
            result = subprocess.run(
                [
                    "pandoc",
                    str(invoice_path),
                    "-o", str(pdf_path)
                ],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0 and pdf_path.exists():
                print(f"✓ Successfully converted to PDF: {pdf_path} ({pdf_path.stat().st_size} bytes)")
                
                # Update order's invoice_file_path to point to PDF
                await db.execute(
                    update(models.Order)
                    .where(models.Order.order_id == 41)
                    .values(invoice_file_path=str(pdf_path))
                )
                await db.commit()
                print(f"✓ Updated order 41 invoice_file_path to PDF")
                
                # If invoice_ids exists, update the document record
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
                        # Get the invoice document
                        invoices = await get_documents_by_ids(db, invoice_doc_ids)
                        if invoices:
                            invoice_doc = invoices[0]
                            print(f"✓ Invoice document ID {invoice_doc.id} exists")
                            print(f"  Current file_path: {invoice_doc.file_path}")
                            # Note: We could update the document's file_path, but it's better to keep both
                            print(f"  PDF file available at: {pdf_path}")
                
            else:
                print(f"✗ Conversion failed:")
                print(f"  Return code: {result.returncode}")
                print(f"  Stdout: {result.stdout}")
                print(f"  Stderr: {result.stderr}")
                
        except Exception as e:
            print(f"✗ Error during conversion: {e}")
            import traceback
            traceback.print_exc()
        
        print("=" * 60)

if __name__ == "__main__":
    asyncio.run(convert_order_41_invoice())



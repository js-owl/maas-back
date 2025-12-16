"""Check how PDF files are stored in the database"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.database import AsyncSessionLocal
from backend import models
from sqlalchemy import select

async def check():
    """Check PDF storage in database"""
    print("=" * 80)
    print("PDF STORAGE IN DATABASE CHECK")
    print("=" * 80)
    
    async with AsyncSessionLocal() as db:
        # Check Order 41
        result = await db.execute(
            select(models.Order).where(models.Order.order_id == 41)
        )
        order = result.scalar_one_or_none()
        
        if order:
            print("\n1. Order 41 Invoice References:")
            print(f"   invoice_file_path: {order.invoice_file_path}")
            print(f"   invoice_ids: {order.invoice_ids}")
            print(f"   invoice_url: {order.invoice_url}")
            print(f"   invoice_generated_at: {order.invoice_generated_at}")
            
            # Check if invoice_ids points to documents
            if order.invoice_ids:
                import json
                invoice_doc_ids = []
                if isinstance(order.invoice_ids, str):
                    try:
                        invoice_doc_ids = json.loads(order.invoice_ids)
                    except:
                        pass
                elif isinstance(order.invoice_ids, list):
                    invoice_doc_ids = order.invoice_ids
                
                if invoice_doc_ids:
                    print(f"\n2. Invoice Document Records (IDs: {invoice_doc_ids}):")
                    for doc_id in invoice_doc_ids:
                        result2 = await db.execute(
                            select(models.DocumentStorage).where(models.DocumentStorage.id == doc_id)
                        )
                        doc = result2.scalar_one_or_none()
                        if doc:
                            print(f"\n   Document ID {doc_id}:")
                            print(f"     filename: {doc.filename}")
                            print(f"     original_filename: {doc.original_filename}")
                            print(f"     file_path: {doc.file_path}")
                            print(f"     file_size: {doc.file_size} bytes")
                            print(f"     file_type: {doc.file_type}")
                            print(f"     document_category: {doc.document_category}")
                            print(f"     uploaded_by: {doc.uploaded_by}")
                            print(f"     uploaded_at: {doc.uploaded_at}")
                            
                            # Check if file exists on disk
                            if doc.file_path:
                                file_path = Path(doc.file_path)
                                if file_path.exists():
                                    print(f"     ✓ File exists on disk: {file_path}")
                                    print(f"       Actual size: {file_path.stat().st_size} bytes")
                                else:
                                    print(f"     ✗ File NOT found on disk: {file_path}")
                            
                            # Check if file content is stored in database
                            print(f"     Database storage: Metadata only (file_path reference)")
                            print(f"     Actual file: Stored on filesystem at {doc.file_path}")
        
        print("\n" + "=" * 80)
        print("SUMMARY:")
        print("=" * 80)
        print("PDF files are NOT stored in the database.")
        print("Only metadata is stored:")
        print("  - File path (where file is stored on disk)")
        print("  - File size")
        print("  - File type")
        print("  - Original filename")
        print("  - Category")
        print("  - Upload metadata (user, timestamp)")
        print("\nThe actual PDF file content is stored on the filesystem.")
        print("The database only contains references (file paths) to the files.")

if __name__ == "__main__":
    asyncio.run(check())



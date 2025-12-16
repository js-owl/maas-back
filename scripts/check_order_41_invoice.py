"""Check order 41 (deal 65) for invoice documents"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.database import AsyncSessionLocal
from backend import models
from backend.bitrix.client import bitrix_client
from sqlalchemy import select
import json

async def check_order_41():
    async with AsyncSessionLocal() as db:
        # Check order 41
        result = await db.execute(
            select(models.Order).where(models.Order.order_id == 41)
        )
        order = result.scalar_one_or_none()
        
        if not order:
            print("Order 41 not found")
            return
        
        print("=" * 60)
        print(f"Order 41 Status:")
        print(f"  bitrix_deal_id: {order.bitrix_deal_id}")
        print(f"  invoice_file_path: {order.invoice_file_path}")
        print(f"  invoice_url: {order.invoice_url}")
        print(f"  invoice_generated_at: {order.invoice_generated_at}")
        print(f"  document_ids: {order.document_ids}")
        print(f"  invoice_ids: {order.invoice_ids}")
        print("=" * 60)
        
        # Check if invoice file exists
        if order.invoice_file_path:
            file_path = Path(order.invoice_file_path)
            if file_path.exists():
                print(f"✓ Invoice file exists: {file_path}")
                print(f"  Size: {file_path.stat().st_size} bytes")
            else:
                print(f"✗ Invoice file path exists in DB but file not found: {file_path}")
        
        # Check invoice_ids first (Bitrix-generated invoices)
        if order.invoice_ids:
            try:
                invoice_doc_ids = json.loads(order.invoice_ids) if isinstance(order.invoice_ids, str) else order.invoice_ids
                print(f"✓ Order has {len(invoice_doc_ids)} invoice(s) attached: {invoice_doc_ids}")
                
                # Get invoice document details
                from backend.documents.service import get_documents_by_ids
                invoices = await get_documents_by_ids(db, invoice_doc_ids)
                for invoice in invoices:
                    print(f"  - Invoice ID {invoice.id}: {invoice.original_filename} ({invoice.document_category})")
                    file_path = invoice.file_path if hasattr(invoice, 'file_path') else getattr(invoice, 'document_path', None)
                    if file_path:
                        invoice_path = Path(file_path)
                        if invoice_path.exists():
                            print(f"    File exists: {invoice_path} ({invoice_path.stat().st_size} bytes)")
                        else:
                            print(f"    File not found: {invoice_path}")
            except Exception as e:
                print(f"Error parsing invoice_ids: {e}")
        
        # Check document_ids (user-uploaded technical documents)
        if order.document_ids:
            try:
                doc_ids = json.loads(order.document_ids) if isinstance(order.document_ids, str) else order.document_ids
                print(f"✓ Order has {len(doc_ids)} document(s) attached: {doc_ids}")
                
                # Get document details
                from backend.documents.service import get_documents_by_ids
                documents = await get_documents_by_ids(db, doc_ids)
                for doc in documents:
                    print(f"  - Document ID {doc.id}: {doc.original_filename} ({doc.document_category})")
                    file_path = doc.file_path if hasattr(doc, 'file_path') else getattr(doc, 'document_path', None)
                    if file_path:
                        doc_path = Path(file_path)
                        if doc_path.exists():
                            print(f"    File exists: {doc_path} ({doc_path.stat().st_size} bytes)")
                        else:
                            print(f"    File not found: {doc_path}")
            except Exception as e:
                print(f"Error parsing document_ids: {e}")
        
        # Check Bitrix for documents
        if order.bitrix_deal_id:
            print("\n" + "=" * 60)
            print(f"Checking Bitrix Deal {order.bitrix_deal_id} for documents:")
            print("=" * 60)
            
            documents = await bitrix_client.list_document_generator_documents(order.bitrix_deal_id)
            if documents:
                print(f"Found {len(documents)} document(s) in Bitrix:")
                for i, doc in enumerate(documents, 1):
                    print(f"\n  Document {i}:")
                    print(f"    ID: {doc.get('id')}")
                    print(f"    Title: {doc.get('title')}")
                    print(f"    Type: {doc.get('type')}")
                    print(f"    Template: {doc.get('templateName')}")
                    print(f"    Created: {doc.get('createTime')}")
                    
                    # Get full document info
                    doc_id = doc.get('id') or doc.get('documentId')
                    if doc_id:
                        doc_info = await bitrix_client.get_document_generator_document(doc_id)
                        if doc_info:
                            print(f"    publicUrl: {doc_info.get('publicUrl') or 'Not available'}")
                            print(f"    downloadUrl: {doc_info.get('downloadUrl') or 'Not available'}")
                            print(f"    pdfUrl: {doc_info.get('pdfUrl') or 'Not available'}")
            else:
                print("No documents found in Bitrix for this deal")
        
        print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(check_order_41())


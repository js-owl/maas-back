"""Check order 30 details"""
import asyncio
import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent))

from backend.database import AsyncSessionLocal
from backend import models
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as db:
        # Get order 30
        result = await db.execute(
            select(models.Order).where(models.Order.order_id == 30)
        )
        order = result.scalar_one_or_none()
        
        if not order:
            print("Order 30 not found!")
            return
        
        print(f"Order 30 details:")
        print(f"  Order ID: {order.order_id}")
        print(f"  User ID: {order.user_id}")
        print(f"  File ID: {order.file_id}")
        print(f"  Document IDs: {order.document_ids}")
        print(f"  Bitrix Deal ID: {order.bitrix_deal_id}")
        print(f"  Status: {order.status}")
        
        # Check if there are any files for this user
        from backend.files.service import get_file_by_id
        from sqlalchemy import select as sql_select
        
        if order.file_id:
            file_record = await get_file_by_id(db, order.file_id)
            if file_record:
                print(f"\nFile record found:")
                print(f"  File ID: {file_record.id}")
                print(f"  File path: {file_record.file_path}")
                print(f"  Filename: {file_record.filename}")
                print(f"  Original filename: {file_record.original_filename}")
                if file_record.file_path:
                    file_path = Path(file_record.file_path)
                    print(f"  File exists: {file_path.exists()}")
        
        # Check documents
        if order.document_ids:
            try:
                doc_ids = json.loads(order.document_ids) if isinstance(order.document_ids, str) else order.document_ids
                if doc_ids:
                    from backend.documents.service import get_documents_by_ids
                    documents = await get_documents_by_ids(db, doc_ids)
                    print(f"\nDocuments found: {len(documents)}")
                    for doc in documents:
                        print(f"  Document ID: {doc.id}")
                        print(f"  Document path: {doc.document_path}")
                        print(f"  Document name: {doc.document_name}")
                        if doc.document_path:
                            doc_path = Path(doc.document_path)
                            print(f"  Document exists: {doc_path.exists()}")
            except Exception as e:
                print(f"Error parsing document_ids: {e}")
        
        # Check all files (FileStorage might not have user_id, check by order_id or just list recent files)
        print(f"\nChecking recent files...")
        files_result = await db.execute(
            sql_select(models.FileStorage).order_by(models.FileStorage.id.desc()).limit(10)
        )
        recent_files = files_result.scalars().all()
        print(f"Found {len(recent_files)} recent files")
        for f in recent_files:
            print(f"  File ID: {f.id}, Path: {f.file_path}, Filename: {f.filename}")

if __name__ == "__main__":
    asyncio.run(main())


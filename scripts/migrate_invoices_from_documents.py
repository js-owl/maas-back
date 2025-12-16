"""Migration script to move invoice data from documents table to invoices table"""
import asyncio
import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.database import AsyncSessionLocal, ensure_invoices_table
from backend import models
from backend.invoices.service import create_invoice_from_file_path
from backend.orders.service import get_order_by_id
from sqlalchemy import select, text, update
from datetime import datetime, timezone

async def migrate_invoices():
    """Migrate invoice documents from documents table to invoices table"""
    print("=" * 80)
    print("MIGRATING INVOICES FROM DOCUMENTS TO INVOICES TABLE")
    print("=" * 80)
    
    # Ensure invoices table exists
    await ensure_invoices_table()
    
    async with AsyncSessionLocal() as db:
        try:
            # Find all documents with document_category="invoice"
            result = await db.execute(
                select(models.DocumentStorage).where(
                    models.DocumentStorage.document_category == "invoice"
                )
            )
            invoice_documents = result.scalars().all()
            
            print(f"\nFound {len(invoice_documents)} invoice document(s) in documents table")
            
            if not invoice_documents:
                print("No invoices to migrate")
                return
            
            migrated_count = 0
            error_count = 0
            invoice_id_mapping = {}  # Map old document ID to new invoice ID
            
            for doc in invoice_documents:
                try:
                    # Find the order that references this document
                    # We need to check all orders' invoice_ids
                    orders_result = await db.execute(
                        select(models.Order)
                    )
                    orders = orders_result.scalars().all()
                    
                    order_id = None
                    for order in orders:
                        if order.invoice_ids:
                            try:
                                invoice_ids = json.loads(order.invoice_ids) if isinstance(order.invoice_ids, str) else order.invoice_ids
                                if doc.id in invoice_ids:
                                    order_id = order.order_id
                                    break
                            except:
                                pass
                    
                    if not order_id:
                        print(f"  ⚠ Document {doc.id} ({doc.original_filename}) not linked to any order, skipping")
                        error_count += 1
                        continue
                    
                    # Check if invoice already exists for this document
                    existing_result = await db.execute(
                        select(models.InvoiceStorage).where(
                            models.InvoiceStorage.filename == doc.filename
                        )
                    )
                    existing_invoice = existing_result.scalar_one_or_none()
                    
                    if existing_invoice:
                        print(f"  ✓ Invoice already exists for document {doc.id}: invoice ID {existing_invoice.id}")
                        invoice_id_mapping[doc.id] = existing_invoice.id
                        continue
                    
                    # Create invoice record
                    invoice_data = {
                        "filename": doc.filename,
                        "original_filename": doc.original_filename,
                        "file_path": doc.file_path,
                        "file_size": doc.file_size,
                        "file_type": doc.file_type,
                        "order_id": order_id,
                        "bitrix_document_id": None,  # We don't have this info from documents
                        "generated_at": doc.uploaded_at,  # Use uploaded_at as generated_at
                        "created_at": doc.uploaded_at,
                        "updated_at": datetime.now(timezone.utc)
                    }
                    
                    from backend.invoices.repository import create_invoice
                    new_invoice = await create_invoice(db, invoice_data)
                    invoice_id_mapping[doc.id] = new_invoice.id
                    
                    print(f"  ✓ Migrated document {doc.id} -> invoice {new_invoice.id} (order {order_id})")
                    migrated_count += 1
                    
                except Exception as e:
                    print(f"  ✗ Error migrating document {doc.id}: {e}")
                    error_count += 1
                    import traceback
                    traceback.print_exc()
            
            # Update orders' invoice_ids to reference new invoice IDs
            print(f"\nUpdating orders' invoice_ids...")
            orders_result = await db.execute(select(models.Order))
            orders = orders_result.scalars().all()
            
            updated_orders = 0
            for order in orders:
                if not order.invoice_ids:
                    continue
                
                try:
                    old_invoice_ids = json.loads(order.invoice_ids) if isinstance(order.invoice_ids, str) else order.invoice_ids
                    new_invoice_ids = []
                    updated = False
                    
                    for old_id in old_invoice_ids:
                        if old_id in invoice_id_mapping:
                            new_id = invoice_id_mapping[old_id]
                            if new_id not in new_invoice_ids:
                                new_invoice_ids.append(new_id)
                                updated = True
                        else:
                            # Keep old ID if not migrated (shouldn't happen, but be safe)
                            new_invoice_ids.append(old_id)
                    
                    if updated:
                        await db.execute(
                            update(models.Order)
                            .where(models.Order.order_id == order.order_id)
                            .values(invoice_ids=json.dumps(new_invoice_ids))
                        )
                        await db.commit()
                        print(f"  ✓ Updated order {order.order_id}: {old_invoice_ids} -> {new_invoice_ids}")
                        updated_orders += 1
                        
                except Exception as e:
                    print(f"  ✗ Error updating order {order.order_id}: {e}")
                    await db.rollback()
            
            print(f"\n" + "=" * 80)
            print("MIGRATION SUMMARY")
            print("=" * 80)
            print(f"  Migrated: {migrated_count}")
            print(f"  Already existed: {len(invoice_id_mapping) - migrated_count}")
            print(f"  Errors: {error_count}")
            print(f"  Updated orders: {updated_orders}")
            print(f"\nMigration completed!")
            
        except Exception as e:
            await db.rollback()
            print(f"\n✗ Migration failed: {e}")
            import traceback
            traceback.print_exc()
            raise

if __name__ == "__main__":
    asyncio.run(migrate_invoices())


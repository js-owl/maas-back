"""
Migration script to separate documents and invoices into separate columns

This script:
1. Reads all orders with document_ids
2. Splits documents by category (invoice vs non-invoice)
3. Populates document_ids (user docs) and invoice_ids (invoices) columns
"""
import asyncio
import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.database import AsyncSessionLocal
from backend import models
from backend.documents.service import get_documents_by_ids
from sqlalchemy import select, update
from backend.utils.logging import get_logger

logger = get_logger(__name__)


async def migrate_documents_invoices():
    """Migrate existing document_ids to separate document_ids and invoice_ids columns"""
    async with AsyncSessionLocal() as db:
        try:
            # Get all orders with document_ids
            result = await db.execute(
                select(models.Order)
                .where(models.Order.document_ids.isnot(None))
            )
            orders = result.scalars().all()
            
            logger.info(f"Found {len(orders)} orders with document_ids to migrate")
            
            stats = {
                "total_orders": len(orders),
                "migrated": 0,
                "skipped": 0,
                "errors": 0,
                "documents_moved_to_invoices": 0,
                "documents_kept_in_documents": 0
            }
            
            for order in orders:
                try:
                    # Parse existing document_ids
                    doc_ids = []
                    if isinstance(order.document_ids, str):
                        try:
                            doc_ids = json.loads(order.document_ids)
                        except (json.JSONDecodeError, ValueError):
                            logger.warning(f"Invalid document_ids format for order {order.order_id}: {order.document_ids}")
                            stats["skipped"] += 1
                            continue
                    elif isinstance(order.document_ids, list):
                        doc_ids = order.document_ids
                    
                    if not doc_ids:
                        stats["skipped"] += 1
                        continue
                    
                    # Get document records to check categories
                    documents = await get_documents_by_ids(db, doc_ids)
                    
                    # Split by category
                    user_doc_ids = []
                    invoice_doc_ids = []
                    
                    for doc in documents:
                        if doc.document_category == "invoice":
                            invoice_doc_ids.append(doc.id)
                            stats["documents_moved_to_invoices"] += 1
                        else:
                            user_doc_ids.append(doc.id)
                            stats["documents_kept_in_documents"] += 1
                    
                    # Update order with separated IDs
                    update_data = {}
                    
                    # Update document_ids (only user-uploaded docs)
                    if user_doc_ids:
                        update_data["document_ids"] = json.dumps(user_doc_ids)
                    else:
                        update_data["document_ids"] = None
                    
                    # Update invoice_ids (only invoices)
                    if invoice_doc_ids:
                        update_data["invoice_ids"] = json.dumps(invoice_doc_ids)
                    else:
                        update_data["invoice_ids"] = None
                    
                    # Only update if there are changes
                    if update_data:
                        await db.execute(
                            update(models.Order)
                            .where(models.Order.order_id == order.order_id)
                            .values(**update_data)
                        )
                        stats["migrated"] += 1
                        logger.info(
                            f"Order {order.order_id}: "
                            f"{len(user_doc_ids)} docs, {len(invoice_doc_ids)} invoices"
                        )
                    else:
                        stats["skipped"] += 1
                    
                except Exception as e:
                    logger.error(f"Error migrating order {order.order_id}: {e}", exc_info=True)
                    stats["errors"] += 1
            
            # Commit all changes
            await db.commit()
            
            logger.info("=" * 60)
            logger.info("Migration completed!")
            logger.info(f"Total orders processed: {stats['total_orders']}")
            logger.info(f"Successfully migrated: {stats['migrated']}")
            logger.info(f"Skipped: {stats['skipped']}")
            logger.info(f"Errors: {stats['errors']}")
            logger.info(f"Documents moved to invoices: {stats['documents_moved_to_invoices']}")
            logger.info(f"Documents kept in documents: {stats['documents_kept_in_documents']}")
            logger.info("=" * 60)
            
            return stats
            
        except Exception as e:
            logger.error(f"Migration failed: {e}", exc_info=True)
            await db.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(migrate_documents_invoices())



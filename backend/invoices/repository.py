"""
Invoices repository module
Database operations for invoice management
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend import models


async def create_invoice(db: AsyncSession, invoice_data: dict) -> models.InvoiceStorage:
    """Create a new invoice record"""
    db_invoice = models.InvoiceStorage(**invoice_data)
    db.add(db_invoice)
    await db.commit()
    await db.refresh(db_invoice)
    return db_invoice


async def get_invoice_by_id(db: AsyncSession, invoice_id: int) -> Optional[models.InvoiceStorage]:
    """Get invoice by ID"""
    result = await db.execute(select(models.InvoiceStorage).where(models.InvoiceStorage.id == invoice_id))
    return result.scalar_one_or_none()


async def get_invoices_by_ids(db: AsyncSession, invoice_ids: List[int]) -> List[models.InvoiceStorage]:
    """Get multiple invoices by their IDs"""
    if not invoice_ids:
        return []
    result = await db.execute(select(models.InvoiceStorage).where(models.InvoiceStorage.id.in_(invoice_ids)))
    return result.scalars().all()


async def get_invoices_by_order_id(db: AsyncSession, order_id: int) -> List[models.InvoiceStorage]:
    """Get all invoices for a specific order"""
    result = await db.execute(select(models.InvoiceStorage).where(models.InvoiceStorage.order_id == order_id))
    return result.scalars().all()


async def get_invoice_by_filename(db: AsyncSession, filename: str) -> Optional[models.InvoiceStorage]:
    """Get invoice by filename"""
    result = await db.execute(select(models.InvoiceStorage).where(models.InvoiceStorage.filename == filename))
    return result.scalar_one_or_none()


async def delete_invoice(db: AsyncSession, invoice_id: int) -> bool:
    """Delete invoice record"""
    invoice = await get_invoice_by_id(db, invoice_id)
    if not invoice:
        return False
    
    await db.delete(invoice)
    await db.commit()
    return True


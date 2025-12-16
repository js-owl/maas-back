"""
Invoice service module
Handles invoice download and management from Bitrix
"""
import os
import httpx
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from backend import models
from backend.bitrix.client import bitrix_client
from backend.core.exceptions import ExternalServiceException, FileProcessingException
from backend.utils.logging import get_logger

logger = get_logger(__name__)


class InvoiceService:
    """Service for managing invoice downloads from Bitrix"""
    
    def __init__(self):
        self.invoice_dir = Path("uploads/invoices")
        self.invoice_dir.mkdir(parents=True, exist_ok=True)
    
    async def check_and_download_invoice(self, db: AsyncSession, order_id: int) -> bool:
        """Check Bitrix for invoice file and download if available"""
        try:
            # Get order with Bitrix deal ID
            result = await db.execute(
                select(models.Order).where(models.Order.order_id == order_id)
            )
            order = result.scalar_one_or_none()
            
            if not order:
                logger.error(f"[INVOICE_CHECK] Order {order_id} not found")
                return False
            
            if not order.bitrix_deal_id:
                logger.warning(f"[INVOICE_CHECK] Order {order_id} has no Bitrix deal ID")
                return False
            
            # Check if invoice already exists
            if order.invoice_file_path and os.path.exists(order.invoice_file_path):
                logger.info(f"[INVOICE_CHECK] Invoice already exists for order {order_id}")
                return True
            
            # Check Bitrix for invoice
            invoice_url = await self._get_invoice_url_from_bitrix(order.bitrix_deal_id)
            if not invoice_url:
                logger.info(f"[INVOICE_CHECK] No invoice found in Bitrix for deal {order.bitrix_deal_id}")
                return False
            
            # Download invoice
            success = await self._download_invoice_from_bitrix(
                db, order_id, order.bitrix_deal_id, invoice_url
            )
            
            if success:
                logger.info(f"[INVOICE_CHECK] Invoice downloaded for order {order_id}")
            else:
                logger.warning(f"[INVOICE_CHECK] Failed to download invoice for order {order_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"[INVOICE_CHECK] Error checking invoice for order {order_id}: {e}")
            return False
    
    async def _get_invoice_url_from_bitrix(self, deal_id: int) -> Optional[str]:
        """Get invoice URL from Bitrix deal using document generator API"""
        try:
            if not bitrix_client.is_configured():
                logger.warning("[INVOICE_URL] Bitrix not configured")
                return None
            
            # List document generator documents for this deal
            documents = await bitrix_client.list_document_generator_documents(deal_id)
            if not documents:
                logger.debug(f"[INVOICE_URL] No document generator documents found for deal {deal_id}")
                return None
            
            # Find invoice documents (typically documents with "invoice" in name or type)
            invoice_document = None
            for doc in documents:
                doc_name = (doc.get("title") or doc.get("name") or "").lower()
                doc_type = (doc.get("type") or doc.get("templateName") or "").lower()
                
                # Check if this looks like an invoice
                if "invoice" in doc_name or "invoice" in doc_type or "счет" in doc_name:
                    invoice_document = doc
                    break
            
            # If no invoice found by name, use the most recent document
            if not invoice_document and documents:
                documents_sorted = sorted(
                    documents,
                    key=lambda x: x.get("createTime", "") or x.get("dateCreate", ""),
                    reverse=True
                )
                invoice_document = documents_sorted[0]
                logger.info(f"[INVOICE_URL] Using most recent document as invoice for deal {deal_id}")
            
            if not invoice_document:
                logger.debug(f"[INVOICE_URL] No suitable invoice document found for deal {deal_id}")
                return None
            
            # Get document ID
            document_id = invoice_document.get("id") or invoice_document.get("documentId")
            if not document_id:
                logger.warning(f"[INVOICE_URL] No document ID found in invoice document for deal {deal_id}")
                return None
            
            # Get full document details
            document_info = await bitrix_client.get_document_generator_document(document_id)
            if not document_info:
                logger.warning(f"[INVOICE_URL] Could not get document details for document {document_id}")
                return None
            
            # Get download URL (prefer PDF, fallback to DOCX)
            download_url = None
            if document_info.get("pdfUrl"):
                download_url = document_info.get("pdfUrl")
            elif document_info.get("downloadUrl"):
                download_url = document_info.get("downloadUrl")
            elif document_info.get("pdfUrlMachine"):
                download_url = document_info.get("pdfUrlMachine")
            elif document_info.get("downloadUrlMachine"):
                download_url = document_info.get("downloadUrlMachine")
            
            if download_url:
                logger.info(f"[INVOICE_URL] Found invoice URL for deal {deal_id}: {download_url}")
                return download_url
            else:
                logger.warning(f"[INVOICE_URL] No download URL found for document {document_id}")
                return None
            
        except Exception as e:
            logger.error(f"[INVOICE_URL] Error getting invoice URL from Bitrix: {e}", exc_info=True)
            return None
    
    async def _download_invoice_from_bitrix(
        self, 
        db: AsyncSession, 
        order_id: int, 
        deal_id: int, 
        invoice_url: str
    ) -> bool:
        """Download invoice file from Bitrix and store locally"""
        try:
            # Download file from Bitrix
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(invoice_url)
                response.raise_for_status()
                
                # Generate filename
                content_type = response.headers.get("content-type", "")
                if "pdf" in content_type:
                    extension = "pdf"
                elif "docx" in content_type or "word" in content_type:
                    extension = "docx"
                else:
                    extension = "pdf"  # Default to PDF
                
                filename = f"invoice_order_{order_id}_deal_{deal_id}.{extension}"
                file_path = self.invoice_dir / filename
                
                # Save file
                with open(file_path, "wb") as f:
                    f.write(response.content)
                
                # Update order with invoice info
                await db.execute(
                    update(models.Order)
                    .where(models.Order.order_id == order_id)
                    .values(
                        invoice_url=invoice_url,
                        invoice_file_path=str(file_path),
                        invoice_generated_at=datetime.now(timezone.utc)
                    )
                )
                await db.commit()
                
                logger.info(f"[INVOICE_DOWNLOAD] Invoice saved: {file_path}")
                return True
                
        except httpx.HTTPError as e:
            logger.error(f"[INVOICE_DOWNLOAD] HTTP error downloading invoice: {e}")
            return False
        except Exception as e:
            logger.error(f"[INVOICE_DOWNLOAD] Error downloading invoice: {e}")
            return False
    
    async def get_invoice_file_path(self, db: AsyncSession, order_id: int) -> Optional[str]:
        """Get local invoice file path for order"""
        try:
            result = await db.execute(
                select(models.Order.invoice_file_path)
                .where(models.Order.order_id == order_id)
            )
            invoice_path = result.scalar_one_or_none()
            
            if invoice_path and os.path.exists(invoice_path):
                return invoice_path
            else:
                logger.warning(f"[INVOICE_PATH] Invoice file not found for order {order_id}")
                return None
                
        except Exception as e:
            logger.error(f"[INVOICE_PATH] Error getting invoice path for order {order_id}: {e}")
            return None
    
    async def refresh_invoice(self, db: AsyncSession, order_id: int) -> bool:
        """Manually refresh invoice for order"""
        try:
            logger.info(f"[INVOICE_REFRESH] Refreshing invoice for order {order_id}")
            return await self.check_and_download_invoice(db, order_id)
            
        except Exception as e:
            logger.error(f"[INVOICE_REFRESH] Error refreshing invoice for order {order_id}: {e}")
            return False
    
    async def get_orders_without_invoices(self, db: AsyncSession) -> list:
        """Get orders that don't have invoices yet"""
        try:
            result = await db.execute(
                select(models.Order.order_id, models.Order.bitrix_deal_id)
                .where(
                    models.Order.bitrix_deal_id.isnot(None),
                    models.Order.invoice_file_path.is_(None)
                )
            )
            orders = result.all()
            
            logger.info(f"[INVOICE_MISSING] Found {len(orders)} orders without invoices")
            return [{"order_id": order.order_id, "deal_id": order.bitrix_deal_id} for order in orders]
            
        except Exception as e:
            logger.error(f"[INVOICE_MISSING] Error getting orders without invoices: {e}")
            return []


# Global instance
invoice_service = InvoiceService()

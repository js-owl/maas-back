"""
Bitrix Deal Sync Service
Periodically syncs Bitrix deal stage status and downloads invoices
"""
import json
import httpx
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from backend import models
from backend.bitrix.client import bitrix_client
from backend.bitrix.funnel_manager import funnel_manager
from backend.invoices.service import create_invoice_from_file_path
from backend.utils.logging import get_logger

logger = get_logger(__name__)


class BitrixDealSyncService:
    """Service for syncing Bitrix deal data with orders"""
    
    def __init__(self):
        self.invoice_dir = Path("uploads/invoices")
        self.invoice_dir.mkdir(parents=True, exist_ok=True)
    
    async def sync_deal_stage(
        self,
        db: AsyncSession,
        order_id: int,
        deal_id: int
    ) -> bool:
        """Update order status from Bitrix deal STAGE_ID"""
        try:
            # Ensure funnel manager is initialized
            if not funnel_manager.is_initialized():
                logger.debug(f"[DEAL_SYNC] Funnel manager not initialized, attempting to initialize...")
                try:
                    await funnel_manager.ensure_maas_funnel()
                    if funnel_manager.is_initialized():
                        logger.info(f"[DEAL_SYNC] Funnel manager initialized successfully")
                    else:
                        logger.warning(f"[DEAL_SYNC] Failed to initialize funnel manager, will use fallback mapping")
                except Exception as e:
                    logger.warning(f"[DEAL_SYNC] Error initializing funnel manager: {e}, will use fallback mapping")
            
            # Get deal from Bitrix
            # Check if deal exists by attempting to get it
            # The client returns None for 400 errors (deleted/invalid deals)
            deal_data = await bitrix_client.get_deal(deal_id)
            if not deal_data:
                # Check if this is a 400 error by making a direct call to see the response
                # For now, log as warning (400 errors are expected for deleted deals)
                logger.warning(f"[DEAL_SYNC] Deal {deal_id} not found or returns error (likely deleted) for order {order_id}")
                return False
            
            # Extract STAGE_ID
            stage_id = deal_data.get("STAGE_ID") or deal_data.get("stage_id")
            if not stage_id:
                logger.debug(f"[DEAL_SYNC] No STAGE_ID found in deal {deal_id}")
                return False
            
            # Use Bitrix stage name directly (without C1: prefix)
            # Remove C1: prefix if present
            order_status = stage_id.replace("C1:", "") if stage_id.startswith("C1:") else stage_id
            
            # Get current order
            result = await db.execute(
                select(models.Order).where(models.Order.order_id == order_id)
            )
            order = result.scalar_one_or_none()
            
            if not order:
                logger.error(f"[DEAL_SYNC] Order {order_id} not found")
                return False
            
            # Update order status if different
            if order.status != order_status:
                await db.execute(
                    update(models.Order)
                    .where(models.Order.order_id == order_id)
                    .values(status=order_status)
                )
                await db.commit()
                logger.info(f"[DEAL_SYNC] Updated order {order_id} status from '{order.status}' to '{order_status}' (stage {stage_id})")
                return True
            else:
                logger.debug(f"[DEAL_SYNC] Order {order_id} status already matches: {order_status}")
                return True
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:
                logger.warning(f"[DEAL_SYNC] Deal {deal_id} returns 400 Bad Request (likely deleted) for order {order_id}")
                return False
            else:
                logger.error(f"[DEAL_SYNC] HTTP error syncing deal stage for order {order_id}: {e}", exc_info=True)
                return False
        except Exception as e:
            logger.error(f"[DEAL_SYNC] Error syncing deal stage for order {order_id}: {e}", exc_info=True)
            return False
    
    async def check_and_download_invoice(
        self,
        db: AsyncSession,
        order_id: int,
        deal_id: int
    ) -> bool:
        """Check for invoice documents and download if available"""
        try:
            # Get order
            result = await db.execute(
                select(models.Order).where(models.Order.order_id == order_id)
            )
            order = result.scalar_one_or_none()
            
            if not order:
                logger.error(f"[INVOICE_SYNC] Order {order_id} not found")
                return False
            
            # Check if invoice already exists
            if order.invoice_file_path and Path(order.invoice_file_path).exists():
                logger.debug(f"[INVOICE_SYNC] Invoice already exists for order {order_id}")
                return True
            
            # List document generator documents for this deal
            try:
                documents = await bitrix_client.list_document_generator_documents(deal_id)
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 400:
                    logger.warning(f"[INVOICE_SYNC] Deal {deal_id} returns 400 Bad Request (likely deleted) for order {order_id}")
                    return False
                else:
                    raise
            except Exception as e:
                logger.error(f"[INVOICE_SYNC] Error listing documents for deal {deal_id}: {e}")
                return False
            
            if not documents:
                logger.debug(f"[INVOICE_SYNC] No document generator documents found for deal {deal_id}")
                return False
            
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
                # Sort by creation date (most recent first)
                documents_sorted = sorted(
                    documents,
                    key=lambda x: x.get("createTime", "") or x.get("dateCreate", ""),
                    reverse=True
                )
                invoice_document = documents_sorted[0]
                logger.info(f"[INVOICE_SYNC] Using most recent document as invoice for deal {deal_id}")
            
            if not invoice_document:
                logger.debug(f"[INVOICE_SYNC] No suitable invoice document found for deal {deal_id}")
                return False
            
            # Get document ID
            document_id = invoice_document.get("id") or invoice_document.get("documentId")
            if not document_id:
                logger.warning(f"[INVOICE_SYNC] No document ID found in invoice document for deal {deal_id}")
                return False
            
            # Get full document details
            document_info = await bitrix_client.get_document_generator_document(document_id)
            if not document_info:
                logger.warning(f"[INVOICE_SYNC] Could not get document details for document {document_id}")
                return False
            
            # Get download URL - try PDF URLs first, fallback to DOCX on 400 error
            download_url = None
            file_extension = "docx"
            
            # Priority order for download URLs:
            # 1. pdfUrlMachine - REST API URL for PDF (try first, catch 400 → fallback)
            # 2. pdfUrl - AJAX endpoint for PDF (try second, catch 400 → fallback)
            # 3. downloadUrlMachine - REST API URL with token (DOCX fallback)
            # 4. downloadUrl - AJAX endpoint (DOCX fallback)
            # Note: publicUrl returns HTML redirect page, not the actual document, so we skip it
            
            # Try PDF URLs first
            pdf_urls = [
                ("pdfUrlMachine", "REST API PDF"),
                ("pdfUrl", "AJAX PDF")
            ]
            
            pdf_download_success = False
            response = None
            import os
            verify_tls = os.getenv("BITRIX_VERIFY_TLS", "true").lower() != "false"
            
            for url_key, url_type in pdf_urls:
                if document_info.get(url_key):
                    test_url = document_info.get(url_key)
                    logger.info(f"[INVOICE_SYNC] Trying {url_type} for document {document_id}")
                    
                    # Try to download PDF to test if it works
                    try:
                        async with httpx.AsyncClient(timeout=30.0, verify=verify_tls, follow_redirects=True) as client:
                            test_response = await client.get(test_url)
                            test_response.raise_for_status()
                            # Success - PDF URL works, use it
                            download_url = test_url
                            file_extension = "pdf"
                            pdf_download_success = True
                            response = test_response  # Reuse the response to avoid double download
                            logger.info(f"[INVOICE_SYNC] PDF URL ({url_type}) works, downloaded PDF for document {document_id}")
                            break
                    except httpx.HTTPStatusError as e:
                        if e.response.status_code == 400:
                            logger.warning(f"[INVOICE_SYNC] PDF URL ({url_type}) returned 400 error for document {document_id}, trying next URL")
                            continue
                        else:
                            # Other HTTP errors - log and try next
                            logger.warning(f"[INVOICE_SYNC] PDF URL ({url_type}) returned {e.response.status_code} for document {document_id}, trying next URL")
                            continue
                    except Exception as e:
                        logger.warning(f"[INVOICE_SYNC] Error testing PDF URL ({url_type}): {e}, trying next URL")
                        continue
            
            # If PDF failed or not available, try DOCX URLs
            if not pdf_download_success:
                docx_urls = [
                    ("downloadUrlMachine", "REST API DOCX"),
                    ("downloadUrl", "AJAX DOCX")
                ]
                
                for url_key, url_type in docx_urls:
                    if document_info.get(url_key):
                        download_url = document_info.get(url_key)
                        file_extension = "docx"
                        logger.info(f"[INVOICE_SYNC] Using {url_type} fallback for document {document_id}")
                        break
                
                if not download_url:
                    logger.warning(f"[INVOICE_SYNC] No download URL found for document {document_id}")
                    return False
                
                # Download DOCX file
                async with httpx.AsyncClient(timeout=30.0, verify=verify_tls, follow_redirects=True) as client:
                    response = await client.get(download_url)
                    response.raise_for_status()
            
            # Save original file (DOCX or PDF)
            original_filename = f"invoice_order_{order_id}_deal_{deal_id}.{file_extension}"
            original_path = self.invoice_dir / original_filename
            
            with open(original_path, "wb") as f:
                f.write(response.content)
            
            logger.info(f"[INVOICE_SYNC] Downloaded invoice to {original_path}")
            
            # Validate downloaded file - check if it's actually a DOCX (ZIP file) or HTML
            if file_extension == "docx":
                import zipfile
                try:
                    # Check if file is a valid ZIP (DOCX files are ZIP archives)
                    with zipfile.ZipFile(original_path, 'r') as zip_file:
                        # Check for required DOCX files
                        if 'word/document.xml' not in zip_file.namelist():
                            logger.warning(f"[INVOICE_SYNC] Downloaded file is not a valid DOCX (missing word/document.xml), checking if HTML")
                            # Check if it's HTML instead
                            with open(original_path, 'rb') as f:
                                content_start = f.read(100)
                                if b'<!DOCTYPE html' in content_start or b'<html' in content_start:
                                    logger.error(f"[INVOICE_SYNC] Downloaded file is HTML, not DOCX. URL may be incorrect or document not available.")
                                    return False
                                else:
                                    logger.warning(f"[INVOICE_SYNC] Downloaded file is not a valid DOCX format")
                                    return False
                except zipfile.BadZipFile:
                    # Check if it's HTML
                    with open(original_path, 'rb') as f:
                        content_start = f.read(100)
                        if b'<!DOCTYPE html' in content_start or b'<html' in content_start:
                            logger.error(f"[INVOICE_SYNC] Downloaded file is HTML, not DOCX. URL may be incorrect or document not available.")
                            return False
                        else:
                            logger.error(f"[INVOICE_SYNC] Downloaded file is not a valid DOCX (not a ZIP file)")
                            return False
            
            # Convert DOCX to PDF if needed
            pdf_path = None
            if file_extension == "docx":
                pdf_filename = f"invoice_order_{order_id}_deal_{deal_id}.pdf"
                pdf_path = self.invoice_dir / pdf_filename
                
                try:
                    # Use Pandoc with wkhtmltopdf engine for DOCX to PDF conversion
                    import subprocess
                    # Use XeLaTeX engine for Unicode support (Russian Cyrillic characters)
                    result = subprocess.run(
                        [
                            "pandoc",
                            str(original_path),
                            "-o", str(pdf_path),
                            "--pdf-engine=xelatex",
                            "-V", "mainfont=DejaVu Sans"
                        ],
                        capture_output=True,
                        text=True,
                        timeout=60
                    )
                    
                    if result.returncode == 0 and pdf_path.exists():
                        logger.info(f"[INVOICE_SYNC] Converted DOCX to PDF: {pdf_path}")
                    else:
                        logger.warning(f"[INVOICE_SYNC] Pandoc conversion failed: {result.stderr}, keeping DOCX file only")
                        pdf_path = None
                except FileNotFoundError:
                    logger.warning("[INVOICE_SYNC] Pandoc not found, keeping DOCX file only")
                    pdf_path = None
                except subprocess.TimeoutExpired:
                    logger.warning("[INVOICE_SYNC] Pandoc conversion timed out, keeping DOCX file only")
                    pdf_path = None
                except Exception as e:
                    logger.error(f"[INVOICE_SYNC] Failed to convert DOCX to PDF: {e}, keeping DOCX file only", exc_info=True)
                    pdf_path = None
            else:
                # Already PDF
                pdf_path = original_path
                
                # Use PDF path for invoice creation (prefer PDF)
                final_path = pdf_path if pdf_path else original_path
                
                # Parse generated_at from document_info if available
                generated_at = None
                if document_info.get("createTime"):
                    try:
                        generated_at = datetime.fromisoformat(document_info["createTime"].replace("Z", "+00:00"))
                    except:
                        pass
                
                # Create invoice record and attach to order
                invoice = await create_invoice_from_file_path(
                    db=db,
                    file_path=str(final_path),
                    order_id=order_id,
                    bitrix_document_id=document_id,
                    generated_at=generated_at,
                    original_filename=f"invoice_order_{order_id}.pdf" if pdf_path else f"invoice_order_{order_id}.{file_extension}"
                )
                
                if invoice:
                    # Update order's invoice_ids
                    current_invoice_ids = []
                    if order.invoice_ids:
                        try:
                            current_invoice_ids = json.loads(order.invoice_ids) if isinstance(order.invoice_ids, str) else order.invoice_ids
                        except (json.JSONDecodeError, TypeError):
                            current_invoice_ids = []
                    
                    if invoice.id not in current_invoice_ids:
                        current_invoice_ids.append(invoice.id)
                        await db.execute(
                            update(models.Order)
                            .where(models.Order.order_id == order_id)
                            .values(
                                invoice_ids=json.dumps(current_invoice_ids),
                                invoice_url=download_url,
                                invoice_file_path=str(final_path),
                                invoice_generated_at=generated_at or datetime.now(timezone.utc)
                            )
                        )
                        await db.commit()
                        logger.info(f"[INVOICE_SYNC] Attached invoice {invoice.id} to order {order_id}")
                    else:
                        # Invoice already attached, just update invoice fields
                        await db.execute(
                            update(models.Order)
                            .where(models.Order.order_id == order_id)
                            .values(
                                invoice_url=download_url,
                                invoice_file_path=str(final_path),
                                invoice_generated_at=generated_at or datetime.now(timezone.utc)
                            )
                        )
                        await db.commit()
                
                return True
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:
                logger.warning(f"[INVOICE_SYNC] Deal {deal_id} returns 400 Bad Request (likely deleted) for order {order_id}")
                return False
            else:
                logger.error(f"[INVOICE_SYNC] HTTP error downloading invoice for order {order_id}: {e}")
                return False
        except httpx.HTTPError as e:
            logger.error(f"[INVOICE_SYNC] HTTP error downloading invoice for order {order_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"[INVOICE_SYNC] Error checking/downloading invoice for order {order_id}: {e}", exc_info=True)
            return False
    
    async def sync_all_orders(self, db: AsyncSession) -> Dict[str, Any]:
        """Sync all orders with associated Bitrix deals"""
        try:
            # Get all orders with Bitrix deal IDs
            result = await db.execute(
                select(models.Order)
                .where(models.Order.bitrix_deal_id.isnot(None))
            )
            orders = result.scalars().all()
            
            logger.info(f"[DEAL_SYNC] Starting sync for {len(orders)} orders with Bitrix deals")
            
            stats = {
                "total": len(orders),
                "stage_synced": 0,
                "stage_errors": 0,
                "invoices_downloaded": 0,
                "invoice_errors": 0,
                "skipped": 0
            }
            
            for order in orders:
                try:
                    if not order.bitrix_deal_id:
                        stats["skipped"] += 1
                        continue
                    
                    # Sync deal stage
                    stage_synced = await self.sync_deal_stage(
                        db, order.order_id, order.bitrix_deal_id
                    )
                    if stage_synced:
                        stats["stage_synced"] += 1
                    else:
                        stats["stage_errors"] += 1
                    
                    # Check and download invoice
                    invoice_downloaded = await self.check_and_download_invoice(
                        db, order.order_id, order.bitrix_deal_id
                    )
                    if invoice_downloaded:
                        stats["invoices_downloaded"] += 1
                    else:
                        stats["invoice_errors"] += 1
                    
                except Exception as e:
                    logger.error(f"[DEAL_SYNC] Error processing order {order.order_id}: {e}", exc_info=True)
                    stats["stage_errors"] += 1
                    stats["invoice_errors"] += 1
            
            logger.info(f"[DEAL_SYNC] Sync completed: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"[DEAL_SYNC] Error syncing all orders: {e}", exc_info=True)
            return {"error": str(e)}


# Global instance
deal_sync_service = BitrixDealSyncService()


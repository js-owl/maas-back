"""Force recreate all invoice DOCX and PDF files using correct download URLs"""
import asyncio
import sys
from pathlib import Path
import httpx
import zipfile
import subprocess
import os

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.database import AsyncSessionLocal
from backend import models
from backend.bitrix.client import BitrixClient
from backend.invoices.service import create_invoice_from_file_path
from backend.invoices.repository import get_invoice_by_filename
from sqlalchemy import select, update
from datetime import datetime, timezone
import json

async def recreate_all_invoices():
    """Recreate all invoice files using correct download URLs"""
    async with AsyncSessionLocal() as db:
        bitrix_client = BitrixClient()
        
        # Get all orders with Bitrix deal IDs
        result = await db.execute(
            select(models.Order)
            .where(models.Order.bitrix_deal_id.isnot(None))
            .order_by(models.Order.order_id)
        )
        orders = result.scalars().all()
        
        if not orders:
            print("No orders with Bitrix deal IDs found")
            return
        
        print("=" * 80)
        print("FORCE RECREATE ALL INVOICES")
        print("=" * 80)
        print(f"Found {len(orders)} orders with Bitrix deals\n")
        
        invoice_dir = Path("uploads/invoices")
        invoice_dir.mkdir(parents=True, exist_ok=True)
        
        verify_tls = os.getenv("BITRIX_VERIFY_TLS", "true").lower() != "false"
        
        success_count = 0
        error_count = 0
        skipped_count = 0
        
        for order in orders:
            order_id = order.order_id
            deal_id = order.bitrix_deal_id
            
            print(f"\n{'='*80}")
            print(f"Order {order_id} - Deal {deal_id}")
            print(f"{'='*80}")
            
            # List documents for this deal
            documents = await bitrix_client.list_document_generator_documents(deal_id)
            
            if not documents:
                print(f"  ⚠ No documents found for deal {deal_id}")
                skipped_count += 1
                continue
            
            print(f"  Found {len(documents)} document(s)")
            
            # Process each document
            invoice_doc_ids = []
            
            for doc in documents:
                doc_id = doc.get("id")
                doc_title = doc.get("title", "Unknown")
                
                print(f"\n  Processing document ID: {doc_id} ({doc_title})")
                
                # Get full document info
                doc_info = await bitrix_client.get_document_generator_document(doc_id)
                
                if not doc_info:
                    print(f"    ✗ Could not get document info")
                    error_count += 1
                    continue
                
                # Get download URL - prioritize downloadUrlMachine
                download_url = None
                file_extension = "docx"
                
                if doc_info.get("downloadUrlMachine"):
                    download_url = doc_info.get("downloadUrlMachine")
                    file_extension = "docx"
                    print(f"    Using downloadUrlMachine (REST API)")
                elif doc_info.get("pdfUrlMachine"):
                    download_url = doc_info.get("pdfUrlMachine")
                    file_extension = "pdf"
                    print(f"    Using pdfUrlMachine (REST API)")
                elif doc_info.get("downloadUrl"):
                    download_url = doc_info.get("downloadUrl")
                    file_extension = "docx"
                    print(f"    Using downloadUrl (AJAX)")
                elif doc_info.get("pdfUrl"):
                    download_url = doc_info.get("pdfUrl")
                    file_extension = "pdf"
                    print(f"    Using pdfUrl (AJAX)")
                
                if not download_url:
                    print(f"    ✗ No download URL available")
                    error_count += 1
                    continue
                
                # Delete old files for this order/deal/document
                old_files = list(invoice_dir.glob(f"invoice_order_{order_id}_deal_{deal_id}_doc_{doc_id}.*"))
                for old_file in old_files:
                    try:
                        old_file.unlink()
                        print(f"    Deleted old file: {old_file.name}")
                    except Exception as e:
                        print(f"    ⚠ Could not delete {old_file.name}: {e}")
                
                # Download the file
                try:
                    async with httpx.AsyncClient(timeout=30.0, verify=verify_tls, follow_redirects=True) as client:
                        response = await client.get(download_url)
                        response.raise_for_status()
                        
                        content = response.content
                        content_type = response.headers.get("content-type", "unknown")
                        
                        print(f"    Downloaded: {len(content)} bytes, Content-Type: {content_type}")
                        
                        # Validate it's not HTML
                        first_bytes = content[:100]
                        if b'<!DOCTYPE html' in first_bytes or b'<html' in first_bytes:
                            print(f"    ✗ ERROR: Downloaded file is HTML, not a document!")
                            error_count += 1
                            continue
                        
                        # Save original file
                        original_filename = f"invoice_order_{order_id}_deal_{deal_id}_doc_{doc_id}.{file_extension}"
                        original_path = invoice_dir / original_filename
                        
                        with open(original_path, "wb") as f:
                            f.write(content)
                        
                        print(f"    ✓ Saved: {original_path.name}")
                        
                        # Validate DOCX if it's a DOCX file
                        if file_extension == "docx":
                            try:
                                with zipfile.ZipFile(original_path, 'r') as zip_file:
                                    if 'word/document.xml' not in zip_file.namelist():
                                        print(f"    ✗ ERROR: File is not a valid DOCX (missing word/document.xml)")
                                        error_count += 1
                                        continue
                                    print(f"    ✓ Valid DOCX file")
                            except zipfile.BadZipFile:
                                print(f"    ✗ ERROR: File is not a valid ZIP/DOCX")
                                error_count += 1
                                continue
                            
                            # Convert to PDF
                            pdf_filename = f"invoice_order_{order_id}_deal_{deal_id}_doc_{doc_id}.pdf"
                            pdf_path = invoice_dir / pdf_filename
                            
                            try:
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
                                    print(f"    ✓ Converted to PDF: {pdf_path.name} ({pdf_path.stat().st_size} bytes)")
                                    final_path = pdf_path
                                else:
                                    print(f"    ⚠ Pandoc conversion failed: {result.stderr}")
                                    print(f"    Keeping DOCX only")
                                    final_path = original_path
                            except FileNotFoundError:
                                print(f"    ⚠ Pandoc not found, keeping DOCX only")
                                final_path = original_path
                            except subprocess.TimeoutExpired:
                                print(f"    ⚠ Pandoc conversion timed out, keeping DOCX only")
                                final_path = original_path
                            except Exception as e:
                                print(f"    ⚠ Conversion error: {e}, keeping DOCX only")
                                final_path = original_path
                        else:
                            # Already PDF
                            final_path = original_path
                            print(f"    ✓ File is already PDF")
                        
                        # Create or update invoice record
                        try:
                            # Parse generated_at from doc_info if available
                            generated_at = None
                            if doc_info.get("createTime"):
                                try:
                                    generated_at = datetime.fromisoformat(doc_info["createTime"].replace("Z", "+00:00"))
                                except:
                                    pass
                            
                            # Check if invoice already exists by filename
                            existing_invoice = await get_invoice_by_filename(db, final_path.name)
                            
                            if existing_invoice:
                                # Update existing invoice
                                existing_invoice.file_path = str(final_path)
                                existing_invoice.file_size = final_path.stat().st_size
                                existing_invoice.file_type = final_path.suffix[1:] if final_path.suffix else "unknown"
                                existing_invoice.updated_at = datetime.now(timezone.utc)
                                await db.commit()
                                print(f"    ✓ Updated existing invoice record ID: {existing_invoice.id}")
                                invoice_doc_ids.append(existing_invoice.id)
                            else:
                                # Create new invoice record
                                invoice = await create_invoice_from_file_path(
                                    db=db,
                                    file_path=str(final_path),
                                    order_id=order_id,
                                    bitrix_document_id=doc_id,
                                    generated_at=generated_at,
                                    original_filename=f"invoice_order_{order_id}_doc_{doc_id}.pdf" if final_path.suffix == ".pdf" else f"invoice_order_{order_id}_doc_{doc_id}.docx"
                                )
                                if invoice:
                                    print(f"    ✓ Created invoice record ID: {invoice.id}")
                                    invoice_doc_ids.append(invoice.id)
                                else:
                                    print(f"    ✗ Failed to create invoice record")
                                    error_count += 1
                                    continue
                            
                            # Update order's invoice_ids
                            existing_invoice_ids = []
                            if order.invoice_ids:
                                if isinstance(order.invoice_ids, str):
                                    try:
                                        existing_invoice_ids = json.loads(order.invoice_ids)
                                    except:
                                        pass
                                elif isinstance(order.invoice_ids, list):
                                    existing_invoice_ids = order.invoice_ids
                            
                            # Add new invoice IDs if not already present
                            for invoice_id_val in invoice_doc_ids:
                                if invoice_id_val not in existing_invoice_ids:
                                    existing_invoice_ids.append(invoice_id_val)
                            
                            await db.execute(
                                update(models.Order)
                                .where(models.Order.order_id == order_id)
                                .values(invoice_ids=json.dumps(existing_invoice_ids))
                            )
                            await db.commit()
                            
                            success_count += 1
                            
                        except Exception as e:
                            print(f"    ✗ Error creating/updating invoice record: {e}")
                            import traceback
                            traceback.print_exc()
                            await db.rollback()
                            error_count += 1
                
                except httpx.HTTPStatusError as e:
                    print(f"    ✗ HTTP Error: {e.response.status_code}")
                    if e.response.status_code == 403:
                        print(f"      (403 Forbidden - URL may require authentication)")
                    error_count += 1
                except Exception as e:
                    print(f"    ✗ Error: {e}")
                    error_count += 1
        
        print("\n" + "=" * 80)
        print("RECREATION SUMMARY")
        print("=" * 80)
        print(f"  Success: {success_count}")
        print(f"  Errors: {error_count}")
        print(f"  Skipped: {skipped_count}")
        print(f"  Total: {len(orders)}")
        print("=" * 80)

if __name__ == "__main__":
    asyncio.run(recreate_all_invoices())


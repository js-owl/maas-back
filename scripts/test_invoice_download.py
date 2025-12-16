"""Test script to investigate why DOCX invoices are downloaded as HTML"""
import asyncio
import sys
from pathlib import Path
import httpx
import zipfile

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.database import AsyncSessionLocal
from backend import models
from backend.bitrix.client import BitrixClient
from sqlalchemy import select
import os

async def test_invoice_download():
    """Test downloading invoices and check what we get"""
    async with AsyncSessionLocal() as db:
        # Get orders with Bitrix deal IDs
        result = await db.execute(
            select(models.Order)
            .where(models.Order.bitrix_deal_id.isnot(None))
            .order_by(models.Order.order_id.desc())
            .limit(5)
        )
        orders = result.scalars().all()
        
        if not orders:
            print("No orders with Bitrix deal IDs found")
            return
        
        bitrix_client = BitrixClient()
        
        print("=" * 80)
        print("INVOICE DOWNLOAD INVESTIGATION")
        print("=" * 80)
        
        for order in orders:
            deal_id = order.bitrix_deal_id
            order_id = order.order_id
            
            print(f"\n{'='*80}")
            print(f"Order {order_id} - Deal {deal_id}")
            print(f"{'='*80}")
            
            # List documents for this deal
            documents = await bitrix_client.list_document_generator_documents(deal_id)
            
            if not documents:
                print(f"  No documents found for deal {deal_id}")
                continue
            
            print(f"  Found {len(documents)} document(s)")
            
            for doc in documents:
                doc_id = doc.get("id")
                doc_title = doc.get("title", "Unknown")
                doc_type = doc.get("type", "Unknown")
                
                print(f"\n  Document ID: {doc_id}")
                print(f"  Title: {doc_title}")
                print(f"  Type: {doc_type}")
                
                # Get full document info
                doc_info = await bitrix_client.get_document_generator_document(doc_id)
                
                if not doc_info:
                    print(f"    Could not get document info")
                    continue
                
                print(f"\n    Document Info:")
                print(f"      publicUrl: {doc_info.get('publicUrl', 'N/A')}")
                print(f"      pdfUrl: {doc_info.get('pdfUrl', 'N/A')}")
                print(f"      downloadUrl: {doc_info.get('downloadUrl', 'N/A')}")
                print(f"      pdfUrlMachine: {doc_info.get('pdfUrlMachine', 'N/A')}")
                print(f"      downloadUrlMachine: {doc_info.get('downloadUrlMachine', 'N/A')}")
                
                # Try to enable public URL if not available
                if not doc_info.get("publicUrl"):
                    print(f"\n    Attempting to enable public URL...")
                    enabled = await bitrix_client.enable_document_public_url(doc_id, enable=True)
                    if enabled:
                        print(f"      ✓ Public URL enabled")
                        # Get document info again
                        doc_info = await bitrix_client.get_document_generator_document(doc_id)
                        print(f"      New publicUrl: {doc_info.get('publicUrl', 'N/A')}")
                    else:
                        print(f"      ✗ Failed to enable public URL")
                
                # Test downloading from each available URL
                urls_to_test = []
                
                if doc_info.get("publicUrl"):
                    urls_to_test.append(("publicUrl", doc_info.get("publicUrl")))
                if doc_info.get("pdfUrl"):
                    urls_to_test.append(("pdfUrl", doc_info.get("pdfUrl")))
                if doc_info.get("downloadUrl"):
                    urls_to_test.append(("downloadUrl", doc_info.get("downloadUrl")))
                if doc_info.get("pdfUrlMachine"):
                    urls_to_test.append(("pdfUrlMachine", doc_info.get("pdfUrlMachine")))
                if doc_info.get("downloadUrlMachine"):
                    urls_to_test.append(("downloadUrlMachine", doc_info.get("downloadUrlMachine")))
                
                if not urls_to_test:
                    print(f"    ✗ No download URLs available")
                    continue
                
                # Test each URL
                verify_tls = os.getenv("BITRIX_VERIFY_TLS", "true").lower() != "false"
                
                for url_name, url in urls_to_test:
                    print(f"\n    Testing {url_name}:")
                    print(f"      URL: {url}")
                    
                    try:
                        async with httpx.AsyncClient(timeout=30.0, verify=verify_tls, follow_redirects=True) as client:
                            response = await client.get(url)
                            response.raise_for_status()
                            
                            content = response.content
                            content_type = response.headers.get("content-type", "unknown")
                            content_length = len(content)
                            
                            print(f"      Status: {response.status_code}")
                            print(f"      Content-Type: {content_type}")
                            print(f"      Content-Length: {content_length} bytes")
                            
                            # Check first bytes
                            first_bytes = content[:100]
                            print(f"      First 100 bytes: {first_bytes[:50]}...")
                            
                            # Check if it's HTML
                            if b'<!DOCTYPE html' in first_bytes or b'<html' in first_bytes:
                                print(f"      ⚠ WARNING: This is HTML, not a document file!")
                                print(f"      HTML content preview:")
                                html_preview = content[:500].decode('utf-8', errors='ignore')
                                print(f"        {html_preview[:200]}...")
                            # Check if it's a ZIP (DOCX)
                            elif first_bytes[:2] == b'PK':
                                print(f"      ✓ Looks like a ZIP file (DOCX)")
                                try:
                                    with zipfile.ZipFile(io.BytesIO(content), 'r') as z:
                                        files = z.namelist()
                                        print(f"      ZIP contains {len(files)} files")
                                        if 'word/document.xml' in files:
                                            print(f"      ✓ Valid DOCX (contains word/document.xml)")
                                        else:
                                            print(f"      ⚠ ZIP but not a valid DOCX")
                                except Exception as e:
                                    print(f"      ⚠ Error checking ZIP: {e}")
                            # Check if it's PDF
                            elif first_bytes[:4] == b'%PDF':
                                print(f"      ✓ Looks like a PDF file")
                            else:
                                print(f"      ⚠ Unknown file type")
                            
                            # Save sample for inspection
                            test_dir = Path("test_downloads")
                            test_dir.mkdir(exist_ok=True)
                            test_file = test_dir / f"order_{order_id}_deal_{deal_id}_doc_{doc_id}_{url_name}.bin"
                            with open(test_file, "wb") as f:
                                f.write(content)
                            print(f"      Saved to: {test_file}")
                            
                    except httpx.HTTPStatusError as e:
                        print(f"      ✗ HTTP Error: {e.response.status_code} - {e.response.text[:100]}")
                    except Exception as e:
                        print(f"      ✗ Error: {e}")
                
                print()  # Blank line between documents
        
        print("\n" + "=" * 80)
        print("INVESTIGATION COMPLETE")
        print("=" * 80)
        print("\nCheck the 'test_downloads' directory for downloaded files")
        print("You can inspect them to see what format they're in")

if __name__ == "__main__":
    import io
    asyncio.run(test_invoice_download())


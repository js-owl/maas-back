"""Check order 41 for duplicate deals and verify webhook test"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.database import AsyncSessionLocal
from backend import models
from backend.bitrix.client import bitrix_client
from sqlalchemy import select
import json
import traceback

async def check_order_41():
    """Check order 41 and find duplicate deals in Bitrix"""
    print("=" * 80)
    print("CHECKING ORDER 41 FOR DUPLICATE DEALS")
    print("=" * 80)
    
    try:
        async with AsyncSessionLocal() as db:
        # Get order 41
        result = await db.execute(
            select(models.Order).where(models.Order.order_id == 41)
        )
        order = result.scalar_one_or_none()
        
        if not order:
            print("\n❌ Order 41 not found in database!")
            return
        
        print(f"\n📋 Order 41 Details:")
        print(f"   Order ID: {order.order_id}")
        print(f"   User ID: {order.user_id}")
        print(f"   Service ID: {order.service_id}")
        print(f"   Status: {order.status}")
        print(f"   Bitrix Deal ID (in DB): {order.bitrix_deal_id}")
        print(f"   Total Price: {order.total_price}")
        print(f"   Created At: {order.created_at}")
        print(f"   Updated At: {order.updated_at}")
        
        # Get user info
        user_result = await db.execute(
            select(models.User).where(models.User.id == order.user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if user:
            print(f"\n👤 User Details:")
            print(f"   User ID: {user.id}")
            print(f"   Username: {user.username}")
            print(f"   Email: {user.email}")
            print(f"   Bitrix Contact ID: {user.bitrix_contact_id}")
        
        # Check the deal stored in DB
        if order.bitrix_deal_id:
            print(f"\n🔍 Checking deal {order.bitrix_deal_id} in Bitrix...")
            deal = await bitrix_client.get_deal(order.bitrix_deal_id)
            if deal:
                print(f"   ✓ Deal {order.bitrix_deal_id} exists:")
                print(f"     Title: {deal.get('TITLE', 'N/A')}")
                print(f"     Category ID: {deal.get('CATEGORY_ID', 'N/A')}")
                print(f"     Stage ID: {deal.get('STAGE_ID', 'N/A')}")
                print(f"     Created: {deal.get('DATE_CREATE', 'N/A')}")
            else:
                print(f"   ❌ Deal {order.bitrix_deal_id} not found in Bitrix!")
        
        # Search for deals with order 41 in title using cleanup service method
        print(f"\n🔍 Searching for ALL deals with 'Order #41' in title...")
        
        from backend.bitrix.cleanup_service import bitrix_cleanup_service
        
        # Use the cleanup service to find duplicates
        matching_deals = await bitrix_cleanup_service.find_duplicate_deals_for_order(
            order_id=41,
            known_deal_id=order.bitrix_deal_id
        )
        
        if matching_deals:
            print(f"\n   ✅ Found {len(matching_deals)} deal(s) for order 41:")
            for i, deal_info in enumerate(matching_deals, 1):
                print(f"\n   Deal {i}:")
                print(f"     ID: {deal_info.get('ID', 'N/A')}")
                print(f"     Title: {deal_info.get('TITLE', 'N/A')}")
                print(f"     Category ID: {deal_info.get('CATEGORY_ID', 'N/A')}")
                print(f"     Stage ID: {deal_info.get('STAGE_ID', 'N/A')}")
                print(f"     Created: {deal_info.get('DATE_CREATE', 'N/A')}")
                print(f"     Modified: {deal_info.get('DATE_MODIFY', 'N/A')}")
                
                deal_id_str = deal_info.get('ID', '')
                if deal_id_str and order.bitrix_deal_id:
                    try:
                        if int(deal_id_str) == order.bitrix_deal_id:
                            print(f"     ✓ This is the deal stored in database")
                        else:
                            print(f"     ⚠️  DUPLICATE DEAL - not stored in database!")
                    except ValueError:
                        pass
        else:
            print(f"   ℹ️  No deals found with order 41 in title")
        
        # Check for potential causes of duplicates
        print(f"\n🔍 Checking for potential duplicate creation causes...")
        
        # Check if order was updated after creation
        if order.created_at and order.updated_at:
            if order.updated_at > order.created_at:
                time_diff = (order.updated_at - order.created_at).total_seconds()
                print(f"   ⚠️  Order was updated {time_diff:.0f} seconds after creation")
                print(f"      This could trigger deal creation if bitrix_deal_id was None at update time")
        
        # Check Redis queue for pending operations
        print(f"\n🔍 Checking Redis queue for pending operations for order 41...")
        try:
            from backend.bitrix.queue_service import bitrix_queue_service
            # Get stream info
            stream_info = await bitrix_queue_service.get_stream_info(
                bitrix_queue_service.operations_stream
            )
            print(f"   Operations stream length: {stream_info.get('length', 0)}")
            print(f"   (Note: Cannot directly search for order 41 in stream without consuming messages)")
        except Exception as e:
            print(f"   ⚠️  Could not check Redis queue: {e}")
    except Exception as e:
        print(f"\n❌ Error checking order 41: {e}")
        traceback.print_exc()

async def check_webhook_test():
    """Check if webhook test was received"""
    print("\n" + "=" * 80)
    print("CHECKING WEBHOOK TEST: http://192.168.0.104:8001/bitrix/webhook?test=\"test2\"")
    print("=" * 80)
    
    # Check application logs (if accessible)
    print("\n📝 To check if the webhook was received, you need to:")
    print("   1. Check application logs for webhook requests")
    print("   2. Look for entries with query parameter test='test2'")
    print("   3. Check the webhook endpoint logs")
    
    print("\n🔍 Webhook endpoint details:")
    print("   Endpoint: POST /bitrix/webhook")
    print("   Query parameter: test=\"test2\"")
    print("   Expected behavior:")
    print("     - Webhook should accept the request")
    print("     - Should log the request")
    print("     - Should return 200 status")
    
    # Check webhook router code
    print("\n📋 Webhook handler code analysis:")
    print("   - Endpoint accepts query parameters via FastAPI Query()")
    print("   - Query parameter 'test' should be logged if present")
    print("   - Token verification happens first")
    print("   - Then payload is parsed and logged")
    
    print("\n💡 To verify webhook was received:")
    print("   1. Check application logs for:")
    print("      - 'Bitrix webhook received' messages")
    print("      - Request with test parameter")
    print("   2. Check webhook router logs for:")
    print("      - 'Bitrix webhook token verified successfully'")
    print("      - Payload logging")
    print("   3. Check if webhook was published to Redis:")
    print("      - 'Published webhook ... to Redis' messages")

async def main():
    try:
        await check_order_41()
        await check_webhook_test()
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    print("\n1. For duplicate deals:")
    print("   - Check if order 41 was updated after creation")
    print("   - Verify if update_order() triggered deal creation when bitrix_deal_id was None")
    print("   - Check worker logs for multiple deal creation attempts")
    print("   - Consider using cleanup_service to remove duplicates")
    
    print("\n2. For webhook test:")
    print("   - Check application logs (docker logs or log files)")
    print("   - Verify webhook endpoint is accessible from Bitrix")
    print("   - Check if BITRIX_WEBHOOK_TOKEN is configured correctly")
    print("   - Test webhook manually with curl:")
    print("     curl -X POST 'http://192.168.0.104:8001/bitrix/webhook?test=test2' \\")
    print("          -H 'Content-Type: application/json' \\")
    print("          -d '{}'")

if __name__ == "__main__":
    asyncio.run(main())


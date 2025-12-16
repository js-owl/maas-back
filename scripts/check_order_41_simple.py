"""Simple script to check order 41 and webhook - writes to file"""
import asyncio
import sys
from pathlib import Path
import traceback

sys.path.insert(0, str(Path(__file__).parent))

async def main():
    output_lines = []
    
    try:
        from backend.database import AsyncSessionLocal
        from backend import models
        from backend.bitrix.client import bitrix_client
        from backend.bitrix.cleanup_service import bitrix_cleanup_service
        from sqlalchemy import select
        
        output_lines.append("=" * 80)
        output_lines.append("CHECKING ORDER 41 FOR DUPLICATE DEALS")
        output_lines.append("=" * 80)
        
        async with AsyncSessionLocal() as db:
            # Get order 41
            result = await db.execute(
                select(models.Order).where(models.Order.order_id == 41)
            )
            order = result.scalar_one_or_none()
            
            if not order:
                output_lines.append("\nOrder 41 not found in database!")
                return output_lines
            
            output_lines.append(f"\nOrder 41 Details:")
            output_lines.append(f"   Order ID: {order.order_id}")
            output_lines.append(f"   User ID: {order.user_id}")
            output_lines.append(f"   Service ID: {order.service_id}")
            output_lines.append(f"   Status: {order.status}")
            output_lines.append(f"   Bitrix Deal ID (in DB): {order.bitrix_deal_id}")
            output_lines.append(f"   Total Price: {order.total_price}")
            output_lines.append(f"   Created At: {order.created_at}")
            output_lines.append(f"   Updated At: {order.updated_at}")
            
            # Get user info
            user_result = await db.execute(
                select(models.User).where(models.User.id == order.user_id)
            )
            user = user_result.scalar_one_or_none()
            
            if user:
                output_lines.append(f"\nUser Details:")
                output_lines.append(f"   User ID: {user.id}")
                output_lines.append(f"   Username: {user.username}")
                output_lines.append(f"   Email: {user.email}")
                output_lines.append(f"   Bitrix Contact ID: {user.bitrix_contact_id}")
            
            # Check the deal stored in DB
            if order.bitrix_deal_id:
                output_lines.append(f"\nChecking deal {order.bitrix_deal_id} in Bitrix...")
                deal = await bitrix_client.get_deal(order.bitrix_deal_id)
                if deal:
                    output_lines.append(f"   Deal {order.bitrix_deal_id} exists:")
                    output_lines.append(f"     Title: {deal.get('TITLE', 'N/A')}")
                    output_lines.append(f"     Category ID: {deal.get('CATEGORY_ID', 'N/A')}")
                    output_lines.append(f"     Stage ID: {deal.get('STAGE_ID', 'N/A')}")
                    output_lines.append(f"     Created: {deal.get('DATE_CREATE', 'N/A')}")
                else:
                    output_lines.append(f"   Deal {order.bitrix_deal_id} not found in Bitrix!")
            
            # Search for all deals with order 41
            output_lines.append(f"\nSearching for ALL deals with 'Order #41' in title...")
            
            matching_deals = await bitrix_cleanup_service.find_duplicate_deals_for_order(
                order_id=41,
                known_deal_id=order.bitrix_deal_id
            )
            
            if matching_deals:
                output_lines.append(f"\n   Found {len(matching_deals)} deal(s) for order 41:")
                for i, deal_info in enumerate(matching_deals, 1):
                    output_lines.append(f"\n   Deal {i}:")
                    output_lines.append(f"     ID: {deal_info.get('ID', 'N/A')}")
                    output_lines.append(f"     Title: {deal_info.get('TITLE', 'N/A')}")
                    output_lines.append(f"     Category ID: {deal_info.get('CATEGORY_ID', 'N/A')}")
                    output_lines.append(f"     Stage ID: {deal_info.get('STAGE_ID', 'N/A')}")
                    output_lines.append(f"     Created: {deal_info.get('DATE_CREATE', 'N/A')}")
                    output_lines.append(f"     Modified: {deal_info.get('DATE_MODIFY', 'N/A')}")
                    
                    deal_id_str = deal_info.get('ID', '')
                    if deal_id_str and order.bitrix_deal_id:
                        try:
                            if int(deal_id_str) == order.bitrix_deal_id:
                                output_lines.append(f"     This is the deal stored in database")
                            else:
                                output_lines.append(f"     DUPLICATE DEAL - not stored in database!")
                        except ValueError:
                            pass
            else:
                output_lines.append(f"   No deals found with order 41 in title")
            
            # Check for potential causes
            output_lines.append(f"\nChecking for potential duplicate creation causes...")
            if order.created_at and order.updated_at:
                if order.updated_at > order.created_at:
                    time_diff = (order.updated_at - order.created_at).total_seconds()
                    output_lines.append(f"   Order was updated {time_diff:.0f} seconds after creation")
                    output_lines.append(f"   This could trigger deal creation if bitrix_deal_id was None at update time")
        
    except Exception as e:
        output_lines.append(f"\nError: {e}")
        output_lines.append(traceback.format_exc())
    
    return output_lines

if __name__ == "__main__":
    result = asyncio.run(main())
    output = "\n".join(result)
    print(output)
    
    # Also write to file
    with open("order_41_check_result.txt", "w", encoding="utf-8") as f:
        f.write(output)
    print("\n\nResults also written to order_41_check_result.txt")






"""
Script to move existing Bitrix deals to MaaS funnel
Interactive script to select deals to move
"""
import asyncio
import sys
from pathlib import Path
from typing import List, Tuple, Optional

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.bitrix.client import bitrix_client
from backend.bitrix.funnel_manager import funnel_manager
from backend.database import AsyncSessionLocal
from backend import models
from sqlalchemy import select
from backend.utils.logging import get_logger

logger = get_logger(__name__)


async def move_deal_to_maas_funnel(deal_id: int, order_id: int) -> bool:
    """Move a deal to MaaS funnel and update its stage based on order status"""
    try:
        # Ensure funnel is initialized
        if not funnel_manager.is_initialized():
            logger.info("Initializing MaaS funnel...")
            await funnel_manager.ensure_maas_funnel()
        
        if not funnel_manager.is_initialized():
            logger.error("Failed to initialize MaaS funnel")
            return False
        
        category_id = funnel_manager.get_category_id()
        if not category_id:
            logger.error("MaaS funnel category ID not found")
            return False
        
        # Get order to determine status and stage
        async with AsyncSessionLocal() as db:
            order_result = await db.execute(
                select(models.Order).where(models.Order.order_id == order_id)
            )
            order = order_result.scalar_one_or_none()
            
            if not order:
                logger.error(f"Order {order_id} not found in database")
                return False
            
            # Get stage ID for order status
            stage_id = funnel_manager.get_stage_id_for_status(order.status)
            if not stage_id:
                logger.warning(f"No stage mapping for status '{order.status}', using default 'NEW'")
                stage_id = "NEW"
            
            # Use crm.item.update to change category (only way to change category)
            success = await bitrix_client.update_deal_category(deal_id, category_id, stage_id)
            
            if success:
                logger.info(
                    f"✅ Moved deal {deal_id} (order {order_id}) to MaaS funnel "
                    f"(category {category_id}, stage {stage_id}, status: {order.status})"
                )
                return True
            else:
                logger.error(f"❌ Failed to update deal {deal_id} in Bitrix")
                return False
                
    except Exception as e:
        logger.error(f"Error moving deal {deal_id} to MaaS funnel: {e}", exc_info=True)
        return False


async def get_all_deals_not_in_maas() -> List[Tuple[int, int, str, Optional[int]]]:
    """
    Get all orders with Bitrix deals that are not in MaaS funnel.
    Returns list of (order_id, bitrix_deal_id, status, current_category_id)
    """
    deals = []
    
    if not funnel_manager.is_initialized():
        await funnel_manager.ensure_maas_funnel()
    
    maas_category_id = funnel_manager.get_category_id() if funnel_manager.is_initialized() else None
    
    async with AsyncSessionLocal() as db:
        # Get all orders with Bitrix deal IDs
        orders_result = await db.execute(
            select(models.Order)
            .where(models.Order.bitrix_deal_id.isnot(None))
            .order_by(models.Order.order_id)
        )
        orders = orders_result.scalars().all()
        
        for order in orders:
            if order.bitrix_deal_id:
                # Get deal info from Bitrix to check current category
                deal_info = await bitrix_client.get_deal(order.bitrix_deal_id)
                current_category_id = None
                
                if deal_info:
                    current_category_id = deal_info.get("CATEGORY_ID")
                    # Convert to int if it's a string
                    if current_category_id:
                        try:
                            current_category_id = int(current_category_id)
                        except (ValueError, TypeError):
                            pass
                
                # Only include if not already in MaaS funnel
                if current_category_id != maas_category_id:
                    deals.append((
                        order.order_id,
                        order.bitrix_deal_id,
                        order.status,
                        current_category_id
                    ))
    
    return deals


async def main():
    """Main function"""
    print("=" * 70)
    print("Move Bitrix Deals to MaaS Funnel")
    print("=" * 70)
    
    # Check Bitrix configuration
    if not bitrix_client.is_configured():
        print("❌ Bitrix not configured. Please check your .env file.")
        return
    
    # Initialize funnel manager
    print("\n[1/4] Initializing MaaS funnel...")
    await funnel_manager.ensure_maas_funnel()
    
    if not funnel_manager.is_initialized():
        print("❌ Failed to initialize MaaS funnel")
        return
    
    category_id = funnel_manager.get_category_id()
    print(f"✅ MaaS funnel initialized with category ID: {category_id}")
    
    # Get all deals not in MaaS funnel
    print("\n[2/4] Finding deals not in MaaS funnel...")
    all_deals = await get_all_deals_not_in_maas()
    
    if not all_deals:
        print("✅ All deals are already in MaaS funnel!")
        return
    
    print(f"\nFound {len(all_deals)} deal(s) not in MaaS funnel:\n")
    print(f"{'#':<4} {'Order ID':<10} {'Deal ID':<10} {'Status':<15} {'Current Category':<20}")
    print("-" * 70)
    
    for idx, (order_id, deal_id, status, cat_id) in enumerate(all_deals, 1):
        cat_str = f"Category {cat_id}" if cat_id else "Default"
        print(f"{idx:<4} {order_id:<10} {deal_id:<10} {status:<15} {cat_str:<20}")
    
    # Interactive selection
    print("\n[3/4] Select deals to move:")
    print("  - Enter deal numbers separated by commas (e.g., 1,3,5)")
    print("  - Enter 'all' to move all deals")
    print("  - Enter 'q' to quit")
    
    while True:
        try:
            selection = input("\nYour choice: ").strip().lower()
            
            if selection == 'q':
                print("Cancelled.")
                return
            
            if selection == 'all':
                selected_deals = all_deals
                break
            
            # Parse comma-separated numbers
            indices = [int(x.strip()) for x in selection.split(',')]
            selected_deals = []
            
            for idx in indices:
                if 1 <= idx <= len(all_deals):
                    selected_deals.append(all_deals[idx - 1])
                else:
                    print(f"⚠️  Invalid number: {idx} (must be between 1 and {len(all_deals)})")
            
            if selected_deals:
                break
            else:
                print("⚠️  No valid deals selected. Please try again.")
                
        except ValueError:
            print("⚠️  Invalid input. Please enter numbers separated by commas, 'all', or 'q'.")
        except KeyboardInterrupt:
            print("\n\nCancelled.")
            return
    
    if not selected_deals:
        print("❌ No deals selected")
        return
    
    # Confirm
    print(f"\n[4/4] Moving {len(selected_deals)} deal(s) to MaaS funnel...")
    confirm = input("Continue? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Cancelled.")
        return
    
    # Move deals
    print()
    success_count = 0
    for order_id, deal_id, status, _ in selected_deals:
        print(f"  Moving deal {deal_id} (order {order_id}, status: {status})...", end=" ")
        if await move_deal_to_maas_funnel(deal_id, order_id):
            success_count += 1
            print("✅")
        else:
            print("❌")
    
    print("\n" + "=" * 70)
    print(f"✅ Successfully moved {success_count}/{len(selected_deals)} deal(s) to MaaS funnel")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())


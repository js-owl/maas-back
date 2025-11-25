"""
Bitrix Cleanup Service
Handles cleanup of duplicate deals and other maintenance tasks
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend import models
from backend.bitrix.client import bitrix_client
from backend.utils.logging import get_logger
from datetime import datetime

logger = get_logger(__name__)


class BitrixCleanupService:
    """Service for cleaning up duplicate or incorrect Bitrix deals"""
    
    async def find_duplicate_deals_for_order(self, order_id: int, known_deal_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Find all deals in Bitrix that match the order pattern.
        Returns list of deals with their IDs and creation dates.
        
        Since crm.deal.list API has format issues, we use a workaround:
        Check deals around the known deal ID to find duplicates.
        """
        try:
            if not bitrix_client.is_configured():
                return []
            
            matching_deals = []
            
            # If we have a known deal ID, check deals around it
            if known_deal_id:
                # Check a range around the known deal ID
                start_id = max(1, known_deal_id - 20)
                end_id = known_deal_id + 20
                
                logger.info(f"Checking deals in range {start_id}-{end_id} for order {order_id}")
                
                for deal_id in range(start_id, end_id + 1):
                    try:
                        deal = await bitrix_client.get_deal(deal_id)
                        if deal:
                            title = deal.get('TITLE', '')
                            # Check if title matches order pattern
                            if f"Order #{order_id}" in title or f"Order #{order_id} -" in title:
                                matching_deals.append({
                                    'ID': str(deal_id),
                                    'TITLE': title,
                                    'DATE_CREATE': deal.get('DATE_CREATE', ''),
                                    'DATE_MODIFY': deal.get('DATE_MODIFY', ''),
                                    'CATEGORY_ID': deal.get('CATEGORY_ID', ''),
                                    'STAGE_ID': deal.get('STAGE_ID', '')
                                })
                    except Exception:
                        # Deal doesn't exist or error, skip silently
                        # This is expected for most IDs in the range
                        pass
            else:
                # No known deal ID - try a broader search
                # Start from deal ID 1 and go up to 200 (reasonable range)
                logger.info(f"No known deal ID, checking deals 1-200 for order {order_id}")
                for deal_id in range(1, 201):
                    try:
                        deal = await bitrix_client.get_deal(deal_id)
                        if deal:
                            title = deal.get('TITLE', '')
                            if f"Order #{order_id}" in title or f"Order #{order_id} -" in title:
                                matching_deals.append({
                                    'ID': str(deal_id),
                                    'TITLE': title,
                                    'DATE_CREATE': deal.get('DATE_CREATE', ''),
                                    'DATE_MODIFY': deal.get('DATE_MODIFY', ''),
                                    'CATEGORY_ID': deal.get('CATEGORY_ID', ''),
                                    'STAGE_ID': deal.get('STAGE_ID', '')
                                })
                    except Exception:
                        pass
            
            # Sort by creation date descending (newest first)
            if matching_deals:
                try:
                    matching_deals.sort(
                        key=lambda d: datetime.fromisoformat(d.get("DATE_CREATE", "1970-01-01").replace("Z", "+00:00")) if d.get("DATE_CREATE") else datetime.min,
                        reverse=True
                    )
                except Exception as e:
                    logger.warning(f"Error sorting deals: {e}")
            
            if matching_deals:
                logger.info(f"Found {len(matching_deals)} deals matching order {order_id}")
                return matching_deals
            return []
            
        except Exception as e:
            logger.error(f"Error finding duplicate deals for order {order_id}: {e}", exc_info=True)
            return []
    
    async def cleanup_duplicate_deals_for_order(
        self, 
        db: AsyncSession, 
        order_id: int, 
        keep_latest: bool = True
    ) -> Dict[str, Any]:
        """
        Clean up duplicate deals for an order.
        Keeps the latest deal (or the one stored in DB) and deletes the rest.
        
        Returns:
            {
                "order_id": order_id,
                "deals_found": count,
                "deals_deleted": count,
                "deal_kept": deal_id,
                "errors": []
            }
        """
        try:
            # Get order from DB
            order_result = await db.execute(
                select(models.Order).where(models.Order.order_id == order_id)
            )
            order = order_result.scalar_one_or_none()
            
            if not order:
                return {
                    "order_id": order_id,
                    "deals_found": 0,
                    "deals_deleted": 0,
                    "deal_kept": None,
                    "errors": [f"Order {order_id} not found"]
                }
            
            # Find all duplicate deals (pass known deal ID for efficient search)
            duplicate_deals = await self.find_duplicate_deals_for_order(order_id, order.bitrix_deal_id)
            
            if not duplicate_deals:
                return {
                    "order_id": order_id,
                    "deals_found": 0,
                    "deals_deleted": 0,
                    "deal_kept": order.bitrix_deal_id,
                    "errors": []
                }
            
            # Determine which deal to keep
            deal_to_keep = None
            
            if keep_latest:
                # Keep the most recently created deal
                if duplicate_deals:
                    deal_to_keep = duplicate_deals[0]  # Already sorted by DATE_CREATE DESC
                    deal_to_keep_id = int(deal_to_keep.get("ID", 0))
            else:
                # Keep the one stored in DB
                if order.bitrix_deal_id:
                    deal_to_keep_id = order.bitrix_deal_id
                    # Find this deal in the list
                    for deal in duplicate_deals:
                        if int(deal.get("ID", 0)) == deal_to_keep_id:
                            deal_to_keep = deal
                            break
                else:
                    # No deal in DB, keep the latest
                    if duplicate_deals:
                        deal_to_keep = duplicate_deals[0]
                        deal_to_keep_id = int(deal_to_keep.get("ID", 0))
            
            if not deal_to_keep:
                logger.warning(f"Could not determine which deal to keep for order {order_id}")
                return {
                    "order_id": order_id,
                    "deals_found": len(duplicate_deals),
                    "deals_deleted": 0,
                    "deal_kept": None,
                    "errors": ["Could not determine which deal to keep"]
                }
            
            deal_to_keep_id = int(deal_to_keep.get("ID", 0))
            
            # Delete all other deals
            deleted_count = 0
            errors = []
            
            for deal in duplicate_deals:
                deal_id = int(deal.get("ID", 0))
                if deal_id != deal_to_keep_id:
                    try:
                        success = await bitrix_client.delete_deal(deal_id)
                        if success:
                            deleted_count += 1
                            logger.info(f"Deleted duplicate deal {deal_id} for order {order_id}")
                        else:
                            errors.append(f"Failed to delete deal {deal_id}")
                    except Exception as e:
                        error_msg = f"Error deleting deal {deal_id}: {e}"
                        errors.append(error_msg)
                        logger.error(error_msg, exc_info=True)
            
            # Update order's bitrix_deal_id if it's not set or points to a deleted deal
            if not order.bitrix_deal_id or order.bitrix_deal_id != deal_to_keep_id:
                order.bitrix_deal_id = deal_to_keep_id
                await db.commit()
                logger.info(f"Updated order {order_id} to point to deal {deal_to_keep_id}")
            
            return {
                "order_id": order_id,
                "deals_found": len(duplicate_deals),
                "deals_deleted": deleted_count,
                "deal_kept": deal_to_keep_id,
                "errors": errors
            }
            
        except Exception as e:
            logger.error(f"Error cleaning up duplicate deals for order {order_id}: {e}", exc_info=True)
            return {
                "order_id": order_id,
                "deals_found": 0,
                "deals_deleted": 0,
                "deal_kept": None,
                "errors": [str(e)]
            }
    
    async def cleanup_all_duplicate_deals(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Clean up duplicate deals for all orders.
        Returns summary of cleanup operations.
        """
        try:
            # Get all orders with Bitrix deals
            orders_result = await db.execute(
                select(models.Order)
                .where(models.Order.bitrix_deal_id.isnot(None))
                .order_by(models.Order.order_id)
            )
            orders = orders_result.scalars().all()
            
            total_orders = len(orders)
            total_deals_found = 0
            total_deals_deleted = 0
            orders_cleaned = 0
            all_errors = []
            
            logger.info(f"Starting cleanup for {total_orders} orders with Bitrix deals")
            
            for order in orders:
                result = await self.cleanup_duplicate_deals_for_order(db, order.order_id)
                total_deals_found += result["deals_found"]
                total_deals_deleted += result["deals_deleted"]
                if result["deals_deleted"] > 0:
                    orders_cleaned += 1
                all_errors.extend(result["errors"])
            
            return {
                "total_orders_checked": total_orders,
                "orders_with_duplicates": orders_cleaned,
                "total_deals_found": total_deals_found,
                "total_deals_deleted": total_deals_deleted,
                "errors": all_errors
            }
            
        except Exception as e:
            logger.error(f"Error in cleanup_all_duplicate_deals: {e}", exc_info=True)
            return {
                "total_orders_checked": 0,
                "orders_with_duplicates": 0,
                "total_deals_found": 0,
                "total_deals_deleted": 0,
                "errors": [str(e)]
            }


# Global instance
bitrix_cleanup_service = BitrixCleanupService()

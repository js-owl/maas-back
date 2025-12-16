"""
Bitrix Deal Sync Scheduler
Runs periodic background task to sync Bitrix deal data
"""
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import AsyncSessionLocal
from backend.bitrix.deal_sync_service import deal_sync_service
from backend.utils.logging import get_logger

logger = get_logger(__name__)


class BitrixDealSyncScheduler:
    """Scheduler for periodic Bitrix deal sync"""
    
    def __init__(self, interval_seconds: int = 300):
        """
        Initialize scheduler
        
        Args:
            interval_seconds: Sync interval in seconds (default: 300 = 5 minutes)
        """
        self.interval_seconds = interval_seconds
        self.running = False
        self.task = None
    
    async def start_sync_task(self) -> None:
        """Start the background sync task"""
        try:
            self.running = True
            logger.info(f"Starting Bitrix deal sync scheduler (interval: {self.interval_seconds}s)")
            
            # Initial delay before first sync
            await asyncio.sleep(10)
            
            while self.running:
                try:
                    # Create database session for this sync cycle
                    async with AsyncSessionLocal() as db:
                        logger.info("[DEAL_SYNC_SCHEDULER] Starting sync cycle")
                        stats = await deal_sync_service.sync_all_orders(db)
                        logger.info(f"[DEAL_SYNC_SCHEDULER] Sync cycle completed: {stats}")
                    
                except asyncio.CancelledError:
                    logger.info("[DEAL_SYNC_SCHEDULER] Sync task cancelled")
                    self.running = False
                    break
                except Exception as e:
                    logger.error(f"[DEAL_SYNC_SCHEDULER] Error in sync cycle: {e}", exc_info=True)
                    # Continue running even if there's an error
                
                # Wait for next interval
                if self.running:
                    await asyncio.sleep(self.interval_seconds)
            
            logger.info("[DEAL_SYNC_SCHEDULER] Sync scheduler stopped")
            
        except Exception as e:
            logger.error(f"[DEAL_SYNC_SCHEDULER] Fatal error in sync scheduler: {e}", exc_info=True)
            self.running = False
    
    def stop(self) -> None:
        """Stop the sync scheduler"""
        logger.info("[DEAL_SYNC_SCHEDULER] Stopping sync scheduler")
        self.running = False
        if self.task:
            self.task.cancel()


# Global instance
deal_sync_scheduler = BitrixDealSyncScheduler()



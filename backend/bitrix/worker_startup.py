"""
Bitrix Worker Startup Script
Starts the Bitrix message worker to process Redis Streams
"""
import asyncio
import signal
import sys
from backend.bitrix.worker import bitrix_worker
from backend.bitrix.queue_service import bitrix_queue_service
from backend.core.config import BITRIX_WORKER_ENABLED
from backend.utils.logging import get_logger

logger = get_logger(__name__)


async def main():
    """Main entry point for worker"""
    if not BITRIX_WORKER_ENABLED:
        logger.info("Bitrix worker is disabled (BITRIX_WORKER_ENABLED=false)")
        return
    
    logger.info("Starting Bitrix worker...")
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, shutting down worker...")
        asyncio.create_task(bitrix_worker.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Start worker
        await bitrix_worker.process_messages()
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
    except Exception as e:
        logger.error(f"Worker error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # Cleanup
        await bitrix_queue_service.close()
        logger.info("Worker stopped")


if __name__ == "__main__":
    asyncio.run(main())


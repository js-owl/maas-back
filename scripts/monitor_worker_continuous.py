"""Continuous monitoring of worker status and message processing"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from backend.bitrix.worker import bitrix_worker
from backend.bitrix.queue_service import bitrix_queue_service
import redis.asyncio as redis
from backend.core.config import REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_STREAM_PREFIX

async def monitor():
    redis_client = await redis.Redis(
        host=REDIS_HOST,
        port=int(REDIS_PORT),
        db=int(REDIS_DB),
        decode_responses=True
    )
    
    operations_stream = f"{REDIS_STREAM_PREFIX}operations"
    consumer_group = "bitrix_workers"
    
    print("=" * 70)
    print("Worker Continuous Monitoring")
    print("=" * 70)
    print("Monitoring every 5 seconds. Press Ctrl+C to stop.\n")
    
    previous_pending = None
    previous_stream_length = None
    iteration = 0
    
    try:
        while True:
            iteration += 1
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # Check worker running status
            worker_running = bitrix_worker.running
            
            # Get stream info
            stream_length = await redis_client.xlen(operations_stream)
            
            # Get pending messages
            try:
                groups = await redis_client.xinfo_groups(operations_stream)
                pending_count = 0
                for group in groups:
                    if group['name'] == consumer_group:
                        pending_count = group['pending']
                        break
            except:
                pending_count = 0
            
            # Get recent messages to see if processing is happening
            try:
                recent = await redis_client.xrevrange(operations_stream, count=3)
                recent_msg_types = []
                for msg_id, fields in recent:
                    entity_type = fields.get('entity_type', 'unknown')
                    entity_id = fields.get('entity_id', 'unknown')
                    operation = fields.get('operation', 'unknown')
                    recent_msg_types.append(f"{entity_type} {entity_id} - {operation}")
            except:
                recent_msg_types = []
            
            # Calculate changes
            pending_change = ""
            if previous_pending is not None:
                change = pending_count - previous_pending
                if change < 0:
                    pending_change = f" (↓{abs(change)})"
                elif change > 0:
                    pending_change = f" (↑{change})"
            
            stream_change = ""
            if previous_stream_length is not None:
                change = stream_length - previous_stream_length
                if change < 0:
                    stream_change = f" (↓{abs(change)})"
                elif change > 0:
                    stream_change = f" (↑{change})"
            
            # Print status
            status_icon = "✓" if worker_running else "✗"
            print(f"[{timestamp}] Iteration {iteration}")
            print(f"  Worker Running: {status_icon} {worker_running}")
            print(f"  Stream Length: {stream_length}{stream_change}")
            print(f"  Pending Messages: {pending_count}{pending_change}")
            if recent_msg_types:
                print(f"  Recent Messages: {', '.join(recent_msg_types[:2])}")
            
            # Check if messages are being processed
            if previous_pending is not None and pending_count < previous_pending:
                print(f"  ✓ Messages being processed! ({previous_pending} → {pending_count})")
            
            if previous_stream_length is not None and stream_length > previous_stream_length:
                print(f"  ⚠️  New messages added to stream ({previous_stream_length} → {stream_length})")
            
            print()
            
            previous_pending = pending_count
            previous_stream_length = stream_length
            
            await asyncio.sleep(5)
            
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped by user")
    except Exception as e:
        print(f"\n\nError during monitoring: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await redis_client.aclose()

if __name__ == "__main__":
    asyncio.run(monitor())










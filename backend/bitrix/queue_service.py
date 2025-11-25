"""
Bitrix Redis Queue Service
Handles publishing and consuming messages via Redis Streams
"""
import json
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from redis import asyncio as aioredis
from backend.core.config import (
    REDIS_HOST, REDIS_PORT, REDIS_PASSWORD, REDIS_DB, REDIS_STREAM_PREFIX
)
from backend.utils.logging import get_logger

logger = get_logger(__name__)


class BitrixQueueService:
    """Service for managing Bitrix operations via Redis Streams"""
    
    def __init__(self):
        self.redis_client: Optional[aioredis.Redis] = None
        self.operations_stream = f"{REDIS_STREAM_PREFIX}operations"
        self.webhooks_stream = f"{REDIS_STREAM_PREFIX}webhooks"
        self.consumer_group = "bitrix_workers"
        self.consumer_name = f"worker_{uuid.uuid4().hex[:8]}"
    
    async def _get_redis(self) -> aioredis.Redis:
        """Get or create Redis connection"""
        if self.redis_client is None:
            redis_url = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
            if REDIS_PASSWORD:
                redis_url = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
            self.redis_client = aioredis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True
            )
        return self.redis_client
    
    async def _ensure_consumer_group(self, stream_name: str) -> None:
        """Ensure consumer group exists for stream"""
        try:
            redis = await self._get_redis()
            # Try to create consumer group, ignore if it already exists
            await redis.xgroup_create(
                name=stream_name,
                groupname=self.consumer_group,
                id="0",
                mkstream=True
            )
            logger.debug(f"Created consumer group {self.consumer_group} for stream {stream_name}")
        except Exception as e:
            error_str = str(e)
            if "BUSYGROUP" in error_str or "already exists" in error_str.lower():
                # Group already exists, that's fine
                logger.debug(f"Consumer group {self.consumer_group} already exists for {stream_name}")
            else:
                logger.error(f"Error creating consumer group: {e}")
                raise
    
    async def publish_operation(
        self,
        entity_type: str,
        entity_id: int,
        operation: str,
        payload: Dict[str, Any]
    ) -> Optional[str]:
        """
        Publish Bitrix operation to Redis Stream
        
        Args:
            entity_type: 'deal', 'contact', or 'lead'
            entity_id: ID of the entity (order_id, user_id, call_request_id)
            operation: 'create' or 'update'
            payload: Operation data
            
        Returns:
            Message ID if successful, None otherwise
        """
        try:
            redis = await self._get_redis()
            
            message_data = {
                "entity_type": entity_type,
                "entity_id": str(entity_id),
                "operation": operation,
                "payload": json.dumps(payload),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "retry_count": "0"
            }
            
            message_id = await redis.xadd(
                name=self.operations_stream,
                fields=message_data
            )
            
            logger.info(
                f"[QUEUE] Published {operation} operation for {entity_type} {entity_id} "
                f"to stream {self.operations_stream} (message_id: {message_id})"
            )
            logger.debug(
                f"[QUEUE] Message payload: {json.dumps(payload)[:200]}..."
            )
            return message_id
            
        except Exception as e:
            logger.error(f"Error publishing operation to Redis: {e}", exc_info=True)
            return None
    
    async def publish_webhook_event(
        self,
        event_type: str,
        entity_type: str,
        entity_id: int,
        data: Dict[str, Any]
    ) -> Optional[str]:
        """
        Publish webhook event to Redis Stream
        
        Args:
            event_type: Event type (e.g., 'deal_updated', 'contact_updated')
            entity_type: 'deal', 'contact', or 'lead'
            entity_id: Bitrix entity ID
            data: Webhook payload data
            
        Returns:
            Message ID if successful, None otherwise
        """
        try:
            redis = await self._get_redis()
            
            message_data = {
                "event_type": event_type,
                "entity_type": entity_type,
                "entity_id": str(entity_id),
                "data": json.dumps(data),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            message_id = await redis.xadd(
                name=self.webhooks_stream,
                fields=message_data
            )
            
            logger.info(
                f"Published webhook event {event_type} for {entity_type} {entity_id} "
                f"to stream {self.webhooks_stream} (message_id: {message_id})"
            )
            return message_id
            
        except Exception as e:
            logger.error(f"Error publishing webhook to Redis: {e}", exc_info=True)
            return None
    
    async def get_pending_messages(
        self,
        stream_name: str,
        count: int = 10,
        block_ms: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Get pending messages from stream for this consumer
        
        Args:
            stream_name: Name of the stream
            count: Maximum number of messages to retrieve
            block_ms: Block for this many milliseconds if no messages available
            
        Returns:
            List of messages with their IDs
        """
        try:
            redis = await self._get_redis()
            await self._ensure_consumer_group(stream_name)
            
            # First, check for messages pending to this consumer or any other consumer (idle > 60s)
            try:
                # Check for messages pending to this consumer
                pending_this_consumer = await redis.xpending_range(
                    name=stream_name,
                    groupname=self.consumer_group,
                    consumername=self.consumer_name,
                    min="-",
                    max="+",
                    count=count
                )
                
                # Also check for messages pending to any consumer (for claiming from dead consumers)
                pending_all = await redis.xpending_range(
                    name=stream_name,
                    groupname=self.consumer_group,
                    min="-",
                    max="+",
                    count=count
                )
                
                # Collect message IDs from both sources
                # xpending_range returns tuples: (message_id, consumer_name, time_since_delivered_ms, delivery_count)
                message_ids = []
                if pending_this_consumer:
                    for msg in pending_this_consumer:
                        if isinstance(msg, (list, tuple)) and len(msg) >= 1:
                            message_ids.append(msg[0])
                        elif isinstance(msg, dict):
                            message_ids.append(msg.get("message_id"))
                
                # Claim messages from other consumers that have been idle for > 60 seconds
                if pending_all:
                    for msg in pending_all:
                        if isinstance(msg, (list, tuple)) and len(msg) >= 3:
                            msg_id = msg[0]
                            time_idle_ms = msg[2]  # time_since_delivered in milliseconds
                            if msg_id not in message_ids and time_idle_ms > 60000:
                                message_ids.append(msg_id)
                        elif isinstance(msg, dict):
                            msg_id = msg.get("message_id")
                            time_idle_ms = msg.get("time_since_delivered", 0)
                            if msg_id and msg_id not in message_ids and time_idle_ms > 60000:
                                message_ids.append(msg_id)
                
                if message_ids:
                    # Claim and read pending messages
                    claimed = await redis.xclaim(
                        name=stream_name,
                        groupname=self.consumer_group,
                        consumername=self.consumer_name,
                        min_idle_time=0,  # Claim immediately
                        message_ids=message_ids
                    )
                    
                    result = []
                    for message_id, fields in claimed:
                        try:
                            # Parse payload if present
                            if "payload" in fields:
                                fields["payload"] = json.loads(fields["payload"])
                            if "data" in fields:
                                fields["data"] = json.loads(fields["data"])
                            
                            result.append({
                                "id": message_id,
                                "stream": stream_name,
                                **fields
                            })
                        except json.JSONDecodeError as e:
                            logger.error(f"Error parsing message {message_id}: {e}")
                            # Acknowledge bad message to prevent reprocessing
                            await self.acknowledge_message(stream_name, message_id)
                    
                    if result:
                        logger.info(f"Read {len(result)} pending messages (claimed) from stream {stream_name}")
                        return result
            except Exception as e:
                logger.debug(f"No pending messages to claim: {e}")
            
            # First, read new messages that arrive after consumer group creation (prioritize new messages)
            # Use ">" to read messages that haven't been delivered to any consumer in the group
            # Skip if block_ms=0 (non-blocking) to avoid hanging
            if block_ms > 0:
                try:
                    messages = await redis.xreadgroup(
                        groupname=self.consumer_group,
                        consumername=self.consumer_name,
                        streams={stream_name: ">"},
                        count=count,
                        block=block_ms
                    )
                    
                    result = []
                    for stream, stream_messages in messages:
                        for message_id, fields in stream_messages:
                            try:
                                # Parse payload if present
                                if "payload" in fields:
                                    fields["payload"] = json.loads(fields["payload"])
                                if "data" in fields:
                                    fields["data"] = json.loads(fields["data"])
                                
                                result.append({
                                    "id": message_id,
                                    "stream": stream,
                                    **fields
                                })
                            except json.JSONDecodeError as e:
                                logger.error(f"Error parsing message {message_id}: {e}")
                                # Acknowledge bad message to prevent reprocessing
                                await self.acknowledge_message(stream_name, message_id)
                    
                    if result:
                        logger.info(f"Read {len(result)} new messages from stream {stream_name}")
                        return result
                except Exception as e:
                    error_str = str(e).lower()
                    # Some Redis errors are expected (timeout, no messages)
                    if "timeout" in error_str or "no messages" in error_str or "empty" in error_str:
                        logger.debug(f"No new messages from stream: {e}")
                    else:
                        logger.warning(f"Unexpected error reading new messages: {e}")
            else:
                # Non-blocking mode: try to read without blocking, but don't wait
                try:
                    messages = await redis.xreadgroup(
                        groupname=self.consumer_group,
                        consumername=self.consumer_name,
                        streams={stream_name: ">"},
                        count=count,
                        block=1  # Use minimal block time (1ms) to avoid hanging
                    )
                    
                    result = []
                    for stream, stream_messages in messages:
                        for message_id, fields in stream_messages:
                            try:
                                # Parse payload if present
                                if "payload" in fields:
                                    fields["payload"] = json.loads(fields["payload"])
                                if "data" in fields:
                                    fields["data"] = json.loads(fields["data"])
                                
                                result.append({
                                    "id": message_id,
                                    "stream": stream,
                                    **fields
                                })
                            except json.JSONDecodeError as e:
                                logger.error(f"Error parsing message {message_id}: {e}")
                                # Acknowledge bad message to prevent reprocessing
                                await self.acknowledge_message(stream_name, message_id)
                    
                    if result:
                        logger.info(f"Read {len(result)} new messages from stream {stream_name}")
                        return result
                except Exception as e:
                    error_str = str(e).lower()
                    # In non-blocking mode, it's expected to get no messages
                    if "timeout" in error_str or "no messages" in error_str or "empty" in error_str:
                        logger.debug(f"No new messages from stream (non-blocking): {e}")
                    else:
                        logger.debug(f"Non-blocking read returned: {e}")
            
            # Then, try to read from beginning (0) to catch messages that existed
            # before the consumer group was created (only if no new messages)
            try:
                messages_from_start = await redis.xreadgroup(
                    groupname=self.consumer_group,
                    consumername=self.consumer_name,
                    streams={stream_name: "0"},
                    count=count
                )
                
                result = []
                for stream, stream_messages in messages_from_start:
                    for message_id, fields in stream_messages:
                        try:
                            # Parse payload if present
                            if "payload" in fields:
                                fields["payload"] = json.loads(fields["payload"])
                            if "data" in fields:
                                fields["data"] = json.loads(fields["data"])
                            
                            result.append({
                                "id": message_id,
                                "stream": stream,
                                **fields
                            })
                        except json.JSONDecodeError as e:
                            logger.error(f"Error parsing message {message_id}: {e}")
                            # Acknowledge bad message to prevent reprocessing
                            await self.acknowledge_message(stream_name, message_id)
                
                if result:
                    logger.info(f"Read {len(result)} messages from beginning of stream {stream_name}")
                    return result
            except Exception as e:
                # If reading from 0 fails (e.g., no messages), that's okay
                logger.debug(f"No messages from beginning of stream: {e}")
            
            # No messages found
            return []
            
        except Exception as e:
            logger.error(f"Error reading messages from Redis: {e}", exc_info=True)
            return []
    
    async def acknowledge_message(self, stream_name: str, message_id: str) -> bool:
        """
        Acknowledge message processing
        
        Args:
            stream_name: Name of the stream
            message_id: Message ID to acknowledge
            
        Returns:
            True if successful, False otherwise
        """
        try:
            redis = await self._get_redis()
            # xack signature: xack(name, groupname, *ids)
            await redis.xack(stream_name, self.consumer_group, message_id)
            logger.debug(f"Acknowledged message {message_id} from stream {stream_name}")
            return True
        except Exception as e:
            logger.error(f"Error acknowledging message: {e}", exc_info=True)
            return False
    
    async def claim_pending_messages(
        self,
        stream_name: str,
        min_idle_time_ms: int = 60000,
        count: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Claim pending messages that have been idle for too long
        (for retry logic)
        
        Args:
            stream_name: Name of the stream
            min_idle_time_ms: Minimum idle time in milliseconds
            count: Maximum number of messages to claim
            
        Returns:
            List of claimed messages
        """
        try:
            redis = await self._get_redis()
            await self._ensure_consumer_group(stream_name)
            
            # Get pending entries
            pending = await redis.xpending_range(
                name=stream_name,
                groupname=self.consumer_group,
                min="-",
                max="+",
                count=count
            )
            
            if not pending:
                return []
            
            # Claim messages that are idle
            message_ids = [msg["message_id"] for msg in pending if msg["time_since_delivered"] >= min_idle_time_ms]
            
            if not message_ids:
                return []
            
            claimed = await redis.xclaim(
                name=stream_name,
                groupname=self.consumer_group,
                consumername=self.consumer_name,
                min_idle_time=min_idle_time_ms,
                message_ids=message_ids
            )
            
            result = []
            for message_id, fields in claimed:
                try:
                    # Parse payload if present
                    if "payload" in fields:
                        fields["payload"] = json.loads(fields["payload"])
                    if "data" in fields:
                        fields["data"] = json.loads(fields["data"])
                    
                    # Increment retry count
                    retry_count = int(fields.get("retry_count", "0")) + 1
                    fields["retry_count"] = str(retry_count)
                    
                    result.append({
                        "id": message_id,
                        "stream": stream_name,
                        **fields
                    })
                except (json.JSONDecodeError, ValueError) as e:
                    logger.error(f"Error parsing claimed message {message_id}: {e}")
            
            if result:
                logger.info(f"Claimed {len(result)} pending messages from {stream_name}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error claiming pending messages: {e}", exc_info=True)
            return []
    
    async def get_stream_info(self, stream_name: str) -> Dict[str, Any]:
        """
        Get stream information (length, groups, etc.)
        
        Args:
            stream_name: Name of the stream
            
        Returns:
            Dictionary with stream information
        """
        try:
            redis = await self._get_redis()
            info = await redis.xinfo_stream(stream_name)
            
            # Get consumer group info
            try:
                groups_info = await redis.xinfo_groups(stream_name)
            except:
                groups_info = []
            
            return {
                "length": info.get("length", 0),
                "groups": len(groups_info),
                "last_id": info.get("last-generated-id", "0-0"),
                "groups_info": groups_info
            }
        except Exception as e:
            error_str = str(e).lower()
            if "no such key" in error_str or "not found" in error_str:
                return {"length": 0, "groups": 0, "last_id": "0-0", "groups_info": []}
            logger.error(f"Error getting stream info: {e}", exc_info=True)
            return {}
    
    async def close(self) -> None:
        """Close Redis connection"""
        if self.redis_client:
            try:
                await self.redis_client.aclose()
            except Exception:
                pass
            self.redis_client = None


# Global instance
bitrix_queue_service = BitrixQueueService()


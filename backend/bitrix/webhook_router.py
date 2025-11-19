"""
Bitrix webhook router
Handles incoming webhooks from Bitrix24 for event notifications
Publishes webhook events to Redis Streams for async processing
"""
from fastapi import APIRouter, Request, Response, HTTPException
from backend.bitrix.queue_service import bitrix_queue_service
from backend.utils.logging import get_logger
import json
from typing import Dict, Any

logger = get_logger(__name__)
router = APIRouter()


@router.post('/bitrix/webhook', tags=["Bitrix Webhook"])
async def bitrix_webhook(request: Request):
    """
    Receive outgoing webhooks from Bitrix24 for event notifications
    Publishes webhook events to Redis Streams for async processing
    
    Handles events:
    - deal updated
    - contact updated  
    - lead updated
    - invoice generated
    """
    try:
        # Get the raw request body
        body = await request.body()
        
        # Parse JSON payload
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            logger.warning("Invalid JSON payload in Bitrix webhook")
            raise HTTPException(status_code=400, detail="Invalid JSON payload")
        
        # Extract event information
        event_type = payload.get('event_type', 'unknown')
        entity_type = payload.get('entity_type', 'unknown')
        entity_id = payload.get('entity_id')
        
        if not entity_id:
            logger.warning("Missing entity_id in webhook payload")
            raise HTTPException(status_code=400, detail="Missing entity_id")
        
        try:
            entity_id = int(entity_id)
        except (ValueError, TypeError):
            logger.warning(f"Invalid entity_id in webhook payload: {entity_id}")
            raise HTTPException(status_code=400, detail="Invalid entity_id")
        
        logger.info(f"Bitrix webhook received: {event_type} for {entity_type} {entity_id}")
        logger.debug(f"Webhook payload: {json.dumps(payload, indent=2)}")
        
        # Map event types to entity types if needed
        if entity_type == 'unknown' and event_type:
            # Try to infer entity type from event type
            if 'deal' in event_type.lower():
                entity_type = 'deal'
            elif 'contact' in event_type.lower():
                entity_type = 'contact'
            elif 'lead' in event_type.lower():
                entity_type = 'lead'
            elif 'invoice' in event_type.lower():
                entity_type = 'invoice'
        
        # Publish webhook event to Redis Stream
        message_id = await bitrix_queue_service.publish_webhook_event(
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            data=payload.get('data', payload)
        )
        
        if message_id:
            logger.info(
                f"Published webhook {event_type} for {entity_type} {entity_id} "
                f"to Redis (message_id: {message_id})"
            )
            return Response(status_code=200, content="Webhook queued successfully")
        else:
            logger.error(f"Failed to publish webhook {event_type} for {entity_type} {entity_id} to Redis")
            # Still return 200 to avoid Bitrix retries, but log the error
            return Response(status_code=200, content="Webhook received but queuing failed")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing Bitrix webhook: {e}", exc_info=True)
        # Return 200 to avoid Bitrix retries for transient errors
        return Response(status_code=200, content="Webhook received but processing failed")


# Note: Webhook handling functions removed
# Webhook events are now published to Redis Streams and processed by BitrixWorker


@router.options('/bitrix/webhook', tags=["Bitrix Webhook"])
async def bitrix_webhook_options():
    """Handle CORS preflight requests for Bitrix webhook"""
    return Response(status_code=200)

"""
Bitrix webhook router
Handles incoming webhooks from Bitrix24 for event notifications
Publishes webhook events to Redis Streams for async processing
"""
from fastapi import APIRouter, Request, Response, HTTPException, Query
from backend.bitrix.queue_service import bitrix_queue_service
from backend.core.config import BITRIX_WEBHOOK_TOKEN
from backend.utils.logging import get_logger
import json
from typing import Dict, Any, Optional

logger = get_logger(__name__)
router = APIRouter()


def verify_bitrix_webhook_token(request: Request, token: Optional[str] = None) -> bool:
    """
    Verify that webhook request is from Bitrix by checking token.
    Token can be provided in:
    - Query parameter: ?token=...
    - Header: X-Bitrix-Token or Authorization: Bearer ...
    - Request body: token field
    
    NOTE: Token verification is currently disabled for easier testing.
    Set BITRIX_WEBHOOK_TOKEN environment variable and uncomment verification code to enable.
    
    Args:
        request: FastAPI Request object
        token: Optional token from query parameter
        
    Returns:
        True (token verification disabled)
    """
    # Token verification disabled - always return True
    logger.info("=== WEBHOOK TOKEN VERIFICATION DISABLED - ALWAYS RETURNING TRUE ===")
    logger.debug("Webhook token verification disabled - accepting all requests")
    return True
    
    # Uncomment below to enable token verification:
    # if not BITRIX_WEBHOOK_TOKEN:
    #     logger.warning("BITRIX_WEBHOOK_TOKEN not configured, skipping webhook authentication")
    #     return True  # Allow if not configured (for backward compatibility)
    # 
    # # Check query parameter
    # if token:
    #     if token == BITRIX_WEBHOOK_TOKEN:
    #         return True
    # 
    # # Check headers
    # bitrix_token_header = request.headers.get("X-Bitrix-Token")
    # if bitrix_token_header and bitrix_token_header == BITRIX_WEBHOOK_TOKEN:
    #     return True
    # 
    # auth_header = request.headers.get("Authorization", "")
    # if auth_header.startswith("Bearer "):
    #     bearer_token = auth_header[7:].strip()
    #     if bearer_token == BITRIX_WEBHOOK_TOKEN:
    #         return True
    # 
    # # Check request body (will be checked after parsing)
    # return False


def parse_bitrix_webhook(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse Bitrix webhook payload and normalize to internal format.
    Handles multiple Bitrix webhook formats:
    - Format 1: {event, data: {FIELDS: {...}}}
    - Format 2: {event_type, entity_type, entity_id, data: {...}}
    - Format 3: Direct deal object with ID, STAGE_ID, etc.
    
    Returns normalized webhook data with:
    - event_type: Event type (e.g., 'deal_updated')
    - entity_type: Entity type ('deal', 'contact', 'lead')
    - entity_id: Entity ID
    - data: Comprehensive entity data including old/new values
    """
    normalized = {
        "event_type": "unknown",
        "entity_type": "unknown",
        "entity_id": None,
        "data": {}
    }
    
    # Format 1: Bitrix standard format with 'event' and 'data'
    if "event" in payload:
        event = payload.get("event", "")
        normalized["event_type"] = event
        
        # Extract data
        data = payload.get("data", {})
        
        # Check if data contains FIELDS
        if "FIELDS" in data:
            fields = data["FIELDS"]
        else:
            fields = data
        
        # Extract entity ID
        entity_id = fields.get("ID") or fields.get("id") or data.get("ID") or data.get("id")
        if entity_id:
            try:
                normalized["entity_id"] = int(entity_id)
            except (ValueError, TypeError):
                pass
        
        # Determine entity type from event
        event_lower = event.lower()
        if "deal" in event_lower or "crm.deal" in event_lower:
            normalized["entity_type"] = "deal"
        elif "contact" in event_lower or "crm.contact" in event_lower:
            normalized["entity_type"] = "contact"
        elif "lead" in event_lower or "crm.lead" in event_lower:
            normalized["entity_type"] = "lead"
        elif "invoice" in event_lower:
            normalized["entity_type"] = "invoice"
        
        # Extract comprehensive deal data
        if normalized["entity_type"] == "deal":
            deal_data = {
                "ID": fields.get("ID") or fields.get("id"),
                "STAGE_ID": fields.get("STAGE_ID") or fields.get("stage_id"),
                "OLD_STAGE_ID": fields.get("OLD_STAGE_ID") or fields.get("old_stage_id") or data.get("OLD_STAGE_ID"),
                "CATEGORY_ID": fields.get("CATEGORY_ID") or fields.get("category_id"),
                "OPPORTUNITY": fields.get("OPPORTUNITY") or fields.get("opportunity"),
                "CONTACT_ID": fields.get("CONTACT_ID") or fields.get("contact_id"),
                "TITLE": fields.get("TITLE") or fields.get("title"),
                "CURRENCY_ID": fields.get("CURRENCY_ID") or fields.get("currency_id"),
                "COMMENTS": fields.get("COMMENTS") or fields.get("comments"),
            }
            # Include all other fields
            for key, value in fields.items():
                if key not in deal_data:
                    deal_data[key] = value
            normalized["data"] = deal_data
        else:
            normalized["data"] = fields if "FIELDS" in data else data
    
    # Format 2: Custom format with explicit fields
    elif "event_type" in payload or "entity_type" in payload:
        normalized["event_type"] = payload.get("event_type", "unknown")
        normalized["entity_type"] = payload.get("entity_type", "unknown")
        entity_id = payload.get("entity_id")
        if entity_id:
            try:
                normalized["entity_id"] = int(entity_id)
            except (ValueError, TypeError):
                pass
        normalized["data"] = payload.get("data", payload)
    
    # Format 3: Direct entity object (e.g., deal object with ID, STAGE_ID)
    elif "ID" in payload or "id" in payload:
        entity_id = payload.get("ID") or payload.get("id")
        try:
            normalized["entity_id"] = int(entity_id)
        except (ValueError, TypeError):
            pass
        
        # Try to infer entity type from fields
        if "STAGE_ID" in payload or "stage_id" in payload:
            normalized["entity_type"] = "deal"
            normalized["event_type"] = "deal_updated"
        elif "STATUS_ID" in payload or "status_id" in payload:
            if "PHONE" in payload or "EMAIL" in payload:
                normalized["entity_type"] = "contact"
                normalized["event_type"] = "contact_updated"
            else:
                normalized["entity_type"] = "lead"
                normalized["event_type"] = "lead_updated"
        
        # Extract comprehensive data
        normalized["data"] = payload.copy()
        
        # For deals, extract old/new stage if available
        if normalized["entity_type"] == "deal":
            normalized["data"]["OLD_STAGE_ID"] = payload.get("OLD_STAGE_ID") or payload.get("old_stage_id")
    
    else:
        # Unknown format, try to extract what we can
        logger.warning(f"Unknown webhook format, attempting to parse: {list(payload.keys())}")
        normalized["data"] = payload
    
    return normalized


@router.post('/bitrix/webhook', tags=["Bitrix Webhook"])
async def bitrix_webhook(
    request: Request,
    token: Optional[str] = Query(None, description="Bitrix webhook token for authentication")
):
    """
    Receive outgoing webhooks from Bitrix24 for event notifications
    Publishes webhook events to Redis Streams for async processing
    
    Authentication: Currently disabled for easier testing.
    To enable: Set BITRIX_WEBHOOK_TOKEN environment variable and uncomment verification code.
    
    Handles events:
    - deal updated (ONCRMDEALUPDATE)
    - contact updated  
    - lead updated
    - invoice generated
    
    Supports multiple Bitrix webhook formats and extracts comprehensive deal data.
    """
    try:
        logger.info("=== WEBHOOK ENDPOINT CALLED - STARTING PROCESSING ===")
        # Verify Bitrix webhook token
        token_valid = verify_bitrix_webhook_token(request, token)
        logger.info(f"=== Token verification result: {token_valid} (should be True) ===")
        
        # Get the raw request body
        body = await request.body()
        
        # Parse JSON payload
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            logger.warning("Invalid JSON payload in Bitrix webhook")
            raise HTTPException(status_code=400, detail="Invalid JSON payload")
        
        # Token verification disabled - accepting all requests
        logger.info("Token verification is disabled - accepting webhook request")
        
        logger.debug("Bitrix webhook received (token verification disabled)")
        
        # Parse and normalize webhook payload
        normalized = parse_bitrix_webhook(payload)
        
        event_type = normalized.get("event_type", "unknown")
        entity_type = normalized.get("entity_type", "unknown")
        entity_id = normalized.get("entity_id")
        data = normalized.get("data", {})
        
        if not entity_id:
            logger.warning("Missing entity_id in webhook payload after parsing")
            raise HTTPException(status_code=400, detail="Missing entity_id")
        
        logger.info(
            f"Bitrix webhook received: {event_type} for {entity_type} {entity_id}"
        )
        logger.debug(f"Webhook payload: {json.dumps(payload, indent=2)}")
        logger.debug(f"Normalized webhook: {json.dumps(normalized, indent=2, default=str)}")
        
        # Filter: Only process deals in MaaS funnel
        if entity_type == "deal":
            category_id = data.get("CATEGORY_ID") or data.get("category_id")
            if category_id:
                try:
                    category_id = int(category_id)
                    # Check if deal belongs to MaaS funnel
                    from backend.bitrix.funnel_manager import funnel_manager
                    maas_category_id = funnel_manager.get_category_id()
                    
                    if maas_category_id and category_id != maas_category_id:
                        logger.info(
                            f"Skipping webhook for deal {entity_id}: "
                            f"Category {category_id} is not MaaS funnel (category {maas_category_id})"
                        )
                        # Return 200 to acknowledge webhook, but don't process it
                        return Response(status_code=200, content="Webhook received but not processed (not in MaaS funnel)")
                except (ValueError, TypeError):
                    logger.warning(f"Invalid CATEGORY_ID in webhook: {category_id}")
            else:
                # If no category_id in webhook, we'll check it in the worker
                logger.debug(f"Deal {entity_id} webhook has no CATEGORY_ID, will check in worker")
        
        # Publish webhook event to Redis Stream with comprehensive data
        message_id = await bitrix_queue_service.publish_webhook_event(
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            data=data
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


@router.post('/bitrix/webhook/test', tags=["Bitrix Webhook"])
async def bitrix_webhook_test(request: Request):
    """
    Test endpoint for Bitrix webhooks - logs all request details without authentication.
    Use this to understand what format Bitrix is actually sending.
    
    This endpoint accepts ANY POST request and logs:
    - All headers
    - All query parameters
    - Raw request body
    - Parsed JSON body (if applicable)
    - URL details
    - Client IP
    """
    try:
        # Get all request details
        client_ip = request.client.host if request.client else "unknown"
        url = str(request.url)
        method = request.method
        path = request.url.path
        query_params = dict(request.query_params)
        
        # Get all headers
        headers = dict(request.headers)
        
        # Get raw body
        body_bytes = await request.body()
        body_raw = body_bytes.decode('utf-8', errors='replace')
        
        # Try to parse as JSON
        body_json = None
        try:
            if body_raw:
                body_json = json.loads(body_raw)
        except (json.JSONDecodeError, ValueError):
            pass
        
        # Log everything
        logger.info("=" * 80)
        logger.info("BITRIX WEBHOOK TEST ENDPOINT - FULL REQUEST DETAILS")
        logger.info("=" * 80)
        logger.info(f"Method: {method}")
        logger.info(f"URL: {url}")
        logger.info(f"Path: {path}")
        logger.info(f"Client IP: {client_ip}")
        logger.info(f"Query Parameters: {json.dumps(query_params, indent=2)}")
        logger.info(f"Headers: {json.dumps(headers, indent=2)}")
        logger.info(f"Raw Body (length: {len(body_bytes)} bytes):")
        logger.info(body_raw[:2000] if len(body_raw) > 2000 else body_raw)
        if body_json:
            logger.info(f"Parsed JSON Body:")
            logger.info(json.dumps(body_json, indent=2, default=str))
        else:
            logger.info("Body is not valid JSON or is empty")
        logger.info("=" * 80)
        
        # Also print to console for immediate visibility
        print("\n" + "=" * 80)
        print("BITRIX WEBHOOK TEST ENDPOINT - FULL REQUEST DETAILS")
        print("=" * 80)
        print(f"Method: {method}")
        print(f"URL: {url}")
        print(f"Path: {path}")
        print(f"Client IP: {client_ip}")
        print(f"Query Parameters: {json.dumps(query_params, indent=2)}")
        print(f"Headers: {json.dumps(headers, indent=2)}")
        print(f"Raw Body (length: {len(body_bytes)} bytes):")
        print(body_raw[:2000] if len(body_raw) > 2000 else body_raw)
        if body_json:
            print(f"Parsed JSON Body:")
            print(json.dumps(body_json, indent=2, default=str))
        else:
            print("Body is not valid JSON or is empty")
        print("=" * 80 + "\n")
        
        # Return success response
        return {
            "status": "received",
            "message": "Webhook test endpoint received request - check logs for full details",
            "summary": {
                "method": method,
                "path": path,
                "client_ip": client_ip,
                "query_params": query_params,
                "body_length": len(body_bytes),
                "body_is_json": body_json is not None,
                "headers_count": len(headers)
            },
            "query_params": query_params,
            "body_preview": body_raw[:500] if body_raw else None,
            "body_json": body_json
        }
        
    except Exception as e:
        logger.error(f"Error in webhook test endpoint: {e}", exc_info=True)
        return {
            "status": "error",
            "message": str(e),
            "error_type": type(e).__name__
        }


@router.options('/bitrix/webhook/test', tags=["Bitrix Webhook"])
async def bitrix_webhook_test_options():
    """Handle CORS preflight requests for webhook test endpoint"""
    return Response(status_code=200)

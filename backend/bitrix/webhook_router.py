"""
Bitrix webhook router
Handles incoming webhooks from Bitrix24 for event notifications
"""
from fastapi import APIRouter, Request, Response, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from backend.core.dependencies import get_db
from backend.utils.logging import get_logger
import json
from typing import Dict, Any

logger = get_logger(__name__)
router = APIRouter()


@router.post('/bitrix/webhook', tags=["Bitrix Webhook"])
async def bitrix_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Receive outgoing webhooks from Bitrix24 for event notifications
    
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
        
        # Log the webhook event
        event_type = payload.get('event_type', 'unknown')
        entity_type = payload.get('entity_type', 'unknown')
        entity_id = payload.get('entity_id', 'unknown')
        
        logger.info(f"Bitrix webhook received: {event_type} for {entity_type} {entity_id}")
        logger.debug(f"Webhook payload: {json.dumps(payload, indent=2)}")
        
        # Handle different event types
        if event_type == 'deal_updated':
            await handle_deal_updated(payload, db)
        elif event_type == 'contact_updated':
            await handle_contact_updated(payload, db)
        elif event_type == 'lead_updated':
            await handle_lead_updated(payload, db)
        elif event_type == 'invoice_generated':
            await handle_invoice_generated(payload, db)
        else:
            logger.warning(f"Unknown webhook event type: {event_type}")
        
        return Response(status_code=200, content="Webhook processed successfully")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing Bitrix webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


async def handle_deal_updated(payload: Dict[str, Any], db: AsyncSession):
    """Handle deal updated webhook"""
    deal_id = payload.get('entity_id')
    deal_data = payload.get('data', {})
    
    logger.info(f"Processing deal update for deal_id: {deal_id}")
    logger.debug(f"Deal data: {deal_data}")
    
    # TODO: Update local order with deal changes
    # - Update order status based on deal stage
    # - Update deal fields if needed
    # - Log changes for audit trail


async def handle_contact_updated(payload: Dict[str, Any], db: AsyncSession):
    """Handle contact updated webhook"""
    contact_id = payload.get('entity_id')
    contact_data = payload.get('data', {})
    
    logger.info(f"Processing contact update for contact_id: {contact_id}")
    logger.debug(f"Contact data: {contact_data}")
    
    # TODO: Update local user with contact changes
    # - Update user profile information
    # - Sync contact fields
    # - Log changes for audit trail


async def handle_lead_updated(payload: Dict[str, Any], db: AsyncSession):
    """Handle lead updated webhook"""
    lead_id = payload.get('entity_id')
    lead_data = payload.get('data', {})
    
    logger.info(f"Processing lead update for lead_id: {lead_id}")
    logger.debug(f"Lead data: {lead_data}")
    
    # TODO: Update local call request with lead changes
    # - Update call request status based on lead stage
    # - Update lead fields if needed
    # - Log changes for audit trail


async def handle_invoice_generated(payload: Dict[str, Any], db: AsyncSession):
    """Handle invoice generated webhook"""
    invoice_id = payload.get('entity_id')
    invoice_data = payload.get('data', {})
    order_id = payload.get('order_id')  # Our internal order ID
    
    logger.info(f"Processing invoice generation for invoice_id: {invoice_id}, order_id: {order_id}")
    logger.debug(f"Invoice data: {invoice_data}")
    
    # TODO: Download and store invoice file
    # - Get invoice file URL from Bitrix
    # - Download invoice file
    # - Store in local file system
    # - Update order with invoice file path
    # - Log changes for audit trail


@router.options('/bitrix/webhook', tags=["Bitrix Webhook"])
async def bitrix_webhook_options():
    """Handle CORS preflight requests for Bitrix webhook"""
    return Response(status_code=200)

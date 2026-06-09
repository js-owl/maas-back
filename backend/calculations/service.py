"""
Calculations service module
Calculator service integration with proper error handling
"""
import os
import httpx
import json
import logging
import time
from typing import Optional, List, Dict, Any
from fastapi import HTTPException
from backend.core.config import CALCULATOR_BASE_URL
from backend.utils.logging import get_logger

logger = get_logger(__name__)


async def call_calculator_service(
    service_id: str,
    material_id: str,
    material_form: str,
    quantity: int,
    length: Optional[int] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
    tolerance_id: str = "1",
    finish_id: str = "1",
    cover_id: List[str] = ["1"],
    is_need_special_equipment: Optional[bool] = None,
    electroplating_family: Optional[str] = None, # add for electroplating_auto service
    electroplating_process_id: Optional[str] = None, # add for electroplating_auto service
    coating_thickness_microns: Optional[float] = None, # add for electroplating_auto service
    processing_depth_microns: Optional[float] = None, # add for electroplating_auto service
    k_otk: str = "1.0",
    k_cert: List[str] = None,
    timeout: float = 15.0,
    forward_headers: Optional[dict] = None,
    file_data: Optional[str] = None,
    file_name: Optional[str] = None,
    file_type: Optional[str] = None,
    location: Optional[str] = None,
    document_ids: Optional[str] = None
) -> dict:
    """Universal function to call the external calculator service using unified /calculate-price endpoint"""
    
    service_url = f"{CALCULATOR_BASE_URL}/calculate-price"
    
    if not CALCULATOR_BASE_URL:
        logger.warning("Calculator service URL not configured, skipping calculator call")
        return {}
    
    # Set default certification types
    if k_cert is None:
        k_cert = ["a", "f"]
    
    try:
        # Build unified payload structure matching 7000 server v3.1.0 API
        post_data = {
            "service_id": service_id,  # Pass as-is from frontend
            "material_id": material_id,
            "material_form": material_form,
            "quantity": quantity,
            "tolerance_id": tolerance_id,
            "finish_id": finish_id,
            "cover_id": cover_id,
            "k_otk": k_otk,
            "k_cert": k_cert,
            "location": location
        }
        
        # Add dimensions only if provided (not None)
        if length is not None or width is not None or (height is not None):
            post_data["dimensions"] = {
                "length": length,
                "width": width,
                "height": height
            }
        
        # Add file data if provided
        if file_data and file_name and file_type:
            post_data.update({
                "file_data": file_data,
                "file_name": file_name,
                "file_type": file_type
            })
        
        if document_ids:
            post_data.update({
                "document_ids": document_ids
            })
        
        # Add if provided
        if is_need_special_equipment:
            post_data.update({
                "is_need_special_equipment": int(is_need_special_equipment)
            })
        
        # add for electroplating_auto service
        if electroplating_family:
            post_data.update({
                "electroplating_family": electroplating_family
            })
        if electroplating_process_id:
            post_data.update({
                "electroplating_process_id": electroplating_process_id
            })
        if coating_thickness_microns:
            post_data.update({
                "coating_thickness_microns": coating_thickness_microns
            })
        if processing_depth_microns:
            post_data.update({
                "processing_depth_microns": processing_depth_microns
            })

        # Log outgoing request payload to calculator
        # logger.info(f"=======================Calculator request payload: {post_data}")
        # filtered_request = {k: v for k, v in post_data.items() if k != "file_data"}
        # logger.info(f"============================= Request: поля: {list(post_data.keys())}, Request data without file_data {filtered_request}")
        # Prepare headers for calculator service call
        headers = {"Content-Type": "application/json"}
        
        # Forward relevant headers from original request if provided
        if forward_headers:
            # Forward X-Forwarded-* headers for proper proxy behavior
            forwarded_headers = [
                "X-Forwarded-For",
                "X-Forwarded-Proto", 
                "X-Forwarded-Host",
                "X-Forwarded-Port",
                "X-Real-IP",
                "X-Original-IP",
                "User-Agent",
                "Accept",
                "Accept-Language",
                "Accept-Encoding"
            ]
            
            for header_name in forwarded_headers:
                if header_name in forward_headers:
                    headers[header_name] = forward_headers[header_name]
                    logger.debug(f"Forwarding header {header_name}: {forward_headers[header_name]}")
        
        # Call external calculator service with proper error handling
        async with httpx.AsyncClient() as client:
            resp = await client.post(service_url, json=post_data, headers=headers, timeout=timeout)
            
            # Log raw response prior to validation/parsing
            try:
                logger.info(f"Calculator raw response status={resp.status_code} body={resp.text}")
            except Exception:
                pass
            
            # IMPORTANT: Preserve HTTP status codes from calculator service
            # Don't use resp.raise_for_status() as it converts all 4xx/5xx to exceptions
            if resp.status_code >= 400:
                # Preserve original status code (especially 422 validation errors)
                try:
                    error_detail = resp.json() if resp.text else str(resp.status_code)
                except:
                    error_detail = resp.text or f"HTTP {resp.status_code}"
                
                raise HTTPException(
                    status_code=resp.status_code,
                    detail=error_detail
                )
            
            calc_res = resp.json()
            
            # 7000 server v3.1.0 now returns ResponseWrapper format
            if isinstance(calc_res, dict) and "data" in calc_res:
                # Extract data from ResponseWrapper format
                calc_res = calc_res["data"]
            elif not isinstance(calc_res, dict):
                try:
                    calc_res = json.loads(resp.text)
                    if isinstance(calc_res, dict) and "data" in calc_res:
                        calc_res = calc_res["data"]
                except Exception:
                    calc_res = {}
            
            logger.info(f"Calculator service response: {calc_res}")
            return calc_res
        
    except HTTPException:
        # Re-raise HTTPExceptions (preserves status codes)
        raise
    except httpx.RequestError as e:
        # Only network/connection errors become 502
        error_msg = f"Network error during calculator service call to {service_url}: {str(e)}"
        logger.error(error_msg)
        logger.error(f"Calculator service URL: {CALCULATOR_BASE_URL}")
        raise HTTPException(
            status_code=502, 
            detail=f"Calculator service unavailable at {CALCULATOR_BASE_URL}. Please ensure the calculator service is running."
        )
    except Exception as e:
        # Other errors become 500
        logger.error(f"Unexpected error during calculator service call: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

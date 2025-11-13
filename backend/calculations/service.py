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
    length: Optional[int],
    width: Optional[int],
    height: Optional[int],
    n_dimensions: int,
    dia: Optional[int] = None,
    tolerance_id: str = "1",
    finish_id: str = "1",
    cover_id: List[str] = ["1"],
    k_otk: str = "1",
    k_cert: List[str] = None,
    k_complexity: float = 1.0,
    timeout: float = 15.0,
    forward_headers: Optional[dict] = None,
    file_data: Optional[str] = None,
    file_name: Optional[str] = None,
    file_type: Optional[str] = None
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
            "n_dimensions": n_dimensions,
            "k_complexity": k_complexity
        }
        
        # Add dimensions only if provided (not None)
        if length is not None or width is not None or (height is not None or dia is not None):
            post_data["dimensions"] = {
                "length": length,
                "width": width,
                "thickness": height or dia  # Use height for milling, dia for lathe
            }
        
        # Add file data if provided
        if file_data and file_name and file_type:
            post_data.update({
                "file_data": file_data,
                "file_name": file_name,
                "file_type": file_type
            })
        
        # Log outgoing request payload to calculator
        logger.info(f"Calculator request payload: {post_data}")
        
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


async def analyze_stp_file(file_path: str, filename: str) -> Dict[str, Any]:
    """Analyze STP file to extract geometric features"""
    try:
        analysis_url = f"{CALCULATOR_BASE_URL}/analyze_base_stp_file/"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Upload file for analysis
            with open(file_path, "rb") as f:
                files = {"file": (filename, f, "application/octet-stream")}
                analysis_response = await client.post(analysis_url, files=files)
            
            if analysis_response.status_code != 200:
                logger.warning(f"STP analysis failed: {analysis_response.status_code} - {analysis_response.text}")
                return {}
            
            analysis_data = analysis_response.json()
            logger.info(f"STP analysis successful: {len(analysis_data)} geometric features")
            
            # Ensure analysis_data is a dict (not a list)
            if isinstance(analysis_data, list):
                analysis_data = analysis_data[0] if analysis_data else {}
            
            # Helper function to convert dict_values to lists for JSON serialization
            def convert_dict_values(obj):
                if isinstance(obj, dict):
                    return {k: convert_dict_values(v) for k, v in obj.items()}
                elif isinstance(obj, (list, tuple)):
                    return [convert_dict_values(item) for item in obj]
                else:
                    if type(obj).__name__ == 'dict_values':
                        return list(obj)
                    return obj
            
            return convert_dict_values(analysis_data)
            
    except Exception as e:
        logger.warning(f"File analysis failed: {e}")
        return {}

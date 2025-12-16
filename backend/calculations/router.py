"""
Calculations router
Handles calculate-price endpoint and proxy endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Header, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
import json
import base64
import os
import time
from backend import models, schemas
from backend.core.dependencies import get_db
from backend.auth.service import decode_access_token
from backend.calculations.service import call_calculator_service, analyze_stp_file
from backend.calculations.proxy import get_services, get_materials, get_coefficients, get_locations
from backend.utils.logging import get_logger
from sqlalchemy import select

logger = get_logger(__name__)
router = APIRouter()


# CORS preflight handlers
@router.options('/calculate-price', tags=["Calculation"])
async def calculate_price_options():
    """Handle CORS preflight requests for calculate-price"""
    return Response(status_code=200)

@router.options('/services', tags=["Calculation"])
async def services_options():
    """Handle CORS preflight requests for services"""
    return Response(status_code=200)

@router.options('/materials', tags=["Calculation"])
async def materials_options():
    """Handle CORS preflight requests for materials"""
    return Response(status_code=200)

@router.options('/coefficients', tags=["Calculation"])
async def coefficients_options():
    """Handle CORS preflight requests for coefficients"""
    return Response(status_code=200)

@router.options('/locations', tags=["Calculation"])
async def locations_options():
    """Handle CORS preflight requests for locations"""
    return Response(status_code=200)

@router.post('/calculate-price', tags=["Calculation"])
async def calculate_price(
    request_data: schemas.CalculationRequest,
    # authorization: Optional[str] = Header(None),  # Commented out - no auth required
    request: Request = None,
    db: AsyncSession = Depends(get_db)
):
    """Calculate price without creating an order or requiring auth.
    Supports both manual dimensions and automatic file analysis.
    
    Parameters:
    - service_id: Manufacturing service type (e.g., "cnc-milling", "cnc-lathe", "printing", "painting")
    - file_id: Optional file ID for automatic analysis (STP/STEP files supported)
    - length/width/height/thickness/dia: Manual dimensions (used if file_id not provided)
    - cover_id: Array of strings for multiple cover types (e.g., ["1", "2"])
    """
    # Log the service ID being used
    logger.info(f"Using service_id: {request_data.service_id}")
    
    # Log document_ids if provided (for debugging)
    if request_data.document_ids:
        logger.info(f"Document IDs provided: {request_data.document_ids}")
    
    # Validate service_id against available services
    try:
        valid_services = await get_services()
        if isinstance(valid_services, list) and request_data.service_id not in valid_services:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid service_id. Must be one of: {', '.join(valid_services)}"
            )
    except HTTPException:
        # Re-raise HTTPExceptions (validation errors)
        raise
    except Exception as e:
        logger.warning(f"Service validation failed: {e}")
        # Continue without validation if services endpoint is unavailable
    
    # Process cover_id list
    processed_cover_id = []
    if request_data.cover_id:
        for item in request_data.cover_id:
            if item.strip():  # Skip empty strings
                if "," in item:
                    # Split comma-separated string and add individual items
                    processed_cover_id.extend([i.strip() for i in item.split(",") if i.strip()])
                else:
                    processed_cover_id.append(item.strip())
    
    cover_id_for_calculator = processed_cover_id
    
    # Handle file input - either file_id (database) or file_data (base64)
    file_data = None
    file_name = None
    file_type = None
    
    if isinstance(request_data.file_id, int):
        # Handle file_id case (existing file in database)
        from backend.files.repository import get_file_by_id
        file_rec = await get_file_by_id(db, request_data.file_id)
        if not file_rec:
            raise HTTPException(status_code=404, detail="File not found")

        # Authentication logic commented out - no auth required for calculate-price
        # is_authenticated = False
        # user_obj: Optional[models.User] = None
        # if isinstance(authorization, str) and authorization:
        #     try:
        #         token = authorization.split(" ", 1)[1] if authorization.lower().startswith("bearer ") else authorization
        #         payload = decode_access_token(token)
        #         if payload and "sub" in payload:
        #             username = payload["sub"]
        #             result = await db.execute(select(models.User).where(models.User.username == username))
        #             user_obj = result.scalar_one_or_none()
        #             is_authenticated = user_obj is not None
        #     except Exception:
        #         is_authenticated = False

        # File access control commented out - all files accessible for calculation
        # is_demo_allowed = bool(getattr(file_rec, 'is_demo', False)) or (file_rec.id in (1, 2, 3, 4, 5))
        # if not is_demo_allowed:
        #     if not is_authenticated:
        #         raise HTTPException(status_code=403, detail="Only demo files allowed for anonymous calculation")
        #     if not (user_obj.is_admin or file_rec.uploaded_by == user_obj.id):
        #         raise HTTPException(status_code=403, detail="File not owned by user")
        
        # Get file data as base64
        from backend.files.service import get_file_data_as_base64
        file_data = await get_file_data_as_base64(file_rec)
        file_name = file_rec.original_filename or file_rec.filename
        # Set correct file type for calculator service
        if file_name and file_name.lower().endswith('.stl'):
            file_type = "stl"
        elif file_name and file_name.lower().endswith(('.stp', '.step')):
            file_type = "stp"
        else:
            file_type = file_rec.file_type or "application/octet-stream"
        logger.info(f"Using model id={request_data.file_id} filename={file_name}")
    
    # Use default values if not provided (let calculator service handle validation)
    quantity = request_data.quantity or 1
    material_id = request_data.material_id or "alum_D16"
    material_form = request_data.material_form or "rod"
    tolerance_id = request_data.tolerance_id or "1"
    finish_id = request_data.finish_id or "1"
    cover_id = request_data.cover_id or ["1"]
    k_otk = request_data.k_otk or "1"
    k_cert = request_data.k_cert or ["a", "f"]
    n_dimensions = request_data.n_dimensions or 1
    location = request_data.location or "location_1"

    # Process k_cert to list if passed as JSON string
    if isinstance(k_cert, str):
        try:
            k_cert = json.loads(k_cert)
        except Exception:
            k_cert = [k_cert]
    
    # Ensure k_cert is a flat list of strings
    if isinstance(k_cert, list):
        flat_k_cert = []
        for item in k_cert:
            if isinstance(item, str):
                try:
                    # Try to parse if it looks like JSON
                    if item.startswith('[') and item.endswith(']'):
                        parsed = json.loads(item)
                        if isinstance(parsed, list):
                            flat_k_cert.extend(parsed)
                        else:
                            flat_k_cert.append(str(parsed))
                    else:
                        flat_k_cert.append(item)
                except Exception:
                    flat_k_cert.append(item)
            else:
                flat_k_cert.append(str(item))
        k_cert = flat_k_cert

    # Note: File analysis is now handled by the calculator service (port 7000)
    # We only need to send file data as base64 to the calculator service
    
    # Validate material_id against available materials from calculator service
    try:
        materials_response = await get_materials()
        logger.info(f"Materials response: {materials_response}")
        # Extract materials list from response
        if isinstance(materials_response, dict) and "materials" in materials_response:
            available_materials = [mat.get("id") for mat in materials_response["materials"] if isinstance(mat, dict) and "id" in mat]
        else:
            available_materials = []
        
        logger.info(f"Available materials: {available_materials}")
        logger.info(f"Checking material_id: {material_id}")
        
        if available_materials and material_id not in available_materials:
            logger.warning(f"Invalid material_id: {material_id} not in {available_materials}")
            raise HTTPException(status_code=400, detail=f"Invalid material_id: {material_id}. Available materials: {available_materials}")
        else:
            logger.info(f"Material validation passed for: {material_id}")
    except HTTPException:
        # Re-raise HTTPExceptions (validation failed)
        raise
    except Exception as e:
        logger.warning(f"Could not validate material_id {material_id}: {e}")
        # Continue without validation if materials service is unavailable
    
    # Start timing total backend processing
    total_start_time = time.time()
    
    # Initialize timing variables
    calculation_time = 0.0
    total_calculation_time = 0.0
    
    # Call calculator service using unified function from service
    try:
        # For calculate-price, don't forward headers to avoid issues with authenticated requests
        # The calculator service should work the same regardless of authentication status
        forward_headers = {}
        
        # Start timing calculator service call specifically
        calc_service_start_time = time.time()
        
        calc_res = await call_calculator_service(
            service_id=request_data.service_id,  # Pass service_id directly
            material_id=material_id,
            material_form=material_form,
            quantity=quantity,
            length=request_data.length,
            width=request_data.width,
            height=request_data.height,
            n_dimensions=n_dimensions,
            dia=request_data.dia,
            tolerance_id=tolerance_id,
            finish_id=finish_id,
            cover_id=cover_id_for_calculator,
            k_otk=k_otk,
            k_cert=k_cert,
            timeout=10.0,
            forward_headers=forward_headers,
            file_data=file_data,
            file_name=file_name,
            file_type=file_type,
            location=location
        )
        # End timing calculator service call
        calc_service_end_time = time.time()
        calculation_time = calc_service_end_time - calc_service_start_time
        logger.info("Calculator response OK")
    except HTTPException as e:
        # Re-raise HTTPExceptions (preserves status codes from calculator service)
        raise e
    except Exception as exc:
        logger.error(f"Calculator service error: {exc}")
        raise HTTPException(status_code=502, detail="Calculator service unavailable")
    
    # Map to simple shape aligning with /orders calc usage
    data = calc_res if isinstance(calc_res, dict) else {}
    logger.info(f"Calculator service response data: {data}")
    
    # Determine calculation type (ML-based vs rule-based)
    calculation_type = "unknown"
    logger.info(f"Calculator service fields: ml_based={data.get('ml_based')}, ml_model={data.get('ml_model')}, rule_based={data.get('rule_based')}, calculation_engine={data.get('calculation_engine')}")
    
    if data.get("ml_based") is True or data.get("ml_model") is not None:
        calculation_type = "ml_based"
        logger.info(f"Mapped to ml_based based on ml_based or ml_model")
    elif data.get("rule_based") is True or data.get("ml_based") is False or data.get("calculation_engine") == "rule_based":
        calculation_type = "rule_based"
        logger.info(f"Mapped to rule_based based on rule_based, ml_based=False, or calculation_engine=rule_based")
    elif data.get("calculation_engine") == "ml_model":
        calculation_type = "ml_based"
        logger.info(f"Mapped to ml_based based on calculation_engine=ml_model")
    else:
        logger.info(f"Mapped to unknown - no matching conditions")
    
    # End timing total backend processing
    total_end_time = time.time()
    total_calculation_time = total_end_time - total_start_time
    logger.info(f"Calculation completed in {total_calculation_time:.3f} seconds (service: {calculation_time:.3f} seconds)")
    
    # Prepare response with appropriate dimension field
    response = {
        "service_id": request_data.service_id,
        "quantity": quantity,
        "length": request_data.length,
        "width": request_data.width,
        "n_dimensions": n_dimensions,
        "k_otk": k_otk,  # OTK (quality control) coefficient
        "mat_volume": data.get("mat_volume"),
        "detail_price": data.get("detail_price"),
        "detail_price_one": data.get("detail_price_one"),  # Price per item without scale discounts
        "mat_weight": data.get("mat_weight"),
        "mat_price": data.get("mat_price"),
        "work_price": data.get("work_price"),
        "k_quantity": data.get("k_quantity"),
        "detail_time": data.get("work_time"),
        "total_price": data.get("total_price", 0),
        "total_time": data.get("total_time", 0),
        "manufacturing_cycle": float(data.get("manufacturing_cycle") or 0),  # Optional field from calculator service, default to 0.0 if null
        "suitable_machines": data.get("suitable_machines"),  # Suitable manufacturing machines from calculator service
        "total_price_breakdown": data.get("total_price_breakdown"),  # Suitable manufacturing machines from calculator service
        "calculation_type": calculation_type,  # "ml_based", "rule_based", or "unknown"
        "ml_model": data.get("ml_model"),  # ML model name if available
        "ml_confidence": data.get("ml_confidence"),  # ML confidence score if available
        "calculation_engine": data.get("calculation_engine"),  # Original calculation engine from calculator service
        "calculation_time": calculation_time,  # Calculator service call duration only
        "total_calculation_time": total_calculation_time  # Total backend processing time
    }
    
    # Add dimension fields to response
    if request_data.height is not None:
        response["height"] = request_data.height
    if request_data.thickness is not None:
        response["thickness"] = request_data.thickness
    if request_data.dia is not None:
        response["dia"] = request_data.dia
    
    # File analysis is now handled by the calculator service (port 7000)
    # The calculator service will return analysis results in the response
    
    return response


# Proxy endpoints
@router.get('/services', tags=["Services"])
async def list_services(request: Request):
    """Get available manufacturing services from calculator service (single source of truth)"""
    return await get_services(request)


@router.get('/materials', tags=["Calculator"])
async def get_calculator_materials(
    request: Request,
    process: Optional[str] = None
):
    """Proxy endpoint to get available materials from calculator service"""
    return await get_materials(process, request)


@router.get('/coefficients', tags=["Calculator"])
@router.get('/coefficients/', tags=["Calculator"])
async def get_calculator_coefficients(request: Request):
    """Proxy endpoint to get available coefficients from calculator service"""
    return await get_coefficients(request)


@router.get('/locations', tags=["Calculator"])
async def get_calculator_locations(request: Request):
    """Proxy endpoint to get available locations from calculator service"""
    return await get_locations(request)

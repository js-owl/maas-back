"""
Calculations proxy module
Proxy helper functions for materials, coefficients, locations, services
"""
import httpx
from typing import Dict, Any, List
from fastapi import HTTPException, Request
from backend.core.config import CALCULATOR_BASE_URL
from backend.utils.logging import get_logger

logger = get_logger(__name__)


async def proxy_request(
    endpoint: str,
    method: str = "GET",
    timeout: float = 10.0,
    request: Request = None,
    json_data: dict = None
) -> Dict[str, Any]:
    """Generic proxy function for GET/POST/PUT/DELETE requests to calculator service"""
    if not CALCULATOR_BASE_URL:
        raise HTTPException(status_code=502, detail="Calculator service unavailable")
    
    try:
        url = f"{CALCULATOR_BASE_URL}/{endpoint}"
        
        # Prepare headers - filter out 'host' and 'authorization'
        headers = {}
        if request:
            headers = {
                k: v for k, v in request.headers.items() 
                if k.lower() not in ['host', 'authorization']
            }
        
        async with httpx.AsyncClient() as client:
            method_upper = method.upper()
            
            if method_upper == "GET":
                resp = await client.get(url, timeout=timeout, headers=headers)
            elif method_upper == "POST":
                resp = await client.post(url, timeout=timeout, headers=headers, json=json_data)
            elif method_upper == "PUT":
                resp = await client.put(url, timeout=timeout, headers=headers, json=json_data)
            elif method_upper == "DELETE":
                resp = await client.delete(url, timeout=timeout, headers=headers)
            else:
                raise HTTPException(status_code=405, detail=f"Method {method} not supported")
            
            # Preserve status codes from calculator service
            if resp.status_code >= 400:
                try:
                    error_detail = resp.json() if resp.text else str(resp.status_code)
                except:
                    error_detail = resp.text or f"HTTP {resp.status_code}"
                
                raise HTTPException(
                    status_code=resp.status_code,
                    detail=error_detail
                )
            
            response_data = resp.json()
            
            # 7000 server v3.1.0 now returns ResponseWrapper format
            if isinstance(response_data, dict) and "data" in response_data:
                # Extract data from ResponseWrapper format
                return response_data["data"]
            else:
                return response_data
            
    except HTTPException:
        raise
    except httpx.RequestError as e:
        logger.error(f"Network error calling calculator service {endpoint}: {e}")
        raise HTTPException(status_code=502, detail="Calculator service unavailable")
    except Exception as e:
        logger.error(f"Unexpected error calling calculator service {endpoint}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


async def proxy_get_request(endpoint: str, timeout: float = 10.0, request: Request = None) -> Dict[str, Any]:
    """Convenience wrapper for GET requests"""
    return await proxy_request(endpoint, method="GET", timeout=timeout, request=request)


async def proxy_post_request(
    endpoint: str,
    json_data: dict,
    timeout: float = 10.0,
    request: Request = None
) -> Dict[str, Any]:
    """Convenience wrapper for POST requests"""
    return await proxy_request(endpoint, method="POST", timeout=timeout, request=request, json_data=json_data)


async def proxy_put_request(
    endpoint: str,
    json_data: dict,
    timeout: float = 10.0,
    request: Request = None
) -> Dict[str, Any]:
    """Convenience wrapper for PUT requests"""
    return await proxy_request(endpoint, method="PUT", timeout=timeout, request=request, json_data=json_data)


async def proxy_delete_request(
    endpoint: str,
    timeout: float = 10.0,
    request: Request = None
) -> Dict[str, Any]:
    """Convenience wrapper for DELETE requests"""
    return await proxy_request(endpoint, method="DELETE", timeout=timeout, request=request)


async def get_services(request: Request = None) -> List[str]:
    """Get available manufacturing services from calculator service"""
    response = await proxy_get_request("services", request=request)
    # 7000 server v3.1.0 returns {"services": ["printing", "cnc-milling", "cnc-lathe", "painting"]}
    if isinstance(response, dict) and "services" in response:
        return response["services"]
    return response


async def get_materials(process: str = None, request: Request = None) -> Dict[str, List[Dict[str, Any]]]:
    """Get available materials from calculator service"""
    endpoint = "materials"
    if process:
        endpoint += f"?process={process}"
    response = await proxy_get_request(endpoint, request=request)
    # 7000 server v3.1.0 returns {"materials": [...]}
    if isinstance(response, dict) and "materials" in response:
        return {"materials": response["materials"]}
    return response


async def get_coefficients(request: Request = None) -> Dict[str, List[Dict[str, Any]]]:
    """Get available coefficients from calculator service"""
    response = await proxy_get_request("coefficients", request=request)
    # 7000 server v3.1.0 returns {"tolerance": [...], "finish": [...], "cover": [...]}
    if isinstance(response, dict) and any(key in response for key in ["tolerance", "finish", "cover"]):
        return response
    return response


async def get_locations(request: Request = None) -> Dict[str, List[Dict[str, Any]]]:
    """Get available locations from calculator service"""
    response = await proxy_get_request("locations", request=request)
    # 7000 server v3.1.0 returns {"locations": [...]}
    if isinstance(response, dict) and "locations" in response:
        return {"locations": response["locations"]}
    return response

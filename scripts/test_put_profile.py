#!/usr/bin/env python3
"""
Test script to verify PUT /api/v3/profile requests work correctly
after nginx configuration update.

Usage:
    python scripts/test_put_profile.py [--base-url BASE_URL] [--token TOKEN]
"""

import argparse
import sys
import json
import requests
from typing import Optional, Dict, Any


def test_options_preflight(base_url: str) -> Dict[str, Any]:
    """Test OPTIONS preflight request for CORS"""
    print("Testing OPTIONS preflight request...")
    
    url = f"{base_url}/api/v3/profile"
    headers = {
        "Origin": base_url,
        "Access-Control-Request-Method": "PUT",
        "Access-Control-Request-Headers": "Authorization,Content-Type"
    }
    
    try:
        response = requests.options(url, headers=headers, timeout=10)
        result = {
            "status_code": response.status_code,
            "success": response.status_code in [200, 204],
            "headers": dict(response.headers),
            "cors_headers": {
                "access-control-allow-origin": response.headers.get("Access-Control-Allow-Origin"),
                "access-control-allow-methods": response.headers.get("Access-Control-Allow-Methods"),
                "access-control-allow-headers": response.headers.get("Access-Control-Allow-Headers"),
            }
        }
        
        if result["success"]:
            print(f"✅ OPTIONS preflight: {response.status_code}")
        else:
            print(f"❌ OPTIONS preflight: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
        
        return result
    except Exception as e:
        print(f"❌ OPTIONS preflight failed: {e}")
        return {"error": str(e), "success": False}


def test_debug_endpoint(base_url: str, token: Optional[str] = None) -> Dict[str, Any]:
    """Test diagnostic endpoint to verify requests reach FastAPI"""
    print("\nTesting diagnostic endpoint (PUT /api/v3/debug/request)...")
    
    url = f"{base_url}/api/v3/debug/request"
    headers = {
        "Content-Type": "application/json"
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    data = {"test": "data", "method": "PUT"}
    
    try:
        response = requests.put(url, headers=headers, json=data, timeout=10)
        result = {
            "status_code": response.status_code,
            "success": response.status_code == 200,
            "reached_fastapi": response.status_code == 200,
            "response": response.json() if response.status_code == 200 else response.text[:500]
        }
        
        if result["success"]:
            print(f"✅ Diagnostic endpoint: Request reached FastAPI")
            print(f"   Status: {response.status_code}")
            if isinstance(result["response"], dict):
                proxy_info = result["response"].get("proxy_detection", {})
                print(f"   Behind proxy: {proxy_info.get('behind_proxy', 'N/A')}")
                print(f"   Forwarded-Proto: {proxy_info.get('forwarded_proto', 'N/A')}")
        else:
            print(f"❌ Diagnostic endpoint: {response.status_code}")
            print(f"   Response: {result['response']}")
            if response.status_code == 403:
                print("   ⚠️  403 Forbidden - Request blocked by nginx before reaching FastAPI")
        
        return result
    except Exception as e:
        print(f"❌ Diagnostic endpoint failed: {e}")
        return {"error": str(e), "success": False, "reached_fastapi": False}


def test_put_profile(base_url: str, token: str) -> Dict[str, Any]:
    """Test PUT /api/v3/profile endpoint"""
    print("\nTesting PUT /api/v3/profile...")
    
    if not token:
        print("⚠️  No token provided, skipping authenticated test")
        return {"skipped": True, "reason": "No token"}
    
    url = f"{base_url}/api/v3/profile"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Test data - minimal update
    data = {
        "full_name": "Test User"
    }
    
    try:
        response = requests.put(url, headers=headers, json=data, timeout=10)
        result = {
            "status_code": response.status_code,
            "success": response.status_code == 200,
            "response": response.json() if response.status_code == 200 else response.text[:500]
        }
        
        if result["success"]:
            print(f"✅ PUT /profile: Success ({response.status_code})")
        elif response.status_code == 403:
            print(f"❌ PUT /profile: 403 Forbidden")
            print(f"   ⚠️  Request blocked by nginx - check nginx configuration")
            print(f"   Response: {result['response']}")
        elif response.status_code == 401:
            print(f"⚠️  PUT /profile: 401 Unauthorized")
            print(f"   Request reached FastAPI but authentication failed")
            print(f"   This is expected if token is invalid/expired")
        else:
            print(f"❌ PUT /profile: {response.status_code}")
            print(f"   Response: {result['response']}")
        
        return result
    except Exception as e:
        print(f"❌ PUT /profile failed: {e}")
        return {"error": str(e), "success": False}


def main():
    parser = argparse.ArgumentParser(description="Test PUT /api/v3/profile endpoint")
    parser.add_argument(
        "--base-url",
        default="https://maas.aeromax-group.ru",
        help="Base URL of the API (default: https://maas.aeromax-group.ru)"
    )
    parser.add_argument(
        "--token",
        help="JWT token for authenticated requests (optional)"
    )
    parser.add_argument(
        "--skip-options",
        action="store_true",
        help="Skip OPTIONS preflight test"
    )
    parser.add_argument(
        "--skip-debug",
        action="store_true",
        help="Skip diagnostic endpoint test"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("PUT /api/v3/profile Test Script")
    print("=" * 60)
    print(f"Base URL: {args.base_url}")
    print(f"Token: {'Provided' if args.token else 'Not provided'}")
    print("=" * 60)
    
    results = {}
    
    # Test OPTIONS preflight
    if not args.skip_options:
        results["options"] = test_options_preflight(args.base_url)
    
    # Test diagnostic endpoint
    if not args.skip_debug:
        results["debug"] = test_debug_endpoint(args.base_url, args.token)
    
    # Test PUT profile
    results["put_profile"] = test_put_profile(args.base_url, args.token)
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    if "options" in results:
        opt_result = results["options"]
        status = "✅ PASS" if opt_result.get("success") else "❌ FAIL"
        print(f"OPTIONS preflight: {status}")
    
    if "debug" in results:
        debug_result = results["debug"]
        if debug_result.get("reached_fastapi"):
            print("Diagnostic endpoint: ✅ PASS (Request reached FastAPI)")
        elif debug_result.get("status_code") == 403:
            print("Diagnostic endpoint: ❌ FAIL (403 - Blocked by nginx)")
        else:
            print(f"Diagnostic endpoint: {'✅ PASS' if debug_result.get('success') else '❌ FAIL'}")
    
    put_result = results["put_profile"]
    if put_result.get("skipped"):
        print("PUT /profile: ⚠️  SKIPPED (No token provided)")
    elif put_result.get("status_code") == 403:
        print("PUT /profile: ❌ FAIL (403 - Blocked by nginx)")
        print("\n⚠️  ACTION REQUIRED:")
        print("   The 403 error indicates nginx is blocking PUT requests.")
        print("   See docs/nginx-configuration-requirements.md for fix instructions.")
    elif put_result.get("success"):
        print("PUT /profile: ✅ PASS")
    else:
        print(f"PUT /profile: {'✅ PASS' if put_result.get('success') else '❌ FAIL'}")
    
    print("=" * 60)
    
    # Exit code
    all_passed = all(
        r.get("success", False) or r.get("skipped", False)
        for r in results.values()
    )
    
    if not all_passed:
        sys.exit(1)


if __name__ == "__main__":
    main()



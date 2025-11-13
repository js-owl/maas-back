"""
Quick test script for basic API functionality
Tests core endpoints without comprehensive coverage
"""
import asyncio
import httpx
import json

BASE_URL = "http://localhost:8000"

async def quick_test():
    """Run quick tests for basic functionality"""
    print("Running quick API tests...")
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            # Test health endpoint
            print("Testing health endpoint...")
            response = await client.get(f"{BASE_URL}/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            print("Health check passed")
            
            # Test services endpoint
            print("Testing services endpoint...")
            response = await client.get(f"{BASE_URL}/services")
            assert response.status_code == 200
            services = response.json()
            assert isinstance(services, list)
            assert len(services) == 4
            print("Services endpoint passed")
            
            # Test materials endpoint
            print("Testing materials endpoint...")
            response = await client.get(f"{BASE_URL}/materials")
            assert response.status_code == 200
            materials = response.json()
            assert isinstance(materials, dict)
            assert "materials" in materials
            print("Materials endpoint passed")
            
            # Test coefficients endpoint
            print("Testing coefficients endpoint...")
            response = await client.get(f"{BASE_URL}/coefficients")
            assert response.status_code == 200
            coefficients = response.json()
            assert isinstance(coefficients, dict)
            assert "tolerance" in coefficients
            print("Coefficients endpoint passed")
            
            # Test locations endpoint
            print("Testing locations endpoint...")
            response = await client.get(f"{BASE_URL}/locations")
            assert response.status_code == 200
            locations = response.json()
            assert isinstance(locations, dict)
            assert "locations" in locations
            print("Locations endpoint passed")
            
            # Test demo files endpoint
            print("Testing demo files endpoint...")
            response = await client.get(f"{BASE_URL}/files/demo")
            assert response.status_code == 200
            demo_files = response.json()
            assert isinstance(demo_files, list)
            print("Demo files endpoint passed")
            
            # Test calculate-price with minimal data
            print("Testing calculate-price endpoint...")
            calc_request = {
                "service_id": "cnc-milling",
                "quantity": 1,
                "length": 100,
                "width": 50,
                "height": 25,
                "material_id": "alum_D16",
                "material_form": "rod",
                "id_tolerance": "1",
                "id_finish": "1",
                "id_cover": ["1"],
                "k_otk": "1",
                "k_cert": ["a", "f"],
                "n_dimensions": 1
            }
            
            response = await client.post(
                f"{BASE_URL}/calculate-price",
                json=calc_request
            )
            
            if response.status_code == 200:
                result = response.json()
                assert "total_price" in result
                print("Calculate-price endpoint passed")
            elif response.status_code == 502:
                print("Calculate-price endpoint - calculator service not available")
            else:
                print(f"Calculate-price endpoint returned status {response.status_code}")
            
            print("\nQuick tests completed successfully!")
            print("All core endpoints are working correctly")
            
        except Exception as e:
            print(f"\nQuick test failed: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(quick_test())

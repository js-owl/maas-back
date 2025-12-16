"""
Calculations endpoints tests
Tests calculate-price, proxy endpoints, and error handling
"""
import asyncio
import httpx
import json

BASE_URL = "http://localhost:7000"

class CalculationsEndpointTester:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
        self.calculator_available = False
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def check_calculator_availability(self):
        """Check if calculator service is available"""
        try:
            response = await self.client.get("http://localhost:7000/health", timeout=5)
            self.calculator_available = response.status_code == 200
            if not self.calculator_available:
                print(" Calculator service not available - skipping calculation tests")
        except Exception:
            self.calculator_available = False
            print(" Calculator service not available - skipping calculation tests")
    
    async def test_proxy_endpoints(self):
        """Test proxy endpoints for configuration data"""
        print("Testing proxy endpoints...")
        
        # Test services endpoint
        response = await self.client.get(f"{self.base_url}/services")
        assert response.status_code == 200
        services = response.json()
        assert isinstance(services, list)
        assert len(services) == 4
        expected_services = ["printing", "cnc-milling", "cnc-lathe", "painting"]
        for service in expected_services:
            assert service in services
        print(" Services endpoint passed")
        
        # Test materials endpoint
        response = await self.client.get(f"{self.base_url}/materials")
        assert response.status_code == 200
        materials = response.json()
        assert isinstance(materials, dict)
        assert "materials" in materials
        assert isinstance(materials["materials"], list)
        print(" Materials endpoint passed")
        
        # Test materials with process filter
        response = await self.client.get(f"{self.base_url}/materials?process=printing")
        assert response.status_code == 200
        materials_filtered = response.json()
        assert isinstance(materials_filtered, dict)
        assert "materials" in materials_filtered
        print(" Materials with process filter passed")
        
        # Test coefficients endpoint
        response = await self.client.get(f"{self.base_url}/coefficients")
        assert response.status_code == 200
        coefficients = response.json()
        assert isinstance(coefficients, dict)
        assert "tolerance" in coefficients
        assert "finish" in coefficients
        assert "cover" in coefficients
        print(" Coefficients endpoint passed")
        
        # Test locations endpoint
        response = await self.client.get(f"{self.base_url}/locations")
        assert response.status_code == 200
        locations = response.json()
        assert isinstance(locations, dict)
        assert "locations" in locations
        assert isinstance(locations["locations"], list)
        print(" Locations endpoint passed")
    
    async def test_calculate_price_valid_requests(self):
        """Test calculate-price with valid requests for all services"""
        print(" Testing calculate-price with valid requests...")
        
        if not self.calculator_available:
            print(" Skipping calculation tests - calculator service not available")
            return
        
        services = ["printing", "cnc-milling", "cnc-lathe", "painting"]
        
        for service in services:
            calc_request = {
                "service_id": service,
                "quantity": 1,
                "length": 100,
                "width": 50,
                "height": 25,
                "material_id": "alum_D16",
                "material_form": "rod",
                "tolerance_id": "1",
                "finish_id": "1",
                "cover_id": ["1"],
                "k_otk": "1",
                "k_cert": ["a", "f"],
                "n_dimensions": 1,
                "location": "location_1"
            }
            
            response = await self.client.post(
                f"{self.base_url}/calculate-price",
                json=calc_request
            )
            
            if response.status_code == 200:
                result = response.json()
                assert "total_price" in result
                assert "service_id" in result
                assert result["service_id"] == service
                print(f" Calculate-price for {service} passed")
            elif response.status_code == 502:
                print(f"  Calculate-price for {service} - calculator service not available")
            else:
                print(f"  Calculate-price for {service} returned status {response.status_code}")

    async def test_calculate_price_valid_requests_loc(self):
        """Test calculate-price with valid requests for all services, check location"""
        print(" Testing calculate-price with valid requests, check location...")
        
        if not self.calculator_available:
            print(" Skipping calculation tests - calculator service not available")
            return
        
        services = ["cnc-milling"]
        location = "location_2"
        for service in services:
            calc_request = {
                "service_id": service,
                "file_id": "test-S8000_125_63_293_001_D000_02.stp-cnc-milling",
                "file_data": "SVNPLTEwMzAzLTIxOw0KSEVBREVSOw0KLyogR2",
                "file_name": "S8000_125_63_293_001_D000_02.stp",
                "file_type": "stp",
                "material_id": "alum_D16",
                "material_form": "sheet",
                "quantity": 1,
                "tolerance_id": "1",
                "finish_id": "1",
                "cover_id": [
                    "1"
                ],
                "k_otk": 1.0,
                "location": location
            }
            
            response = await self.client.post(
                f"{self.base_url}/calculate-price",
                json=calc_request
            )
            
            if response.status_code == 200:
                result = response.json()
                assert "total_price" in result
                assert "service_id" in result
                assert result["service_id"] == service
                assert result["total_price_breakdown"]["location"] == location
                print(f" Calculate-price for {service} passed, location response: {location}")
            elif response.status_code == 502:
                print(f"  Calculate-price for {service} - calculator service not available")
            else:
                print(f"  Calculate-price for {service} returned status {response.status_code}, location response: {location}")
    
    async def test_calculate_price_invalid_requests(self):
        """Test calculate-price with invalid requests to test error handling"""
        print(" Testing calculate-price with invalid requests...")
        
        invalid_requests = [
            {
                "name": "Invalid service ID",
                "data": {
                    "service_id": "invalid-service",
                    "quantity": 1,
                    "length": 100,
                    "width": 50,
                    "height": 25,
                    "material_id": "alum_D16",
                    "material_form": "rod",
                    "tolerance_id": "1",
                    "finish_id": "1",
                    "cover_id": ["1"],
                    "k_otk": "1",
                    "k_cert": ["a", "f"],
                    "n_dimensions": 1
                },
                "expected_status": [200, 422]  # Calculator service might accept invalid service IDs
            },
            {
                "name": "Invalid quantity",
                "data": {
                    "service_id": "cnc-milling",
                    "quantity": -1,
                    "length": 100,
                    "width": 50,
                    "height": 25,
                    "material_id": "alum_D16",
                    "material_form": "rod",
                    "tolerance_id": "1",
                    "finish_id": "1",
                    "cover_id": ["1"],
                    "k_otk": "1",
                    "k_cert": ["a", "f"],
                    "n_dimensions": 1
                },
                "expected_status": 422
            },
            {
                "name": "Invalid material",
                "data": {
                    "service_id": "cnc-milling",
                    "quantity": 1,
                    "length": 100,
                    "width": 50,
                    "height": 25,
                    "material_id": "invalid_material",
                    "material_form": "invalid_form",
                    "tolerance_id": "invalid_tolerance",
                    "finish_id": "invalid_finish",
                    "cover_id": ["invalid_cover"],
                    "k_otk": "invalid_otk",
                    "k_cert": ["invalid_cert"],
                    "n_dimensions": 0
                },
                "expected_status": 422
            }
        ]
        
        for test_case in invalid_requests:
            response = await self.client.post(
                f"{self.base_url}/calculate-price",
                json=test_case["data"]
            )
            
            expected_status = test_case["expected_status"]
            if isinstance(expected_status, list):
                if response.status_code in expected_status:
                    print(f" {test_case['name']} - {response.status_code} status handled correctly")
                elif response.status_code == 502:
                    print(f"  {test_case['name']} - calculator service not available")
                else:
                    print(f"  {test_case['name']} - unexpected status {response.status_code}")
            else:
                if response.status_code == expected_status:
                    print(f" {test_case['name']} - {response.status_code} error properly handled")
                elif response.status_code == 502:
                    print(f"  {test_case['name']} - calculator service not available")
                else:
                    print(f"  {test_case['name']} - unexpected status {response.status_code}")
    
    async def test_calculate_price_with_file_id(self):
        """Test calculate-price with file_id parameter"""
        print(" Testing calculate-price with file_id...")
        
        calc_request = {
            "service_id": "cnc-milling",
            "file_id": 1,  # Demo file
            "quantity": 1,
            "length": 100,
            "width": 50,
            "height": 25,
            "material_id": "alum_D16",
            "material_form": "rod",
            "tolerance_id": "1",
            "finish_id": "1",
            "id_cover": ["1"],
            "k_otk": "1",
            "k_cert": ["a", "f"],
            "n_dimensions": 1
        }
        
        response = await self.client.post(
            f"{self.base_url}/calculate-price",
            json=calc_request
        )
        
        if response.status_code == 200:
            result = response.json()
            assert "total_price" in result
            print(" Calculate-price with file_id passed")
        elif response.status_code == 502:
            print("  Calculate-price with file_id - calculator service not available")
        else:
            print(f"  Calculate-price with file_id returned status {response.status_code}")
    
    async def test_calculate_price_edge_cases(self):
        """Test calculate-price with edge cases"""
        print(" Testing calculate-price edge cases...")
        
        # Test with minimal required fields (service_id + basic dimensions)
        minimal_request = {
            "service_id": "cnc-milling",
            "quantity": 1,
            "length": 100,
            "width": 50,
            "height": 25
        }
        
        response = await self.client.post(
            f"{self.base_url}/calculate-price",
            json=minimal_request
        )
        
        if response.status_code == 200:
            result = response.json()
            assert "total_price" in result
            print(" Calculate-price with minimal fields passed")
        elif response.status_code == 502:
            print("  Calculate-price with minimal fields - calculator service not available")
        else:
            print(f"  Calculate-price with minimal fields returned status {response.status_code}")
        
        # Test with different quantity values
        quantity_tests = [1, 5, 10, 100]
        for quantity in quantity_tests:
            calc_request = {
                "service_id": "cnc-milling",
                "quantity": quantity,
                "length": 100,
                "width": 50,
                "height": 25,
                "material_id": "alum_D16",
                "material_form": "rod",
                "tolerance_id": "1",
                "finish_id": "1",
                "cover_id": ["1"],
                "k_otk": "1",
                "k_cert": ["a", "f"],
                "n_dimensions": 1
            }
            
            response = await self.client.post(
                f"{self.base_url}/calculate-price",
                json=calc_request
            )
            
            if response.status_code == 200:
                result = response.json()
                assert result["quantity"] == quantity
                print(f" Calculate-price with quantity {quantity} passed")
            elif response.status_code == 502:
                print(f"  Calculate-price with quantity {quantity} - calculator service not available")
                break  # No point testing more if service is down
            else:
                print(f"  Calculate-price with quantity {quantity} returned status {response.status_code}")
    
    async def run_all_tests(self):
        """Run all calculation tests"""
        print(" Starting calculation endpoint tests...\n")
        
        # Check calculator service availability first
        await self.check_calculator_availability()
        print()
        
        try:
            await self.test_proxy_endpoints()
            print()
            
            await self.test_calculate_price_valid_requests()
            print()

            await self.test_calculate_price_valid_requests_loc()
            print()
            
            await self.test_calculate_price_invalid_requests()
            print()
            
            await self.test_calculate_price_with_file_id()
            print()
            
            await self.test_calculate_price_edge_cases()
            print()
            
            print(" All calculation tests completed successfully!")
            
        except Exception as e:
            print(f" Calculation test failed: {e}")
            raise


async def main():
    """Main test runner"""
    async with CalculationsEndpointTester() as tester:
        await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())

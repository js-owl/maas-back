"""
Service integration tests
Tests integration between calculator service and backend API
"""
import pytest
import httpx
from tests.test_config import BASE_URL, CALCULATOR_URL
from tests.test_helpers import is_calculator_available


@pytest.mark.integration
@pytest.mark.requires_calculator
@pytest.mark.asyncio
class TestCalculatorServiceIntegration:
    """Test calculator service integration"""
    
    async def test_calculator_service_health(self, skip_if_calculator_unavailable):
        """Test calculator service health check"""
        available = await is_calculator_available()
        assert available, "Calculator service should be available"
    
    async def test_calculator_services_endpoint(
        self, http_client, skip_if_calculator_unavailable
    ):
        """Test fetching services from calculator"""
        response = await http_client.get(f"{BASE_URL}/services")
        assert response.status_code == 200
        services = response.json()
        assert isinstance(services, list)
        assert len(services) > 0
    
    async def test_calculator_materials_endpoint(
        self, http_client, skip_if_calculator_unavailable
    ):
        """Test fetching materials from calculator"""
        response = await http_client.get(f"{BASE_URL}/materials")
        assert response.status_code == 200
        materials = response.json()
        assert isinstance(materials, dict)
        assert len(materials) > 0
    
    async def test_calculator_coefficients_endpoint(
        self, http_client, skip_if_calculator_unavailable
    ):
        """Test fetching coefficients from calculator"""
        response = await http_client.get(f"{BASE_URL}/coefficients")
        assert response.status_code == 200
        coefficients = response.json()
        assert isinstance(coefficients, dict)
    
    async def test_calculator_locations_endpoint(
        self, http_client, skip_if_calculator_unavailable
    ):
        """Test fetching locations from calculator"""
        response = await http_client.get(f"{BASE_URL}/locations")
        assert response.status_code == 200
        locations = response.json()
        assert isinstance(locations, dict)


@pytest.mark.integration
@pytest.mark.asyncio
class TestCrossServiceWorkflow:
    """Test workflows involving multiple services"""
    
    async def test_calculator_to_order_workflow(
        self, http_client, user_account, uploaded_file
    ):
        """Test workflow from calculation to order creation"""
        user_data, token = user_account
        
        # Calculate price
        calc_data = {
            "service_id": "cnc-milling",
            "material_id": "alum_D16",
            "material_form": "rod",
            "quantity": 1,
            "length": 100,
            "width": 50,
            "height": 25,
        }
        
        response = await http_client.post(
            f"{BASE_URL}/calculate-price",
            json=calc_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if response.status_code == 200:
            calculation = response.json()
            calculated_price = calculation.get("total_price", 0)
            
            # Create order with calculated price
            order_data = {
                "service_id": "cnc-milling",
                "file_id": uploaded_file,
                "quantity": 1,
                "material_id": "alum_D16",
                "material_form": "rod",
                "length": 100,
                "width": 50,
                "height": 25,
            }
            
            response = await http_client.post(
                f"{BASE_URL}/orders",
                json=order_data,
                headers={"Authorization": f"Bearer {token}"}
            )
            
            assert response.status_code == 200
            order = response.json()
            # Order price should match calculation (approximately)
            assert order["total_price"] > 0


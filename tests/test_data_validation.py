"""
Data validation tests
Tests schema validation, field types, required fields, and boundary values
"""
import pytest
import httpx
from tests.test_config import BASE_URL
from tests.test_helpers import (
    generate_test_user,
    generate_test_calculation_data,
    validate_error_response,
    assert_user_schema,
    assert_file_schema,
    assert_order_schema,
    assert_calculation_schema,
)


@pytest.mark.unit
class TestUserDataValidation:
    """Test user data validation"""
    
    @pytest.mark.asyncio
    async def test_registration_missing_required_fields(self, http_client):
        """Test registration with missing required fields"""
        required_fields = ["username", "password", "user_type"]
        
        for field_to_omit in required_fields:
            user_data = generate_test_user()
            del user_data[field_to_omit]
            
            response = await http_client.post(
                f"{BASE_URL}/register",
                json=user_data
            )
            validate_error_response(response, 422)
    
    @pytest.mark.asyncio
    async def test_registration_with_empty_fields(self, http_client):
        """Test registration with empty string fields"""
        user_data = generate_test_user()
        
        # Empty username
        user_data["username"] = ""
        response = await http_client.post(f"{BASE_URL}/register", json=user_data)
        validate_error_response(response, 422)
        
        # Empty password
        user_data = generate_test_user()
        user_data["password"] = ""
        response = await http_client.post(f"{BASE_URL}/register", json=user_data)
        validate_error_response(response, 422)
    
    @pytest.mark.asyncio
    async def test_registration_with_invalid_user_type(self, http_client):
        """Test registration with invalid user_type"""
        user_data = generate_test_user()
        invalid_types = ["", "admin", "superuser", "123", None]
        
        for invalid_type in invalid_types:
            user_data["user_type"] = invalid_type
            response = await http_client.post(
                f"{BASE_URL}/register",
                json=user_data
            )
            validate_error_response(response, 422)
    
    @pytest.mark.asyncio
    async def test_registration_with_invalid_email(self, http_client):
        """Test registration with invalid email formats"""
        invalid_emails = [
            "",
            "not-an-email",
            "@example.com",
            "user@",
            "user@.com",
            "user..double@example.com",
        ]
        
        for invalid_email in invalid_emails:
            user_data = generate_test_user()
            user_data["email"] = invalid_email
            response = await http_client.post(
                f"{BASE_URL}/register",
                json=user_data
            )
            validate_error_response(response, 422)
    
    @pytest.mark.asyncio
    async def test_registration_username_length_boundaries(self, http_client):
        """Test username length boundaries"""
        # Too short
        user_data = generate_test_user()
        user_data["username"] = "a"
        response = await http_client.post(f"{BASE_URL}/register", json=user_data)
        validate_error_response(response, 422)
        
        # Too long (>255 characters)
        user_data = generate_test_user()
        user_data["username"] = "a" * 300
        response = await http_client.post(f"{BASE_URL}/register", json=user_data)
        validate_error_response(response, 422)
    
    @pytest.mark.asyncio
    async def test_duplicate_username_rejected(self, http_client, user_account):
        """Test that duplicate usernames are rejected"""
        existing_user, token = user_account
        
        # Try to register with same username
        user_data = generate_test_user()
        user_data["username"] = existing_user["username"]
        
        response = await http_client.post(
            f"{BASE_URL}/register",
            json=user_data
        )
        validate_error_response(response, 400)
    
    @pytest.mark.asyncio
    async def test_user_response_schema(self, http_client, user_account):
        """Test that user responses match expected schema"""
        user_data, token = user_account
        
        response = await http_client.get(
            f"{BASE_URL}/profile",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        
        user_profile = response.json()
        assert_user_schema(user_profile)


@pytest.mark.unit
class TestFileDataValidation:
    """Test file upload data validation"""
    
    @pytest.mark.asyncio
    async def test_file_upload_missing_required_fields(
        self, http_client, user_account
    ):
        """Test file upload with missing required fields"""
        user_data, token = user_account
        
        # Missing file_name
        response = await http_client.post(
            f"{BASE_URL}/files",
            json={"file_data": "dGVzdA=="},
            headers={"Authorization": f"Bearer {token}"}
        )
        validate_error_response(response, 422)
        
        # Missing file_data
        response = await http_client.post(
            f"{BASE_URL}/files",
            json={"file_name": "test.stl"},
            headers={"Authorization": f"Bearer {token}"}
        )
        validate_error_response(response, 422)
    
    @pytest.mark.asyncio
    async def test_file_upload_with_invalid_base64(
        self, http_client, user_account
    ):
        """Test file upload with invalid base64 data"""
        user_data, token = user_account
        
        invalid_base64 = [
            "not-base64!@#",
            "invalid=base64=",
            "12345",  # Too short
        ]
        
        for invalid_data in invalid_base64:
            response = await http_client.post(
                f"{BASE_URL}/files",
                json={
                    "file_name": "test.stl",
                    "file_data": invalid_data
                },
                headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code in [400, 422], \
                f"Invalid base64 should be rejected: {invalid_data[:20]}"
    
    @pytest.mark.asyncio
    async def test_file_upload_with_empty_content(
        self, http_client, user_account
    ):
        """Test file upload with empty content"""
        user_data, token = user_account
        
        response = await http_client.post(
            f"{BASE_URL}/files",
            json={
                "file_name": "test.stl",
                "file_data": ""  # Empty
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        validate_error_response(response, 422)
    
    @pytest.mark.asyncio
    async def test_file_response_schema(
        self, http_client, user_account, uploaded_file
    ):
        """Test that file responses match expected schema"""
        user_data, token = user_account
        
        response = await http_client.get(
            f"{BASE_URL}/files/{uploaded_file}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        
        file_data = response.json()
        assert_file_schema(file_data)


@pytest.mark.unit
class TestCalculationDataValidation:
    """Test calculation request data validation"""
    
    @pytest.mark.asyncio
    async def test_calculation_missing_required_fields(self, http_client):
        """Test calculation with missing required fields"""
        required_fields = ["service_id", "material_id", "quantity"]
        
        for field_to_omit in required_fields:
            calc_data = generate_test_calculation_data()
            del calc_data[field_to_omit]
            
            response = await http_client.post(
                f"{BASE_URL}/calculate-price",
                json=calc_data
            )
            validate_error_response(response, 422)
    
    @pytest.mark.asyncio
    async def test_calculation_with_invalid_service_id(self, http_client):
        """Test calculation with invalid service_id"""
        calc_data = generate_test_calculation_data()
        invalid_services = ["", "invalid-service", "123", None]
        
        for invalid_service in invalid_services:
            calc_data["service_id"] = invalid_service
            response = await http_client.post(
                f"{BASE_URL}/calculate-price",
                json=calc_data
            )
            assert response.status_code in [400, 422], \
                f"Invalid service_id should be rejected: {invalid_service}"
    
    @pytest.mark.asyncio
    async def test_calculation_with_invalid_quantity(self, http_client):
        """Test calculation with invalid quantity values"""
        calc_data = generate_test_calculation_data()
        invalid_quantities = [0, -1, -100, "not-a-number"]
        
        for invalid_qty in invalid_quantities:
            calc_data["quantity"] = invalid_qty
            response = await http_client.post(
                f"{BASE_URL}/calculate-price",
                json=calc_data
            )
            assert response.status_code in [400, 422], \
                f"Invalid quantity should be rejected: {invalid_qty}"
    
    @pytest.mark.asyncio
    async def test_calculation_with_negative_dimensions(self, http_client):
        """Test calculation with negative dimension values"""
        calc_data = generate_test_calculation_data()
        
        # Negative length
        calc_data["length"] = -100
        response = await http_client.post(
            f"{BASE_URL}/calculate-price",
            json=calc_data
        )
        validate_error_response(response, 422)
        
        # Negative width
        calc_data = generate_test_calculation_data()
        calc_data["width"] = -50
        response = await http_client.post(
            f"{BASE_URL}/calculate-price",
            json=calc_data
        )
        validate_error_response(response, 422)
    
    @pytest.mark.asyncio
    async def test_calculation_with_zero_dimensions(self, http_client):
        """Test calculation with zero dimension values"""
        calc_data = generate_test_calculation_data()
        
        calc_data["length"] = 0
        response = await http_client.post(
            f"{BASE_URL}/calculate-price",
            json=calc_data
        )
        validate_error_response(response, 422)
    
    @pytest.mark.asyncio
    async def test_calculation_with_extreme_dimensions(self, http_client):
        """Test calculation with extremely large dimensions"""
        calc_data = generate_test_calculation_data()
        
        # Very large dimensions
        calc_data["length"] = 1000000  # 1000 meters
        calc_data["width"] = 1000000
        calc_data["height"] = 1000000
        
        response = await http_client.post(
            f"{BASE_URL}/calculate-price",
            json=calc_data
        )
        # Should either accept or reject based on business rules
        assert response.status_code in [200, 400, 422]
    
    @pytest.mark.asyncio
    async def test_calculation_response_schema(self, http_client):
        """Test that calculation responses match expected schema"""
        calc_data = generate_test_calculation_data()
        
        response = await http_client.post(
            f"{BASE_URL}/calculate-price",
            json=calc_data
        )
        
        if response.status_code == 200:
            calculation = response.json()
            assert_calculation_schema(calculation)


@pytest.mark.unit
class TestOrderDataValidation:
    """Test order creation data validation"""
    
    @pytest.mark.asyncio
    async def test_order_missing_required_fields(
        self, http_client, user_account, uploaded_file
    ):
        """Test order creation with missing required fields"""
        user_data, token = user_account
        required_fields = ["service_id", "file_id", "quantity", "material_id"]
        
        for field_to_omit in required_fields:
            order_data = {
                "service_id": "cnc-milling",
                "file_id": uploaded_file,
                "quantity": 1,
                "material_id": "alum_D16",
                "length": 100,
                "width": 50,
                "height": 25,
            }
            del order_data[field_to_omit]
            
            response = await http_client.post(
                f"{BASE_URL}/orders",
                json=order_data,
                headers={"Authorization": f"Bearer {token}"}
            )
            validate_error_response(response, 422)
    
    @pytest.mark.asyncio
    async def test_order_with_nonexistent_file(
        self, http_client, user_account
    ):
        """Test order creation with nonexistent file_id"""
        user_data, token = user_account
        
        order_data = {
            "service_id": "cnc-milling",
            "file_id": 999999,  # Nonexistent
            "quantity": 1,
            "material_id": "alum_D16",
            "length": 100,
            "width": 50,
            "height": 25,
            "tolerance_id": "1",
            "finish_id": "1",
            "cover_id": ["1"],
            "k_otk": "1",
            "k_cert": ["a"],
            "n_dimensions": 3,
        }
        
        response = await http_client.post(
            f"{BASE_URL}/orders",
            json=order_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code in [400, 404], \
            "Order with nonexistent file should be rejected"
    
    @pytest.mark.asyncio
    async def test_order_with_invalid_quantity(
        self, http_client, user_account, uploaded_file
    ):
        """Test order creation with invalid quantity"""
        user_data, token = user_account
        invalid_quantities = [0, -1, -100]
        
        for invalid_qty in invalid_quantities:
            order_data = {
                "service_id": "cnc-milling",
                "file_id": uploaded_file,
                "quantity": invalid_qty,
                "material_id": "alum_D16",
                "length": 100,
                "width": 50,
                "height": 25,
            }
            
            response = await http_client.post(
                f"{BASE_URL}/orders",
                json=order_data,
                headers={"Authorization": f"Bearer {token}"}
            )
            validate_error_response(response, 422)
    
    @pytest.mark.asyncio
    async def test_order_response_schema(
        self, http_client, user_account, created_order
    ):
        """Test that order responses match expected schema"""
        user_data, token = user_account
        
        response = await http_client.get(
            f"{BASE_URL}/orders/{created_order}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        
        order = response.json()
        assert_order_schema(order)


@pytest.mark.unit
class TestBoundaryValues:
    """Test boundary value validation"""
    
    @pytest.mark.asyncio
    async def test_minimum_valid_dimensions(self, http_client):
        """Test minimum valid dimension values"""
        calc_data = generate_test_calculation_data()
        
        # Minimum valid dimensions (0.1mm)
        calc_data["length"] = 0.1
        calc_data["width"] = 0.1
        calc_data["height"] = 0.1
        
        response = await http_client.post(
            f"{BASE_URL}/calculate-price",
            json=calc_data
        )
        # Should either accept or have defined minimum
        assert response.status_code in [200, 422]
    
    @pytest.mark.asyncio
    async def test_maximum_valid_quantity(
        self, http_client, user_account, uploaded_file
    ):
        """Test maximum valid quantity values"""
        user_data, token = user_account
        
        # Very large quantity
        order_data = {
            "service_id": "cnc-milling",
            "file_id": uploaded_file,
            "quantity": 10000,
            "material_id": "alum_D16",
            "length": 100,
            "width": 50,
            "height": 25,
        }
        
        response = await http_client.post(
            f"{BASE_URL}/orders",
            json=order_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        # Should either accept or have defined maximum
        assert response.status_code in [200, 422]
    
    @pytest.mark.asyncio
    async def test_float_precision_handling(self, http_client):
        """Test handling of floating point precision"""
        calc_data = generate_test_calculation_data()
        
        # High precision floats
        calc_data["length"] = 100.123456789
        calc_data["width"] = 50.987654321
        calc_data["k_complexity"] = 1.5555555555
        
        response = await http_client.post(
            f"{BASE_URL}/calculate-price",
            json=calc_data
        )
        assert response.status_code in [200, 422]


@pytest.mark.unit
class TestTypeValidation:
    """Test data type validation"""
    
    @pytest.mark.asyncio
    async def test_string_as_number_rejected(self, http_client):
        """Test that strings are rejected for numeric fields"""
        calc_data = generate_test_calculation_data()
        
        # String as quantity
        calc_data["quantity"] = "ten"
        response = await http_client.post(
            f"{BASE_URL}/calculate-price",
            json=calc_data
        )
        validate_error_response(response, 422)
        
        # String as dimension
        calc_data = generate_test_calculation_data()
        calc_data["length"] = "hundred"
        response = await http_client.post(
            f"{BASE_URL}/calculate-price",
            json=calc_data
        )
        validate_error_response(response, 422)
    
    @pytest.mark.asyncio
    async def test_number_as_string_rejected(self, http_client):
        """Test that numbers are rejected for string fields"""
        user_data = generate_test_user()
        
        # Number as username
        user_data["username"] = 12345
        response = await http_client.post(
            f"{BASE_URL}/register",
            json=user_data
        )
        # May be accepted if coerced to string, or rejected
        assert response.status_code in [200, 422]
    
    @pytest.mark.asyncio
    async def test_null_values_handled(self, http_client):
        """Test that null values are handled appropriately"""
        calc_data = generate_test_calculation_data()
        
        # Null for optional field
        calc_data["special_instructions"] = None
        response = await http_client.post(
            f"{BASE_URL}/calculate-price",
            json=calc_data
        )
        # Should accept null for optional fields
        assert response.status_code in [200, 422]
        
        # Null for required field
        calc_data["service_id"] = None
        response = await http_client.post(
            f"{BASE_URL}/calculate-price",
            json=calc_data
        )
        validate_error_response(response, 422)
    
    @pytest.mark.asyncio
    async def test_array_fields_validation(self, http_client):
        """Test validation of array fields"""
        # Invalid array format for cover_id
        invalid_arrays = [
            "not-an-array",
            123,
            {"key": "value"},
            None,
        ]
        
        for invalid_array in invalid_arrays:
            calc_data = generate_test_calculation_data()  # Create fresh data for each iteration
            calc_data["cover_id"] = invalid_array
            response = await http_client.post(
                f"{BASE_URL}/calculate-price",
                json=calc_data
            )
            validate_error_response(response, 422)


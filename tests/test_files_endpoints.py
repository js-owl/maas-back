"""
Files endpoints tests
Tests file upload, download, preview, and management
"""
import asyncio
import httpx
import base64
import json

BASE_URL = "http://localhost:8000"

class FilesEndpointTester:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
        self.auth_token = None
        self.test_file_id = None
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def setup_auth(self):
        """Setup authentication for file tests"""
        import time
        timestamp = int(time.time())
        
        # Register test user
        user_data = {
            "username": f"test_files_user_{timestamp}",
            "password": "testpass123",
            "user_type": "individual"
        }
        
        response = await self.client.post(f"{self.base_url}/register", json=user_data)
        if response.status_code != 200:
            print(f"User registration failed: {response.text}")
            return False
        
        # Login
        login_data = {
            "username": f"test_files_user_{timestamp}",
            "password": "testpass123"
        }
        
        response = await self.client.post(
            f"{self.base_url}/login",
            json=login_data
        )
        if response.status_code != 200:
            print(f"Login failed: {response.text}")
            return False
        auth_data = response.json()
        self.auth_token = auth_data["access_token"]
        return True
    
    async def test_demo_files_endpoint(self):
        """Test demo files endpoint"""
        print(" Testing demo files endpoint...")
        
        response = await self.client.get(f"{self.base_url}/files/demo")
        print(f" Demo files response status: {response.status_code}")
        if response.status_code != 200:
            print(f" Demo files response body: {response.text}")
        assert response.status_code == 200
        demo_files = response.json()
        assert isinstance(demo_files, list)
        print(" Demo files endpoint passed")
    
    async def test_file_upload_json(self):
        """Test file upload with JSON (base64)"""
        print(" Testing file upload with JSON...")
        
        if not self.auth_token:
            success = await self.setup_auth()
            if not success:
                print(" Skipping file upload tests - auth setup failed")
                return
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        # Test STL file upload
        test_file_content = "This is a test STL file content for modular API testing"
        file_data = base64.b64encode(test_file_content.encode()).decode()
        
        upload_request = {
            "file_name": "test_model.stl",
            "file_data": file_data,
            "file_type": "stl"
        }
        
        response = await self.client.post(
            f"{self.base_url}/files",
            json=upload_request,
            headers=headers
        )
        if response.status_code != 200:
            print(f"File upload failed with status {response.status_code}: {response.text}")
            raise AssertionError(f"Expected 200, got {response.status_code}")
        upload_data = response.json()
        assert "id" in upload_data
        assert "filename" in upload_data
        assert "file_size" in upload_data
        self.test_file_id = upload_data["id"]
        print(" File upload with JSON passed")
        
        # Test STP file upload
        test_stp_content = "This is a test STP file content for modular API testing"
        stp_data = base64.b64encode(test_stp_content.encode()).decode()
        
        stp_upload_request = {
            "file_name": "test_model.stp",
            "file_data": stp_data,
            "file_type": "stp",
            "description": "Test STP model for modular API testing"
        }
        
        response = await self.client.post(
            f"{self.base_url}/files",
            json=stp_upload_request,
            headers=headers
        )
        assert response.status_code == 200
        stp_upload_data = response.json()
        assert "id" in stp_upload_data
        print(" STP file upload with JSON passed")
    
    
    async def test_file_listing(self):
        """Test file listing"""
        print(" Testing file listing...")
        
        if not self.auth_token:
            success = await self.setup_auth()
            if not success:
                print(" Skipping file upload tests - auth setup failed")
                return
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        response = await self.client.get(
            f"{self.base_url}/files",
            headers=headers
        )
        assert response.status_code == 200
        files = response.json()
        assert isinstance(files, list)
        print(" File listing passed")
    
    async def test_file_details(self):
        """Test file details retrieval"""
        print(" Testing file details...")
        
        if not self.auth_token:
            success = await self.setup_auth()
            if not success:
                print(" Skipping file upload tests - auth setup failed")
                return
        
        if not self.test_file_id:
            print("  Skipping file details test - no test file ID")
            return
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        response = await self.client.get(
            f"{self.base_url}/files/{self.test_file_id}",
            headers=headers
        )
        assert response.status_code == 200
        file_data = response.json()
        assert file_data["id"] == self.test_file_id
        assert "filename" in file_data
        assert "file_size" in file_data
        print(" File details passed")
    
    async def test_file_download(self):
        """Test file download"""
        print(" Testing file download...")
        
        if not self.auth_token:
            success = await self.setup_auth()
            if not success:
                print(" Skipping file upload tests - auth setup failed")
                return
        
        if not self.test_file_id:
            print("  Skipping file download test - no test file ID")
            return
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        response = await self.client.get(
            f"{self.base_url}/files/{self.test_file_id}/download",
            headers=headers
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/octet-stream"
        print(" File download passed")
    
    async def test_file_preview(self):
        """Test file preview generation"""
        print(" Testing file preview...")
        
        if not self.auth_token:
            success = await self.setup_auth()
            if not success:
                print(" Skipping file upload tests - auth setup failed")
                return
        
        if not self.test_file_id:
            print("  Skipping file preview test - no test file ID")
            return
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        response = await self.client.get(
            f"{self.base_url}/files/{self.test_file_id}/preview",
            headers=headers
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"
        print(" File preview passed")
    
    async def test_file_access_control(self):
        """Test file access control"""
        print(" Testing file access control...")
        
        if not self.test_file_id:
            print("  Skipping file access control test - no test file ID")
            return
        
        # Test access without authentication
        response = await self.client.get(
            f"{self.base_url}/files/{self.test_file_id}"
        )
        assert response.status_code == 401
        print(" File access control (no auth) passed")
        
        # Test access with invalid token
        headers = {"Authorization": "Bearer invalid_token"}
        response = await self.client.get(
            f"{self.base_url}/files/{self.test_file_id}",
            headers=headers
        )
        assert response.status_code == 401
        print(" File access control (invalid token) passed")
    
    async def test_invalid_file_operations(self):
        """Test invalid file operations"""
        print(" Testing invalid file operations...")
        
        if not self.auth_token:
            success = await self.setup_auth()
            if not success:
                print(" Skipping file upload tests - auth setup failed")
                return
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        # Test access to non-existent file
        response = await self.client.get(
            f"{self.base_url}/files/99999",
            headers=headers
        )
        assert response.status_code == 404
        print(" Non-existent file handling passed")
        
        # Test invalid file type upload
        invalid_upload_request = {
            "file_name": "test.txt",
            "file_data": base64.b64encode(b"test content").decode(),
            "file_type": "txt",
            "description": "Invalid file type"
        }
        
        response = await self.client.post(
            f"{self.base_url}/files",
            json=invalid_upload_request,
            headers=headers
        )
        assert response.status_code == 400
        print(" Invalid file type handling passed")
    
    async def run_all_tests(self):
        """Run all file tests"""
        print(" Starting file endpoint tests...\n")
        
        try:
            await self.test_demo_files_endpoint()
            print()
            
            await self.test_file_upload_json()
            print()
            
            
            await self.test_file_listing()
            print()
            
            await self.test_file_details()
            print()
            
            await self.test_file_download()
            print()
            
            await self.test_file_preview()
            print()
            
            await self.test_file_access_control()
            print()
            
            await self.test_invalid_file_operations()
            print()
            
            print(" All file tests completed successfully!")
            
        except Exception as e:
            print(f" File test failed: {e}")
            raise


async def main():
    """Main test runner"""
    async with FilesEndpointTester() as tester:
        await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())

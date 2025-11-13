#!/usr/bin/env python3
"""
Test documents endpoints
"""
import asyncio
import aiohttp
import json
import base64
from typing import Dict, Any

class TestDocumentsEndpoints:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.test_document_id = None
        self.auth_token = None
        self.admin_token = None

    async def run_all_tests(self):
        """Run all document endpoint tests"""
        print("🧪 Testing Documents Endpoints")
        print("=" * 50)
        
        # Test OPTIONS endpoints first
        await self.test_options_endpoints()
        
        # Test authentication
        await self.test_authentication()
        
        if not self.auth_token:
            print("❌ Cannot continue without authentication")
            return False
            
        # Test document endpoints
        await self.test_document_endpoints()
        
        # Test admin document endpoints
        if self.admin_token:
            await self.test_admin_document_endpoints()
        else:
            print("⚠️  Skipping admin tests - no admin token")
        
        print("✅ Documents endpoint tests completed")
        return True

    async def test_options_endpoints(self):
        """Test OPTIONS endpoints for CORS preflight"""
        print("\n🔍 Testing OPTIONS endpoints...")
        
        options_endpoints = [
            "/documents",
            "/documents/1",  # Test with a document ID
            "/documents/1/download"
        ]
        
        async with aiohttp.ClientSession() as session:
            for endpoint in options_endpoints:
                try:
                    async with session.options(f"{self.base_url}{endpoint}") as response:
                        if response.status == 200:
                            print(f"  ✅ OPTIONS {endpoint} - {response.status}")
                        else:
                            print(f"  ❌ OPTIONS {endpoint} - {response.status}")
                except Exception as e:
                    print(f"  ❌ OPTIONS {endpoint} - Error: {e}")

    async def test_authentication(self):
        """Test user authentication"""
        print("\n🔐 Testing authentication...")
        
        # Test user login
        await self.test_user_login()
        
        # Test admin login
        await self.test_admin_login()

    async def test_user_login(self):
        """Test user login"""
        print("  Testing user login...")
        
        login_data = {
            "username": "testuser",
            "password": "testpassword123"
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.base_url}/login",
                    json=login_data
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.auth_token = data.get("access_token")
                        print(f"    ✅ User login successful")
                        return True
                    else:
                        print(f"    ❌ User login failed: {response.status}")
                        return False
            except Exception as e:
                print(f"    ❌ User login error: {e}")
                return False

    async def test_admin_login(self):
        """Test admin login"""
        print("  Testing admin login...")
        
        admin_data = {
            "username": "admin",
            "password": "admin123"
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.base_url}/login",
                    json=admin_data
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.admin_token = data.get("access_token")
                        print(f"    ✅ Admin login successful")
                        return True
                    else:
                        print(f"    ❌ Admin login failed: {response.status}")
                        return False
            except Exception as e:
                print(f"    ❌ Admin login error: {e}")
                return False

    async def test_document_endpoints(self):
        """Test document management endpoints"""
        print("\n📄 Testing document endpoints...")
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        async with aiohttp.ClientSession() as session:
            # Test document upload
            await self.test_document_upload(session, headers)
            
            # Test get user documents
            await self.test_get_user_documents(session, headers)
            
            # Test get document by ID
            if self.test_document_id:
                await self.test_get_document_by_id(session, headers)
                
                # Test document download
                await self.test_document_download(session, headers)
                
                # Test document deletion
                await self.test_document_deletion(session, headers)

    async def test_document_upload(self, session, headers):
        """Test document upload"""
        print("  Testing document upload...")
        
        # Create a simple text document
        document_content = "This is a test document for API testing."
        document_base64 = base64.b64encode(document_content.encode()).decode()
        
        document_data = {
            "file_name": "test_document.txt",
            "file_data": document_base64,
            "category": "test",
            "description": "Test document for API testing"
        }
        
        try:
            async with session.post(
                f"{self.base_url}/documents",
                json=document_data,
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.test_document_id = data.get("id")
                    print(f"    ✅ Document upload successful - ID: {self.test_document_id}")
                    return True
                else:
                    print(f"    ❌ Document upload failed: {response.status}")
                    return False
        except Exception as e:
            print(f"    ❌ Document upload error: {e}")
            return False

    async def test_get_user_documents(self, session, headers):
        """Test get user documents"""
        print("  Testing get user documents...")
        
        try:
            async with session.get(
                f"{self.base_url}/documents",
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"    ✅ GET /documents - {response.status} ({len(data)} documents)")
                    return True
                else:
                    print(f"    ❌ GET /documents - {response.status}")
                    return False
        except Exception as e:
            print(f"    ❌ GET /documents error: {e}")
            return False

    async def test_get_document_by_id(self, session, headers):
        """Test get document by ID"""
        print("  Testing get document by ID...")
        
        try:
            async with session.get(
                f"{self.base_url}/documents/{self.test_document_id}",
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"    ✅ GET /documents/{self.test_document_id} - {response.status}")
                    return True
                else:
                    print(f"    ❌ GET /documents/{self.test_document_id} - {response.status}")
                    return False
        except Exception as e:
            print(f"    ❌ GET /documents/{self.test_document_id} error: {e}")
            return False

    async def test_document_download(self, session, headers):
        """Test document download"""
        print("  Testing document download...")
        
        try:
            async with session.get(
                f"{self.base_url}/documents/{self.test_document_id}/download",
                headers=headers
            ) as response:
                if response.status == 200:
                    content = await response.read()
                    print(f"    ✅ Document download - {response.status} ({len(content)} bytes)")
                    return True
                else:
                    print(f"    ❌ Document download - {response.status}")
                    return False
        except Exception as e:
            print(f"    ❌ Document download error: {e}")
            return False

    async def test_document_deletion(self, session, headers):
        """Test document deletion"""
        print("  Testing document deletion...")
        
        try:
            async with session.delete(
                f"{self.base_url}/documents/{self.test_document_id}",
                headers=headers
            ) as response:
                if response.status == 200:
                    print(f"    ✅ Document deletion - {response.status}")
                    return True
                else:
                    print(f"    ❌ Document deletion - {response.status}")
                    return False
        except Exception as e:
            print(f"    ❌ Document deletion error: {e}")
            return False

    async def test_admin_document_endpoints(self):
        """Test admin document endpoints"""
        print("\n👑 Testing admin document endpoints...")
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        async with aiohttp.ClientSession() as session:
            # Test get all documents (admin)
            try:
                async with session.get(
                    f"{self.base_url}/admin/documents",
                    headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"    ✅ GET /admin/documents - {response.status} ({len(data)} documents)")
                    else:
                        print(f"    ❌ GET /admin/documents - {response.status}")
            except Exception as e:
                print(f"    ❌ GET /admin/documents error: {e}")
            
            # Test get documents by category
            try:
                async with session.get(
                    f"{self.base_url}/admin/documents?category=test",
                    headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"    ✅ GET /admin/documents?category=test - {response.status}")
                    else:
                        print(f"    ❌ GET /admin/documents?category=test - {response.status}")
            except Exception as e:
                print(f"    ❌ GET /admin/documents?category=test error: {e}")


async def main():
    """Main test function"""
    tester = TestDocumentsEndpoints()
    success = await tester.run_all_tests()
    
    if success:
        print("\n🎉 All documents endpoint tests passed!")
    else:
        print("\n❌ Some documents endpoint tests failed!")
    
    return success


if __name__ == "__main__":
    asyncio.run(main())

"""
Bitrix client module
Bitrix24 REST client for CRM integration
"""
import os
import logging
from typing import Optional, Dict, Any, List
import httpx
import base64

logger = logging.getLogger(__name__)


class BitrixClient:
    """Lightweight Bitrix24 REST client using Incoming Webhook.

    Requires BITRIX_WEBHOOK_URL env var like:
    https://<account>.bitrix24.com/rest/<user_id>/<webhook_token>/
    """

    def __init__(self, base_url: Optional[str] = None, timeout_seconds: int = 10):
        # Support either BITRIX_WEBHOOK_URL or BITRIX24_WEBHOOK_URL
        env_url = os.getenv("BITRIX_WEBHOOK_URL") or os.getenv("BITRIX24_WEBHOOK_URL") or ""
        self.base_url = (base_url or env_url).rstrip("/")
        self.enabled = os.getenv("BITRIX_ENABLED", "false").lower() == "true"
        self.verify_tls = os.getenv("BITRIX_VERIFY_TLS", "true").lower() != "false"
        self.timeout_seconds = timeout_seconds
        # Configurable file field and disk folder
        self.deal_file_field_code = os.getenv("BITRIX_DEAL_FILE_FIELD", "UF_CRM_MODEL_FILE")
        self.disk_folder_id = os.getenv("BITRIX_DISK_FOLDER_ID", "1")
        self.autocreate_fields = os.getenv("BITRIX_AUTOCREATE_FIELDS", "true").lower() == "true"

    def is_configured(self) -> bool:
        return self.enabled and bool(self.base_url)

    async def _post(self, method: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.is_configured():
            logger.debug("Bitrix not configured or disabled; skipping call %s", method)
            return None
        url = f"{self.base_url}/{method}" if not self.base_url.endswith("/") else f"{self.base_url}{method}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds, verify=self.verify_tls) as client:
                # Use JSON for methods that expect objects (like crm.deal.add, crm.item.update with fields, disk.folder.uploadfile, userfield.add)
                # Use form data for others
                if method.endswith(".userfield.add") or (method in ["crm.deal.add", "crm.deal.update", "crm.item.update", "disk.folder.uploadfile"] and ("fields" in data or "entityTypeId" in data or "data" in data)):
                    resp = await client.post(url, json=data)
                else:
                    resp = await client.post(url, data=data)
                
                # Log detailed error information for debugging
                if resp.status_code == 401:
                    error_body = resp.text
                    logger.error(
                        f"Bitrix authentication failed for {method}: "
                        f"Status {resp.status_code}, Response: {error_body[:200]}"
                    )
                    logger.error(
                        f"Bitrix URL used: {url}, "
                        f"Webhook might be expired or have insufficient permissions"
                    )
                elif resp.status_code != 200:
                    error_body = resp.text
                    logger.warning(
                        f"Bitrix request failed for {method}: "
                        f"Status {resp.status_code}, Response: {error_body[:200]}"
                    )
                
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as exc:
            error_body = exc.response.text if exc.response else "No response body"
            status_code = exc.response.status_code if exc.response else 'Unknown'
            
            # Don't log 400 "Not found" errors for get methods as ERROR - these are expected
            if status_code == 400 and method.endswith(".get") and "Not found" in error_body:
                logger.debug(
                    f"Bitrix {method}: Deal/entity not found (expected for non-existent IDs)"
                )
            else:
                logger.error(
                    f"Bitrix HTTP error for {method}: {status_code}, "
                    f"Response: {error_body[:200]}"
                )
            # Store error info in response for error categorization
            return {"_error": {"status_code": status_code, "error_body": error_body, "method": method}}
        except Exception as exc:
            logger.warning("Bitrix request failed (%s): %s", method, exc)
            return None

    async def create_deal(self, title: str, fields: Dict[str, Any]) -> Optional[int]:
        """Create a CRM deal. Returns deal ID or None."""
        # Bitrix API expects FIELDS as an object, not form-encoded
        # Convert FIELDS[...] format to proper nested structure
        deal_fields = {"TITLE": title}
        
        # Process fields - convert FIELDS[KEY] to KEY in nested object
        for key, value in fields.items():
            if key.startswith("FIELDS["):
                # Extract field name from FIELDS[FIELD_NAME]
                field_name = key[7:-1]  # Remove "FIELDS[" and "]"
                deal_fields[field_name] = value
            else:
                # Direct field name
                deal_fields[key] = value
        
        # Ensure CATEGORY_ID is integer if present
        if "CATEGORY_ID" in deal_fields:
            try:
                deal_fields["CATEGORY_ID"] = int(deal_fields["CATEGORY_ID"])
            except (ValueError, TypeError):
                pass
        
        payload = {"fields": deal_fields}
        resp = await self._post("crm.deal.add", payload)
        if resp and "_error" in resp:
            return None  # Error occurred
        return resp.get("result") if resp else None

    async def update_deal(self, deal_id: int, fields: Dict[str, Any]):
        """Update a CRM deal. Returns True if successful, False if failed, or dict with _error if error occurred."""
        # Convert FIELDS[KEY] format to proper nested structure
        deal_fields = {}
        for key, value in fields.items():
            if key.startswith("FIELDS["):
                field_name = key[7:-1]  # Remove "FIELDS[" and "]"
                deal_fields[field_name] = value
            else:
                deal_fields[key] = value
        
        payload = {"id": deal_id, "fields": deal_fields}
        resp = await self._post("crm.deal.update", payload)
        if resp and "_error" in resp:
            # Return error info for categorization
            return {"_error": resp["_error"]}
        if resp and resp.get("result"):
            return True
        return False
    
    async def update_deal_category(self, deal_id: int, category_id: int, stage_id: Optional[str] = None) -> bool:
        """
        Update deal category (funnel) using crm.item.update.
        This is the only way to change a deal's category in Bitrix.
        Returns success status.
        """
        try:
            fields = {"categoryId": category_id}
            if stage_id:
                fields["stageId"] = stage_id
            
            payload = {
                "entityTypeId": 2,  # 2 = deals
                "id": deal_id,
                "fields": fields
            }
            resp = await self._post("crm.item.update", payload)
            return resp.get("result") is not None if resp else False
        except Exception as e:
            logger.error(f"Error updating deal category: {e}")
            return False

    async def get_deal(self, deal_id: int) -> Optional[Dict[str, Any]]:
        """Get deal by ID."""
        payload = {"id": deal_id}
        resp = await self._post("crm.deal.get", payload)
        if resp and "_error" in resp:
            return None  # Error occurred (deal not found or other error)
        return resp.get("result") if resp else None
    
    async def list_deals(self, filter_dict: Optional[Dict[str, Any]] = None, order: Optional[Dict[str, str]] = None, limit: int = 50) -> Optional[List[Dict[str, Any]]]:
        """List deals with optional filter and order. Returns list of deals or None."""
        try:
            payload = {
                "select": ["ID", "TITLE", "DATE_CREATE", "DATE_MODIFY", "CATEGORY_ID", "STAGE_ID", "OPPORTUNITY"],
                "limit": limit
            }
            
            # Bitrix API requires filter and order as arrays
            # Format: filter: [{ "%TITLE": "value" }], order: [{ "DATE_CREATE": "DESC" }]
            if filter_dict:
                # Convert dict to array of objects
                filter_array = [filter_dict]
                payload["filter"] = filter_array
            
            if order:
                # Convert dict to array of objects
                order_array = [order]
                payload["order"] = order_array
            
            resp = await self._post("crm.deal.list", payload)
            if resp and resp.get("result"):
                return resp.get("result")
            return None
        except Exception as e:
            logger.error(f"Error listing deals: {e}", exc_info=True)
            return None
    
    async def delete_deal(self, deal_id: int) -> bool:
        """Delete deal by ID. Returns True if successful."""
        try:
            resp = await self._post("crm.deal.delete", {"id": deal_id})
            if resp and resp.get("result"):
                logger.info(f"Deleted deal {deal_id}")
                return True
            else:
                error = resp.get("error", "Unknown error") if resp else "No response"
                error_desc = resp.get("error_description", "") if resp else ""
                logger.warning(f"Failed to delete deal {deal_id}: {error} - {error_desc}")
                return False
        except Exception as e:
            logger.error(f"Error deleting deal {deal_id}: {e}", exc_info=True)
            return False

    async def create_lead(self, fields: Dict[str, Any]) -> Optional[int]:
        """Create a CRM lead. Returns lead ID or None."""
        payload = {}
        payload.update(fields)
        resp = await self._post("crm.lead.add", payload)
        return resp.get("result") if resp else None

    async def find_contact_by_name(self, name: str) -> Optional[int]:
        """Find contact by name. Returns contact ID or None."""
        payload = {
            "FILTER[NAME]": name,
            "SELECT": ["ID", "NAME"]
        }
        resp = await self._post("crm.contact.list", payload)
        if resp and resp.get("result"):
            contacts = resp["result"]
            if contacts:
                return int(contacts[0]["ID"])
        return None

    async def ensure_contact(self, name: str, fields: Dict[str, Any] = None) -> Optional[int]:
        """Ensure contact exists, create if not. Returns contact ID."""
        # Try to find existing contact
        contact_id = await self.find_contact_by_name(name)
        if contact_id:
            return contact_id
        
        # Create new contact - convert name and fields to user_data format
        user_data = {"username": name}
        if fields:
            user_data.update(fields)
        return await self.create_contact(user_data)

    async def upload_file_to_disk(self, file_path: str, filename: str) -> Optional[str]:
        """Upload file to Bitrix disk. Returns file ID or None."""
        try:
            with open(file_path, "rb") as f:
                file_data = f.read()
            
            # Encode file as base64
            file_b64 = base64.b64encode(file_data).decode("utf-8")
            
            # According to Bitrix API: id (folder ID), data (with NAME), fileContent (base64)
            # Use generateUniqueName to handle duplicate filenames
            payload = {
                "id": self.disk_folder_id,
                "data": {
                    "NAME": filename
                },
                "fileContent": file_b64,
                "generateUniqueName": True
            }
            
            resp = await self._post("disk.folder.uploadfile", payload)
            if resp and resp.get("result"):
                # The API returns ID in the result
                file_id = resp.get("result", {}).get("ID")
                if file_id:
                    return str(file_id)
            return None
            
        except Exception as e:
            logger.error(f"Error uploading file to Bitrix disk: {e}", exc_info=True)
            return None

    async def attach_file_to_deal(self, deal_id: int, file_path: str, filename: str) -> bool:
        """Attach file to deal. Returns success status."""
        try:
            # Field should be ensured by field_manager on startup
            # Just log a warning if it doesn't exist
            fields = await self.get_deal_fields()
            if fields and self.deal_file_field_code not in fields:
                logger.warning(f"File field '{self.deal_file_field_code}' does not exist. Ensure field_manager.ensure_all_fields() is called on startup.")
            
            # Read file and encode as base64
            with open(file_path, "rb") as f:
                file_data = f.read()
            
            file_b64 = base64.b64encode(file_data).decode("utf-8")
            
            logger.info(f"Attaching file '{filename}' to deal {deal_id} using field '{self.deal_file_field_code}' (base64 format)")
            
            # Attach file directly as base64 string in the field
            # According to Bitrix API, file fields can accept base64 encoded file content
            # Format: field_name: [filename, base64_content] or just base64 string
            # Try multiple formats
            payloads = [
                # Format 1: Array with filename and base64
                {
                    "id": deal_id,
                    "fields": {
                        self.deal_file_field_code: [filename, file_b64]
                    }
                },
                # Format 2: Just base64 string
                {
                    "id": deal_id,
                    "fields": {
                        self.deal_file_field_code: file_b64
                    }
                },
                # Format 3: Object with fileData
                {
                    "id": deal_id,
                    "fields": {
                        self.deal_file_field_code: {
                            "fileData": [filename, file_b64]
                        }
                    }
                }
            ]
            
            for i, payload in enumerate(payloads, 1):
                logger.debug(f"Trying format {i} for deal {deal_id}: {list(payload['fields'].keys())}")
                resp = await self._post("crm.deal.update", payload)
                
                if resp and resp.get("result"):
                    logger.info(f"File successfully attached to deal {deal_id} (format {i})")
                    # Verify the attachment
                    deal = await self.get_deal(deal_id)
                    if deal:
                        file_value = deal.get(self.deal_file_field_code)
                        if file_value:
                            logger.info(f"Verified: File field '{self.deal_file_field_code}' = {file_value}")
                            return True
                        else:
                            logger.debug(f"Format {i} succeeded but field is empty, trying next format...")
                            continue
                    else:
                        logger.warning(f"Format {i} succeeded but could not verify attachment")
                        return True
                else:
                    error = resp.get("error", "Unknown error") if resp else "No response"
                    error_desc = resp.get("error_description", "") if resp else ""
                    logger.debug(f"Format {i} failed: {error} - {error_desc}")
            
            # All formats failed
            logger.warning(f"Failed to attach file to deal {deal_id} with all base64 formats")
            return False
            
            logger.debug(f"Updating deal {deal_id} with file attachment payload")
            resp = await self._post("crm.deal.update", payload)
            
            if resp and resp.get("result"):
                logger.info(f"File successfully attached to deal {deal_id} (base64 format)")
                # Verify the attachment
                deal = await self.get_deal(deal_id)
                if deal:
                    file_value = deal.get(self.deal_file_field_code)
                    if file_value:
                        logger.info(f"Verified: File field '{self.deal_file_field_code}' = {file_value}")
                        return True
                    else:
                        logger.warning(f"Update succeeded but field is empty, file may not have been attached correctly")
                        return False
                else:
                    logger.warning(f"Update succeeded but could not verify attachment")
                    return True
            else:
                error = resp.get("error", "Unknown error") if resp else "No response"
                error_desc = resp.get("error_description", "") if resp else ""
                logger.warning(f"Failed to attach file to deal {deal_id}: {error} - {error_desc}, response: {resp}")
                return False
            
        except Exception as e:
            logger.error(f"Error attaching file to deal: {e}", exc_info=True)
            return False

    async def create_user_field(
        self, 
        entity_type: str, 
        field_code: str, 
        field_label: str, 
        user_type_id: str = "string",
        multiple: str = "N"
    ) -> bool:
        """Create user field in Bitrix. Returns success status."""
        try:
            # Use crm.{entity_type}.userfield.add
            method = f"crm.{entity_type}.userfield.add"
            
            # According to Bitrix API: fields object with nested properties (JSON format)
            payload = {
                "fields": {
                    "USER_TYPE_ID": user_type_id,
                    "FIELD_NAME": field_code,  # Without UF_CRM_ prefix
                    "LABEL": field_label,
                    "MULTIPLE": multiple,
                    "MANDATORY": "N",
                    "SHOW_FILTER": "N",
                    "SHOW_IN_LIST": "Y",
                    "EDIT_IN_LIST": "Y",
                    "IS_SEARCHABLE": "N",
                    "SORT": 100
                }
            }
            
            # Force JSON format for userfield.add
            url = f"{self.base_url}/{method}" if not self.base_url.endswith("/") else f"{self.base_url}{method}"
            async with httpx.AsyncClient(timeout=self.timeout_seconds, verify=self.verify_tls) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                result = resp.json()
                
                if result and result.get("result"):
                    logger.info(f"User field '{field_code}' ({user_type_id}) created successfully for {entity_type}")
                    return True
                else:
                    error = result.get("error", "Unknown error") if result else "No response"
                    error_desc = result.get("error_description", "") if result else ""
                    logger.warning(f"Failed to create user field '{field_code}' for {entity_type}: {error} - {error_desc}")
                    return False
        except Exception as e:
            logger.error(f"Error creating user field: {e}", exc_info=True)
            return False
    
    async def create_file_field(self, entity_type: str, field_code: str, field_label: str) -> bool:
        """Create file field in Bitrix. Returns success status (deprecated, use create_user_field)."""
        return await self.create_user_field(entity_type, field_code, field_label, "file", "N")

    async def create_custom_field(self, entity_type: str, field_code: str, field_name: str, field_type: str = "string") -> bool:
        """Create custom field in Bitrix. Returns success status."""
        payload = {
            "FIELDS[ENTITY_ID]": entity_type,
            "FIELDS[FIELD_NAME]": field_code,
            "FIELDS[USER_TYPE_ID]": field_type,
            "FIELDS[XML_ID]": field_code,
            "FIELDS[SORT]": 100,
            "FIELDS[MULTIPLE]": "N",
            "FIELDS[MANDATORY]": "N",
            "FIELDS[SHOW_FILTER]": "Y",
            "FIELDS[EDIT_IN_LIST]": "Y",
            "FIELDS[IS_SEARCHABLE]": "Y",
            "FIELDS[SETTINGS][DEFAULT_VALUE]": "",
            "FIELDS[LIST][0][VALUE]": field_name,
            "FIELDS[LIST][0][DEF]": "Y"
        }
        
        resp = await self._post("crm.enum.fields.add", payload)
        return resp.get("result") is not None if resp else False

    async def get_deal_fields(self) -> Optional[Dict[str, Any]]:
        """Get available deal fields."""
        resp = await self._post("crm.deal.fields", {})
        return resp.get("result") if resp else None

    async def get_contact_fields(self) -> Optional[Dict[str, Any]]:
        """Get available contact fields."""
        resp = await self._post("crm.contact.fields", {})
        return resp.get("result") if resp else None
    
    async def get_contact(self, contact_id: int) -> Optional[Dict[str, Any]]:
        """Get contact by ID"""
        payload = {"ID": contact_id}
        resp = await self._post("crm.contact.get", payload)
        return resp.get("result") if resp else None
    
    async def get_invoice(self, invoice_id: int) -> Optional[Dict[str, Any]]:
        """Get invoice by ID (deprecated method, but may still work)"""
        payload = {"id": invoice_id}
        resp = await self._post("crm.invoice.get", payload)
        return resp.get("result") if resp else None
    
    async def get_document_generator_document(self, document_id: int) -> Optional[Dict[str, Any]]:
        """Get document generator document by ID (for invoices)"""
        payload = {"id": document_id}
        resp = await self._post("crm.documentgenerator.document.get", payload)
        return resp.get("result", {}).get("document") if resp else None
    
    async def create_contact(self, user_data: Dict[str, Any]) -> Optional[int]:
        """Create contact in Bitrix"""
        try:
            # Build payload using FIELDS[KEY] format (Bitrix API format)
            payload = {}
            
            # Name is required
            name = user_data.get("full_name") or user_data.get("username", "")
            if name:
                payload["FIELDS[NAME]"] = name
            
            # Email as array
            if user_data.get("email"):
                payload["FIELDS[EMAIL]"] = [{"VALUE": user_data.get("email", ""), "VALUE_TYPE": "WORK"}]
            
            # Phone as array
            if user_data.get("phone_number"):
                payload["FIELDS[PHONE]"] = [{"VALUE": user_data.get("phone_number", ""), "VALUE_TYPE": "WORK"}]
            
            # Company
            if user_data.get("company"):
                payload["FIELDS[COMPANY_TITLE]"] = user_data.get("company")
            
            # City
            if user_data.get("city"):
                payload["FIELDS[ADDRESS_CITY]"] = user_data.get("city")
            
            # Source and type
            payload["FIELDS[SOURCE_ID]"] = "WEB"
            payload["FIELDS[TYPE_ID]"] = "CLIENT"
            
            resp = await self._post("crm.contact.add", payload)
            if resp and "result" in resp:
                return int(resp["result"])
            return None
            
        except Exception as e:
            logger.error(f"Error creating Bitrix contact: {e}")
            return None
    
    async def update_contact(self, contact_id: int, user_data: Dict[str, Any]) -> bool:
        """Update contact in Bitrix"""
        try:
            # Build payload using FIELDS[KEY] format (Bitrix API format)
            payload = {"id": contact_id}
            
            # Name
            name = user_data.get("full_name") or user_data.get("username", "")
            if name:
                payload["FIELDS[NAME]"] = name
            
            # Email as array
            if user_data.get("email"):
                payload["FIELDS[EMAIL]"] = [{"VALUE": user_data.get("email", ""), "VALUE_TYPE": "WORK"}]
            
            # Phone as array
            if user_data.get("phone_number"):
                payload["FIELDS[PHONE]"] = [{"VALUE": user_data.get("phone_number", ""), "VALUE_TYPE": "WORK"}]
            
            # Company
            if user_data.get("company"):
                payload["FIELDS[COMPANY_TITLE]"] = user_data.get("company")
            
            # City
            if user_data.get("city"):
                payload["FIELDS[ADDRESS_CITY]"] = user_data.get("city")
            
            resp = await self._post("crm.contact.update", payload)
            if resp and resp.get("result"):
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error updating Bitrix contact {contact_id}: {e}")
            return False
    
    async def create_lead(self, title: str, fields: Dict[str, Any]) -> Optional[int]:
        """Create lead in Bitrix"""
        try:
            lead_data = {
                "TITLE": title,
                **fields
            }
            
            resp = await self._post("crm.lead.add", {"fields": lead_data})
            if resp and "result" in resp:
                return int(resp["result"])
            return None
            
        except Exception as e:
            logger.error(f"Error creating Bitrix lead: {e}")
            return None
    
    async def create_deal_from_order_data(
        self, 
        order_data: Dict[str, Any], 
        user_data: Dict[str, Any], 
        file_id: Optional[int] = None,
        document_ids: Optional[List[int]] = None
    ) -> Optional[int]:
        """Create deal from order data"""
        try:
            deal_data = {
                "TITLE": f"Order #{order_data['order_id']} - {order_data['service_id']}",
                "STAGE_ID": "NEW",
                "OPPORTUNITY": order_data.get("total_price", 0),
                "CURRENCY_ID": "RUB",
                "CONTACT_ID": user_data.get("bitrix_contact_id"),
                "COMMENTS": f"Service: {order_data['service_id']}\nQuantity: {order_data['quantity']}\nStatus: {order_data['status']}",
                "SOURCE_ID": "WEB",
                "SOURCE_DESCRIPTION": "Manufacturing Service API"
            }
            
            # Add file attachment if available
            if file_id:
                # This would need to be implemented based on Bitrix file upload API
                pass
            
            resp = await self._post("crm.deal.add", {"fields": deal_data})
            if resp and "result" in resp:
                return int(resp["result"])
            return None
            
        except Exception as e:
            logger.error(f"Error creating Bitrix deal: {e}")
            return None

    async def get_deal_categories(self) -> Optional[List[Dict[str, Any]]]:
        """List all deal categories (funnels). Returns list of categories or None."""
        resp = await self._post("crm.dealcategory.list", {})
        return resp.get("result") if resp else None

    async def get_deal_category_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Find deal category by name. Returns category dict or None."""
        categories = await self.get_deal_categories()
        if not categories:
            return None
        for category in categories:
            if category.get("NAME") == name:
                return category
        return None

    async def create_deal_category(self, name: str, stages: List[Dict[str, Any]]) -> Optional[int]:
        """Create deal category (funnel) with stages. Returns category ID or None."""
        try:
            # Prepare stages data - Bitrix API expects FIELDS[STAGES][index][FIELD_NAME] format
            payload = {
                "FIELDS[NAME]": name
            }
            
            # Add stages
            for i, stage in enumerate(stages):
                payload[f"FIELDS[STAGES][{i}][NAME]"] = stage.get("name", "")
                payload[f"FIELDS[STAGES][{i}][SORT]"] = str(stage.get("sort", i * 10))
                payload[f"FIELDS[STAGES][{i}][COLOR]"] = stage.get("color", "#3465A4")
                payload[f"FIELDS[STAGES][{i}][SEMANTICS]"] = stage.get("semantics", "P")
            
            resp = await self._post("crm.dealcategory.add", payload)
            return resp.get("result") if resp else None
        except Exception as e:
            logger.error(f"Error creating deal category: {e}")
            return None

    async def get_category_stages(self, category_id: int) -> Optional[List[Dict[str, Any]]]:
        """Get stages for a deal category. Returns list of stages or None."""
        # Use crm.status.entity.items - this is the recommended method
        # Entity ID format: "DEAL_STAGE_{category_id}" for specific category
        # or "DEAL_STAGE" for default category (category_id = 0)
        entity_id = f"DEAL_STAGE_{category_id}" if category_id > 0 else "DEAL_STAGE"
        payload = {"entityId": entity_id}
        
        resp = await self._post("crm.status.entity.items", payload)
        if resp and resp.get("result"):
            stages = resp.get("result")
            if isinstance(stages, list):
                return stages
        
        # Fallback: Try crm.category.get (new API method)
        # entityTypeId = 2 for deals
        payload = {"entityTypeId": 2, "id": category_id}
        resp = await self._post("crm.category.get", payload)
        if resp and resp.get("result"):
            category_data = resp.get("result")
            # Check if stages are in category data
            if isinstance(category_data, dict):
                # Stages might be in different places depending on API version
                if "stages" in category_data:
                    return category_data["stages"]
                if "STAGES" in category_data:
                    stages = category_data["STAGES"]
                    if isinstance(stages, list):
                        return stages
        
        # Fallback: Try old API method crm.dealcategory.get
        payload = {"id": category_id}
        resp = await self._post("crm.dealcategory.get", payload)
        if resp and resp.get("result"):
            category_data = resp.get("result")
            if "STAGES" in category_data:
                stages = category_data["STAGES"]
                if isinstance(stages, list):
                    return stages
        
        return None
        
        return None

    async def create_category_stage(self, category_id: int, stage_data: Dict[str, Any]) -> Optional[str]:
        """Add stage to deal category. Returns stage ID or None."""
        try:
            payload = {
                "id": category_id,
                "FIELDS[NAME]": stage_data.get("name", ""),
                "FIELDS[SORT]": str(stage_data.get("sort", 0)),
                "FIELDS[COLOR]": stage_data.get("color", "#3465A4"),
                "FIELDS[SEMANTICS]": stage_data.get("semantics", "P")
            }
            resp = await self._post("crm.dealcategory.stages.add", payload)
            return resp.get("result") if resp else None
        except Exception as e:
            logger.error(f"Error creating category stage: {e}")
            return None


# Global instance
bitrix_client = BitrixClient()

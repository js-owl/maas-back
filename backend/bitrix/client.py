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
            logger.error(
                f"Bitrix HTTP error for {method}: {exc.response.status_code if exc.response else 'Unknown'}, "
                f"Response: {error_body[:200]}"
            )
            return None
        except Exception as exc:
            logger.warning("Bitrix request failed (%s): %s", method, exc)
            return None

    async def create_deal(self, title: str, fields: Dict[str, Any]) -> Optional[int]:
        """Create a CRM deal. Returns deal ID or None."""
        payload = {
            "FIELDS[TITLE]": title,
        }
        payload.update(fields)
        resp = await self._post("crm.deal.add", payload)
        return resp.get("result") if resp else None

    async def update_deal(self, deal_id: int, fields: Dict[str, Any]) -> bool:
        """Update a CRM deal. Returns success status."""
        payload = {"ID": deal_id}
        payload.update(fields)
        resp = await self._post("crm.deal.update", payload)
        return resp.get("result") is not None if resp else False

    async def get_deal(self, deal_id: int) -> Optional[Dict[str, Any]]:
        """Get deal by ID."""
        payload = {"ID": deal_id}
        resp = await self._post("crm.deal.get", payload)
        return resp.get("result") if resp else None


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
            
            payload = {
                "FOLDER_ID": self.disk_folder_id,
                "NAME": filename,
                "FILE_CONTENT": file_b64
            }
            
            resp = await self._post("disk.folder.uploadfile", payload)
            return resp.get("result", {}).get("ID") if resp else None
            
        except Exception as e:
            logger.error(f"Error uploading file to Bitrix disk: {e}")
            return None

    async def attach_file_to_deal(self, deal_id: int, file_path: str, filename: str) -> bool:
        """Attach file to deal. Returns success status."""
        try:
            # Upload file to disk
            file_id = await self.upload_file_to_disk(file_path, filename)
            if not file_id:
                return False
            
            # Attach file to deal
            payload = {
                "ID": deal_id,
                f"FIELDS[{self.deal_file_field_code}]": file_id
            }
            
            resp = await self._post("crm.deal.update", payload)
            return resp.get("result") is not None if resp else False
            
        except Exception as e:
            logger.error(f"Error attaching file to deal: {e}")
            return False

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


# Global instance
bitrix_client = BitrixClient()

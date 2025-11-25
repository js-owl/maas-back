"""
Bitrix Field Manager
Ensures all required user fields exist in Bitrix
"""
from typing import Optional, Dict, Any, List
from backend.bitrix.client import bitrix_client
from backend.utils.logging import get_logger

logger = get_logger(__name__)


class BitrixFieldManager:
    """Manages required Bitrix user fields"""
    
    def __init__(self):
        self.initialized = False
        self.required_fields = {
            "deal": [
                {
                    "field_code": "MODEL_FILE",
                    "field_label": "Model File",
                    "user_type_id": "file",
                    "multiple": "N"
                }
            ],
            "contact": [
                {
                    "field_code": "APP_USER_ID",
                    "field_label": "App User ID",
                    "user_type_id": "string",
                    "multiple": "N"
                },
                {
                    "field_code": "APP_IS_ADMIN",
                    "field_label": "App Is Admin",
                    "user_type_id": "string",
                    "multiple": "N"
                }
            ]
        }
    
    async def ensure_all_fields(self) -> bool:
        """
        Ensure all required user fields exist, create if not.
        Returns True if successful, False otherwise.
        """
        try:
            if not bitrix_client.is_configured():
                logger.warning("Bitrix not configured, skipping field initialization")
                return False
            
            if not bitrix_client.autocreate_fields:
                logger.info("Field auto-creation disabled, skipping field initialization")
                return False
            
            logger.info("Ensuring all required Bitrix user fields exist...")
            
            # Ensure deal fields
            deal_success = await self._ensure_entity_fields("deal", self.required_fields["deal"])
            
            # Ensure contact fields
            contact_success = await self._ensure_entity_fields("contact", self.required_fields["contact"])
            
            if deal_success and contact_success:
                self.initialized = True
                logger.info("All required Bitrix user fields ensured")
                return True
            else:
                logger.warning("Some fields may not have been created successfully")
                return False
                
        except Exception as e:
            logger.error(f"Error ensuring Bitrix fields: {e}", exc_info=True)
            return False
    
    async def _ensure_entity_fields(self, entity_type: str, fields: List[Dict[str, Any]]) -> bool:
        """Ensure fields for a specific entity type exist"""
        try:
            # Get existing fields
            if entity_type == "deal":
                existing_fields = await bitrix_client.get_deal_fields()
            elif entity_type == "contact":
                existing_fields = await bitrix_client.get_contact_fields()
            else:
                logger.error(f"Unknown entity type: {entity_type}")
                return False
            
            if not existing_fields:
                logger.warning(f"Could not retrieve {entity_type} fields from Bitrix")
                return False
            
            all_success = True
            for field_def in fields:
                field_code = f"UF_CRM_{field_def['field_code']}"
                
                if field_code in existing_fields:
                    logger.debug(f"Field '{field_code}' already exists for {entity_type}")
                    continue
                
                # Field doesn't exist, create it
                logger.info(f"Creating field '{field_code}' for {entity_type}...")
                success = await bitrix_client.create_user_field(
                    entity_type=entity_type,
                    field_code=field_def["field_code"],
                    field_label=field_def["field_label"],
                    user_type_id=field_def["user_type_id"],
                    multiple=field_def.get("multiple", "N")
                )
                
                if success:
                    logger.info(f"Successfully created field '{field_code}' for {entity_type}")
                else:
                    logger.warning(f"Failed to create field '{field_code}' for {entity_type}")
                    all_success = False
            
            return all_success
            
        except Exception as e:
            logger.error(f"Error ensuring {entity_type} fields: {e}", exc_info=True)
            return False
    
    def is_initialized(self) -> bool:
        return self.initialized


# Global field manager instance
field_manager = BitrixFieldManager()


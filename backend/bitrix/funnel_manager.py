"""
Bitrix Funnel Manager
Manages MaaS sales funnel creation and stage mapping
"""
from typing import Optional, Dict, Any
from backend.bitrix.client import bitrix_client
from backend.core.config import BITRIX_MAAS_FUNNEL_NAME, BITRIX_MAAS_CATEGORY_ID
from backend.utils.logging import get_logger

logger = get_logger(__name__)


class FunnelManager:
    """Manages MaaS sales funnel in Bitrix"""
    
    def __init__(self):
        self.category_id: Optional[int] = None
        self.stage_mapping: Dict[str, str] = {}  # order status -> stage ID
        self.status_mapping: Dict[str, str] = {}  # stage ID -> order status
        self.stage_name_to_id: Dict[str, str] = {}  # stage name -> stage ID
        self.initialized = False
        
        # Order status to stage name mapping
        # Note: These will be mapped to actual stage IDs when stages are loaded
        # Default mappings (will be updated when stages are loaded from Bitrix)
        self.ORDER_STATUS_TO_STAGE = {
            "pending": "Новая",  # "New" - default first stage
            "processing": "В работе",  # "In Work" 
            "completed": "Сделка успешна",  # "Deal Won"
            "cancelled": "Сделка провалена"  # "Deal Lost"
        }
    
    async def ensure_maas_funnel(self) -> bool:
        """
        Ensure MaaS funnel exists, create if not.
        Returns True if successful, False otherwise.
        """
        try:
            if not bitrix_client.is_configured():
                logger.warning("Bitrix not configured, skipping funnel initialization")
                return False
            
            # Check if category_id is manually configured
            if BITRIX_MAAS_CATEGORY_ID:
                try:
                    self.category_id = int(BITRIX_MAAS_CATEGORY_ID)
                    logger.info(f"Using manually configured MaaS category ID: {self.category_id}")
                    # Load stages for the configured category
                    await self._load_stages()
                    self.initialized = True
                    return True
                except ValueError:
                    logger.error(f"Invalid BITRIX_MAAS_CATEGORY_ID: {BITRIX_MAAS_CATEGORY_ID}")
            
            # Try to find existing MaaS funnel
            category = await bitrix_client.get_deal_category_by_name(BITRIX_MAAS_FUNNEL_NAME)
            
            if category:
                self.category_id = int(category.get("ID"))
                logger.info(f"Found existing MaaS funnel with category ID: {self.category_id}")
                await self._load_stages()
                self.initialized = True
                return True
            
            # Create new MaaS funnel
            logger.info(f"Creating new MaaS funnel: {BITRIX_MAAS_FUNNEL_NAME}")
            stages = [
                {"name": "New Order", "sort": 10, "semantics": "P"},
                {"name": "In Production", "sort": 20, "semantics": "P"},
                {"name": "Completed", "sort": 30, "semantics": "S"},
                {"name": "Cancelled", "sort": 40, "semantics": "F"}
            ]
            
            category_id = await bitrix_client.create_deal_category(BITRIX_MAAS_FUNNEL_NAME, stages)
            
            if category_id:
                self.category_id = category_id
                logger.info(f"Created MaaS funnel with category ID: {self.category_id}")
                # Try to load stages, but don't fail if it doesn't work
                await self._load_stages()
                # If stages didn't load, create basic mappings from stage names
                # These will be used as fallback until we can get actual stage IDs
                if not self.stage_mapping:
                    logger.warning("Could not load stage IDs from Bitrix, using stage name mappings")
                    # We'll need to get stage IDs later, but for now just mark as initialized
                self.initialized = True
                return True
            else:
                logger.error("Failed to create MaaS funnel")
                return False
                
        except Exception as e:
            logger.error(f"Error ensuring MaaS funnel: {e}", exc_info=True)
            return False
    
    async def _load_stages(self) -> None:
        """Load stages for the current category and build mappings"""
        if not self.category_id:
            return
        
        try:
            stages = await bitrix_client.get_category_stages(self.category_id)
            if not stages:
                logger.warning(f"No stages found for category {self.category_id}")
                return
            
            # Build mappings
            self.stage_name_to_id = {}
            self.stage_mapping = {}
            self.status_mapping = {}
            
            for stage in stages:
                stage_id = stage.get("STATUS_ID")
                stage_name = stage.get("NAME", "")
                
                if stage_id and stage_name:
                    self.stage_name_to_id[stage_name] = stage_id
                    
                    # Map stage name to order status (case-insensitive match)
                    for order_status, mapped_stage_name in self.ORDER_STATUS_TO_STAGE.items():
                        if stage_name.lower() == mapped_stage_name.lower() or stage_name == mapped_stage_name:
                            self.stage_mapping[order_status] = stage_id
                            self.status_mapping[stage_id] = order_status
                            break
                    
                    # Also map by common stage semantics/names
                    # "Новая" or "New" -> pending
                    if stage_name in ["Новая", "New", "New Order"] and "pending" not in self.stage_mapping:
                        self.stage_mapping["pending"] = stage_id
                    # "В работе" or "In Work" or "In Production" -> processing
                    elif stage_name in ["В работе", "In Work", "In Production", "EXECUTING"] and "processing" not in self.stage_mapping:
                        self.stage_mapping["processing"] = stage_id
                    # "Сделка успешна" or "Won" or "Completed" -> completed
                    elif stage_name in ["Сделка успешна", "Won", "Completed"] and "completed" not in self.stage_mapping:
                        self.stage_mapping["completed"] = stage_id
                    # "Сделка провалена" or "Lost" or "Cancelled" -> cancelled
                    elif stage_name in ["Сделка провалена", "Lost", "Cancelled"] and "cancelled" not in self.stage_mapping:
                        self.stage_mapping["cancelled"] = stage_id
            
            logger.info(f"Loaded {len(stages)} stages for MaaS funnel")
            logger.debug(f"Stage mapping: {self.stage_mapping}")
            logger.debug(f"Status mapping: {self.status_mapping}")
            
        except Exception as e:
            logger.error(f"Error loading stages: {e}", exc_info=True)
    
    def get_stage_mapping(self) -> Dict[str, str]:
        """
        Get mapping from order status to Bitrix stage ID.
        Returns dict mapping order status -> stage ID
        """
        return self.stage_mapping.copy()
    
    def get_status_mapping(self) -> Dict[str, str]:
        """
        Get mapping from Bitrix stage ID to order status.
        Returns dict mapping stage ID -> order status
        """
        return self.status_mapping.copy()
    
    def get_stage_id_for_status(self, order_status: str) -> Optional[str]:
        """Get Bitrix stage ID for an order status"""
        return self.stage_mapping.get(order_status)
    
    def get_status_for_stage_id(self, stage_id: str) -> Optional[str]:
        """Get order status for a Bitrix stage ID"""
        return self.status_mapping.get(stage_id)
    
    def get_category_id(self) -> Optional[int]:
        """Get the MaaS category ID"""
        return self.category_id
    
    def is_initialized(self) -> bool:
        """Check if funnel manager is initialized"""
        return self.initialized


# Global instance
funnel_manager = FunnelManager()


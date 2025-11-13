"""
Calculation routing utility
"""

import logging
from typing import Dict, Any, Optional

# Import calculators lazily to avoid circular imports
from models.calculation_models import (
    PrintingCalculationRequest,
    CNCMillingCalculationRequest,
    CNCLatheCalculationRequest,
    PaintingCalculationRequest
)
from models.response_models import UnifiedCalculationResponse
from utils.ml_predictor import ml_predictor
from constants import ENABLE_ML_MODELS, ML_FALLBACK_TO_RULES

logger = logging.getLogger(__name__)


class CalculationRouter:
    """Routes calculations to appropriate calculators"""
    
    def __init__(self):
        self.calculators = {}
    
    def _get_calculator(self, service_id: str, use_ml: bool = False):
        """Get calculator lazily to avoid circular imports"""
        calculator_key = f"{service_id}_{'ml' if use_ml else 'rule'}"
        
        if calculator_key not in self.calculators:
            if use_ml and ENABLE_ML_MODELS and ml_predictor.is_model_available():
                # Use ML calculators
                if service_id == "printing":
                    from calculators.ml_calculator import MLPrintingCalculator
                    self.calculators[calculator_key] = MLPrintingCalculator()
                elif service_id == "cnc-milling":
                    from calculators.ml_calculator import MLCNCMillingCalculator
                    self.calculators[calculator_key] = MLCNCMillingCalculator()
                elif service_id == "cnc-lathe":
                    from calculators.ml_calculator import MLCNCLatheCalculator
                    self.calculators[calculator_key] = MLCNCLatheCalculator()
                elif service_id == "painting":
                    from calculators.ml_calculator import MLPaintingCalculator
                    self.calculators[calculator_key] = MLPaintingCalculator()
            else:
                # Use rule-based calculators
                if service_id == "printing":
                    from calculators import PrintingCalculator
                    self.calculators[calculator_key] = PrintingCalculator()
                elif service_id == "cnc-milling":
                    from calculators import CNCMillingCalculator
                    self.calculators[calculator_key] = CNCMillingCalculator()
                elif service_id == "cnc-lathe":
                    from calculators import CNCLatheCalculator
                    self.calculators[calculator_key] = CNCLatheCalculator()
                elif service_id == "painting":
                    from calculators import PaintingCalculator
                    self.calculators[calculator_key] = PaintingCalculator()
        return self.calculators.get(calculator_key)
    
    async def route_calculation(
        self, 
        service_id: str, 
        parameters: Dict[str, Any],
        use_ml: bool = False
    ) -> UnifiedCalculationResponse:
        """
        Route calculation to appropriate calculator
        
        Args:
            service_id: Manufacturing service ID
            parameters: Calculation parameters
            use_ml: Whether to use ML-based calculation
            
        Returns:
            Unified calculation response
        """
        logger.info(f"Routing calculation to service: {service_id} (ML: {use_ml})")
        
        # Get calculator
        calculator = self._get_calculator(service_id, use_ml)
        if not calculator:
            raise ValueError(f"Unknown service ID: {service_id}")
        
        # Create appropriate request object
        request = self._create_request(service_id, parameters, use_ml)
        
        # Perform calculation
        return await calculator.calculate(request)
    
    def should_use_ml(self, parameters: Dict[str, Any]) -> bool:
        """
        Determine if ML calculation should be used
        
        Args:
            parameters: Calculation parameters
            
        Returns:
            True if ML should be used, False otherwise
        """
        # Check if ML is enabled and models are available
        if not ENABLE_ML_MODELS or not ml_predictor.is_model_available():
            return False
        
        # check service type
        service_id = parameters.get('service_id', None)
        if service_id not in ["cnc-milling", "cnc-lathe"]:
            return False
        
        # Check if file features are available
        ml_features = parameters.get('ml_features')
        if not ml_features:
            return False
        
        # Check if we have sufficient features for ML prediction
        required_features = ['volume', 'surface_area', 'obb_x', 'obb_y', 'obb_z']
        has_required_features = all(
            feature in ml_features and ml_features[feature] is not None 
            for feature in required_features
        )
        
        if not has_required_features:
            logger.warning("Insufficient features for ML prediction, falling back to rule-based")
            return False
        
        return True
    
    def _create_request(self, service_id: str, parameters: Dict[str, Any], use_ml: bool = False):
        """Create appropriate request object based on service ID"""
        file_id = parameters.get("file_id", "unknown")
        
        # Add ML features if using ML calculation
        if use_ml:
            ml_features = parameters.get('ml_features', {})
            # Add ML features to all request types
            base_params = {
                'file_id': file_id,
                'ml_features': ml_features,
                'filename': parameters.get('filename'),
                'location': parameters.get('location', 'location_1'),
                'material_id': parameters.get('material_id'),
                'material_form': parameters.get('material_form'),
                'quantity': parameters.get('quantity', 1),
                'cover_id': parameters.get('cover_id', ['1']),
                'k_otk': parameters.get('k_otk', 1.0),
                'service_id': service_id,
                'obb_x': parameters.get('obb_x'),
                'obb_y': parameters.get('obb_y'),
                'obb_z': parameters.get('obb_z')
            }
            
            if service_id == "printing":
                return type('MLPrintingRequest', (), base_params)()
            elif service_id == "cnc-milling":
                return type('MLCNCMillingRequest', (), base_params)()
            elif service_id == "cnc-lathe":
                return type('MLCNCLatheRequest', (), base_params)()
            elif service_id == "painting":
                return type('MLPaintingRequest', (), base_params)()
        
        if service_id == "printing":
            return PrintingCalculationRequest(
                file_id=file_id,
                dimensions=parameters["dimensions"],
                material_id=parameters["material_id"],
                material_form=parameters["material_form"],
                quantity=parameters["quantity"],
                cover_id=parameters["cover_id"],
                location=parameters["location"],
                n_dimensions=parameters["n_dimensions"],
                k_type=parameters["k_type"],
                k_process=parameters["k_process"],
                k_otk=parameters["k_otk"],
                k_cert=parameters["k_cert"],
                service_id=service_id
            )
        elif service_id == "cnc-milling":
            return CNCMillingCalculationRequest(
                file_id=file_id,
                dimensions=parameters["dimensions"],
                material_id=parameters["material_id"],
                material_form=parameters["material_form"],
                quantity=parameters["quantity"],
                cover_id=parameters["cover_id"],
                tolerance_id=parameters["tolerance_id"],
                finish_id=parameters["finish_id"],
                location=parameters["location"],
                k_otk=parameters["k_otk"],
                cnc_complexity=parameters["cnc_complexity"],
                cnc_setup_time=parameters["cnc_setup_time"]
            )
        elif service_id == "cnc-lathe":
            return CNCLatheCalculationRequest(
                file_id=file_id,
                dimensions=parameters["dimensions"],
                material_id=parameters["material_id"],
                material_form=parameters["material_form"],
                quantity=parameters["quantity"],
                cover_id=parameters["cover_id"],
                tolerance_id=parameters["tolerance_id"],
                finish_id=parameters["finish_id"],
                location=parameters["location"],
                k_otk=parameters["k_otk"],
                cnc_complexity=parameters["cnc_complexity"],
                cnc_setup_time=parameters["cnc_setup_time"]
            )
        elif service_id == "painting":
            return PaintingCalculationRequest(
                file_id=file_id,
                dimensions=parameters["dimensions"],
                material_id=parameters["material_id"],
                material_form=parameters["material_form"],
                quantity=parameters["quantity"],
                cover_id=parameters["cover_id"],
                tolerance_id=parameters["tolerance_id"],
                finish_id=parameters["finish_id"],
                location=parameters["location"],
                k_otk=parameters["k_otk"],
                paint_type=parameters.get("paint_type", "epoxy"),
                paint_prepare=parameters.get("paint_prepare", "a"),
                paint_primer=parameters.get("paint_primer", "b"),
                paint_lakery=parameters.get("paint_lakery", "a"),
                control_type=parameters.get("control_type", "1"),
                k_cert=parameters.get("k_cert", [])
            )
        else:
            raise ValueError(f"Unknown service ID: {service_id}")






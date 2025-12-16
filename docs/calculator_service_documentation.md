# Calculator Service Documentation

## Overview

The Manufacturing Calculation API v3.3.0 (running on port 7000) provides comprehensive manufacturing cost calculations with **automatic parameter extraction from CAD files** and **Machine Learning (ML) model integration** for intelligent price prediction.

## Key Features

### 🤖 Machine Learning Integration
- **Intelligent Price Prediction**: ML models trained on historical manufacturing data
- **Automatic Feature Extraction**: Comprehensive geometric analysis from STL/STP files
- **Smart Fallback**: Graceful degradation to rule-based calculations when ML features insufficient
- **Multi-Process Support**: ML models work across all manufacturing processes

### 🔄 Dual Calculation Engine
- **ML-Based Calculation**: Uses trained models when sufficient features are available
- **Rule-Based Calculation**: Fallback to traditional calculation methods
- **Automatic Selection**: System automatically chooses the best calculation method

## API Endpoints

### Main Calculation Endpoint
**POST** `/calculate-price`

Unified endpoint for all manufacturing calculations including:
- 3D Printing (`printing`)
- CNC Milling (`cnc-milling`) 
- CNC Lathe (`cnc-lathe`)
- Painting (`painting`)

### Supporting Endpoints
- **GET** `/health` - Health check
- **GET** `/version` - API version information
- **GET** `/services` - Available manufacturing services
- **GET** `/materials` - Available materials
- **GET** `/coefficients` - Calculation coefficients
- **GET** `/locations` - Available locations

## Request Examples

### Rule-Based Calculation (Dimensions Only)

```json
{
  "service_id": "cnc-milling",
  "file_id": "test-cnc-milling-001",
  "dimensions": {
    "length": 80.0,
    "width": 60.0,
    "thickness": 15.0
  },
  "quantity": 10,
  "material_id": "alum_D16",
  "material_form": "sheet",
  "tolerance_id": "1",
  "finish_id": "1",
  "cover_id": ["1"],
  "k_otk": 1.0,
  "cnc_complexity": "medium",
  "cnc_setup_time": 2.0
}
```

### ML-Based Calculation (With File Upload)

```json
{
  "service_id": "cnc-milling",
  "file_id": "ml-test-001",
  "file_data": "base64_encoded_stl_file_content",
  "file_name": "complex_part.stl",
  "file_type": "stl",
  "quantity": 5,
  "material_id": "alum_D16",
  "material_form": "rod",
  "tolerance_id": "1",
  "finish_id": "1",
  "cover_id": ["1"],
  "k_otk": 1.0,
  "k_cert": ["a", "f"],
  "n_dimensions": 1,
  "location": "location_1"
}
```

### 3D Printing Example

```json
{
  "service_id": "printing",
  "file_id": "test-printing-001",
  "dimensions": {
    "length": 100.0,
    "width": 50.0,
    "thickness": 10.0
  },
  "quantity": 5,
  "material_id": "PA11",
  "material_form": "powder",
  "n_dimensions": 1,
  "k_type": 1.0,
  "k_process": 1.0,
  "cover_id": ["1"],
  "k_otk": 1.0,
  "k_cert": ["a", "f"]
}
```

### CNC Lathe Example

```json
{
  "service_id": "cnc-lathe",
  "file_id": "test-cnc-lathe-001",
  "dimensions": {
    "length": 120.0,
    "width": 25.0,
    "thickness": 25.0
  },
  "quantity": 8,
  "material_id": "alum_AMC",
  "material_form": "rod",
  "tolerance_id": "2",
  "finish_id": "3",
  "cover_id": ["2"],
  "k_otk": 1.0,
  "cnc_complexity": "high",
  "cnc_setup_time": 3.0
}
```

### Painting Example

```json
{
  "service_id": "painting",
  "file_id": "test-painting-001",
  "dimensions": {
    "length": 100.0,
    "width": 80.0,
    "thickness": 5.0
  },
  "quantity": 15,
  "material_id": "alum_D16",
  "material_form": "sheet",
  "paint_type": "acrylic",
  "paint_prepare": "a",
  "paint_primer": "b",
  "paint_lakery": "a",
  "control_type": "1",
  "k_cert": ["a", "f", "g"]
}
```

## Response Format

### Success Response Structure

```json
{
  "success": true,
  "message": "Calculation completed successfully for cnc-milling",
  "data": {
    "file_id": "unknown",
    "filename": null,
    "detail_price": 1339.0,
    "detail_price_one": 1339.0,
    "total_price": 1339.0,
    "total_time": 0.369,
    "mat_volume": 0.000125,
    "mat_weight": 0.35,
    "mat_price": 223.05,
    "work_price": 263.35076906250004,
    "work_time": 0.369,
    "k_quantity": 1.0,
    "k_complexity": 0.75,
    "k_cover": 1.05,
    "k_tolerance": 1.15,
    "k_finish": 0.9,
    "manufacturing_cycle": 10.0,
    "suitable_machines": [
      "machine_101",
      "machine_102",
      "machine_103",
      "machine_104",
      "SGT-MC116",
      "SGT-MC64",
      "Uni.5 600U",
      "Uni.5 800U",
      "DMU 65",
      "DMU 100 Р",
      "HURON K2X 10 FIVE и",
      "HURON KX 50 L"
    ],
    "n_dimensions": null,
    "k_type": null,
    "k_process": null,
    "cnc_complexity": "medium",
    "cnc_setup_time": 2.0,
    "extracted_dimensions": {
      "length": 100.0,
      "width": 50.0,
      "thickness": 25.0
    },
    "used_parameters": {
      "length": 100.0,
      "width": 50.0,
      "thickness": 25.0,
      "quantity": 1,
      "material_id": "alum_D16",
      "material_form": "rod",
      "cover_id": ["1"],
      "tolerance_id": "1",
      "finish_id": "1",
      "location": "location_1",
      "k_otk": 1.0,
      "cnc_complexity": "medium",
      "cnc_setup_time": 2.0
    },
    "service_id": "cnc-milling",
    "calculation_method": "CNC Milling Price Calculation",
    "calculation_engine": "rule_based",
    "message": "Calculation completed successfully",
    "timestamp": "2025-10-16T09:39:49.134259",
    "ml_prediction_hours": null,
    "features_extracted": null,
    "material_costs": null,
    "work_price_breakdown": null
  },
  "timestamp": "2025-10-16T09:39:49.138152",
  "version": "3.3.0"
}
```

### Key Response Fields

#### Calculation Type Information
- **`calculation_engine`**: `"rule_based"` or `"ml_model"` - Indicates which calculation method was used
- **`ml_prediction_hours`**: ML prediction hours (null for rule-based)
- **`features_extracted`**: ML features extracted from file (null for rule-based)

#### Pricing Information
- **`detail_price`**: Total price for the order
- **`detail_price_one`**: Price per individual item
- **`total_price`**: Total price (same as detail_price)
- **`mat_price`**: Material cost
- **`work_price`**: Labor cost

#### Manufacturing Information
- **`total_time`**: Total manufacturing time in hours
- **`manufacturing_cycle`**: Manufacturing cycle time
- **`suitable_machines`**: List of suitable manufacturing machines
- **`cnc_complexity`**: Complexity level (low/medium/high)

#### File Analysis (ML-based only)
- **`extracted_dimensions`**: Dimensions extracted from uploaded file
- **`features_extracted`**: Geometric features extracted for ML analysis

## Calculation Engine Selection

### Rule-Based Calculation
**Triggered when:**
- No file is uploaded (dimensions-only calculation)
- File analysis fails to extract sufficient features
- ML models are not available for the specific service/material combination

**Characteristics:**
- Uses traditional calculation formulas
- Based on dimensions, material properties, and process parameters
- Faster execution
- More predictable results

### ML-Based Calculation
**Triggered when:**
- File is uploaded successfully
- Sufficient geometric features are extracted
- ML model is available for the service type
- File complexity warrants ML analysis

**Characteristics:**
- Uses trained machine learning models
- Considers complex geometric features
- More accurate for complex parts
- Slower execution due to model inference

## File Support

### Supported File Types
- **STL files**: `file_type: "stl"`
- **STP/STEP files**: `file_type: "stp"`

### File Upload Format
```json
{
  "file_data": "base64_encoded_file_content",
  "file_name": "part.stl",
  "file_type": "stl"
}
```

## Material Support

### Available Materials
- **Aluminum**: `alum_D16`, `alum_AMC`, `alum_AMG3`, `alum_AMG6`, `alum_1163T`, `alum_B95ochT2`
- **Steel**: `steel_12X18H10T`, `steel_30XGSA`, `steel_14X17H2`
- **Plastic**: `PA11`, `PA12` (for 3D printing)

### Material Forms
- **Sheet**: `"sheet"`
- **Rod**: `"rod"`
- **Hexagon**: `"hexagon"`
- **Powder**: `"powder"` (for 3D printing)

## Testing Examples

### Running Tests
```bash
# Start the calculator service
uvicorn main:app --reload --host 0.0.0.0 --port 7000

# Run all tests
python api_test_examples.py

# Run specific test categories
python run_tests.py --category basic
python run_tests.py --category materials
python run_tests.py --category tolerance
```

### Test Categories
- **Basic**: Health check, services, materials, coefficients
- **Materials**: Different material combinations
- **Tolerance**: Various tolerance and finish combinations
- **Cover**: Different cover processing types
- **Edge Cases**: Boundary conditions and edge cases
- **Error Cases**: Invalid requests and error handling

## Integration with Backend API

The calculator service is integrated with the main Manufacturing Service API (port 8000) through:

1. **File Upload**: Backend uploads files and gets `file_id`
2. **Calculation Request**: Backend calls calculator service with `file_id` or dimensions
3. **Response Mapping**: Backend maps calculator response to its own format
4. **Calculation Type**: Backend extracts `calculation_engine` field and maps to `calculation_type`

### Backend Integration Example
```python
# Backend calls calculator service
calc_result = await call_calculator_service(
    service_id="cnc-milling",
    material_id="alum_D16",
    quantity=1,
    file_data=base64_file_data,
    file_name="part.stl",
    file_type="stl"
)

# Backend maps response
calculation_type = "ml_based" if calc_result.get("calculation_engine") == "ml_model" else "rule_based"
```

This documentation provides comprehensive information about the calculator service's capabilities, request/response formats, and integration patterns for both rule-based and ML-based calculations.

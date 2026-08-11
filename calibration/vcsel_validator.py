#!/usr/bin/env python3
"""
VCSEL LIV Telemetry Schema Validator.
Validates uploaded JSON files against the standards-compliant VCSEL schema
and checks array length constraints.
"""

from __future__ import annotations
import json
from pathlib import Path
import jsonschema

def validate_vcsel_liv(data: dict | str) -> tuple[bool, str | None]:
    """
    Validates a VCSEL LIV measurement dataset.
    Returns:
        (is_valid: bool, error_message: str | None)
    """
    try:
        # Load data if passed as a string or file path
        if isinstance(data, (str, Path)):
            with open(data, "r", encoding="utf-8") as f:
                data_dict = json.load(f)
        elif isinstance(data, dict):
            data_dict = data
        else:
            return False, "Input data must be a dictionary, JSON string, or file path."

        # Load Schema
        schema_path = Path(__file__).resolve().parent.parent / "data" / "schemas" / "vcsel_liv_measurement.schema.json"
        if not schema_path.exists():
            return False, f"VCSEL Schema not found at: {schema_path}"
            
        with open(schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)

        # Validate against JSON Schema
        jsonschema.validate(instance=data_dict, schema=schema)

        # Enforce business rules: Check array lengths are equal
        len_cur = len(data_dict["current_mA"])
        len_vol = len(data_dict["voltage_V"])
        len_pow = len(data_dict["optical_power_mW"])

        if len_cur != len_vol or len_cur != len_pow:
            return False, f"Array length mismatch: current_mA ({len_cur}), voltage_V ({len_vol}), optical_power_mW ({len_pow}) must be identical."

        # Optional arrays checking
        for opt_field in ["wavelength_nm", "monitor_current_mA", "measurement_temperature_K"]:
            if opt_field in data_dict and data_dict[opt_field] is not None:
                len_opt = len(data_dict[opt_field])
                if len_opt != len_cur:
                    return False, f"Optional array length mismatch: {opt_field} ({len_opt}) must match current_mA ({len_cur})."

        return True, None

    except jsonschema.exceptions.ValidationError as e:
        return False, f"JSON Schema Validation Error: {e.message}"
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON format: {e}"
    except Exception as e:
        return False, f"Unexpected validation error: {e}"

if __name__ == "__main__":
    # Smoke run
    root_dir = Path(__file__).resolve().parent.parent
    valid_fixture = root_dir / "tests" / "fixtures" / "vcsel_valid_liv.json"
    invalid_fixture = root_dir / "tests" / "fixtures" / "vcsel_invalid_liv.json"
    
    if valid_fixture.exists():
        ok, msg = validate_vcsel_liv(valid_fixture)
        print(f"Valid fixture test: {'PASS' if ok else 'FAIL'} (msg: {msg})")
        
    if invalid_fixture.exists():
        ok, msg = validate_vcsel_liv(invalid_fixture)
        print(f"Invalid fixture test: {'PASS' if not ok else 'FAIL'} (msg: {msg})")

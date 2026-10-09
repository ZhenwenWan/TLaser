"""Versioned fixed ridge-device configuration; UI units are explicit throughout."""
from __future__ import annotations

from copy import deepcopy
import json
import math

VERSION = 1
DESIGN_BOUNDS = {
    "L_um": (100.0, 1000.0), "w_um": (1.5, 4.0), "d_um": (0.1, 0.5),
    "R1": (0.1, 0.95), "R2": (0.05, 0.5), "T0_K": (250.0, 360.0),
    "I_active_A": (0.01, 0.5),
}
PHYSICAL_BOUNDS = {
    "alpha_i": (5.0, 20.0), "Gamma": (0.03, 0.08), "C_mult": (0.5, 3.0),
    "R_series": (0.1, 3.0), "R_shunt": (50.0, 1000.0),
}
PHYSICAL_UNITS = {"alpha_i": "cm⁻¹", "Gamma": "1", "C_mult": "1",
                  "R_series": "Ω", "R_shunt": "Ω"}


def default_config():
    return {
        "schema_version": VERSION,
        "architecture": "facet_mirror_ridge_edge_emitter",
        "operating_preset": "steady_state_cw",
        "geometry": {"L_um": 300.0, "w_um": 2.8, "d_um": 0.342},
        "optical": {"R1": 0.90, "R2": 0.05},
        "operating": {"T0_K": 298.0, "I_active_A": 0.15,
                      "current_semantics": "active_region"},
        "physical": {"alpha_i": 10.0, "Gamma": 0.05, "C_mult": 1.0,
                     "R_series": 0.85, "R_shunt": 150.0},
        "provenance": {"source": "user_design", "estimated_parameters": []},
        "backend": {"nominal": "pinn_7d", "fitted": "reduced_longitudinal_v1"},
    }


def validate_config(config):
    if not isinstance(config, dict):
        raise ValueError("Configuration must be a JSON object.")
    expected = default_config()
    if set(config) != set(expected):
        raise ValueError("Configuration fields do not match schema version 1.")
    if type(config["schema_version"]) is not int or config["schema_version"] != VERSION:
        raise ValueError("Unsupported configuration schema version.")
    for key in ("architecture", "operating_preset", "backend"):
        if config[key] != expected[key]:
            raise ValueError(f"Unsupported {key}.")
    for section in ("geometry", "optical", "operating", "physical"):
        values = config[section]
        if not isinstance(values, dict) or set(values) != set(expected[section]):
            raise ValueError(f"Invalid {section} fields.")
        for key, value in values.items():
            if key == "current_semantics":
                if value != "active_region":
                    raise ValueError("This release requires active-region current.")
                continue
            bounds = PHYSICAL_BOUNDS if section == "physical" else DESIGN_BOUNDS
            low, high = bounds[key]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"{key} must be a finite number.")
            if not low <= value <= high:
                raise ValueError(f"{key} must be between {low} and {high}.")
    provenance = config["provenance"]
    if not isinstance(provenance, dict) or not isinstance(provenance.get("source"), str):
        raise ValueError("Configuration provenance must specify its source.")
    fitted = provenance.get("estimated_parameters")
    if not isinstance(fitted, list) or any(p not in PHYSICAL_BOUNDS for p in fitted):
        raise ValueError("Unsupported estimated parameters.")
    return deepcopy(config)


def dumps(config):
    return json.dumps(validate_config(config), indent=2, ensure_ascii=False, allow_nan=False)


def loads(payload):
    return validate_config(json.loads(payload))


def surrogate_inputs(config):
    c = validate_config(config)
    return dict(R1=c["optical"]["R1"], R2=c["optical"]["R2"],
                L_um=c["geometry"]["L_um"], T0=c["operating"]["T0_K"],
                I_active=c["operating"]["I_active_A"],
                w_active_um=c["geometry"]["w_um"], d_active_um=c["geometry"]["d_um"])


def estimated_config(original, values, measurement_id):
    c = validate_config(original)
    if set(values) != set(PHYSICAL_BOUNDS):
        raise ValueError("Calibration must supply the five supported physical parameters.")
    c["physical"] = dict(values)
    c["provenance"] = {"source": "inverse_fit", "estimated_parameters": list(values),
                       "measurement_id": measurement_id, "geometry_status": "held_fixed"}
    return validate_config(c)


def geometry_model(config):
    """Named topology, with physical region dimensions and separate illustrative regions."""
    c = validate_config(config)
    return {
        "template": c["architecture"], "axes": {"z": "cavity", "x": "width", "y": "thickness"},
        "regions": [{"name": "effective_active_region", "dimensions_um": c["geometry"]},
                    {"name": "substrate_context", "illustrative": True},
                    {"name": "cladding_context", "illustrative": True}],
        "boundaries": [{"name": "rear_facet", "z_um": 0.0, "reflectivity": c["optical"]["R1"]},
                       {"name": "front_facet", "z_um": c["geometry"]["L_um"],
                        "reflectivity": c["optical"]["R2"]}],
    }

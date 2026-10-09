"""In-memory forward and inverse adapters for the fixed edge-emitter template."""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
import numpy as np
from scipy.optimize import minimize
from device_model import validate_config, estimated_config, PHYSICAL_BOUNDS
from simulator.quasi_3d_synthesizer import Quasi3DSimulator


def simulate(config, currents=None):
    c = validate_config(config)
    currents = np.asarray([c["operating"]["I_active_A"]] if currents is None else currents, dtype=float)
    if currents.ndim != 1 or currents.size == 0 or not np.isfinite(currents).all() or np.any((currents < .01) | (currents > .5)):
        raise ValueError("Active currents must be a nonempty finite array in 0.01–0.5 A.")
    outputs = []
    g, o, p = c["geometry"], c["optical"], c["physical"]
    for current in currents:
        sim = Quasi3DSimulator(L_cavity=g["L_um"]*1e-4, w_active=g["w_um"]*1e-4,
                              d_active=g["d_um"]*1e-4, R1=o["R1"], R2=o["R2"],
                              T0=c["operating"]["T0_K"], alpha_i=p["alpha_i"])
        sim.Gamma = p["Gamma"]
        sim.C_recomb *= p["C_mult"]
        sim.R_series, sim.R_shunt = p["R_series"], p["R_shunt"]
        result = sim.solve_longitudinal(current/(g["L_um"]*1e-4))
        voltage = result["P_elec"]/result["I_total"]
        values = [result["P_opt"], voltage, result["WPE"], result["I_total"]]
        if not np.isfinite(values).all():
            raise ValueError("Simulator returned nonfinite output.")
        outputs.append({"power_W": values[0], "voltage_V": values[1], "wpe": values[2],
                        "current_total_A": values[3], "N": result["N"],
                        "P": result["P_plus"]+result["P_minus"], "z_um": result["z_grid"]*1e4})
    return outputs


def validate_measurements(data, config):
    c = validate_config(config)
    if not isinstance(data, dict):
        raise ValueError("Measurements must be a JSON object.")
    if data.get("current_semantics") != "active_region":
        raise ValueError("Specify current_semantics='active_region'. Terminal-current fitting is not supported in this release.")
    arrays = {}
    for key in ("current_A", "voltage_V", "optical_power_W"):
        try:
            raw = data[key]
            if not isinstance(raw, list) or any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in raw):
                raise ValueError()
            arrays[key] = np.asarray(raw, dtype=float)
        except (KeyError, ValueError, TypeError):
            raise ValueError(f"{key} must be an array of numbers.") from None
        if arrays[key].ndim != 1 or arrays[key].size < 5 or arrays[key].size > 200:
            raise ValueError("Use 5–200 measurement points per sweep.")
        if not np.isfinite(arrays[key]).all():
            raise ValueError(f"{key} contains nonfinite values.")
    if len({len(a) for a in arrays.values()}) != 1:
        raise ValueError("Measurement array lengths must match.")
    i, v, p = (arrays[k] for k in ("current_A", "voltage_V", "optical_power_W"))
    if np.any((i < .01) | (i > .5)) or np.unique(i).size < 5:
        raise ValueError("Provide at least five distinct active currents within 0.01–0.5 A.")
    if np.any(v <= 0) or np.any(p < 0) or not np.any(p > 0):
        raise ValueError("Voltage must be positive; power must be nonnegative and informative.")
    expected = {**c["geometry"], **c["optical"], "T0": c["operating"]["T0_K"]}
    metadata = data.get("metadata")
    if not isinstance(metadata, dict):
        raise ValueError("Measurement metadata must identify geometry, facets, and T0.")
    for key, value in expected.items():
        actual = metadata.get(key)
        if isinstance(actual, bool) or not isinstance(actual, (int, float)) or not np.isfinite(actual) or not np.isclose(actual, value, rtol=1e-8, atol=1e-10):
            raise ValueError(f"Measurement metadata {key} must match the selected configuration ({value:g}).")
    return arrays


def demo_measurements(config, selected=None):
    c = validate_config(config)
    target = validate_config(c)
    drift = dict(alpha_i=12.5, Gamma=.048, C_mult=1.35, R_series=1.15, R_shunt=180.)
    for key in (list(drift) if selected is None else selected):
        target["physical"][key] = drift[key]
    currents = np.linspace(.05, .4, 8)
    out = simulate(target, currents)
    return {"current_semantics": "active_region", "current_A": currents.tolist(),
            "voltage_V": [o["voltage_V"] for o in out], "optical_power_W": [o["power_W"] for o in out],
            "metadata": {**c["geometry"], **c["optical"], "T0": c["operating"]["T0_K"],
                         "source": "synthetic_demo", "known_physical": target["physical"]}}


def fit_measurements(config, data, selected=None, max_iterations=40):
    original = validate_config(config)
    arrays = validate_measurements(data, original)
    selected = list(PHYSICAL_BOUNDS) if selected is None else list(selected)
    if not selected or len(set(selected)) != len(selected) or any(k not in PHYSICAL_BOUNDS for k in selected):
        raise ValueError("Choose supported physical parameters to estimate.")
    bounds = np.array([PHYSICAL_BOUNDS[k] for k in selected])
    low, span = bounds[:, 0], bounds[:, 1]-bounds[:, 0]
    start = (np.array([original["physical"][k] for k in selected])-low)/span
    currents = arrays["current_A"]
    power_scale = max(float(np.sqrt(np.mean(arrays["optical_power_W"]**2))), 1e-6)
    voltage_scale = float(np.sqrt(np.mean(arrays["voltage_V"]**2)))

    def candidate(x):
        c = validate_config(original)
        for key, value in zip(selected, low+np.clip(x, 0., 1.)*span):
            c["physical"][key] = float(value)
        return c

    def residual(x):
        out = simulate(candidate(x), currents)
        p = np.array([o["power_W"] for o in out])
        v = np.array([o["voltage_V"] for o in out])
        return np.concatenate(((p-arrays["optical_power_W"])/power_scale,
                               (v-arrays["voltage_V"])/voltage_scale))

    def loss(x):
        return float(np.mean(residual(x)**2))

    before = loss(start)
    result = minimize(loss, start, method="L-BFGS-B", bounds=[(0., 1.)]*len(selected),
                      options={"maxiter": max_iterations, "ftol": 1e-10, "eps": 1e-5})
    fitted = candidate(result.x)
    after = loss(result.x)
    measurement_id = hashlib.sha256(json.dumps(data, sort_keys=True, allow_nan=False).encode()).hexdigest()
    estimated = estimated_config(original, fitted["physical"], measurement_id)
    estimated["provenance"]["estimated_parameters"] = selected
    sensitivities, jac = {}, []
    for j, key in enumerate(selected):
        a, b = result.x.copy(), result.x.copy()
        a[j], b[j] = max(0., a[j]-.001), min(1., b[j]+.001)
        derivative = (residual(b)-residual(a))/(b[j]-a[j])
        sensitivities[key] = float(np.linalg.norm(derivative))
        jac.append(derivative)
    singular = np.linalg.svd(np.array(jac).T, compute_uv=False)
    insensitive = [k for k, value in sensitivities.items() if value < 1e-6]
    condition = float(singular[0]/singular[-1]) if singular[-1] > 1e-12 else None
    on_bounds = [k for k, x in zip(selected, result.x) if x < .001 or x > .999]
    return {"schema_version": 1, "original": original, "estimated": estimated,
            "measurement_id": measurement_id, "measurements": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "success": bool(result.success), "message": str(result.message),
            "iterations": int(result.nit), "loss_before": before, "loss_after": after,
            "bounds_reached": on_bounds, "sensitivity": sensitivities,
            "insensitive_parameters": insensitive, "jacobian_condition": condition,
            "acceptance_loss_limit": .01,
            "acceptable": bool(result.success and after < before and not on_bounds and not insensitive
                               and condition is not None and condition < 1e6 and after < .01)}

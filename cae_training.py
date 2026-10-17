"""Simulation-driven PINN training with independent held-out evaluation."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import runpy
import sys
import zipfile
import numpy as np
from scipy.stats import qmc
from cae_jobs import ROOT, write_json, check_cancel
from device_model import DESIGN_BOUNDS, validate_config, surrogate_inputs
from device_workflow import simulate

KEYS = ["R1", "R2", "L_um", "T0_K", "I_active_A", "w_um", "d_um"]
SECTIONS = ["optical", "optical", "geometry", "operating", "operating", "geometry", "geometry"]
PREDICT_KEYS = ["R1", "R2", "L_um", "T0", "I_active", "w_active_um", "d_active_um"]


def input_vector(c):
    return [c[s][k] * (1e-4 if k in {"L_um", "w_um", "d_um"} else 1)
            for k, s in zip(KEYS, SECTIONS)]


def evaluate(model, configurations, targets, train_targets):
    outputs = []
    for c in configurations:
        p = model.predict(**surrogate_inputs(c))
        outputs.append(np.r_[p["P_opt"], p["wpe"], p["I_total"], p["N"], p["P"]])
    predictions = np.asarray(outputs)
    if not np.isfinite(predictions).all():
        raise ValueError("Nonfinite held-out predictions")
    scale = np.maximum(np.ptp(train_targets, axis=0), np.maximum(np.abs(train_targets).mean(axis=0)*.01, 1e-12))
    errors = predictions-targets
    normalized = np.sqrt(np.mean((errors/scale)**2, axis=0))
    groups = {"power": [0], "wpe": [1], "terminal_current": [2],
              "carrier_profile": list(range(3,54)), "power_profile": list(range(54,105))}
    return {"samples": len(targets), "normalized_rmse": float(np.sqrt(np.mean((errors/scale)**2))),
            "groups": {name: {"normalized_rmse": float(np.sqrt(np.mean((errors[:, ids]/scale[ids])**2))),
                               "rmse": float(np.sqrt(np.mean(errors[:, ids]**2)))} for name, ids in groups.items()}}


def run_training(folder, settings):
    config = validate_config(settings["configuration"])
    samples, epochs, seed = int(settings["samples"]), int(settings["epochs"]), int(settings["seed"])
    if not 20 <= samples <= 10000 or not 5 <= epochs <= 5000 or not 0 <= seed <= 2**32-1:
        raise ValueError("Invalid training settings")
    threshold = float(settings["max_normalized_rmse"])
    if not .001 <= threshold <= 1:
        raise ValueError("Invalid validation threshold")
    ranges = settings["ranges"]
    for key in KEYS:
        low, high = ranges[key]
        a, b = DESIGN_BOUNDS[key]
        if not np.isfinite([low, high]).all() or not a <= low < high <= b:
            raise ValueError(f"Invalid sampling range: {key}")
    design = qmc.scale(qmc.LatinHypercube(7, seed=seed).random(samples),
                       [ranges[k][0] for k in KEYS], [ranges[k][1] for k in KEYS])
    inputs, outputs, configs, failures = [], [], [], []
    for i, row in enumerate(design):
        check_cancel(folder)
        c = deepcopy(config)
        for key, section, value in zip(KEYS, SECTIONS, row):
            c[section][key] = float(value)
        try:
            result = simulate(c)[0]
            target = np.r_[result["power_W"], result["wpe"], result["current_total_A"], result["N"], result["P"]]
            if target.shape != (105,) or not np.isfinite(target).all():
                raise ValueError("Invalid simulator targets")
            inputs.append(input_vector(c)); outputs.append(target); configs.append(c)
        except (ValueError, RuntimeError, OverflowError) as ex:
            failures.append({"sample": i, "error": str(ex), "input": row.tolist()})
        write_json(folder / "progress.json", {"stage": "simulation sampling", "done": i+1,
                   "total": samples, "accepted": len(inputs), "failed": len(failures)})
    write_json(folder / "sampling_failures.json", failures)
    if len(inputs) < 20:
        raise ValueError("Fewer than 20 usable simulations; training was not started")
    inputs, outputs = np.asarray(inputs), np.asarray(outputs)
    order = np.random.default_rng(seed).permutation(len(inputs))
    ntrain, nval = int(len(order)*.6), int(len(order)*.2)
    train, validation, test = order[:ntrain], order[ntrain:ntrain+nval], order[ntrain+nval:]
    data = folder / "model"
    data.mkdir()
    np.save(data/"pinn_inputs.npy", inputs[train]); np.save(data/"pinn_targets.npy", outputs[train])
    np.savez_compressed(folder/"dataset.npz", inputs=inputs, targets=outputs,
                        train_indices=train, validation_indices=validation, test_indices=test)
    write_json(folder/"dataset.json", {"backend": "TLaser reduced longitudinal v1", "seed": seed,
        "requested": samples, "accepted": len(inputs), "failures": len(failures), "ranges": ranges,
        "physical": config["physical"], "configuration": config,
        "simulator_sha256": hashlib.sha256((ROOT/"simulator/quasi_3d_synthesizer.py").read_bytes()).hexdigest(),
        "input_order": KEYS, "input_storage_units": ["1","1","cm","K","A","cm","cm"],
        "split": {"train": train.tolist(), "validation": validation.tolist(), "test": test.tolist()}})
    check_cancel(folder)
    old_argv = sys.argv
    write_json(folder/"physical.json", config["physical"])
    try:
        sys.argv = ["train.py", "--output-dir", str(data), "--epochs", str(epochs), "--seed", str(seed),
                    "--progress-file", str(folder/"progress.json"), "--cancel-file", str(folder/"cancel"),
                    "--physical-config", str(folder/"physical.json")]
        runpy.run_path(str(ROOT/"surrogate/train.py"), run_name="__main__")
    finally:
        sys.argv = old_argv
    check_cancel(folder)
    from surrogate.pinn_surrogate import PINNSurrogate
    model = PINNSurrogate(data)
    val_report = evaluate(model, [configs[i] for i in validation], outputs[validation], outputs[train])
    test_report = evaluate(model, [configs[i] for i in test], outputs[test], outputs[train])
    eligible = all(group["normalized_rmse"] <= threshold for report in (val_report,test_report)
                   for group in report["groups"].values())
    report = {"validation": val_report, "test": test_report, "threshold": threshold, "eligible": eligible,
              "ranges": ranges, "physical": config["physical"], "epochs": epochs, "seed": seed,
              "checkpoint_sha256": hashlib.sha256((data/"pinn_laser_model.pt").read_bytes()).hexdigest(),
              "scale_sha256": hashlib.sha256((data/"pinn_scale_params.npz").read_bytes()).hexdigest(),
              "scope": "Simulator-relative validation only; does not establish measured-device accuracy"}
    write_json(folder/"evaluation.json", report)
    with zipfile.ZipFile(folder/"trained_model.zip", "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in ("pinn_laser_model.pt", "pinn_scale_params.npz", "training_history.json"):
            archive.write(data/name, name)
        archive.write(folder/"evaluation.json", "evaluation.json")
        archive.write(folder/"dataset.json", "dataset.json")
    return ("completed" if eligible else "candidate"), ("Validation gates passed" if eligible else "Trained model needs further validation/training; activation disabled")


class ValidatedSurrogate:
    """Prediction wrapper carrying sampling-domain and fixed-physics metadata."""
    def __init__(self, folder):
        from surrogate.pinn_surrogate import PINNSurrogate
        report = json.loads((folder/"evaluation.json").read_text(encoding="utf-8"))
        if not report["eligible"]:
            raise ValueError("Model has not passed validation gates")
        path = folder/"model/pinn_laser_model.pt"
        if hashlib.sha256(path.read_bytes()).hexdigest() != report["checkpoint_sha256"]:
            raise ValueError("Model checksum mismatch")
        if hashlib.sha256((folder/"model/pinn_scale_params.npz").read_bytes()).hexdigest() != report.get("scale_sha256"):
            raise ValueError("Model scaling checksum mismatch")
        self.delegate = PINNSurrogate(folder/"model")
        self.model, self.physical, self.ranges = self.delegate.model, report["physical"], report["ranges"]

    def predict(self, **kwargs):
        for key, input_key in zip(KEYS, PREDICT_KEYS):
            low, high = self.ranges[key]
            if not low <= kwargs[input_key] <= high:
                raise ValueError(f"{input_key} is outside the trained model domain [{low:g}, {high:g}]")
        return self.delegate.predict(**kwargs)

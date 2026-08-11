#!/usr/bin/env python3
"""
Automated Verification Pipeline for TLaser.
Verifies dependencies, dataset creation, training residuals, and calibration optimization.
"""

import sys
import os
import json
import subprocess
from pathlib import Path
import numpy as np

def run_step(name, cmd_args, cwd):
    print(f"\n>>> Running Step: {name}...")
    # Find current python executable
    python_exe = sys.executable
    cmd = [python_exe] + cmd_args
    
    # Run process
    res = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    if res.returncode == 0:
        print(f"  [SUCCESS] {name} completed successfully.")
        return True, res.stdout
    else:
        print(f"  [FAILED] {name} exited with code {res.returncode}.")
        print("  Error output:")
        print(res.stderr)
        return False, res.stderr

def write_report(data_dir, success, steps_status):
    report_path = data_dir.parent / "verification_report.json"
    from datetime import datetime
    report = {
        "timestamp": datetime.now().isoformat(),
        "overall_success": success,
        "steps": steps_status
    }
    try:
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=4)
        print(f"\n  [INFO] Saved machine-readable verification report to {report_path}")
    except Exception as e:
        print(f"Warning: Failed to write verification report JSON: {e}")

def main():
    print("==================================================")
    print("          TLaser Pipeline Verification            ")
    print("==================================================")
    
    root_dir = Path(__file__).resolve().parent
    data_dir = root_dir / "data" / "smoke_test"
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Establish strict data separation folders
    (root_dir / "data" / "datasets" / "edge_emitter").mkdir(parents=True, exist_ok=True)
    (root_dir / "data" / "datasets" / "vcsel").mkdir(parents=True, exist_ok=True)
    
    steps_status = {
        "dependencies": False,
        "dataset_smoke_test": False,
        "surrogate_train_smoke_test": False,
        "calibration_smoke_test": False,
        "unit_tests": False
    }
    
    # Step 1: Verify Dependencies
    print("\n>>> Step 1: Checking imports...")
    try:
        import numpy
        import matplotlib
        import streamlit
        import torch
        import scipy
        print("  [SUCCESS] All primary dependencies (numpy, matplotlib, streamlit, torch, scipy) imported correctly.")
        steps_status["dependencies"] = True
    except ImportError as e:
        print(f"  [FAILED] Dependency import check failed: {e}")
        print("  Please run: pip install -r requirements.txt")
        write_report(data_dir, False, steps_status)
        sys.exit(1)
        
    # Step 2: Smoke test dataset generation
    success, stdout = run_step(
        "Dataset Generator Smoke Test",
        ["simulator/generate_dataset.py", "--smoke-test", "--output-dir", str(data_dir)],
        root_dir
    )
    if not success:
        write_report(data_dir, False, steps_status)
        sys.exit(1)
        
    # Verify dataset files exist and look correct
    inputs_path = data_dir / "pinn_inputs.npy"
    targets_path = data_dir / "pinn_targets.npy"
    meta_path = data_dir / "pinn_dataset_metadata.json"
    
    if not inputs_path.exists() or not targets_path.exists() or not meta_path.exists():
        print("  [FAILED] Dataset files or metadata json missing after run.")
        write_report(data_dir, False, steps_status)
        sys.exit(1)
        
    steps_status["dataset_smoke_test"] = True
        
    # Step 3: Smoke test training with physics residuals
    success, stdout = run_step(
        "PINN Surrogate Training Smoke Test",
        ["surrogate/train.py", "--smoke-test", "--output-dir", str(data_dir)],
        root_dir
    )
    if not success:
        write_report(data_dir, False, steps_status)
        sys.exit(1)
        
    # Verify training weights exist
    weights_path = data_dir / "pinn_laser_model.pt"
    scales_path = data_dir / "pinn_scale_params.npz"
    loss_path = data_dir / "pinn_training_loss.svg"
    
    if not weights_path.exists() or not scales_path.exists() or not loss_path.exists():
        print("  [FAILED] Trained weights or scale params missing after training.")
        write_report(data_dir, False, steps_status)
        sys.exit(1)
        
    steps_status["surrogate_train_smoke_test"] = True
        
    # Step 4: Smoke test calibration optimization
    success, stdout = run_step(
        "Parameter Calibration Smoke Test",
        ["calibration/calibrate.py", "--smoke-test", "--output-dir", str(data_dir)],
        root_dir
    )
    if not success:
        write_report(data_dir, False, steps_status)
        sys.exit(1)
        
    # Verify calibrated parameters exist
    cal_path = data_dir / "calibrated_params.json"
    fit_plot_path = data_dir / "calibration_fit.svg"
    
    if not cal_path.exists() or not fit_plot_path.exists():
        print("  [FAILED] Calibrated JSON or fit plot missing after calibration.")
        write_report(data_dir, False, steps_status)
        sys.exit(1)
        
    steps_status["calibration_smoke_test"] = True
    
    # Step 5: Run Unit Test Suite
    success, stdout = run_step(
        "Automated Unit Test Suite",
        ["-m", "unittest", "tests.test_tlaser"],
        root_dir
    )
    if not success:
        write_report(data_dir, False, steps_status)
        sys.exit(1)
        
    steps_status["unit_tests"] = True
    
    write_report(data_dir, True, steps_status)
        
    print("\n==================================================")
    print("  Verification Pipeline Completed: ALL STEPS PASS ")
    print("==================================================")

if __name__ == "__main__":
    main()

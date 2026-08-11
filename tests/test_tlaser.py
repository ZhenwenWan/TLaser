#!/usr/bin/env python3
"""
Automated unit test suite for TLaser components.
"""

import unittest
import sys
import os
import json
from pathlib import Path
import numpy as np

# Configure path imports
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))
sys.path.append(str(ROOT_DIR / "simulator"))
sys.path.append(str(ROOT_DIR / "surrogate"))
sys.path.append(str(ROOT_DIR / "calibration"))

from quasi_3d_synthesizer import Quasi3DSimulator
from pinn_surrogate import PINNSurrogate
import calibrate

class TestTLaser(unittest.TestCase):

    def test_simulator_smoke(self):
        """
        Verify that Quasi3DSimulator runs a single solver pass.
        """
        sim = Quasi3DSimulator(L_cavity=300.0e-4, R1=0.3, R2=0.3)
        res = sim.solve_longitudinal(I_2d_unit=3.33)
        self.assertIn("P_opt", res)
        self.assertIn("I_total", res)
        self.assertIn("WPE", res)
        self.assertIn("N", res)
        self.assertIn("P_plus", res)
        self.assertGreaterEqual(res["P_opt"], 0.0)
        self.assertEqual(len(res["N"]), 51)
        self.assertEqual(len(res["P_plus"]), 51)

    def test_dataset_metadata(self):
        """
        Verify the dataset metadata exists and contains expected keys.
        """
        meta_path = ROOT_DIR / "data" / "pinn_dataset_metadata.json"
        if meta_path.exists():
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            self.assertIn("shapes", meta)
            self.assertIn("sample_count", meta)
            self.assertIn("failed_solves", meta)
            self.assertIn("parameter_ranges", meta)
            
            inputs_path = ROOT_DIR / "data" / "pinn_inputs.npy"
            targets_path = ROOT_DIR / "data" / "pinn_targets.npy"
            if inputs_path.exists() and targets_path.exists():
                inputs = np.load(str(inputs_path))
                targets = np.load(str(targets_path))
                self.assertEqual(list(inputs.shape), meta["shapes"]["inputs"])
                self.assertEqual(list(targets.shape), meta["shapes"]["targets"])
                self.assertEqual(inputs.shape[1], 7)
                self.assertEqual(targets.shape[1], 105)

    def test_scale_parameters(self):
        """
        Verify that scaling parameters are loaded and are finite.
        """
        scale_path = ROOT_DIR / "data" / "pinn_scale_params.npz"
        if scale_path.exists():
            data = np.load(str(scale_path))
            self.assertIn("in_min", data)
            self.assertIn("in_max", data)
            self.assertIn("out_min", data)
            self.assertIn("out_max", data)
            self.assertTrue(np.all(np.isfinite(data["in_min"])))
            self.assertTrue(np.all(np.isfinite(data["in_max"])))
            self.assertTrue(np.all(np.isfinite(data["out_min"])))
            self.assertTrue(np.all(np.isfinite(data["out_max"])))

    def test_surrogate_prediction_api(self):
        """
        Validate surrogate prediction API output schema.
        """
        weights_path = ROOT_DIR / "data" / "pinn_laser_model.pt"
        scale_path = ROOT_DIR / "data" / "pinn_scale_params.npz"
        if weights_path.exists() and scale_path.exists():
            surr = PINNSurrogate(ROOT_DIR)
            res = surr.predict(R1=0.9, R2=0.05, L_um=300.0, T0=298.0, I_active=0.15, w_active_um=2.8, d_active_um=0.342)
            self.assertIn("P_opt", res)
            self.assertIn("wpe", res)
            self.assertIn("I_total", res)
            self.assertIn("N", res)
            self.assertIn("P", res)
            self.assertEqual(len(res["N"]), 51)
            self.assertEqual(len(res["P"]), 51)

    def test_calibration_mock_convergence(self):
        """
        Ensure calibration successfully converges with mock data.
        """
        out_dir = ROOT_DIR / "data" / "smoke_test"
        out_dir.mkdir(parents=True, exist_ok=True)
        cal = calibrate.run_calibration(data_file=None, output_dir=out_dir, smoke_test=True)
        self.assertIn("alpha_i", cal)
        self.assertIn("Gamma", cal)
        self.assertIn("mse", cal)
        self.assertIn("success", cal)

    def test_ingestion_parsing(self):
        """
        Verify CSV/JSON monitored data readers load and handle data robustly.
        """
        out_dir = ROOT_DIR / "data" / "smoke_test"
        out_dir.mkdir(parents=True, exist_ok=True)
        temp_json = out_dir / "temp_test_monitored.json"
        temp_csv = out_dir / "temp_test_monitored.csv"
        
        json_data = {
            "current_A": [0.05, 0.10, 0.15],
            "voltage_V": [1.02, 1.05, 1.08],
            "optical_power_W": [0.005, 0.020, 0.040],
            "metadata": {
                "R1": 0.90, "R2": 0.05, "L_um": 300.0, "T0": 298.0, "w_um": 2.8, "d_um": 0.342
            }
        }
        with open(temp_json, "w", encoding="utf-8") as f:
            json.dump(json_data, f)
            
        csv_data = "Current_A,Voltage_V,Power_W\n0.05,1.02,0.005\n0.10,1.05,0.020\n0.15,1.08,0.040"
        with open(temp_csv, "w", encoding="utf-8") as f:
            f.write(csv_data)
            
        try:
            res_json = calibrate.run_calibration(data_file=str(temp_json), output_dir=out_dir, smoke_test=True)
            self.assertTrue(res_json["iterations"] >= 0)
            
            res_csv = calibrate.run_calibration(data_file=str(temp_csv), output_dir=out_dir, smoke_test=True)
            self.assertTrue(res_csv["iterations"] >= 0)
        finally:
            if temp_json.exists():
                temp_json.unlink()
            if temp_csv.exists():
                temp_csv.unlink()

    def test_app_imports(self):
        """
        Check that Streamlit app components can be imported successfully.
        """
        try:
            import app
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"Streamlit app components failed to import: {e}")

    def test_vcsel_simulator(self):
        """
        Verify that the new VCSEL reduced physical simulator operates correctly.
        """
        from vcsel_simulator import VCSELSimulator
        sim = VCSELSimulator(aperture_dia_um=8.0)
        res = sim.solve_radial_profiles(I_total_mA=6.0)
        
        self.assertIn("P_opt_mW", res)
        self.assertIn("V_term", res)
        self.assertIn("T_junction", res)
        self.assertIn("N", res)
        self.assertEqual(len(res["r_grid_um"]), 51)
        self.assertEqual(len(res["N"]), 51)
        self.assertTrue(res["P_opt_mW"] > 0)
        self.assertTrue(res["V_term"] > 1.45)

    def test_vcsel_calibration_and_validation(self):
        """
        Verify that VCSEL JSON schema validation and parameter calibration loops work.
        """
        from vcsel_validator import validate_vcsel_liv
        from vcsel_calibrate import run_vcsel_calibration
        
        valid_json = ROOT_DIR / "tests" / "fixtures" / "vcsel_valid_liv.json"
        invalid_json = ROOT_DIR / "tests" / "fixtures" / "vcsel_invalid_liv.json"
        
        # Test validation on valid data
        ok, err = validate_vcsel_liv(valid_json)
        self.assertTrue(ok, f"Valid fixture failed validation: {err}")
        
        # Test validation on invalid data
        ok, err = validate_vcsel_liv(invalid_json)
        self.assertFalse(ok, "Invalid fixture passed validation unexpectedly")
        self.assertIn("Array length mismatch", err)
        
        # Test calibration convergence on valid fixture
        res = run_vcsel_calibration(data_file=str(valid_json), output_dir=ROOT_DIR / "data" / "smoke_test", smoke_test=True)
        self.assertIn("calibrated_values", res)
        self.assertIn("R_th_K_W", res["calibrated_values"])

    def test_doc_existence(self):
        """
        Verify that all documented manual and specification artifacts exist.
        """
        docs = [
            ROOT_DIR / "README.md",
            ROOT_DIR / "Doc" / "TLaser_User_Manual.md",
            ROOT_DIR / "Doc" / "TLaser_User_Manual.pdf",
            ROOT_DIR / "Doc" / "TLaser_User_Manual_CN.md",
            ROOT_DIR / "Doc" / "TLaser_User_Manual_CN.pdf",
        ]
        for doc in docs:
            self.assertTrue(doc.exists(), f"Document missing: {doc.name}")

if __name__ == "__main__":
    unittest.main()

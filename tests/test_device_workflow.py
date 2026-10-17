"""Configuration, geometry, inverse recovery, and shared UI behavior checks."""
import json
import unittest
from copy import deepcopy
from pathlib import Path
import numpy as np
from device_model import default_config, dumps, loads, surrogate_inputs, geometry_model, validate_config
from device_geometry import schematic
from device_workflow import simulate, validate_measurements, fit_measurements


class DeviceWorkflowTests(unittest.TestCase):
    def test_roundtrip_and_domain(self):
        c = default_config()
        self.assertEqual(c, loads(dumps(c)))
        for key, value in [("L_um", 99.), ("w_um", float("nan")), ("d_um", True)]:
            bad = deepcopy(c); bad["geometry"][key] = value
            with self.assertRaises(ValueError): validate_config(bad)
        bad = deepcopy(c); bad["schema_version"] = 2
        with self.assertRaises(ValueError): loads(json.dumps(bad))
        bad = deepcopy(c); bad["architecture"] = "dfb"
        with self.assertRaises(ValueError): validate_config(bad)

    def test_geometry_and_backend_share_dimensions(self):
        c = default_config(); old_svg = schematic(c)
        c["geometry"].update(L_um=520., w_um=3.2, d_um=.23)
        inputs = surrogate_inputs(c)
        self.assertEqual(inputs["L_um"], 520.)
        self.assertEqual(inputs["w_active_um"], 3.2)
        self.assertEqual(inputs["d_active_um"], .23)
        model = geometry_model(c)
        self.assertEqual(model["boundaries"][1]["z_um"], 520.)
        self.assertNotEqual(schematic(c), old_svg)
        for label in ("L = 520", "w = 3.2", "d = 0.23", "thickness exaggerated"):
            self.assertIn(label, schematic(c))

    def measurement(self, original, target):
        currents = np.linspace(.05, .4, 6)
        out = simulate(target, currents)
        return {"current_semantics": "active_region", "current_A": currents.tolist(),
                "voltage_V": [o["voltage_V"] for o in out], "optical_power_W": [o["power_W"] for o in out],
                "metadata": {**original["geometry"], **original["optical"], "T0": original["operating"]["T0_K"]}}

    def test_measurement_rejections(self):
        c = default_config(); good = self.measurement(c, c)
        validate_measurements(good, c)
        for key, value in [("current_semantics", "terminal"), ("current_A", []),
                           ("voltage_V", [float("nan")]*6), ("optical_power_W", [0]*6)]:
            bad = deepcopy(good); bad[key] = value
            with self.assertRaises(ValueError): validate_measurements(bad, c)
        bad = deepcopy(good); bad["metadata"]["w_um"] = 3.
        with self.assertRaisesRegex(ValueError, "w_um"): validate_measurements(bad, c)
        bad = deepcopy(good); bad["voltage_V"].pop()
        with self.assertRaisesRegex(ValueError, "lengths"): validate_measurements(bad, c)

    def test_fit_recovers_supported_parameter_and_preserves_geometry(self):
        original = default_config(); target = deepcopy(original)
        target["physical"]["R_series"] = 1.4
        data = self.measurement(original, target)
        fit = fit_measurements(original, data, selected=["R_series"], max_iterations=20)
        self.assertTrue(fit["success"], fit["message"])
        self.assertTrue(fit["acceptable"])
        self.assertLess(fit["loss_after"], fit["loss_before"]*.001)
        self.assertAlmostEqual(fit["estimated"]["physical"]["R_series"], 1.4, places=3)
        self.assertEqual(fit["original"]["geometry"], fit["estimated"]["geometry"])
        self.assertEqual(fit["estimated"]["provenance"]["estimated_parameters"], ["R_series"])
        self.assertEqual(schematic(original), schematic(fit["estimated"]))
        self.assertNotEqual(simulate(original)[0]["voltage_V"], simulate(fit["estimated"])[0]["voltage_V"])
        self.assertEqual(surrogate_inputs(original), surrogate_inputs(fit["estimated"]))

    def test_failed_fit_is_not_accepted(self):
        c = default_config(); target = deepcopy(c); target["physical"]["R_series"] = 1.4
        fit = fit_measurements(c, self.measurement(c, target), ["R_series"], max_iterations=0)
        self.assertFalse(fit["acceptable"])


class DeviceUITests(unittest.TestCase):
    def test_shared_design_survives_workflow_and_language_switch(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/"app.py"), default_timeout=90).run()
        self.assertFalse(app.exception)
        self.assertEqual([tab.label for tab in app.tabs], ["1. Device model", "2. Simulator core", "3. PINN surrogate", "4. Instant Performance Prediction", "5. Instant Parameter Calibration"])
        app.number_input(key="ridge_L_um").set_value(520.)
        next(b for b in app.button if b.label == "Update device").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["ridge_config"]["geometry"]["L_um"], 520.)
        self.assertFalse(app.exception)
        self.assertEqual(app.number_input(key="ridge_L_um").value, 520.)
        app.sidebar.selectbox[0].set_value("CN").run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["ridge_config"]["geometry"]["L_um"], 520.)

    def test_demo_fit_apply_and_simulator_prediction(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/"app.py"), default_timeout=90).run()
        next(r for r in app.radio if r.label == "Measurement source").set_value("Synthetic demo / 合成演示").run()
        next(b for b in app.button if b.label == "Run calibration").click().run()
        self.assertFalse(app.exception)
        self.assertTrue(app.session_state["ridge_fit"]["acceptable"])
        next(b for b in app.button if b.label == "Use fitted constants for simulator prediction").click().run()
        self.assertTrue(app.session_state["ridge_applied"])
        next(r for r in app.radio if r.label == "Prediction source").set_value("Physical simulator / 物理模拟器").run()
        self.assertFalse(app.exception)
        self.assertTrue(any("accepted fitted constants" in x.value for x in app.caption))
        app.number_input(key="ridge_w_um").set_value(3.1)
        next(b for b in app.button if b.label == "Update device").click().run()
        self.assertIsNone(app.session_state["ridge_fit"])
        self.assertFalse(app.session_state["ridge_applied"])


if __name__ == "__main__":
    unittest.main()

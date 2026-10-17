"""Exercise the new simulation and surrogate workflows and stale-report handling."""
from copy import deepcopy
from pathlib import Path
import unittest
from unittest.mock import patch
from device_model import default_config
from device_sections import run_sweep, compare_nominal
from device_workflow import validate_measurements


class SectionTests(unittest.TestCase):
    def test_sweep_uses_requested_currents_and_configuration(self):
        c = default_config()
        result = run_sweep(c, .05, .2, 3)
        self.assertEqual(len(result["rows"]), 3)
        self.assertEqual(result["configuration"], c)
        self.assertEqual(result["rows"][0]["active_current_A"], .05)
        self.assertEqual(result["rows"][-1]["active_current_A"], .2)
        with self.assertRaises(ValueError):
            run_sweep(c, .2, .05, 3)

    def test_pinn_comparison_resets_only_physical_constants(self):
        class Surrogate:
            def predict(self, **kwargs):
                return {"P_opt": .001, "wpe": .1, "I_total": .15}
        c = default_config()
        c["physical"]["R_series"] = 1.7
        c["geometry"]["L_um"] = 520.
        original = deepcopy(c)
        with patch("device_sections.simulate", return_value=[{
                "power_W": .002, "wpe": .2, "current_total_A": .16}]) as solver:
            report = compare_nominal(c, Surrogate())
        used = solver.call_args.args[0]
        self.assertEqual(used["physical"], default_config()["physical"])
        self.assertEqual(used["geometry"], c["geometry"])
        self.assertEqual(c, original)
        self.assertAlmostEqual(report["rows"][0]["Absolute difference"], 1.)

    def test_panels_run_and_reject_stale_reports(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/"app.py"), default_timeout=90).run()
        app.number_input(key="sweep_points").set_value(3)
        next(b for b in app.button if b.label == "Run physical simulation").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.session_state["ridge_sweep"]["rows"]), 3)
        app.button(key="compare_pinn").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.session_state["ridge_pinn_check"]["rows"]), 3)
        app.number_input(key="ridge_L_um").set_value(510.)
        next(b for b in app.button if b.label == "Update device").click().run()
        self.assertFalse(app.exception)
        self.assertTrue(any("Run the simulation again" in i.value for i in app.info))
        self.assertTrue(any("Compare again" in i.value for i in app.info))


if __name__ == "__main__":
    unittest.main()

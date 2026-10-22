from pathlib import Path
import tempfile
import json
import unittest
from unittest.mock import patch
import numpy as np
from cae_jobs import write_json
from cae_coupling import run_coupled,solve_1d,heat_target
from cae_workspace import decode_configuration
from device_model import default_config


class WorkspaceTests(unittest.TestCase):
    def test_config_roundtrip_and_wrong_section(self):
        defaults=dict(temperature=298.,nodes=51,frequency=1.934e14,configuration=default_config())
        encoded=json.dumps(dict(schema_version=1,kind='longitudinal',settings=defaults))
        self.assertEqual(decode_configuration(encoded,'longitudinal',defaults),defaults)
        with self.assertRaises(ValueError):
            decode_configuration(encoded,'fields',defaults)
        defaults['nodes']=1
        with self.assertRaises(ValueError):
            decode_configuration(json.dumps(dict(schema_version=1,kind='longitudinal',settings=defaults)),'longitudinal',defaults)

    def test_independent_1d_resolution_and_heat_units(self):
        result=solve_1d(dict(configuration=default_config(),temperature=300.,nodes=31))
        self.assertEqual(len(result['N']),31)
        result.update(z_grid=[0.,.01,.02],P_plus=[2.,2.,2.],P_minus=[1.,1.,1.])
        self.assertAlmostEqual(heat_target(result,.5,.25),15.)

    def test_feedback_changes_applied_source_and_reports_nonconvergence(self):
        calls=[]
        def fake_fields(folder,settings,cancel_folder=None):
            calls.append(settings['optical_heat_W_cm3'])
            write_json(folder/'fields.json',{'files':['fake.vtu']})
        result=dict(z_grid=[0.,1.],P_plus=[1.,1.],P_minus=[1.,1.],P_opt=1.,configuration=default_config())
        settings=dict(configuration=default_config(),outer_iterations=3,relaxation=.5,outer_tolerance=.01,absorption_fraction=1.)
        with tempfile.TemporaryDirectory() as tmp, patch('cae_coupling.run_fields',side_effect=fake_fields), \
             patch('cae_coupling.read_vtu',return_value=(None,None,None)), \
             patch('cae_coupling.mqw_temperature',return_value=(300.,1.)), \
             patch('cae_coupling.solve_1d',return_value=result):
            state,message=run_coupled(Path(tmp),settings)
            report=json.loads((Path(tmp)/'coupling.json').read_text())
        self.assertEqual(calls,[0.,10.,15.])
        self.assertFalse(report['converged'])
        self.assertEqual(state,'candidate')
        self.assertIn('not converged',message)

    def test_four_sections_render_and_preserve_options(self):
        from streamlit.testing.v1 import AppTest
        app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=120).run()
        self.assertFalse(app.exception)
        for section in (1,2,3,0,2):
            app.radio(key='simulator_workspace').set_value(section).run()
            self.assertFalse(app.exception)
            self.assertTrue(any(b.label=='Run configured task' for b in app.button))
        app.number_input(key='option_longitudinal_nodes').set_value(71).run()
        app.radio(key='simulator_workspace').set_value(0).run()
        app.radio(key='simulator_workspace').set_value(2).run()
        self.assertEqual(app.number_input(key='option_longitudinal_nodes').value,71)


if __name__=='__main__':
    unittest.main()

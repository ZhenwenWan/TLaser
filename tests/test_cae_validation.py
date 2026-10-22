import json
from copy import deepcopy
from pathlib import Path
import unittest
from cae_validation import longitudinal_validation, coupled_validation

EXAMPLES=Path(__file__).resolve().parents[1]/'validation/solver_baseline'


class ValidationTests(unittest.TestCase):
    def test_independent_checks_reject_corrupted_carriers_and_mirror(self):
        baseline=json.loads((EXAMPLES/'longitudinal/longitudinal.json').read_text())
        self.assertTrue(longitudinal_validation(baseline)['numerical_checks_passed'])
        bad=deepcopy(baseline); bad['N'][20]*=1.2
        checks=longitudinal_validation(bad)['checks']
        self.assertFalse(next(v for v in checks if v['check']=='Local carrier balance')['passed'])
        bad=deepcopy(baseline); bad['P_plus'][0]*=1.1
        checks=longitudinal_validation(bad)['checks']
        self.assertFalse(next(v for v in checks if v['check']=='Rear mirror boundary')['passed'])

    def test_outer_convergence_does_not_hide_transverse_diagnostic_failure(self):
        folder=EXAMPLES/'coupled'
        settings=json.loads((folder/'request.json').read_text())['settings']
        validation=coupled_validation(folder,settings)
        self.assertTrue(validation['outer_converged'])
        self.assertFalse(validation['numerical_checks_passed'])
        failed=[r['check'] for r in validation['checks'] if not r['passed']]
        self.assertEqual(failed,['Nonfinite solver diagnostics'])
        saved=json.loads((folder/'validation.json').read_text())
        self.assertEqual(saved['checks'],validation['checks'])

    def test_bundled_examples_render_without_local_jobs(self):
        from streamlit.testing.v1 import AppTest
        code="""from unittest.mock import patch
from device_model import default_config
from cae_workspace import render_workspace
with patch('cae_workspace.read_jobs',return_value=[]), patch('cae_ui.read_jobs',return_value=[]):
    render_workspace(default_config(),lambda en,cn:en)
"""
        app=AppTest.from_string(code,default_timeout=120).run()
        for choice in (2,3):
            app.radio(key='simulator_workspace').set_value(choice).run()
            self.assertFalse(app.exception)
            self.assertTrue(app.radio(key='result_source_'+('longitudinal' if choice==2 else 'coupled')).value)
            self.assertTrue(any('Numerical validation' in m.value for m in app.markdown))
        self.assertTrue(any('Validation is incomplete' in w.value for w in app.warning))


if __name__=='__main__':
    unittest.main()

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from mesh_ui import preflight,displayed_mesh

class MeshUITests(unittest.TestCase):
    def test_preflight(self):
        with tempfile.TemporaryDirectory() as tmp:
            executable=Path(tmp)/'gmsh.exe';executable.touch()
            settings=dict(gmsh=str(executable),scale=1.,lateral_scale=1.,vertical_scale=1.)
            self.assertEqual(preflight(settings)['gmsh'],str(executable.resolve()))
            with self.assertRaises(ValueError): preflight({**settings,'scale':0.})
            with self.assertRaises(ValueError): preflight({**settings,'gmsh':str(executable)+'missing'})

    def test_failed_run_retains_completed_mesh(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);(folder/'mesh').mkdir();(folder/'mesh/mesh.nodes').touch();(folder/'mesh.zip').touch()
            jobs=[('new',{},dict(state='failed')),('old',{},dict(state='completed'))]
            with patch('mesh_ui.job_path',return_value=folder):
                self.assertEqual(displayed_mesh(jobs),folder)
            self.assertIsNone(displayed_mesh([]))

    def test_clean_reference_view_and_invalid_generate(self):
        script="from mesh_ui import render_mesh\nfrom device_model import default_config\nrender_mesh(default_config(),lambda en,cn:en)"
        with patch('mesh_ui.read_jobs',return_value=[]),patch('cae_workspace.read_jobs',return_value=[]):
            app=AppTest.from_string(script,default_timeout=60).run()
            self.assertFalse(app.exception)
            self.assertEqual([t.label for t in app.tabs],['Visualization & results','Configure & run'])
            labels=[x.label for x in app.expander]
            self.assertNotIn('Model details',labels)
            self.assertNotIn('Validated mesh examples',labels)
            self.assertIn('Mesh details',labels)
            self.assertFalse(app.metric)
            self.assertFalse(any(b.label=='Refresh job results' for b in app.button))
            self.assertFalse(any(s.label=='Saved runs' for s in app.selectbox))
            app.text_input(key='option_mesh_gmsh').set_value('missing-gmsh.exe').run()
            with patch('mesh_ui.start_job') as start:
                app.button(key='run_mesh').click().run()
                start.assert_not_called()
            self.assertTrue(any('Gmsh executable not found' in e.value for e in app.error))
            app.radio(key='mesh_view').set_value('3D').run()
            self.assertFalse(app.exception)

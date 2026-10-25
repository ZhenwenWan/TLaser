import json
import tempfile
import unittest
from pathlib import Path
import numpy as np
from cae_tetra import grid,validate,run_tetra,boundary_faces
from cad_dimensions import defaults
from mesh_ui import preflight

class TetraTests(unittest.TestCase):
    def test_reference_volume_and_shared_faces(self):
        folder=Path(__file__).resolve().parents[1]/'validation/tetrahedral/reference'
        with np.load(folder/'tetra.npz') as data:
            points,tets,bodies=data['points'],data['tetrahedra'],data['bodies']
        model=json.loads((folder/'geometry.json').read_text())
        report,faces=validate(points,tets,bodies,model)
        self.assertEqual(report['material_regions'],15)
        self.assertGreater(report['shared_interface_triangles'],0)
        self.assertEqual(tets.shape[1],4)
        with self.assertRaises(ValueError): validate(points,tets[:-1],bodies[:-1],model)
        bad=points.copy();bad[0]=bad[1]
        with self.assertRaises(ValueError): validate(bad,tets,bodies,model)
        rows=np.loadtxt(folder/'mesh/mesh.elements',dtype=int)
        self.assertTrue(np.all(rows[:,2]==504))
        self.assertEqual(rows.shape[1],7)
        boundaries=np.loadtxt(folder/'mesh/mesh.boundary',dtype=int)
        for row in boundaries:
            self.assertEqual(row[4],303)
            for parent in row[2:4]:
                if parent:
                    self.assertTrue(set(row[5:]).issubset(set(rows[parent-1,3:])))

    def test_transverse_solver_rejects_tetrahedra(self):
        from unittest.mock import patch
        from cae_elmer import run_fields
        from device_model import default_config
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); job=root/'meshjob'; job.mkdir()
            (job/'status.json').write_text(json.dumps(dict(state='completed')))
            (job/'tetra.npz').touch()
            output=root/'solver'; output.mkdir()
            settings=dict(lasers_root=str(root),mesh_job='test',temperature=298.,p_potential=.57724,
                          frequency=1.934e14,iterations=15,tolerance=1e-4,configuration=default_config())
            with patch('cae_elmer.runtime',return_value=(root,root,root/'solver.exe',root)), \
                 patch('cae_elmer.job_path',return_value=job), patch('cae_elmer.subprocess.Popen') as launch:
                with self.assertRaisesRegex(ValueError,'2D triangular mesh'): run_fields(output,settings)
                launch.assert_not_called()
            (output/'case').rmdir()
            (job/'section.json').write_text('{}')
            with patch('cae_elmer.runtime',return_value=(root,root,root/'solver.exe',root)), \
                 patch('cae_elmer.job_path',return_value=job), patch('cae_elmer.subprocess.Popen') as launch:
                with self.assertRaisesRegex(ValueError,'matching physics/material mapping'): run_fields(output,settings)
                launch.assert_not_called()

    def test_changed_cad_and_resource_limit(self):
        d=defaults(100.);d.update(substrate_height=120.,chip_width=150.,isolation_width=60.)
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            settings=dict(dimension=3,cad_dimensions=d,target_size_um=20.,min_size_um=.02,max_size_um=40.)
            self.assertEqual(preflight(settings),settings)
            self.assertEqual(run_tetra(folder,settings)[0],'completed')
            report=json.loads((folder/'mesh.json').read_text())
            self.assertAlmostEqual(report['regions'][0]['volume_um3'],100.*150.*120.)
        with self.assertRaises(ValueError): grid(dict(target_size_um=.02,min_size_um=.01,max_size_um=.1))

    def test_view_cutaway(self):
        from streamlit.testing.v1 import AppTest
        folder=Path(__file__).resolve().parents[1]/'validation/tetrahedral/reference'
        script="from pathlib import Path\nfrom tetra_ui import tetra_view\ntetra_view(Path("+repr(str(folder))+"),lambda en,cn:en)"
        app=AppTest.from_string(script,default_timeout=60).run()
        self.assertFalse(app.exception)
        app.slider(key='tetra_cut').set_value(50).run()
        self.assertFalse(app.exception)
        app.selectbox(key='tetra_part').set_value(4).run()
        self.assertFalse(app.exception)

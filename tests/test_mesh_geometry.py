"""Dimension scaling, legacy settings and independent mesh acceptance checks."""
import json
import tempfile
import shutil
import unittest
from unittest.mock import patch
from pathlib import Path
import numpy as np
from cae_mesh import ROOT, scaled_model, validate_mesh
from cae_workspace import decode_configuration

class MeshGeometryTests(unittest.TestCase):
    def test_topology_and_region_measure_scaling(self):
        baseline=scaled_model()
        scaled=scaled_model(1.4,.8)
        for a,b in zip(baseline['rectangles'],scaled['rectangles']):
            self.assertEqual(a['name'],b['name'])
            self.assertAlmostEqual(b['size_um']['width_y'],1.4*a['size_um']['width_y'])
            self.assertAlmostEqual(b['size_um']['height_z'],.8*a['size_um']['height_z'])
        self.assertAlmostEqual(scaled['parameters']['ridge_width_um'],4.2)
        self.assertAlmostEqual(scaled['parameters']['active_mqw_thickness_um'],.064)
        for value in (float('nan'),True,0.,3.):
            with self.assertRaises(ValueError): scaled_model(value,1.)

    def test_reference_and_corruption_rejection(self):
        report=validate_mesh(ROOT/'assets/elmer/mesh',scaled_model())
        self.assertTrue(report['passed'])
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/'mesh'
            shutil.copytree(ROOT/'assets/elmer/mesh',folder)
            data=np.loadtxt(folder/'mesh.nodes'); data[:,2]*=1.1
            np.savetxt(folder/'mesh.nodes',data)
            with self.assertRaises(ValueError): validate_mesh(folder,scaled_model())
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/'mesh'
            shutil.copytree(ROOT/'assets/elmer/mesh',folder)
            data=np.loadtxt(folder/'mesh.boundary',dtype=int)
            data[data[:,1]==2,1]=5
            np.savetxt(folder/'mesh.boundary',data,fmt='%d')
            with self.assertRaises(ValueError): validate_mesh(folder,scaled_model())

    def test_legacy_mesh_configuration(self):
        defaults=dict(gmsh='C:/gmsh/gmsh.exe',scale=1.,lateral_scale=1.,vertical_scale=1.)
        old=dict(schema_version=1,kind='mesh',settings=dict(gmsh='C:/gmsh/gmsh.exe',scale=1.))
        self.assertEqual(decode_configuration(json.dumps(old),'mesh',defaults),defaults)
        old['settings']['vertical_scale']=float('nan')
        with self.assertRaises(ValueError): decode_configuration(json.dumps(old),'mesh',defaults)

    def test_solver_rejects_changed_mesh_before_launch(self):
        from cae_elmer import run_fields
        from device_model import default_config
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); job=root/'meshjob'; job.mkdir()
            shutil.copytree(ROOT/'assets/elmer/mesh',job/'mesh')
            (job/'status.json').write_text(json.dumps(dict(state='completed')))
            (job/'geometry.json').write_text(json.dumps(scaled_model(1.4,.8)))
            output=root/'solver'; output.mkdir()
            settings=dict(lasers_root=str(root),mesh_job='test',temperature=298.,p_potential=.57724,
                          frequency=1.934e14,iterations=15,tolerance=1e-4,configuration=default_config())
            with patch('cae_elmer.runtime',return_value=(root,root,root/'solver.exe',root)), \
                 patch('cae_elmer.job_path',return_value=job), patch('cae_elmer.subprocess.Popen') as launch:
                with self.assertRaises(ValueError): run_fields(output,settings)
                launch.assert_not_called()

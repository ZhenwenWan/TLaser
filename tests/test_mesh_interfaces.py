import unittest
import tempfile
import shutil
from pathlib import Path
import numpy as np
from cae_mesh import ROOT,mesh_sizes,validate_interfaces

class InterfaceTests(unittest.TestCase):
    def test_size_order_and_defaults(self):
        self.assertIsNone(mesh_sizes({}))
        self.assertEqual(mesh_sizes(dict(target_size_um=.2))['min_size_um'],.045)
        for settings in [dict(target_size_um=.01),dict(min_size_um=.3,target_size_um=.2),dict(max_size_um=float('nan'))]:
            with self.assertRaises(ValueError): mesh_sizes(settings)

    def test_shared_boundaries_and_corruption(self):
        report=validate_interfaces(ROOT/'assets/elmer/mesh')
        self.assertEqual(len(report['regions_with_boundaries']),11)
        self.assertGreater(report['shared_interface_elements'],0)
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/'mesh';shutil.copytree(ROOT/'assets/elmer/mesh',folder)
            rows=np.loadtxt(folder/'mesh.boundary',dtype=int)
            np.savetxt(folder/'mesh.boundary',rows[1:],fmt='%d')
            with self.assertRaises(ValueError): validate_interfaces(folder)
            rows[0,2]=999999
            np.savetxt(folder/'mesh.boundary',rows,fmt='%d')
            with self.assertRaises(ValueError): validate_interfaces(folder)

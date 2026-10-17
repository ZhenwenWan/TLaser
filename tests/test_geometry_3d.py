"""Verify source material geometry, cavity adaptation, and inspection modes."""
import json
import unittest
from pathlib import Path
from device_geometry import geometry_3d
from device_model import default_config

class Geometry3DTests(unittest.TestCase):
    def test_source_parts_preserved(self):
        source = json.loads((Path(__file__).resolve().parents[1]/'assets/lasers_geometry.json').read_text())
        meshes = [t for t in geometry_3d(default_config()).data if t.type == 'mesh3d']
        self.assertEqual(len(meshes), 15)
        for part, mesh in zip(source['parts'], meshes):
            self.assertEqual(mesh.name, part['name'])
            self.assertEqual(mesh.color, part['color'])
            for axis in ('x','y','z'):
                self.assertAlmostEqual(max(mesh[axis])-min(mesh[axis]), part['size_um'][axis])
            edges = {}
            for tri in zip(mesh.i,mesh.j,mesh.k):
                for a,b in zip(tri,tri[1:]+tri[:1]):
                    e=tuple(sorted((a,b))); edges[e]=edges.get(e,0)+1
            self.assertTrue(all(v==2 for v in edges.values()))

    def test_cavity_and_inspection(self):
        c=default_config(); c['geometry']['L_um']=520.
        meshes=[t for t in geometry_3d(c).data if t.type=='mesh3d']
        self.assertEqual(max(meshes[4].x)-min(meshes[4].x),520.)
        self.assertAlmostEqual(max(meshes[13].x),-260.)
        self.assertAlmostEqual(min(meshes[14].x),260.)
        fig=geometry_3d(c,'CN',True,False,4.)
        self.assertEqual(fig.layout.scene.aspectmode,'data')
        self.assertIn('腔长',fig.layout.scene.xaxis.title.text)
        self.assertEqual(len([t for t in fig.data if t.type=='mesh3d']),11)
        # Exploded inspection must preserve each part's thickness.
        for mesh in (t for t in fig.data if t.type=='mesh3d'):
            self.assertAlmostEqual(max(mesh.z)-min(mesh.z),mesh.meta['size_um']['z'])
        self.assertEqual(fig.layout.scene.dragmode,'orbit')

if __name__=='__main__': unittest.main()

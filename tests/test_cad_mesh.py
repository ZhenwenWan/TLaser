import json
import unittest
from pathlib import Path
import numpy as np
from cae_section import section,write_geo
from cae_tetra import grid
from cad_dimensions import defaults
from mesh_grading import axis_report

class CADMeshTests(unittest.TestCase):
    def test_true_ridge_and_part_dimensions(self):
        d=defaults();d['ridge_width']=4.;d['chip_width']=300.
        cut=section(dict(cad_dimensions=d))
        self.assertEqual([p['body'] for p in cut['polygons']],list(range(1,14)))
        ridge=next(p for p in cut['polygons'] if p['body']==7)
        self.assertAlmostEqual(np.ptp(np.array(ridge['uv'])[:,0]),4.)
        self.assertAlmostEqual(ridge['area_um2'],4.*d['ridge_height'])
        self.assertEqual(cut['cad']['parts'][6]['size_um']['y'],4.)

    def test_oblique_and_longitudinal_cuts(self):
        for normal in ([1,.3,.2],[0,1,0],[0,0,1]):
            cut=section(dict(cut_normal=normal,cut_point=[0,0,50]))
            for p in cut['polygons']:
                world=np.array(cut['origin'])+np.array(p['uv'])[:,0,None]*cut['u']+np.array(p['uv'])[:,1,None]*cut['v']
                self.assertTrue(np.allclose((world-cut['origin'])@np.array(cut['normal']),0))
                part=cut['cad']['parts'][p['body']-1];center=np.array(list(part['center_um'].values()));size=np.array(list(part['size_um'].values()))
                self.assertTrue(np.all(world>=center-size/2-1e-8))
                self.assertTrue(np.all(world<=center+size/2+1e-8))
        for settings in (dict(cut_normal=[0,0,0]),dict(cut_point=[10000,0,0]),dict(cut_point=[float('nan'),0,0])):
            with self.assertRaises(ValueError):section(settings)

    def test_graded_volume_preserves_planes(self):
        model,axes,spans,count=grid({})
        self.assertLess(count,1500000)
        self.assertLess(max(axis_report(axes)['max_adjacent_axis_interval_ratio']),1.4)
        for part in model['parts']:
            for i,a in enumerate('xyz'):
                for sign in (-1,1):
                    coordinate=part['center_um'][a]+sign*part['size_um'][a]/2
                    self.assertLess(np.min(abs(axes[i]-coordinate)),1e-8)

    def test_section_controls(self):
        from streamlit.testing.v1 import AppTest
        from unittest.mock import patch
        script="from mesh_ui import render_mesh\nfrom device_model import default_config\nrender_mesh(default_config(),lambda en,cn:en)"
        with patch('mesh_ui.read_jobs',return_value=[]):
            app=AppTest.from_string(script,default_timeout=60).run()
            app.radio(key='mesh_dimension').set_value('2D').run()
            self.assertFalse(app.exception)
            app.number_input(key='cut_normal_x').set_value(0.).run()
            with patch('mesh_ui.start_job') as start:
                app.button(key='run_mesh').click().run();start.assert_not_called()
            self.assertTrue(any('nonzero' in e.value for e in app.error))

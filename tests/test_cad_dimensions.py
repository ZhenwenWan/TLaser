import unittest
from cad_dimensions import defaults,assembly,reference,validate,DIMENSIONS
from device_model import default_config,loads,dumps
from device_geometry import geometry_3d

class CADDimensionsTests(unittest.TestCase):
    def test_reference_reproduction(self):
        for a,b in zip(assembly(defaults())['parts'],reference()['parts']):
            for field in ('center_um','size_um'):
                for axis in 'xyz': self.assertAlmostEqual(a[field][axis],b[field][axis])
        self.assertEqual(len(DIMENSIONS),16)
        self.assertEqual(len({key for _,_,key,_ in DIMENSIONS}),16)

    def test_dependencies_and_independent_equal_heights(self):
        d=defaults(520.);d.update(chip_width=300.,ridge_width=4.,lower_sch_height=.3,shoulder_height=.6)
        parts=assembly(d)['parts']
        self.assertTrue(all(p['size_um']['x']==520. for p in parts[:13]))
        for i in [0,1,2,3,4,5,12,13,14]: self.assertEqual(parts[i]['size_um']['y'],300.)
        self.assertEqual(parts[7]['size_um'],parts[8]['size_um'])
        self.assertEqual(parts[7]['size_um']['y'],148.)
        self.assertEqual(parts[11]['size_um']['y'],6.4)
        self.assertEqual(parts[3]['size_um']['z'],.3)
        self.assertEqual(parts[5]['size_um']['z'],.25)
        for a,b in zip(parts[:5],parts[1:6]):
            self.assertAlmostEqual(a['center_um']['z']+a['size_um']['z']/2,b['center_um']['z']-b['size_um']['z']/2)
        self.assertEqual(parts[13]['size_um'],parts[14]['size_um'])

    def test_roundtrip_and_invalid_geometry(self):
        c=default_config();c['cad_dimensions']=defaults();c['cad_dimensions']['substrate_height']=150.
        self.assertEqual(loads(dumps(c)),c)
        self.assertEqual(geometry_3d(c).data[0].meta['size_um']['z'],150.)
        for change in [dict(chip_width=100.),dict(shoulder_height=1.6),dict(mqw_height=float('nan'))]:
            with self.assertRaises(ValueError): validate({**defaults(),**change})
        c['cad_dimensions']['length']=400.
        with self.assertRaises(ValueError): dumps(c)

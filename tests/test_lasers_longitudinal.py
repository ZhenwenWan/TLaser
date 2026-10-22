import unittest
import numpy as np
from cae_coupling import solve_1d
from device_model import default_config


class LasersLongitudinalTests(unittest.TestCase):
    def test_lasers_reference_power_regression(self):
        # Original Lasers Tools/quasi_3d_synthesizer.py, SHA256
        # ba0962f8092534e565d0cde6c2912f8c7e467d7c1317102fc8be937f14f3cc56.
        # Same default TLaser geometry/current/temperature, 401-node Euler solve.
        reference_power=.002506211066441665
        result=solve_1d(dict(configuration=default_config(),nodes=401))
        self.assertLess(abs(result['P_opt']/reference_power-1),3e-4)

    def test_active_laser_balances_and_mirrors_without_probe(self):
        c=default_config(); r=solve_1d(dict(configuration=c,nodes=51))
        self.assertTrue(r['converged'],r['residual_history'])
        self.assertGreater(r['P_opt'],0.)
        self.assertAlmostEqual(r['P_plus'][0],c['optical']['R1']*r['P_minus'][0],places=10)
        self.assertAlmostEqual(r['P_minus'][-1],c['optical']['R2']*r['P_plus'][-1],places=10)
        n=np.array(r['N']); g=np.array(r['g']); total=np.array(r['P_plus'])+r['P_minus']
        temp=r['active_temperature_K']; area=r['active_area_cm2']; length=c['geometry']['L_um']*1e-4
        generation=c['operating']['I_active_A']/(1.60213377e-19*length*area)
        recombination=1e8*n+1e-10*n*n+3e-29*(temp/300)**2*n**3
        stimulated=g*total/(area*6.62607015e-34*r['frequency'])
        np.testing.assert_allclose((recombination+stimulated)/generation,1.,rtol=1e-8)
        self.assertGreater(np.ptp(n),1e14)

    def test_symmetric_cavity_and_current_response(self):
        c=default_config(); c['optical'].update(R1=.3,R2=.3)
        high=solve_1d(dict(configuration=c,nodes=71))
        np.testing.assert_allclose(high['P_plus'],high['P_minus'][::-1],rtol=1e-6)
        np.testing.assert_allclose(high['N'],high['N'][::-1],rtol=1e-6)
        c['operating']['I_active_A']=.01
        low=solve_1d(dict(configuration=c,nodes=31))
        self.assertTrue(low['converged'])
        self.assertLess(low['P_opt'],high['P_opt'])

    def test_actual_mesh_area_and_temperature_enter_carrier_equations(self):
        settings=dict(configuration=default_config(),nodes=31)
        baseline=solve_1d(settings)
        changed=solve_1d({**settings,'_active_area_cm2':5e-9},330.)
        self.assertEqual(changed['active_area_cm2'],5e-9)
        self.assertEqual(changed['active_temperature_K'],330.)
        self.assertNotAlmostEqual(changed['P_opt'],baseline['P_opt'],places=6)

    def test_passive_configuration_rejected_and_cancellation(self):
        with self.assertRaises(ValueError):
            solve_1d(dict(configuration=default_config(),optical_input_W=.001))
        def cancel(): raise InterruptedError('cancelled')
        with self.assertRaises(InterruptedError):
            solve_1d(dict(configuration=default_config()),check=cancel)


if __name__=='__main__':
    unittest.main()

import unittest
import numpy as np
from cae_coupling import solve_1d
from device_model import default_config
from simulator.longitudinal_multiphysics import maxwell


class MultiphysicsTests(unittest.TestCase):
    def test_maxwell_matches_analytic_lossy_fabry_perot(self):
        z=np.linspace(0,.03,31); zero=np.zeros(31); temperature=np.full(31,300.)
        frequency=1.934e14; index=3.35; alpha=10.; incident=.001
        wave=maxwell(z,zero,zero,temperature,frequency,1e-8,alpha,[.9,.05],incident,index)
        phase=2*np.pi*frequency/2.99792458e10*index*z[-1]
        expected=.1*.95*incident*np.exp(-alpha*z[-1])/abs(1-np.sqrt(.9*.05)*np.exp(2j*phase-alpha*z[-1]))**2
        self.assertAlmostEqual(.95*wave['P_plus'][-1]/expected,1.,places=8)
        self.assertLess(wave['maxwell_residual'],1e-12)
        self.assertGreater(len(wave['wave_z_cm']),10000)

    def test_all_equations_converge_and_carrier_balance(self):
        c=default_config(); r=solve_1d(dict(configuration=c,nodes=31))
        self.assertTrue(r['converged'],r['residual_history'][-1])
        for key in ('electron_density_cm3','hole_density_cm3','potential_V','temperature_K','EM_real','EM_imag'):
            self.assertTrue(np.isfinite(r[key]).all())
        self.assertGreater(min(r['temperature_K']),c['operating']['T0_K'])
        n=np.array(r['electron_density_cm3']); p=np.array(r['hole_density_cm3']); temp=np.array(r['temperature_K'])
        excess=n*p-1.05494e10**2
        recombination=excess/(1e-8*(n+p+2*1.05494e10))+1e-10*excess+1.5e-29*(n+p)*excess*(temp/300)**2
        z=np.array(r['z_grid']); area=c['geometry']['w_um']*c['geometry']['d_um']*1e-8
        generated=c['operating']['I_active_A']/1.602176634e-19+np.trapezoid(r['optical_heat_W_cm3'],z)*area/(6.62607015e-34*r['frequency'])
        self.assertAlmostEqual(np.trapezoid(recombination,z)*area/generated,1.,places=5)

    def test_zero_drive_has_zero_waves_and_iteration_limit_is_not_success(self):
        r=solve_1d(dict(configuration=default_config(),nodes=11,optical_input_W=0.))
        self.assertTrue(r['converged'])
        self.assertEqual(r['P_opt'],0.)
        self.assertTrue(np.all(np.array(r['EM_real'])==0))
        r=solve_1d(dict(configuration=default_config(),nodes=11,multiphysics_iterations=2))
        self.assertFalse(r['converged'])

    def test_cancellation_and_invalid_options(self):
        def cancel(): raise InterruptedError('cancelled')
        with self.assertRaises(InterruptedError):
            solve_1d(dict(configuration=default_config()),check=cancel)
        with self.assertRaises(ValueError):
            solve_1d(dict(configuration=default_config(),thermal_sink=-1.))


if __name__=='__main__':
    unittest.main()

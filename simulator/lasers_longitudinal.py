"""Lasers Task 1.6: active longitudinal carrier balance and optical transport.

Equations follow Lasers/Tools/quasi_3d_synthesizer.py. Adaptive collocation
replaces its clipped forward-Euler shooting; no coherent probe is injected.
"""
import numpy as np
from scipy.integrate import solve_bvp
from simulator.quasi_3d_synthesizer import Quasi3DSimulator

DEFAULTS = dict(longitudinal_tolerance=1e-4, longitudinal_max_nodes=4001)


def solve(c, settings, temperature, check=lambda: None):
    check()
    tolerance=settings.get('longitudinal_tolerance',1e-4)
    maximum=settings.get('longitudinal_max_nodes',4001)
    if not np.isfinite(tolerance) or not 1e-7<=tolerance<=.01:
        raise ValueError('Invalid longitudinal tolerance')
    if type(maximum) is not int or not 401<=maximum<=20001:
        raise ValueError('Invalid longitudinal maximum mesh nodes')
    geom,opt,phys=c['geometry'],c['optical'],c['physical']
    area=float(settings.get('_active_area_cm2',geom['w_um']*geom['d_um']*1e-8))
    if not np.isfinite(area) or area<=0:
        raise ValueError('Active area must be positive')
    sim=Quasi3DSimulator(L_cavity=geom['L_um']*1e-4,R1=opt['R1'],R2=opt['R2'],
        M=settings.get('nodes',51),w_active=geom['w_um']*1e-4,d_active=area/(geom['w_um']*1e-4),
        T0=temperature,alpha_i=phys['alpha_i'])
    sim.Gamma=phys['Gamma']; sim.C_recomb*=phys['C_mult']
    sim.R_series=phys['R_series']; sim.R_shunt=phys['R_shunt']
    frequency=float(settings.get('frequency',1.934e14)); energy=sim.h_planck*frequency
    current=c['operating']['I_active_A']; generation=current/(sim.q0*sim.L_cavity*area)
    def carriers(power):
        x=np.full_like(power,np.log(1.5e18))
        for _ in range(60):
            n=np.exp(x); gain=np.maximum(sim.g0_gain*(x-np.log(sim.N_tr)),0.)
            recombination=sim.A_recomb*n+sim.B_recomb*n*n+sim.C_recomb*n**3
            residual=generation-recombination-gain*power/(area*energy)
            derivative=-sim.A_recomb*n-2*sim.B_recomb*n*n-3*sim.C_recomb*n**3
            derivative-=np.where(gain>0,sim.g0_gain*power/(area*energy),0.)
            step=np.clip(-residual/derivative,-2.,2.); x+=step
            if np.max(abs(step))<1e-11: break
        n=np.exp(x); gain=np.maximum(sim.g0_gain*(x-np.log(sim.N_tr)),0.)
        balance=(generation-sim.A_recomb*n-sim.B_recomb*n*n-sim.C_recomb*n**3-gain*power/(area*energy))/generation
        return n,gain,balance
    def equations(z,y):
        check()
        power=np.exp(np.clip(y,-60,10))
        n,gain,_=carriers(power.sum(axis=0))
        modal=sim.Gamma*gain-sim.alpha_i
        spontaneous=sim.beta_sp*sim.B_recomb*n*n*area*energy
        return np.vstack((modal+spontaneous/power[0],-modal-spontaneous/power[1]))
    def boundaries(left,right):
        return np.array([left[0]-left[1]-np.log(sim.R1),right[1]-right[0]-np.log(sim.R2)])
    initial=sim.solve_longitudinal(current/sim.L_cavity,freq=frequency)
    z=initial['z_grid']; guess=np.log(np.maximum([initial['P_plus'],initial['P_minus']],1e-15))
    solution=solve_bvp(equations,boundaries,z,guess,tol=tolerance,max_nodes=maximum)
    check()
    y=solution.sol(z); power=np.exp(y)
    n,gain,balance=carriers(power.sum(axis=0))
    if not np.isfinite(power).all() or np.any(y<-60) or np.any(y>10):
        raise ValueError('Longitudinal solve left the supported positive-power range')
    mirror=float(np.max(abs(boundaries(y[:,0],y[:,-1]))))
    carrier=float(np.max(abs(balance))); transport=float(np.max(solution.rms_residuals))
    converged=bool(solution.success and max(mirror,carrier,transport)<=tolerance)
    front=(1-sim.R2)*power[0,-1]; rear=(1-sim.R1)*power[1,0]
    return dict(z_grid=z.tolist(),N=n.tolist(),g=gain.tolist(),P_plus=power[0].tolist(),P_minus=power[1].tolist(),
        photon_density_cm3=(power.sum(axis=0)/(area*energy*sim.v_g)).tolist(),
        P_opt=float(front+rear),P_front_W=float(front),P_rear_W=float(rear),
        I_total=float(initial['I_total']),P_elec=float(initial['P_elec']),WPE=float((front+rear)/initial['P_elec']),
        active_temperature_K=temperature,active_area_cm2=area,converged=converged,
        model='Lasers Task 1.6 active gain / bidirectional photon transport / spatial hole burning',
        source_methodology='Lasers/Tools/quasi_3d_synthesizer.py; Pages/Projects/Lasers/index.html Task 1.6',
        solver_options=dict(longitudinal_tolerance=tolerance,longitudinal_max_nodes=maximum),
        residual_history=[dict(iteration=int(solution.niter),carrier=carrier,mirror=mirror,transport=transport)],
        adaptive_nodes=int(solution.x.size),solver_message=solution.message,
        electrical_model='TLaser series/shunt estimate; not an extracted transverse terminal current',
        optical_scope='Active intensity transport with spontaneous/stimulated emission; complex transverse EM fields are solved in Elmer',
        boundaries='P+(0)=R1 P-(0); P-(L)=R2 P+(L); no external optical drive')

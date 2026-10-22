"""Cross-section-averaged steady drift diffusion, heat and driven Maxwell model.

Units: cm, s, V, K, W. Optical fields are power-normalized (sqrt(W)).
This is a driven passive cavity, not a self-lasing eigenmode calculation.
"""
import numpy as np
from scipy.linalg import solve_banded
from scipy.optimize import least_squares, brentq
from scipy.sparse import lil_matrix

DEFAULTS = dict(axial_bias=0., optical_input_W=.001, thermal_conductivity=.03,
                thermal_sink=1e7, refractive_index=3.35, multiphysics_iterations=30,
                multiphysics_tolerance=1e-4)


def bernoulli(x):
    x = np.asarray(x)
    return np.divide(x, np.expm1(np.clip(x, -700, 700)), out=np.ones_like(x), where=abs(x)>1e-8)


def maxwell(z, n, p, temperature, frequency, area, alpha, reflectivities, input_power, index):
    """Scalar 1D Helmholtz, partially reflecting facets and left incident wave.

    Optical mesh resolves the in-medium wavelength with at least 24 points.
    Drude plasma dispersion and thermo-optic shift feed electrical/thermal fields
    into Maxwell; absorption feeds photogeneration and heat back to the PDEs.
    """
    c = 2.99792458e10
    k0 = 2*np.pi*frequency/c
    # Effective electron/hole masses 0.08/0.6 m0; density conversion cm^-3 -> m^-3.
    plasma = 1.602176634e-19**2 * 1e6*(n/.08+p/.6)/(8.8541878128e-12*9.1093837e-31*(2*np.pi*frequency)**2)
    eps = (index+2e-4*(temperature-300))**2-plasma
    if np.min(eps) <= 1:
        raise ValueError('Carrier plasma exceeds the supported dielectric regime')
    count = max(101, int(np.ceil(z[-1]*k0*np.sqrt(np.max(eps))*24/(2*np.pi)))+1)
    if count > 300000:
        raise ValueError('Optical mesh exceeds 300000 nodes; reduce frequency or cavity length')
    zw = np.linspace(0, z[-1], count); dz = zw[1]
    k = k0*np.sqrt(np.interp(zw,z,eps)) + .5j*alpha
    ab = np.zeros((3,count),complex); ab[0,1:]=1; ab[2,:-1]=1
    # Exponentially fitted stencil avoids accumulating numerical phase error
    # over hundreds of optical wavelengths in a uniform cavity.
    ab[1] = -2*np.cos(dz*k)
    r1,r2 = np.sqrt(reflectivities)
    ab[1,0] += 2j*np.sin(dz*k[0])*(1-r1)/(1+r1); ab[0,1]=2
    ab[1,-1] += 2j*np.sin(dz*k[-1])*(1-r2)/(1+r2); ab[2,-2]=2
    rhs = np.zeros(count,complex)
    # Incident amplitude transmitted through the left facet (lossless coating).
    drive = np.sqrt(input_power*(1-r1*r1))
    rhs[0] = 4j*np.sin(dz*k[0])*drive/(1+r1)
    field = solve_banded((1,1),ab,rhs)
    derivative = np.gradient(field,zw,edge_order=2)
    derivative[1:-1] *= (dz*k/np.sin(dz*k))[1:-1]
    derivative[0] = -1j*k[0]*(1-r1)/(1+r1)*field[0]+2j*k[0]*drive/(1+r1)
    derivative[-1] = 1j*k[-1]*(1-r2)/(1+r2)*field[-1]
    forward = abs((field+derivative/(1j*k))/2)**2
    backward = abs((field-derivative/(1j*k))/2)**2
    intensity = np.interp(z,zw,forward+backward)
    error=ab[1]*field-rhs
    error[:-1]+=ab[0,1:]*field[1:]; error[1:]+=ab[2,:-1]*field[:-1]
    wave_residual=float(np.max(abs(error))/max(4*np.max(abs(field)),1e-30))
    return dict(wave_z_cm=zw, EM_real=field.real, EM_imag=field.imag, maxwell_residual=wave_residual,
                P_plus=np.interp(z,zw,forward),P_minus=np.interp(z,zw,backward),
                optical_heat_W_cm3=alpha*intensity/area,
                photon_density_cm3=intensity/(area*6.62607015e-34*frequency*c/index))


def solve(c, settings, sink_temperature, check=lambda: None):
    options = {**DEFAULTS, **{k:settings[k] for k in DEFAULTS if k in settings}}
    bounds = dict(axial_bias=(-1,1),optical_input_W=(0,1),thermal_conductivity=(.001,10),
                  thermal_sink=(1e3,1e9),refractive_index=(1.5,5),
                  multiphysics_iterations=(2,100),multiphysics_tolerance=(1e-7,.01))
    for key,(low,high) in bounds.items():
        if not np.isfinite(options[key]) or not low<=options[key]<=high:
            raise ValueError('Invalid '+key)
    if type(options['multiphysics_iterations']) is not int:
        raise ValueError('Multiphysics iterations must be an integer')
    m=settings.get('nodes',51); freq=settings.get('frequency',1.934e14)
    geom=c['geometry']; area=geom['w_um']*geom['d_um']*1e-8
    z=np.linspace(0,geom['L_um']*1e-4,m); dz=z[1]
    q=1.602176634e-19; ns=1e18; vt=8.617333262e-5*sink_temperature
    injection=c['operating']['I_active_A']/(q*z[-1]*area)
    scale=max(injection,1e24); energy=6.62607015e-34*freq
    auger=3e-29*c['physical']['C_mult']; ni=1.05494e10
    density=brentq(lambda a:1e8*a+1e-10*a*a+auger*a**3-injection,1e8,1e21)
    x=np.zeros((4,m)); x[0]=np.linspace(0,options['axial_bias']/vt,m)
    x[1:3]=np.log(density/ns)
    # Block order: potential/Vt, log(n/ns), log(p/ns), temperature rise/10 K.
    pattern=lil_matrix((4*m,4*m))
    for block in range(4):
        for i in range(m):
            for other in range(4):
                pattern[block*m+i,other*m+max(0,i-1):other*m+min(m,i+2)]=1
    pattern=pattern.tocsr()
    heat=np.zeros(m); history=[]; converged=False
    def residual(flat):
        u,ln,lp,theta=flat.reshape(4,m)
        n,p=ns*np.exp(ln),ns*np.exp(lp); temp=sink_temperature+10*theta
        tedge=(temp[:-1]+temp[1:])/2; local_vt=8.617333262e-5*tedge
        du=np.diff(u)*vt/local_vt
        dn=500*(300/tedge)**1.5*local_vt; dp=150*(300/tedge)**1.5*local_vt
        fn=dn/dz*(n[:-1]*bernoulli(-du)-n[1:]*bernoulli(du))
        fp=dp/dz*(p[:-1]*bernoulli(du)-p[1:]*bernoulli(-du))
        # Insulating facets; half-sized boundary control volumes.
        volume=np.full(m,dz); volume[[0,-1]]*=.5
        divn=np.diff(np.r_[0.,fn,0.])/volume; divp=np.diff(np.r_[0.,fp,0.])/volume
        excess=n*p-ni**2
        srh=excess/(1e-8*(n+p+2*ni))
        rad=1e-10*excess; aug=.5*auger*(n+p)*excess*(temp/300)**2
        recombination=srh+rad+aug
        poisson=(p-n)/ns
        poisson[1:-1]+=12*8.8541878128e-14*vt/(q*ns)*np.diff(u,2)/dz**2
        poisson[0]=u[0]; poisson[-1]=u[-1]-options['axial_bias']/vt
        # Absorbed photons generate pairs; thermalization represented by the
        # nonradiative recombination energy, avoiding duplicate absorption heat.
        rn=(-divn+injection+heat/energy-recombination)/scale
        rp=(-divp+injection+heat/energy-recombination)/scale
        electric=-vt*np.diff(u)/dz
        joule=np.maximum(q*(fp-fn)*electric,0.)
        joule_nodes=np.r_[joule[0],.5*(joule[:-1]+joule[1:]),joule[-1]]
        flux=-options['thermal_conductivity']*np.diff(temp)/dz
        thermal=(-np.diff(np.r_[0.,flux,0.])/volume + energy*(srh+aug)+joule_nodes
                 -options['thermal_sink']*(temp-sink_temperature))/(scale*energy)
        return np.r_[poisson,rn,rp,thermal]
    lower=np.r_[np.full(m,-100.),np.full(2*m,-25.),np.full(m,(200-sink_temperature)/10)]
    upper=np.r_[np.full(m,100.),np.full(2*m,8.),np.full(m,(600-sink_temperature)/10)]
    for iteration in range(options['multiphysics_iterations']):
        check()
        solution=least_squares(residual,x.ravel(),jac_sparsity=pattern,bounds=(lower,upper),
                               max_nfev=150,ftol=1e-10,xtol=1e-10,gtol=1e-10)
        x=solution.x.reshape(4,m); n,p=ns*np.exp(x[1:3]); temp=sink_temperature+10*x[3]
        waves=maxwell(z,n,p,temp,freq,area,c['physical']['alpha_i'],
                      [c['optical']['R1'],c['optical']['R2']],options['optical_input_W'],options['refractive_index'])
        target=waves['optical_heat_W_cm3']
        feedback=float(np.max(abs(target-heat))/max(float(np.max(target)),1.))
        # Evaluate PDE residual against the NEW optical field, not the old source.
        old_heat=heat; heat=target
        blocks=np.max(abs(residual(x.ravel()).reshape(4,m)),axis=1)
        history.append(dict(iteration=iteration+1,poisson=float(blocks[0]),electron=float(blocks[1]),
                            hole=float(blocks[2]),heat=float(blocks[3]),optical_feedback=feedback,maxwell=waves['maxwell_residual']))
        converged=max(np.max(blocks),feedback,waves['maxwell_residual'])<=options['multiphysics_tolerance']
        if converged: break
        heat=.5*(old_heat+target)
    result=dict(z_grid=z,N=n,electron_density_cm3=n,hole_density_cm3=p,potential_V=x[0]*vt,
                electric_field_V_cm=-np.gradient(x[0]*vt,z),temperature_K=temp,**waves)
    result.update(active_temperature_K=float(np.mean(temp)),P_opt=float((1-c['optical']['R2'])*waves['P_plus'][-1]),
                  converged=bool(converged),residual_history=history,solver_options=options,
                  model='Cross-section-averaged drift-diffusion / heat / driven scalar Helmholtz',
                  optical_scope='Passive driven cavity with plasma and thermo-optic feedback; not self-lasing output',
                  boundaries='Uniform transverse pair injection; insulating carrier/heat facets; prescribed axial potentials; distributed transverse heat sink',
                  field_units='Power-normalized complex optical amplitude: sqrt(W)',
                  constants=dict(electron_mobility_cm2_Vs=500,hole_mobility_cm2_Vs=150,relative_permittivity=12,
                                 electron_effective_mass=.08,hole_effective_mass=.6,thermo_optic_per_K=2e-4))
    return {k:v.tolist() if isinstance(v,np.ndarray) else v for k,v in result.items()}

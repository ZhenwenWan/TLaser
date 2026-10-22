"""Numerical acceptance evidence; never equates solver completion with validation."""
import json
import re
import numpy as np
from cae_fields import read_vtu


def check(name, value, limit):
    finite=bool(np.isfinite(value))
    return dict(check=name,value=float(value) if finite else None,limit=float(limit),
                passed=bool(finite and abs(value)<=limit))


def longitudinal_validation(r):
    c=r['configuration']; p=c['physical']; g=c['geometry']; o=c['optical']
    z=np.asarray(r['z_grid']); n=np.asarray(r['N']); forward=np.asarray(r['P_plus']); backward=np.asarray(r['P_minus'])
    area=r['active_area_cm2']; temp=r['active_temperature_K']; energy=6.62607015e-34*r['frequency']
    gain=np.maximum(1200*np.exp(-(temp-300)/120)*np.log(n/(1e18*(temp/300)**1.5)),0.)
    generation=c['operating']['I_active_A']/(1.60213377e-19*g['L_um']*1e-4*area)
    recombination=1e8*n+1e-10*n*n+3e-29*p['C_mult']*(temp/300)**2*n**3
    balance=(generation-recombination-gain*(forward+backward)/(area*energy))/generation
    scale=max(float(np.max(forward+backward)),1e-30)
    facet=(1-o['R1'])*backward[0]+(1-o['R2'])*forward[-1]
    source=1e-4*1e-10*n*n*area*energy
    integrated=np.trapezoid((p['Gamma']*gain-p['alpha_i'])*(forward+backward)+2*source,z)
    tol=r['solver_options']['longitudinal_tolerance']
    residual=r['residual_history'][-1]
    checks=[check('Local carrier balance',np.max(abs(balance)),tol),
            check('Rear mirror boundary',(forward[0]-o['R1']*backward[0])/scale,tol),
            check('Front mirror boundary',(backward[-1]-o['R2']*forward[-1])/scale,tol),
            check('Gain consistency',np.max(abs(gain-np.asarray(r['g'])))/max(float(np.max(gain)),1.),tol),
            check('Facet output accounting',(r['P_opt']-facet)/max(abs(facet),1e-30),tol),
            check('Integrated photon transport',(facet-integrated)/max(abs(facet),abs(integrated),1e-30),max(1e-3,10*tol)),
            check('Adaptive transport residual',residual['transport'],tol),
            check('Finite positive carriers and powers',0. if all(np.isfinite(a).all() and np.all(a>0) for a in (n,forward,backward)) else 1.,0.),
            check('Nonlinear solver reported convergence',0. if r['converged'] else 1.,0.)]
    return dict(kind='longitudinal',checks=checks,numerical_checks_passed=all(v['passed'] for v in checks),
                scope='Numerical consistency of the Lasers reduced longitudinal equations; not measured-device qualification',
                metrics=dict(power_W=r['P_opt'],front_power_W=r['P_front_W'],rear_power_W=r['P_rear_W'],
                             temperature_K=temp,active_area_cm2=area,minimum_carrier_cm3=float(n.min()),maximum_carrier_cm3=float(n.max())))


def transverse_evidence(folder,tolerance):
    report=json.loads((folder/'fields.json').read_text())
    log=(folder/'solver.log').read_text(encoding='utf-8',errors='replace')
    pattern=r'ComputeChange:\s*SS\s*\(ITER=(\d+)\)\s*\(NRM,RELC\):\s*\(\s*(\S+)\s+(\S+)\s*\)\s*::\s*(\S+)'
    last={}
    for iteration,norm,relative,name in re.findall(pattern,log):
        last[name]=dict(iteration=int(iteration),relative_change=float(relative.replace('D','E')))
    checks=[]
    for name in ('carriers','temperature','vectorhelmholtz'):
        checks.append(check('Transverse '+name+' steady-state change',last.get(name,{}).get('relative_change',np.nan),tolerance))
    points,triangles,fields=read_vtu(folder/report['files'][-1])
    checks.append(check('Finite transverse fields',0. if all(np.isfinite(a).all() for a in fields.values()) else 1.,0.))
    warnings=report.get('warnings',[])
    nonfinite=list(dict.fromkeys(line.strip() for line in log.splitlines()
        if re.search(r'\bNaN\b|\bInfinity\b',line,re.I) and not re.search(r'any NaN.*:\s*F\s*$',line)))
    checks.append(check('Nonfinite solver diagnostics',len(nonfinite),0.))
    ranges={k:dict(minimum=float(v.min()),maximum=float(v.max())) for k,v in fields.items()}
    return dict(checks=checks,steady_state=last,warnings=warnings,field_ranges=ranges,
                scope='Final logged steady-state changes and finite-field/diagnostic checks; no experimental qualification')


def coupled_validation(folder,settings):
    coupling=json.loads((folder/'coupling.json').read_text())
    final=folder/coupling['final_folder']; r=json.loads((final/'longitudinal.json').read_text())
    longitudinal=longitudinal_validation(r)
    transverse=transverse_evidence(final,settings['tolerance'])
    row=coupling['history'][-1]; tol=coupling['tolerance']
    checks=[check('Outer heat mismatch',row['heat_residual'],tol),
            check('Outer temperature change',row['temperature_residual'] if row['temperature_residual'] is not None else np.nan,tol),
            check('MQW area handoff',(r['active_area_cm2']-row['area_cm2'])/row['area_cm2'],1e-12),
            check('MQW temperature handoff',r['active_temperature_K']-row['temperature_K'],1e-10),
            check('Outer loop reported convergence',0. if coupling['converged'] else 1.,0.)]
    all_checks=checks+longitudinal['checks']+transverse['checks']
    return dict(kind='coupled',checks=all_checks,numerical_checks_passed=all(v['passed'] for v in all_checks),
                outer_converged=coupling['converged'],longitudinal=longitudinal,transverse=transverse,
                metrics=dict(power_W=r['P_opt'],temperature_K=row['temperature_K'],iterations=len(coupling['history'])),
                scope='Averaged 1D–2D optothermal coupling; all gates include final transverse evidence. Outer convergence alone is insufficient.')

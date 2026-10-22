"""Independent 1D transport and relaxed 1D–2D optothermal fixed-point jobs."""
from copy import deepcopy
import json
import numpy as np
from cae_jobs import check_cancel, write_json
from cae_elmer import run_fields
from cae_fields import read_vtu
from cae_mesh import mqw_temperature
from device_model import validate_config
from simulator.quasi_3d_synthesizer import Quasi3DSimulator


def solve_1d(settings, temperature=None):
    c=validate_config(settings['configuration'])
    nodes=settings.get('nodes',51)
    frequency=float(settings.get('frequency',1.934e14))
    temp=float(settings.get('temperature',c['operating']['T0_K']) if temperature is None else temperature)
    if type(nodes) is not int or not 11<=nodes<=401:
        raise ValueError('Cavity nodes must be an integer in [11, 401]')
    if not np.isfinite([frequency,temp]).all() or not 1e13<=frequency<=1e15 or not 250<=temp<=450:
        raise ValueError('Temperature/frequency outside the supported solver range')
    g,o,p=c['geometry'],c['optical'],c['physical']
    sim=Quasi3DSimulator(L_cavity=g['L_um']*1e-4,w_active=g['w_um']*1e-4,d_active=g['d_um']*1e-4,
        R1=o['R1'],R2=o['R2'],T0=temp,alpha_i=p['alpha_i'],M=nodes)
    sim.Gamma=p['Gamma']; sim.C_recomb*=p['C_mult']
    sim.R_series,sim.R_shunt=p['R_series'],p['R_shunt']
    raw=sim.solve_longitudinal(c['operating']['I_active_A']/sim.L_cavity,freq=frequency)
    if not all(np.isfinite(v).all() for v in raw.values()):
        raise ValueError('Nonfinite longitudinal output')
    report={k:v.tolist() if isinstance(v,np.ndarray) else float(v) for k,v in raw.items()}
    report.update(active_temperature_K=temp,current_source='Configured active-region current',nodes=nodes,
                  frequency=frequency,configuration=c)
    return report


def run_longitudinal(folder,settings):
    check_cancel(folder)
    result=solve_1d(settings)
    write_json(folder/'longitudinal.json',result)
    return 'candidate','1D solve finished; review physical validity and discretization'


def heat_target(result, area_cm2, fraction):
    """Cavity-averaged distributed optical loss deposited uniformly in MQW."""
    z=np.asarray(result['z_grid'])
    power=np.asarray(result['P_plus'])+np.asarray(result['P_minus'])
    if not np.isfinite(area_cm2) or area_cm2<=0:
        raise ValueError('Invalid active-region mesh area')
    mean=float(np.trapezoid(power,z)/(z[-1]-z[0]))
    return fraction*result['configuration']['physical']['alpha_i']*mean/area_cm2


def run_coupled(folder,settings):
    count=settings.get('outer_iterations',8)
    relaxation=float(settings.get('relaxation',.5))
    tolerance=float(settings.get('outer_tolerance',.01))
    fraction=float(settings.get('absorption_fraction',1.))
    if type(count) is not int or not 2<=count<=30 or not np.isfinite([relaxation,tolerance,fraction]).all():
        raise ValueError('Invalid coupling configuration')
    if not 0<relaxation<=1 or not 1e-6<=tolerance<=.1 or not 0<fraction<=1:
        raise ValueError('Invalid relaxation, tolerance or absorption fraction')
    solve_1d(settings)  # Validate all 1D inputs before launching an external solver.
    history=[]; heat=0.; previous_temperature=None; converged=False
    for iteration in range(1,count+1):
        check_cancel(folder)
        step=folder/f'iteration_{iteration:03d}'; step.mkdir()
        transverse=deepcopy(settings); transverse['optical_heat_W_cm3']=heat
        write_json(step/'request.json',transverse)
        run_fields(step,transverse,cancel_folder=folder)
        field_report=json.loads((step/'fields.json').read_text())
        points,_,fields=read_vtu(step/field_report['files'][-1])
        temp,area=mqw_temperature(step,points,fields)
        result=solve_1d(settings,temp)
        target=heat_target(result,area,fraction)
        if not np.isfinite(target) or target>1e10:
            raise ValueError('Optical heating outside supported range')
        residual=abs(target-heat)/max(abs(target),abs(heat),1.)
        delta_t=None if previous_temperature is None else abs(temp-previous_temperature)/max(abs(temp),1.)
        history.append(dict(iteration=iteration,temperature_K=temp,power_W=result['P_opt'],
            heat_applied_W_cm3=heat,heat_target_W_cm3=target,heat_residual=residual,
            temperature_residual=delta_t,area_cm2=area,folder=step.name))
        write_json(step/'longitudinal.json',result)
        write_json(folder/'longitudinal.json',result)
        converged=delta_t is not None and residual<=tolerance and delta_t<=tolerance
        write_json(folder/'coupling.json',dict(history=history,converged=converged,
            scope='Cavity-averaged optical absorption ↔ MQW temperature; electrical current remains configured',
            final_folder=step.name,tolerance=tolerance))
        write_json(folder/'progress.json',dict(done=iteration,total=count,stage='optothermal feedback',heat_residual=residual))
        if converged:
            break
        heat+=relaxation*(target-heat); previous_temperature=temp
    return 'candidate',('Outer optothermal loop converged; inspect inner solver convergence' if converged
                         else 'Outer iteration limit reached; coupling has not converged')

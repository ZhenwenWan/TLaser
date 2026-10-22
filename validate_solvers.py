"""Reproduce and package numerical validation examples for solver workspaces 3/4.

python validate_solvers.py --lasers-root PATH --coupled-job JOB_ID
The coupled job must already have finished; this script never synthesizes fields.
"""
import argparse
from copy import deepcopy
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from cae_coupling import solve_1d
from cae_validation import longitudinal_validation, coupled_validation, check
from cae_fields import read_vtu
from cae_jobs import job_path, write_json
from device_model import default_config

ROOT=Path(__file__).resolve().parent


def table(path, rows):
    with path.open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)


def build(lasers_root, coupled_job, output):
    source=Path(lasers_root)/'Tools/quasi_3d_synthesizer.py'
    spec=importlib.util.spec_from_file_location('lasers_reference',source)
    reference=importlib.util.module_from_spec(spec); spec.loader.exec_module(reference)
    source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
    folder=output/'longitudinal'; folder.mkdir(parents=True,exist_ok=True)
    settings=dict(configuration=default_config(),temperature=298.,frequency=1.934e14,nodes=51,
                  longitudinal_tolerance=1e-4,longitudinal_max_nodes=4001)
    baseline=solve_1d(settings); validation=longitudinal_validation(baseline)
    comparisons=[]
    for label,r1,r2 in [('HR-AR',.9,.05),('Symmetric',.3,.3)]:
        c=default_config(); c['optical'].update(R1=r1,R2=r2)
        result=solve_1d({**settings,'configuration':c,'nodes':401,'longitudinal_tolerance':1e-6})
        ref=reference.Quasi3DSimulator(R1=r1,R2=r2,M=401,T0=298.,w_active=2.8e-4,d_active=.342e-4).solve_longitudinal(.15/.03)
        error=abs(result['P_opt']/ref['P_opt']-1)
        comparisons.append(dict(case=label,reference_power_W=float(ref['P_opt']),tlaser_power_W=result['P_opt'],relative_difference=error))
        validation['checks'].append(check(label+' Lasers reference power agreement',error,.005))
        if label=='Symmetric':
            symmetry=np.max(abs(np.array(result['P_plus'])-np.array(result['P_minus'])[::-1]))/max(result['P_plus'])
            validation['checks'].append(check('Symmetric cavity profile symmetry',symmetry,1e-5))
    meshes=[]
    for nodes in (31,51,101,201,401):
        r=solve_1d({**settings,'nodes':nodes,'longitudinal_tolerance':1e-6})
        meshes.append(dict(nodes=nodes,power_W=r['P_opt'],adaptive_nodes=r['adaptive_nodes'],converged=r['converged']))
    mesh_error=max(abs(row['power_W']/meshes[-1]['power_W']-1) for row in meshes)
    validation['checks'].append(check('Grid refinement power change (31–401 nodes)',mesh_error,1e-3))
    sweep=[]
    for current in (.01,.03,.05,.1,.15,.25,.4,.5):
        c=default_config(); c['operating']['I_active_A']=current
        r=solve_1d({**settings,'configuration':c,'nodes':101})
        sweep.append(dict(current_A=current,power_W=r['P_opt'],converged=r['converged']))
    validation['checks'].append(check('All current sweep solves converged',sum(not r['converged'] for r in sweep),0.))
    validation['checks'].append(check('Nondecreasing current–power response',float(max(0.,-np.min(np.diff([r['power_W'] for r in sweep])))),0.))
    validation['numerical_checks_passed']=all(v['passed'] for v in validation['checks'])
    validation['reference_source_sha256']=source_hash
    validation['reference_source']='Lasers/Tools/quasi_3d_synthesizer.py'
    write_json(folder/'request.json',dict(kind='longitudinal',settings=settings))
    write_json(folder/'longitudinal.json',baseline); write_json(folder/'validation.json',validation)
    table(folder/'reference_comparison.csv',comparisons); table(folder/'grid_refinement.csv',meshes); table(folder/'current_sweep.csv',sweep)
    z=np.array(baseline['z_grid'])*1e4
    fig,axes=plt.subplots(2,2,figsize=(10,7))
    axes[0,0].plot(z,np.array(baseline['P_plus'])*1000,label='Forward'); axes[0,0].plot(z,np.array(baseline['P_minus'])*1000,label='Backward')
    axes[0,0].set(xlabel='z (µm)',ylabel='Internal power (mW)'); axes[0,0].legend()
    axes[0,1].plot(z,np.array(baseline['N'])/1e18); axes[0,1].set(xlabel='z (µm)',ylabel='Carriers (10¹⁸ cm⁻³)')
    axes[1,0].plot([r['current_A'] for r in sweep],[1000*r['power_W'] for r in sweep],'o-'); axes[1,0].set(xlabel='Active current (A)',ylabel='Both-facet power (mW)')
    axes[1,1].plot([r['nodes'] for r in meshes],[100*abs(r['power_W']/meshes[-1]['power_W']-1) for r in meshes],'o-'); axes[1,1].set(xlabel='Initial/output nodes',ylabel='Difference from 401 nodes (%)')
    fig.suptitle('Longitudinal active-laser numerical validation'); fig.tight_layout(); fig.savefig(folder/'validation_curves.png',dpi=150); plt.close(fig)
    source_folder=job_path(coupled_job)
    status=json.loads((source_folder/'status.json').read_text())
    if status['state'] not in {'candidate','completed'}: raise ValueError('Coupled job must be finished')
    request=json.loads((source_folder/'request.json').read_text())
    evidence=coupled_validation(source_folder,request['settings'])
    write_json(source_folder/'validation.json',evidence)
    target=output/'coupled'; target.mkdir(parents=True,exist_ok=True)
    report=json.loads((source_folder/'coupling.json').read_text())
    for name in ('request.json','coupling.json','longitudinal.json'):
        shutil.copyfile(source_folder/name,target/name)
    write_json(target/'validation.json',evidence)
    summaries=[]
    for row in report['history']:
        step=source_folder/row['folder']; dest=target/row['folder']; (dest/'case').mkdir(parents=True,exist_ok=True)
        fields=json.loads((step/'fields.json').read_text())
        # Keep the final two actual field snapshots for contour/history inspection.
        files=fields['files'][-2:]; fields['files']=files
        for name in files:
            # Normalize Windows paths for portable checked-in examples.
            relative=Path(name.replace('\\','/')); (dest/relative).parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(step/relative,dest/relative)
        fields['files']=[name.replace('\\','/') for name in files]
        write_json(dest/'fields.json',fields)
        for name in ('longitudinal.json','solver.log','provenance.json'):
            shutil.copyfile(step/name,dest/name)
        shutil.copyfile(step/'case/case.sif',dest/'case/case.sif')
        write_json(dest/'validation.json',longitudinal_validation(json.loads((step/'longitudinal.json').read_text())))
        summaries.append(row)
    table(target/'coupling_history.csv',summaries)
    fig,axes=plt.subplots(1,3,figsize=(13,3.5)); iterations=[r['iteration'] for r in summaries]
    axes[0].plot(iterations,[r['temperature_K'] for r in summaries],'o-'); axes[0].set(ylabel='MQW temperature (K)')
    axes[1].plot(iterations,[r['power_W']*1000 for r in summaries],'o-'); axes[1].set(ylabel='Both-facet power (mW)')
    axes[2].semilogy(iterations,[max(r['heat_residual'],1e-16) for r in summaries],'o-',label='Heat mismatch')
    axes[2].axhline(report['tolerance'],linestyle='--',color='red',label='Tolerance'); axes[2].legend()
    for ax in axes: ax.set_xlabel('Outer iteration')
    fig.suptitle('Two-way coupling: outer convergence, with separate inner-field checks')
    fig.tight_layout(); fig.savefig(target/'validation_curves.png',dpi=150); plt.close(fig)
    final=target/report['final_folder']; fields=json.loads((final/'fields.json').read_text())
    points,tri,raw=read_vtu(final/fields['files'][-1])
    fig,axes=plt.subplots(1,3,figsize=(13,4))
    for ax,values,title in zip(axes,[raw['temperature'],raw['carriers'][:,1],raw['carriers'][:,2]],['Temperature (K)','Electrons (cm⁻³)','Holes (cm⁻³)']):
        im=ax.tripcolor(points[:,0]*1e4,points[:,1]*1e4,tri,values,shading='gouraud'); fig.colorbar(im,ax=ax)
        ax.set(title=title,xlabel='x (µm)',ylabel='y (µm)',aspect='equal')
    fig.tight_layout(); fig.savefig(target/'transverse_fields.png',dpi=150); plt.close(fig)
    write_json(output/'manifest.json',dict(source_job=coupled_job,reference_source_sha256=source_hash,
        tlaser_longitudinal_sha256=hashlib.sha256((ROOT/'simulator/lasers_longitudinal.py').read_bytes()).hexdigest(),
        longitudinal_checks_passed=validation['numerical_checks_passed'],coupled_checks_passed=evidence['numerical_checks_passed'],
        note='Numerical examples, not measurements. Coupled examples retain final two VTU snapshots per outer iteration. Full local runs are not included.'))
    print(json.dumps(dict(longitudinal=validation['numerical_checks_passed'],coupled=evidence['numerical_checks_passed'],output=str(output))))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lasers-root',required=True); parser.add_argument('--coupled-job',required=True)
    parser.add_argument('--output',type=Path,default=ROOT/'validation/solver_baseline')
    args=parser.parse_args(); build(args.lasers_root,args.coupled_job,args.output)

"""Lasers Gmsh mesh generation, with isolated outputs and explicit quality checks."""
import importlib.util
import json
from pathlib import Path
import subprocess
import time
import zipfile
import numpy as np
from cae_jobs import ROOT, write_json, check_cancel


def read_mesh(folder):
    nodes = np.loadtxt(folder/'mesh.nodes', ndmin=2)
    elements = np.loadtxt(folder/'mesh.elements', dtype=int, ndmin=2)
    lookup = {int(row[0]): i for i,row in enumerate(nodes)}
    triangles = np.array([[lookup[n] for n in row[3:6]] for row in elements])
    return nodes[:,2:5], triangles, elements[:,1]


def run_mesh(folder, settings):
    scale = float(settings['scale'])
    if not np.isfinite(scale) or not .5 <= scale <= 3:
        raise ValueError('Mesh scale must be between 0.5 and 3')
    gmsh = Path(settings['gmsh'])
    if not gmsh.is_file():
        raise ValueError('Gmsh executable not found')
    spec = importlib.util.spec_from_file_location('lasers_mesher', ROOT/'assets/elmer/lasers_mesher.py')
    mesher = importlib.util.module_from_spec(spec); spec.loader.exec_module(mesher)
    model = json.loads((ROOT/'assets/elmer/geometry.json').read_text())
    geo, msh = folder/'model.geo', folder/'model.msh'
    mesher.write_geo(mesher.right_half_model(model), geo, scale)
    with (folder/'solver.log').open('w') as log:
        proc = subprocess.Popen([str(gmsh),str(geo),'-2','-format','msh2','-o',str(msh)],
            stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        started=time.monotonic()
        try:
            while proc.poll() is None:
                check_cancel(folder)
                if time.monotonic()-started > 300:
                    raise TimeoutError('Meshing exceeded five minutes')
                time.sleep(.2)
        except BaseException:
            proc.kill(); proc.wait(); raise
    if proc.returncode:
        raise RuntimeError('Gmsh failed; inspect solver.log')
    nodes,triangles,_=mesher.parse_msh2(msh)
    nodes,triangles=mesher.mirror_half_mesh(nodes,triangles)
    boundaries=mesher.boundaries_from_triangles(nodes,triangles,model)
    mesher.write_elmer_mesh(nodes,triangles,boundaries,folder/'mesh')
    xyz,tri,bodies=read_mesh(folder/'mesh')
    vertices=xyz[tri,:2]
    a,b=vertices[:,1]-vertices[:,0],vertices[:,2]-vertices[:,0]
    areas=np.abs(a[:,0]*b[:,1]-a[:,1]*b[:,0])/2
    if not np.isfinite(xyz).all() or np.any(areas<=0) or set(bodies)!=set(range(1,12)):
        raise ValueError('Mesh failed finite-area/material-region checks')
    write_json(folder/'mesh.json',dict(nodes=len(xyz),triangles=len(tri),bodies=11,
        min_area_um2=float(areas.min()),scale=scale,source='Lasers Gmsh symmetric transverse mesher'))
    with zipfile.ZipFile(folder/'mesh.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for path in (folder/'mesh').iterdir():
            archive.write(path,'mesh/'+path.name)
        archive.write(geo,'model.geo')
    return 'completed','Mesh generated and checked'


def longitudinal_from_fields(folder, config, points, fields):
    """One-way area-averaged MQW thermal coupling, following Lasers 2D+1D architecture."""
    from scipy.spatial import cKDTree
    from simulator.quasi_3d_synthesizer import Quasi3DSimulator
    xyz,tri,bodies=read_mesh(folder/'case/mesh')
    active=tri[bodies==4]
    distances,indices=cKDTree(points).query(xyz*1e-4)
    if distances.max()>1e-8:
        raise ValueError('Field coordinates do not match the solver mesh')
    vertices=xyz[active,:2]
    a,b=vertices[:,1]-vertices[:,0],vertices[:,2]-vertices[:,0]
    area=np.abs(a[:,0]*b[:,1]-a[:,1]*b[:,0])/2
    temperature=float(np.average(fields['temperature'][indices[active]].mean(axis=1),weights=area))
    if not np.isfinite(temperature) or temperature<=0:
        raise ValueError('Invalid active-region temperature')
    g,o,p=config['geometry'],config['optical'],config['physical']
    sim=Quasi3DSimulator(L_cavity=g['L_um']*1e-4,w_active=g['w_um']*1e-4,d_active=g['d_um']*1e-4,
        R1=o['R1'],R2=o['R2'],T0=temperature,alpha_i=p['alpha_i'])
    sim.Gamma=p['Gamma']; sim.C_recomb*=p['C_mult']
    sim.R_series,sim.R_shunt=p['R_series'],p['R_shunt']
    result=sim.solve_longitudinal(config['operating']['I_active_A']/(g['L_um']*1e-4))
    report={k:v.tolist() if isinstance(v,np.ndarray) else float(v) for k,v in result.items()}
    report.update(active_temperature_K=temperature,current_source='Configured active-region current',
                  coupling='One-way transverse MQW temperature to longitudinal carrier/optical transport')
    write_json(folder/'longitudinal.json',report)

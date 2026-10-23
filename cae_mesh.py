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


def scaled_model(lateral_scale=1., vertical_scale=1.):
    """Scale the reduced transverse topology; keep effective 1D dimensions separate."""
    for value in (lateral_scale, vertical_scale):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not np.isfinite(value) or not .5 <= value <= 2.:
            raise ValueError('Geometry scales must be finite numbers between 0.5 and 2')
    model=json.loads((ROOT/'assets/elmer/geometry.json').read_text())
    for rect in model['rectangles']:
        for key in rect['bounds_um']:
            rect['bounds_um'][key] *= lateral_scale if key.startswith('y_') else vertical_scale
        rect['size_um']['width_y'] *= lateral_scale
        rect['size_um']['height_z'] *= vertical_scale
    for key in model['metadata']['physical_bounds_um']:
        model['metadata']['physical_bounds_um'][key] *= lateral_scale if key in ('width_y','y_min','y_max') else vertical_scale
    for key in model['parameters']:
        if key.endswith('_um'):
            model['parameters'][key] *= lateral_scale if 'width' in key else vertical_scale
    model['metadata']['geometry_scales']=dict(lateral=lateral_scale,vertical=vertical_scale)
    return model


def validate_mesh(folder, model):
    """Check region measures and contact tags against the requested geometry."""
    xyz,tri,bodies=read_mesh(folder)
    vertices=xyz[tri,:2]
    a,b=vertices[:,1]-vertices[:,0],vertices[:,2]-vertices[:,0]
    areas=np.abs(a[:,0]*b[:,1]-a[:,1]*b[:,0])/2
    if not np.isfinite(xyz).all() or not np.allclose(xyz[:,2],0.,atol=1e-12) or np.any(areas<=0) or set(bodies)!=set(range(1,12)):
        raise ValueError('Mesh failed finite-area/material-region checks')
    rows=[]
    for body,rect in enumerate(model['rectangles'],1):
        expected=rect['size_um']['width_y']*rect['size_um']['height_z']
        actual=float(areas[bodies==body].sum())
        if not np.isclose(actual,expected,rtol=1e-7,atol=1e-10):
            raise ValueError(f'Material region {body} area differs from requested geometry')
        rows.append(dict(body=body,name=rect['name'],expected_area_um2=expected,mesh_area_um2=actual))
    bounds=model['metadata']['physical_bounds_um']
    if not np.allclose([xyz[:,0].min(),xyz[:,0].max(),xyz[:,1].min(),xyz[:,1].max()],
                       [bounds[k] for k in ('y_min','y_max','z_min','z_max')],rtol=1e-9,atol=1e-9):
        raise ValueError('Mesh bounds differ from requested geometry')
    boundary=np.loadtxt(folder/'mesh.boundary',dtype=int,ndmin=2)
    if not set(range(1,6)).issubset(set(boundary[:,1])):
        raise ValueError('Mesh lacks required contact or exterior boundary tags')
    nodes=np.loadtxt(folder/'mesh.nodes',ndmin=2)
    lookup={int(row[0]):row[2:5] for row in nodes}
    for tag,height,width in [(1,bounds['z_min'],bounds['width_y']),
                             (2,bounds['z_max'],model['parameters']['ridge_width_um'])]:
        segments=np.array([[lookup[int(n)] for n in row[-2:]] for row in boundary[boundary[:,1]==tag]])
        if not np.allclose(segments[:,:,1],height,rtol=0,atol=1e-9):
            raise ValueError(f'Contact {tag} is on the wrong surface')
        length=np.linalg.norm(segments[:,1]-segments[:,0],axis=1).sum()
        if not np.isclose(length,width,rtol=1e-8,atol=1e-9):
            raise ValueError(f'Contact {tag} has incorrect length')
    return dict(passed=True,nodes=len(xyz),triangles=len(tri),bodies=11,
                min_area_um2=float(areas.min()),regions=rows,bounds_um=bounds,
                boundary_ids=sorted(int(v) for v in set(boundary[:,1])))


def run_mesh(folder, settings):
    scale = float(settings['scale'])
    if not np.isfinite(scale) or not .5 <= scale <= 3:
        raise ValueError('Mesh scale must be between 0.5 and 3')
    gmsh = Path(settings['gmsh'])
    if not gmsh.is_file():
        raise ValueError('Gmsh executable not found')
    spec = importlib.util.spec_from_file_location('lasers_mesher', ROOT/'assets/elmer/lasers_mesher.py')
    mesher = importlib.util.module_from_spec(spec); spec.loader.exec_module(mesher)
    model = scaled_model(settings.get('lateral_scale',1.),settings.get('vertical_scale',1.))
    write_json(folder/'geometry.json',model)
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
    report=validate_mesh(folder/'mesh',model)
    report.update(scale=scale,geometry_scales=model['metadata']['geometry_scales'],
                  source='Lasers Gmsh symmetric transverse mesher')
    write_json(folder/'mesh.json',report)
    with zipfile.ZipFile(folder/'mesh.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for path in (folder/'mesh').iterdir():
            archive.write(path,'mesh/'+path.name)
        archive.write(geo,'model.geo')
        archive.write(folder/'geometry.json','geometry.json')
        archive.write(folder/'mesh.json','mesh.json')
    return 'completed','Mesh generated and checked'


def mqw_temperature(folder, points, fields):
    """Area-weighted temperature and actual MQW cross-sectional area in cm²."""
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
    return temperature, float(area.sum()*1e-8)


def longitudinal_from_fields(folder, config, points, fields):
    """Legacy one-way adapter retained for saved-job compatibility."""
    from simulator.quasi_3d_synthesizer import Quasi3DSimulator
    temperature, _ = mqw_temperature(folder, points, fields)
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

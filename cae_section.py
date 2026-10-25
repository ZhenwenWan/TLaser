"""Exact plane sections of CAD boxes, meshed as separate conforming regions."""
import itertools
import json
import time
import subprocess
import zipfile
from collections import defaultdict
from pathlib import Path
import numpy as np
from scipy.spatial import ConvexHull
from cad_dimensions import assembly, defaults
from cae_jobs import check_cancel, write_json


def section(settings):
    model=assembly(settings.get('cad_dimensions',defaults()))
    origin=np.asarray(settings.get('cut_point',[0.,0.,0.]),dtype=float)
    normal=np.asarray(settings.get('cut_normal',[1.,0.,0.]),dtype=float)
    if origin.shape!=(3,) or normal.shape!=(3,) or not np.isfinite(origin).all() or not np.isfinite(normal).all() or np.linalg.norm(normal)<1e-12:
        raise ValueError('Cut point and direction require three finite coordinates and a nonzero direction')
    normal=normal/np.linalg.norm(normal)
    seed=np.eye(3)[np.argmin(abs(normal))]; u=seed-normal*np.dot(seed,normal);u/=np.linalg.norm(u);v=np.cross(normal,u)
    polygons=[]
    for body,part in enumerate(model['parts'],1):
        center=np.array(list(part['center_um'].values()));size=np.array(list(part['size_um'].values()))
        corners=np.array(list(itertools.product(*zip(center-size/2,center+size/2))))
        distance=(corners-origin)@normal; points=[]
        # Ignore tangent-only contact: no duplicate coincident material surfaces.
        if distance.min()>=-1e-9 or distance.max()<=1e-9: continue
        for a,b in itertools.combinations(range(8),2):
            if np.count_nonzero(corners[a]!=corners[b])!=1: continue
            da,db=distance[a],distance[b]
            if abs(da)<1e-9: points.append(corners[a])
            if da*db<0: points.append(corners[a]+da/(da-db)*(corners[b]-corners[a]))
            if abs(db)<1e-9: points.append(corners[b])
        points=np.unique(np.round(points,10),axis=0)
        if len(points)<3: continue
        uv=np.column_stack(((points-origin)@u,(points-origin)@v))
        hull=ConvexHull(uv); uv=uv[hull.vertices]
        polygons.append(dict(body=body,name=part['name'],uv=uv.tolist(),area_um2=float(hull.volume)))
    if not polygons: raise ValueError('Cutting plane does not intersect any part interior; move the point into the model')
    return dict(cad=model,origin=origin.tolist(),normal=normal.tolist(),u=u.tolist(),v=v.tolist(),polygons=polygons)


def write_geo(model,path,settings):
    from cae_tetra import sizes
    minimum,target,maximum=sizes(settings)
    vertices=np.unique(np.round(np.concatenate([p['uv'] for p in model['polygons']]),9),axis=0)
    lines={};loops=[]
    for p in model['polygons']:
        loop=[]; poly=np.array(p['uv'])
        for a,b in zip(poly,np.roll(poly,-1,axis=0)):
            delta=b-a; t=(vertices-a)@delta/(delta@delta)
            on=np.linalg.norm(vertices-a-t[:,None]*delta,axis=1)<1e-7
            ids=np.where(on&(t>=-1e-8)&(t<=1+1e-8))[0];ids=ids[np.argsort(t[ids])]+1
            for aa,bb in zip(ids[:-1],ids[1:]):
                key=tuple(sorted((int(aa),int(bb))));lines.setdefault(key,len(lines)+1)
                loop.append(lines[key]*(1 if aa<bb else -1))
        loops.append((p['body'],loop))
    out=['SetFactory("Built-in");']
    for i,(x,y) in enumerate(vertices,1): out.append(f'Point({i}) = {{{x:.12g},{y:.12g},0,1}};')
    for (a,b),i in lines.items(): out.append(f'Line({i}) = {{{a},{b}}};')
    for body,loop in loops:
        out.extend([f'Curve Loop({body}) = {{'+','.join(map(str,loop))+'};',f'Plane Surface({body}) = {{{body}}};',f'Physical Surface({body}) = {{{body}}};'])
    # Distance to sampled boundary curves is continuous (nearest-point envelope).
    out.extend(['Field[1] = Distance;', 'Field[1].CurvesList = {'+','.join(map(str,lines.values()))+'};',
        'Field[1].Sampling = 2000;', 'Field[2] = MathEval;',
        f'Field[2].F = "Min({target}, {minimum}+0.3*F1)";', 'Background Field = 2;',
        'Mesh.MeshSizeFromPoints=0; Mesh.MeshSizeFromCurvature=0; Mesh.MeshSizeExtendFromBoundary=0;',
        f'Mesh.MeshSizeMin={minimum}; Mesh.MeshSizeMax={maximum}; Mesh.Algorithm=5; Mesh.MshFileVersion=2.2;'])
    path.write_text('\n'.join(out),encoding='utf-8')


def run_section(folder,settings):
    from cae_mesh import validate_interfaces
    model=section(settings);write_json(folder/'section.json',model)
    write_json(folder/'geometry.json',model['cad'])
    geo=folder/'model.geo';msh=folder/'model.msh';write_geo(model,geo,settings)
    with (folder/'solver.log').open('w') as log:
        proc=subprocess.Popen([settings['gmsh'],str(geo),'-2','-algo','del2d','-format','msh2','-o',str(msh)],stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        started=time.monotonic()
        try:
            while proc.poll() is None:
                check_cancel(folder)
                if time.monotonic()-started>300: raise TimeoutError('Section meshing exceeded five minutes')
                time.sleep(.2)
        except BaseException:
            proc.kill();proc.wait();raise
    if proc.returncode: raise ValueError('Gmsh failed; inspect solver.log')
    return finish_section(folder,model)


def cross2(a,b):
    return a[...,0]*b[...,1]-a[...,1]*b[...,0]


def finish_section(folder,model):
    from cae_mesh import validate_interfaces
    msh=folder/"model.msh"
    from assets.elmer.lasers_mesher import parse_msh2
    nodes,tri,_=parse_msh2(msh)
    ids=sorted(nodes);lookup={n:i for i,n in enumerate(ids)}
    points=np.array([nodes[i] for i in ids]);tets=np.array([[lookup[n] for n in t['nodes']] for t in tri]);bodies=np.array([t['body_id'] for t in tri])
    areas=abs(cross2(points[tets[:,1],:2]-points[tets[:,0],:2],points[tets[:,2],:2]-points[tets[:,0],:2]))/2
    if not np.isfinite(points).all() or np.any(areas<=0): raise ValueError('Invalid section elements')
    if set(bodies)!=set(p['body'] for p in model['polygons']): raise ValueError('Missing or unexpected section regions')
    for p in model['polygons']:
        if not np.isclose(areas[bodies==p['body']].sum(),p['area_um2'],rtol=1e-7): raise ValueError('Section part area mismatch')
        # Convex polygon containment, including every triangle vertex.
        poly=np.array(p['uv']); vertices=points[tets[bodies==p['body']],:2].reshape(-1,2)
        for a,b in zip(poly,np.roll(poly,-1,axis=0)):
            if np.min(cross2(b-a,vertices-a)) < -1e-6: raise ValueError('Element leaves its CAD part')
    edges=defaultdict(list)
    for i,t in enumerate(tets):
        for a,b in itertools.combinations(t,2):edges[tuple(sorted((a,b)))].append(i)
    rows=[];tags={}
    for edge,parents in edges.items():
        if len(parents)>2:raise ValueError('Nonmanifold section')
        if len(parents)==2 and bodies[parents[0]]==bodies[parents[1]]:continue
        pair=tuple(sorted(int(bodies[p]) for p in parents));tags.setdefault(pair,len(tags)+1)
        rows.append([len(rows)+1,tags[pair],parents[0]+1,parents[1]+1 if len(parents)==2 else 0,202,edge[0]+1,edge[1]+1])
    mesh=folder/'mesh';mesh.mkdir()
    np.savetxt(mesh/'mesh.nodes',np.column_stack((np.arange(1,len(points)+1),np.full(len(points),-1),points)),fmt=['%d','%d','%.12g','%.12g','%.12g'])
    np.savetxt(mesh/'mesh.elements',np.column_stack((np.arange(1,len(tets)+1),bodies,np.full(len(tets),303),tets+1)),fmt='%d')
    np.savetxt(mesh/'mesh.boundary',rows,fmt='%d')
    (mesh/'mesh.header').write_text(f'{len(points)} {len(tets)} {len(rows)}\n2\n202 {len(rows)}\n303 {len(tets)}\n')
    report=dict(dimension=2,source='Exact CAD plane section',nodes=len(points),triangles=len(tets),regions=model['polygons'],boundary_tags={str(v):list(k) for k,v in tags.items()},interface_checks=validate_interfaces(mesh),size_field='continuous distance envelope, slope 0.3',solver_compatible=False)
    write_json(folder/'mesh.json',report)
    with zipfile.ZipFile(folder/'mesh.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for path in mesh.iterdir():archive.write(path,'mesh/'+path.name)
        for name in ['section.json','geometry.json','mesh.json','model.geo','model.msh']:archive.write(folder/name,name)
    return 'completed','CAD section meshed and checked'

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
from mesh_grading import edge_target,GROWTH_SLOPE


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
    lines={};loops=[];line_lengths={};short_edges=defaultdict(list);curve_divisions={}
    for p in model['polygons']:
        loop=[]; poly=np.array(p['uv']);body=p['body']
        edge_lengths=np.linalg.norm(np.roll(poly,-1,axis=0)-poly,axis=1)
        local_part_target=edge_target(float(edge_lengths.min()),target)
        for a,b in zip(poly,np.roll(poly,-1,axis=0)):
            delta=b-a; edge_length=float(np.linalg.norm(delta))
            local=local_part_target if edge_length<2*target else target
            t=(vertices-a)@delta/(delta@delta)
            on=np.linalg.norm(vertices-a-t[:,None]*delta,axis=1)<1e-7
            ids=np.where(on&(t>=-1e-8)&(t<=1+1e-8))[0];ids=ids[np.argsort(t[ids])]+1
            edge_curves=[]
            for aa,bb in zip(ids[:-1],ids[1:]):
                key=tuple(sorted((int(aa),int(bb))));lines.setdefault(key,len(lines)+1)
                lid=lines[key];loop.append(lid*(1 if aa<bb else -1));edge_curves.append(lid)
                length=float(np.linalg.norm(vertices[bb-1]-vertices[aa-1]));line_lengths[lid]=length
                curve_divisions[lid]=max(curve_divisions.get(lid,1),int(np.ceil(length/local)))
            needed=max(2,int(np.ceil(edge_length/local)))
            while sum(curve_divisions[lid] for lid in edge_curves)<needed:
                lid=max(edge_curves,key=lambda item:line_lengths[item]/curve_divisions[item])
                curve_divisions[lid]+=1
            if edge_length<2*target: short_edges[body].append((edge_curves,local))
        loops.append((p['body'],loop))
    out=['SetFactory("Built-in");']
    for i,(x,y) in enumerate(vertices,1): out.append(f'Point({i}) = {{{x:.12g},{y:.12g},0,1}};')
    for (a,b),i in lines.items(): out.append(f'Line({i}) = {{{a},{b}}};')
    for body,loop in loops:
        out.extend([f'Curve Loop({body}) = {{'+','.join(map(str,loop))+'};',f'Plane Surface({body}) = {{{body}}};',f'Physical Surface({body}) = {{{body}}};'])
    for lid,n in curve_divisions.items(): out.append(f'Transfinite Curve {{{lid}}} = {n+1};')
    fields=[];field_id=1
    for body,groups in short_edges.items():
        for curves,local in groups:
            out.extend([f'Field[{field_id}] = Distance;',f'Field[{field_id}].CurvesList = {{{",".join(map(str,curves))}}};',f'Field[{field_id}].Sampling = 2000;'])
            distance_id=field_id;field_id+=1
            out.extend([f'Field[{field_id}] = MathEval;',f'Field[{field_id}].F = "Min({target}, {local}+{GROWTH_SLOPE}*F{distance_id})";'])
            value_id=field_id;field_id+=1
            out.extend([f'Field[{field_id}] = Restrict;',f'Field[{field_id}].InField = {value_id};',f'Field[{field_id}].SurfacesList = {{{body}}};'])
            fields.append(field_id);field_id+=1
    out.extend([f'Field[{field_id}] = MathEval;',f'Field[{field_id}].F = "{target}";']);fields.append(field_id);field_id+=1
    out.append(f'Field[{field_id}] = Min; Field[{field_id}].FieldsList = {{{",".join(map(str,fields))}}}; Background Field = {field_id};')
    out.extend(['Mesh.MeshSizeFromPoints=0; Mesh.MeshSizeFromCurvature=0; Mesh.MeshSizeExtendFromBoundary=0;',
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
    return finish_section(folder,model,settings)


def cross2(a,b):
    return a[...,0]*b[...,1]-a[...,1]*b[...,0]


def finish_section(folder,model,settings):
    from cae_tetra import sizes
    minimum,target,maximum=sizes(settings)
    from cae_mesh import validate_interfaces
    msh=folder/"model.msh"
    from assets.elmer.lasers_mesher import parse_msh2
    nodes,tri,_=parse_msh2(msh)
    ids=sorted(nodes);lookup={n:i for i,n in enumerate(ids)}
    points=np.array([nodes[i] for i in ids]);tets=np.array([[lookup[n] for n in t['nodes']] for t in tri]);bodies=np.array([t['body_id'] for t in tri])
    areas=abs(cross2(points[tets[:,1],:2]-points[tets[:,0],:2],points[tets[:,2],:2]-points[tets[:,0],:2]))/2
    if not np.isfinite(points).all() or np.any(areas<=0): raise ValueError('Invalid section elements')
    expected_bodies=set(p['body'] for p in model['polygons'])
    actual_bodies=set(int(body) for body in np.unique(bodies))
    if actual_bodies!=expected_bodies:
        missing=sorted(expected_bodies-actual_bodies)
        raise ValueError(f'Every intersected CAD part must contain section elements; missing parts: {missing}')
    for p in model['polygons']:
        if not np.isclose(areas[bodies==p['body']].sum(),p['area_um2'],rtol=1e-7): raise ValueError('Section part area mismatch')
        # Convex polygon containment, including every triangle vertex.
        poly=np.array(p['uv']); vertices=points[tets[bodies==p['body']],:2].reshape(-1,2)
        for a,b in zip(poly,np.roll(poly,-1,axis=0)):
            if np.min(cross2(b-a,vertices-a)) < -1e-6: raise ValueError('Element leaves its CAD part')
    minimum_edge_elements=10**9
    for p in model['polygons']:
        poly=np.asarray(p['uv'])
        for a,b in zip(poly,np.roll(poly,-1,axis=0)):
            delta=b-a;length=float(np.linalg.norm(delta));t=(points[:,:2]-a)@delta/(length*length)
            on=(t>=-1e-8)&(t<=1+1e-8)&(np.abs(cross2(delta,points[:,:2]-a))<=1e-7*length)
            count=len(np.unique(np.round(t[on],9)))-1
            if count<2: raise ValueError(f'CAD part {p["name"]} edge has fewer than two mesh elements')
            minimum_edge_elements=min(minimum_edge_elements,count)
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
    local_targets=[]
    for p in model['polygons']:
        edge_lengths=np.linalg.norm(np.roll(np.asarray(p['uv']),-1,axis=0)-np.asarray(p['uv']),axis=1)
        short_count=int(np.count_nonzero(edge_lengths<2*target))
        if short_count:
            local_targets.append(dict(body=p['body'],name=p['name'],shortest_edge_um=float(edge_lengths.min()),
                                      local_target_um=float(edge_lengths.min()/2),short_edges=short_count))
    short_edges_refined=sum(item['short_edges'] for item in local_targets)
    region_counts={str(p['body']):int(np.count_nonzero(bodies==p['body'])) for p in model['polygons']}
    report=dict(dimension=2,source='Exact CAD plane section',nodes=len(points),triangles=len(tets),regions=model['polygons'],elements_by_region=region_counts,boundary_tags={str(v):list(k) for k,v in tags.items()},interface_checks=validate_interfaces(mesh),size_field='ideal target with continuous local-edge envelopes',growth_slope=GROWTH_SLOPE,sizing_um=dict(minimum=minimum,target=target,maximum=maximum),short_edges_refined=short_edges_refined,part_local_targets=local_targets,minimum_edge_elements=minimum_edge_elements,local_edge_rule='for each part with a short edge, use half its shortest CAD edge as the local target for its short edges; enforce at least two elements and allow local override of minimum size',solver_compatible=False)
    write_json(folder/'mesh.json',report)
    with zipfile.ZipFile(folder/'mesh.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for path in mesh.iterdir():archive.write(path,'mesh/'+path.name)
        for name in ['section.json','geometry.json','mesh.json','model.geo','model.msh']:archive.write(folder/name,name)
    return 'completed','CAD section meshed and checked'

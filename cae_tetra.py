"""Conforming tetrahedral subdivision of the fixed box-part CAD assembly."""
import itertools
import json
import math
import zipfile
from collections import defaultdict
from pathlib import Path
import numpy as np
from cad_dimensions import assembly,defaults
from cae_jobs import write_json,check_cancel

MAX_TETS=2500000

def sizes(settings):
    values=[settings.get(k,d) for k,d in [('min_size_um',.02),('target_size_um',20.),('max_size_um',40.)]]
    if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in values) or not .005<=values[0]<=values[1]<=values[2]<=500.:
        raise ValueError('Require 0.005 <= minimum <= target <= maximum <= 500 micrometers')
    return values

def grid(settings):
    _,target,_=sizes(settings)
    model=assembly(settings.get('cad_dimensions',defaults()))
    bounds=np.array([[[p['center_um'][a]-p['size_um'][a]/2,p['center_um'][a]+p['size_um'][a]/2] for a in 'xyz'] for p in model['parts']])
    axes=[]
    for axis in range(3):
        from mesh_grading import edge_target,graded_axis
        planes=np.unique(np.round(bounds[:,axis,:].ravel(),10))
        features=[]
        for box in bounds:
            lo,hi=box[axis]
            edge=hi-lo
            local=edge_target(float(np.min(box[:,1]-box[:,0])),target)
            if edge<2*target and local<target: features.append((lo,hi,local))
        axes.append(graded_axis(planes,target,edge_features=features))
    spans=[];count=0
    for box in bounds:
        span=[(int(np.argmin(abs(axes[a]-box[a,0]))),int(np.argmin(abs(axes[a]-box[a,1])))) for a in range(3)]
        for axis,(lo,hi) in enumerate(span):
            edge=box[axis,1]-box[axis,0]
            if edge<2*target and hi-lo<2:
                raise ValueError('Short CAD edge received fewer than two tetrahedral mesh intervals')
        count+=6*math.prod(hi-lo for lo,hi in span);spans.append(span)
    if count>MAX_TETS: raise ValueError(f'Requested {count:,} tetrahedra exceeds {MAX_TETS:,}; increase target size')
    return model,axes,spans,count

def boundary_faces(tets,bodies):
    faces=defaultdict(list)
    for i,tet in enumerate(tets):
        for face in itertools.combinations(tet,3): faces[tuple(sorted(face))].append(i)
    result=[]
    for face,parents in faces.items():
        if len(parents)>2: raise ValueError('Nonmanifold tetrahedral face')
        if len(parents)==1 or bodies[parents[0]]!=bodies[parents[1]]:
            result.append((face,parents))
    return result

def validate(points,tets,bodies,model):
    if not np.isfinite(points).all() or len(np.unique(np.round(points,10),axis=0))!=len(points):
        raise ValueError('Invalid or duplicate mesh nodes')
    expected_bodies=set(range(1,len(model['parts'])+1))
    actual_bodies=set(int(body) for body in np.unique(bodies))
    if actual_bodies!=expected_bodies:
        missing=sorted(expected_bodies-actual_bodies)
        raise ValueError(f'Every CAD part must contain volume elements; missing parts: {missing}')
    v=points[tets]; volumes=np.linalg.det(v[:,1:]-v[:,0,None,:])/6
    if np.any(volumes<=0): raise ValueError('Nonpositive tetrahedron volume')
    rows=[]
    for i,part in enumerate(model['parts'],1):
        expected=math.prod(part['size_um'].values());actual=float(volumes[bodies==i].sum())
        if not np.isclose(actual,expected,rtol=1e-7,atol=1e-8): raise ValueError(f'Incorrect material volume: {i}')
        rows.append(dict(part=i,name=part['name'],tetrahedra=int(np.count_nonzero(bodies==i)),
                         volume_um3=actual,expected_volume_um3=expected))
    faces=boundary_faces(tets,bodies);present=set();shared=0
    for face,parents in faces:
        present.update(int(bodies[p]) for p in parents);shared+=len(parents)==2
    if present!=set(range(1,16)): raise ValueError('Missing part boundary faces')
    # Each part must have exactly its cuboid surface area, including shared faces.
    surface=np.zeros(15)
    for face,parents in faces:
        a,b,c=points[list(face)];area=np.linalg.norm(np.cross(b-a,c-a))/2
        for parent in parents: surface[bodies[parent]-1]+=area
    for i,part in enumerate(model['parts']):
        a,b,c=part['size_um'].values()
        if not np.isclose(surface[i],2*(a*b+a*c+b*c),rtol=1e-7): raise ValueError('Nonconforming or incomplete part boundary')
    return dict(dimension=3,element_type='tetrahedron',nodes=len(points),tetrahedra=len(tets),
        material_regions=15,min_volume_um3=float(volumes.min()),boundary_triangles=len(faces),
        shared_interface_triangles=shared,conforming=True,regions=rows),faces

def run_tetra(folder,settings):
    model,axes,spans,count=grid(settings)
    bounds=np.array([[[p['center_um'][a]-p['size_um'][a]/2,p['center_um'][a]+p['size_um'][a]/2] for a in 'xyz'] for p in model['parts']])
    points=[];node_ids={};tets=[];bodies=[];cells=set()
    def node(index):
        if index not in node_ids:
            node_ids[index]=len(points);points.append([axes[a][index[a]] for a in range(3)])
        return node_ids[index]
    for body,span in enumerate(spans,1):
        check_cancel(folder)
        for base in itertools.product(*(range(lo,hi) for lo,hi in span)):
            if base in cells: raise ValueError('Overlapping CAD parts')
            cells.add(base)
            for order in itertools.permutations(range(3)):
                current=list(base);vertices=[node(tuple(current))]
                for axis in order:
                    current[axis]+=1;vertices.append(node(tuple(current)))
                tets.append(vertices);bodies.append(body)
    points=np.array(points);tets=np.array(tets);bodies=np.array(bodies)
    v=points[tets];negative=np.linalg.det(v[:,1:]-v[:,0,None,:])<0
    tets[negative,1],tets[negative,2]=tets[negative,2].copy(),tets[negative,1].copy()
    report,faces=validate(points,tets,bodies,model);report['sizing']=dict(zip(['minimum_um','target_um','maximum_um'],sizes(settings)))
    from mesh_grading import axis_report
    report['grading']=axis_report(axes)
    _,target,_=sizes(settings);short_edge_intervals=[]
    part_local_targets=[]
    for span,box in zip(spans,bounds):
        for axis,(lo,hi) in enumerate(span):
            if box[axis,1]-box[axis,0]<2*target: short_edge_intervals.append(hi-lo)
    for part in model['parts']:
        dims=part['size_um'];short_axes=[axis for axis in 'xyz' if dims[axis]<2*target]
        if short_axes:
            shortest=min(dims.values())
            part_local_targets.append(dict(name=part['name'],shortest_edge_um=shortest,
                local_target_um=shortest/2,short_edges=4*len(short_axes)))
    report['minimum_short_edge_intervals']=min(short_edge_intervals)
    report['part_local_targets']=part_local_targets
    report['local_edge_rule']='for each part with short edges, half its shortest CAD edge is the local target for its short edges; enforce at least two intervals and allow local override of minimum size'
    report['backend']='Conforming structured-grid subdivision, six tetrahedra per cuboid cell'
    mesh=folder/'mesh';mesh.mkdir()
    np.savetxt(mesh/'mesh.nodes',np.column_stack((np.arange(1,len(points)+1),np.full(len(points),-1),points)),fmt=['%d','%d','%.12g','%.12g','%.12g'])
    np.savetxt(mesh/'mesh.elements',np.column_stack((np.arange(1,len(tets)+1),bodies,np.full(len(tets),504),tets+1)),fmt='%d')
    rows=[];tags={}
    for i,(face,parents) in enumerate(faces,1):
        pair=tuple(sorted(int(bodies[p]) for p in parents))
        tags.setdefault(pair,len(tags)+1)
        rows.append([i,tags[pair],parents[0]+1,parents[1]+1 if len(parents)==2 else 0,303,*[v+1 for v in face]])
    np.savetxt(mesh/'mesh.boundary',rows,fmt='%d')
    (mesh/'mesh.header').write_text(f'{len(points)} {len(tets)} {len(faces)}\n2\n303 {len(faces)}\n504 {len(tets)}\n')
    report['boundary_tags']={str(v):list(k) for k,v in tags.items()}
    np.savez_compressed(folder/'tetra.npz',points=points,tetrahedra=tets,bodies=bodies)
    write_json(folder/'geometry.json',model);write_json(folder/'mesh.json',report)
    # Portable Gmsh 2.2 tetrahedral file, with physical material tags.
    with (folder/'model.msh').open('w') as out:
        out.write('$MeshFormat\n2.2 0 8\n$EndMeshFormat\n$Nodes\n'+str(len(points))+'\n')
        for i,p in enumerate(points,1): out.write(f'{i} {p[0]:.12g} {p[1]:.12g} {p[2]:.12g}\n')
        out.write('$EndNodes\n$Elements\n'+str(len(tets)+len(rows))+'\n')
        for i,(tet,body) in enumerate(zip(tets,bodies),1): out.write(f'{i} 4 2 {body} {body} '+ ' '.join(str(n+1) for n in tet)+'\n')
        for i,row in enumerate(rows,len(tets)+1): out.write(f'{i} 2 2 {row[1]} {row[1]} '+' '.join(str(n) for n in row[-3:])+'\n')
        out.write('$EndElements\n')
    with zipfile.ZipFile(folder/'mesh.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for path in mesh.iterdir(): archive.write(path,'mesh/'+path.name)
        for name in ['tetra.npz','geometry.json','mesh.json','model.msh']: archive.write(folder/name,name)
    return 'completed','Tetrahedral mesh generated and checked'

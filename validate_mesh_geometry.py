"""Reproduce geometry-to-mesh checks with the installed Gmsh executable."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from cae_mesh import run_mesh, read_mesh
from cae_jobs import write_json

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--gmsh',default='C:/gmsh/gmsh.exe')
    parser.add_argument('--output',type=Path,default=Path('validation/mesh_geometry'))
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    rows=[]
    fig,axes=plt.subplots(1,3,figsize=(15,4),constrained_layout=True)
    for ax,(name,lateral,vertical,scale) in zip(axes,[('reference',1.,1.,1.),('scaled',1.4,.8,1.),('scaled_refined',1.4,.8,.5)]):
        folder=args.output/name; folder.mkdir(exist_ok=True)
        settings=dict(gmsh=args.gmsh,scale=scale,lateral_scale=lateral,vertical_scale=vertical)
        write_json(folder/'request.json',dict(schema_version=1,kind='mesh',settings=settings))
        state,message=run_mesh(folder,settings)
        report=json.loads((folder/'mesh.json').read_text())
        rows.append(dict(case=name,state=state,**report))
        xyz,tri,bodies=read_mesh(folder/'mesh')
        ax.tripcolor(xyz[:,0],xyz[:,1],tri,facecolors=bodies,cmap='tab20',edgecolors='#555',linewidth=.1)
        ax.set(title=f"{name}: {len(tri)} elements",xlabel='Lateral (µm)',ylabel='Layer height (µm)',aspect='equal')
        print(name,state,len(xyz),len(tri),flush=True)
    if rows[2]['triangles']<=rows[1]['triangles']:
        raise RuntimeError('Refinement did not increase element count')
    fig.savefig(args.output/'mesh_comparison.png',dpi=160); plt.close(fig)
    write_json(args.output/'validation.json',dict(passed=True,cases=rows,
        scope='Geometry dimensions, material areas, contact boundaries and refinement; not solver or experimental validation'))

if __name__=='__main__': main()

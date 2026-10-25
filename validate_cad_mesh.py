"""Reproduce CAD-section and graded-volume acceptance runs outside version control."""
import argparse
from pathlib import Path
from cae_jobs import write_json
from cae_section import run_section
from cae_tetra import run_tetra

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=Path('tmp/cad-mesh-validation'))
    parser.add_argument('--gmsh',default='C:/gmsh/gmsh.exe')
    args=parser.parse_args()
    for name,normal in [('transverse',[1,0,0]),('oblique',[1,.2,.15])]:
        folder=args.output/name;folder.mkdir(parents=True)
        settings=dict(cad_section=True,dimension=2,cut_normal=normal,gmsh=args.gmsh,target_size_um=5.,min_size_um=.045,max_size_um=10.)
        write_json(folder/'request.json',settings)
        print(name,run_section(folder,settings),flush=True)
    folder=args.output/'volume';folder.mkdir(parents=True)
    write_json(folder/'request.json',dict(dimension=3))
    print('volume',run_tetra(folder,{}),flush=True)

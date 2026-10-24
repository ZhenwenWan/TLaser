"""Independent dimensions and fixed topology from Lasers telecom_laser_geometry.py."""
import json
import math
from pathlib import Path
from copy import deepcopy

# First owning part, axis, parameter, reference value. Equal values are not ties.
DIMENSIONS=[(0,'x','length',300.),(0,'y','chip_width',250.),(0,'z','substrate_height',100.),
 (1,'z','buffer_height',2.),(2,'z','lower_cladding_height',1.5),
 (3,'z','lower_sch_height',.25),(4,'z','mqw_height',.08),(5,'z','upper_sch_height',.25),
 (6,'y','ridge_width',3.),(6,'z','ridge_height',1.75),(7,'z','shoulder_height',.55),
 (9,'y','isolation_width',120.5),(9,'z','isolation_height',.25),
 (11,'z','p_metal_height',.25),(12,'z','n_metal_height',.25),(13,'x','coating_length',.08)]
NAMES_CN=['InP 衬底','n-InP 缓冲层','n-InP 下包层','下 SCH 波导','MQW 有源层','上 SCH 波导',
 'p-InP 脊与包层','左刻蚀 p-InP 肩部','右刻蚀 p-InP 肩部','左 SiN 隔离层','右 SiN 隔离层',
 '顶部 p 金属条','背面 n 金属','高反射后端面','减反射输出端面']

def reference():
    return json.loads((Path(__file__).parent/'assets/lasers_geometry.json').read_text(encoding='utf-8'))

def defaults(length=300.):
    return {**{key:value for _,_,key,value in DIMENSIONS},'length':length}

def validate(values):
    if not isinstance(values,dict) or set(values)!=set(defaults()):
        raise ValueError('Invalid independent dimension fields')
    for key,value in values.items():
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<=0:
            raise ValueError(f'{key} must be a finite positive dimension')
        base=defaults()[key]
        low,high=(100.,1000.) if key=='length' else (base*.2,base*5.)
        if not low<=value<=high: raise ValueError(f'{key} must be in [{low:g}, {high:g}] µm')
    shoulder=(values['chip_width']-values['ridge_width'])/2
    if shoulder<=0 or values['isolation_width']>shoulder:
        raise ValueError('Isolation width must fit within each shoulder; increase chip width or reduce isolation width')
    if values['shoulder_height']+values['isolation_height']>=values['ridge_height']:
        raise ValueError('Shoulder plus isolation height must be below the ridge top')
    if 1.6*values['ridge_width']>values['chip_width']:
        raise ValueError('Metal stripe must fit within chip width')
    return deepcopy(values)

def assembly(values):
    d=validate(values); model=reference(); parts=model['parts']; L=d['length']; W=d['chip_width']
    def box(i,x,y,z,sx,sy,sz):
        parts[i]['center_um']=dict(x=x,y=y,z=z);parts[i]['size_um']=dict(x=sx,y=sy,z=sz)
    z=0.
    for i,key in enumerate(['substrate_height','buffer_height','lower_cladding_height','lower_sch_height','mqw_height','upper_sch_height']):
        h=d[key];box(i,0.,0.,z+h/2,L,W,h);z+=h
    r=d['ridge_width'];h=d['ridge_height'];sh=d['shoulder_height'];sw=(W-r)/2;offset=(W+r)/4
    box(6,0.,0.,z+h/2,L,r,h)
    for i,sign in [(7,-1),(8,1)]: box(i,0.,sign*offset,z+sh/2,L,sw,sh)
    for i,sign in [(9,-1),(10,1)]: box(i,0.,sign*offset,z+sh+d['isolation_height']/2,L,d['isolation_width'],d['isolation_height'])
    top=z+h
    box(11,0.,0.,top+d['p_metal_height']/2,L,1.6*r,d['p_metal_height'])
    box(12,0.,0.,-d['n_metal_height']/2,L,W,d['n_metal_height'])
    height=top+d['p_metal_height']+d['n_metal_height']
    # Preserve the source facet placement convention.
    for i,sign in [(13,-1),(14,1)]: box(i,sign*(L+d['coating_length'])/2,0.,height/2,d['coating_length'],W,height)
    model['parameters']['length_um']=L
    model['metadata']['physical_bounds_um']=dict(length=L,width=W,height=height)
    return model

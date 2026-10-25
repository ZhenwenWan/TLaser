"""Continuous Lipschitz size envelopes on fixed CAD coordinate planes."""
import numpy as np

GROWTH_SLOPE=1.0
MAX_INTERVAL_RATIO=2.0

def edge_target(length,target):
    """Keep the ideal size except on a CAD edge that cannot fit two ideal cells."""
    return length/2 if length < 2*target else target

def graded_axis(planes,target,growth=GROWTH_SLOPE,edge_features=(),ratio_limit=MAX_INTERVAL_RATIO):
    planes=np.asarray(planes); widths=np.diff(planes)
    interval_targets=np.full(len(widths),target,dtype=float)
    for lo,hi,local in edge_features:
        inside=(planes[:-1]>=lo-1e-9)&(planes[1:]<=hi+1e-9)
        interval_targets[inside]=np.minimum(interval_targets[inside],local)
    seeds=np.r_[interval_targets[0],interval_targets]
    seeds=np.minimum(seeds,np.r_[interval_targets,interval_targets[-1]])
    segments=[]
    for i,(lo,hi,interval_target) in enumerate(zip(planes[:-1],planes[1:],interval_targets)):
        h_floor=min(interval_target,seeds[i],seeds[i+1])
        samples=max(4097,min(131073,int(np.ceil((hi-lo)/max(1e-5,h_floor*.25/growth)))+1))
        x=np.linspace(lo,hi,samples)
        h=np.minimum(interval_target,np.min(seeds[:,None]+growth*np.abs(x[None,:]-planes[:,None]),axis=0))
        metric=np.r_[0,np.cumsum(np.diff(x)*(1/h[:-1]+1/h[1:])/2)]
        n=int(np.ceil(metric[-1]))
        if n>250000: raise ValueError('Requested mesh is too fine; increase target size')
        segments.append([x,metric,n])
    for _ in range(1000):
        pieces=[np.interp(np.linspace(0,m[-1],n+1),m,x) for x,m,n in segments]
        change=set()
        widths=[np.diff(piece) for piece in pieces]
        for i,current in enumerate(widths):
            ratios=np.maximum(current[1:]/current[:-1],current[:-1]/current[1:])
            if len(ratios) and ratios.max()>ratio_limit: change.add(i)
            if i<len(widths)-1:
                left,right=current[-1],widths[i+1][0]
                if left>ratio_limit*right: change.add(i)
                if right>ratio_limit*left: change.add(i+1)
        if not change: return np.r_[np.concatenate([p[:-1] for p in pieces]),planes[-1]]
        for i in change: segments[i][2]+=max(1,segments[i][2]//4)
    details=[]
    for i,p in enumerate(pieces):
        d=np.diff(p)
        if len(d)>1:
            q=np.maximum(d[1:]/d[:-1],d[:-1]/d[1:])
            if q.max()>ratio_limit: details.append((i,segments[i][2],float(q.max()),float(d[q.argmax()]),float(d[q.argmax()+1])))
    raise ValueError(f'Could not grade requested geometry; {details[:4]}')

def axis_report(axes):
    ratios=[]
    for a in axes:
        d=np.diff(a)
        ratios.append(float(np.maximum(d[1:]/d[:-1],d[:-1]/d[1:]).max()))
    return dict(size_field='continuous Lipschitz envelope',growth_slope=GROWTH_SLOPE,max_interval_ratio=MAX_INTERVAL_RATIO,
                max_adjacent_axis_interval_ratio=ratios)

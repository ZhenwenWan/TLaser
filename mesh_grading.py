"""Continuous Lipschitz size envelopes on fixed CAD coordinate planes."""
import numpy as np

def graded_axis(planes,target,growth=.3):
    planes=np.asarray(planes); widths=np.diff(planes)
    seeds=np.minimum(np.r_[widths[0],widths],np.r_[widths,widths[-1]])
    seeds=np.minimum(seeds,target)
    segments=[]
    for lo,hi in zip(planes[:-1],planes[1:]):
        x=np.linspace(lo,hi,4097)
        h=np.minimum(target,np.min(seeds[:,None]+growth*np.abs(x[None,:]-planes[:,None]),axis=0))
        metric=np.r_[0,np.cumsum(np.diff(x)*(1/h[:-1]+1/h[1:])/2)]
        n=int(np.ceil(metric[-1]))
        if n>250000: raise ValueError('Requested mesh is too fine; increase target size')
        segments.append([x,metric,n])
    for _ in range(1000):
        pieces=[np.interp(np.linspace(0,m[-1],n+1),m,x) for x,m,n in segments]
        change=set()
        for i in range(len(pieces)-1):
            left=pieces[i][-1]-pieces[i][-2];right=pieces[i+1][1]-pieces[i+1][0]
            if left>1.4*right: change.add(i)
            if right>1.4*left: change.add(i+1)
        if not change: return np.r_[np.concatenate([p[:-1] for p in pieces]),planes[-1]]
        for i in change: segments[i][2]+=1
    raise ValueError('Could not grade the requested geometry')

def axis_report(axes):
    ratios=[]
    for a in axes:
        d=np.diff(a)
        ratios.append(float(np.maximum(d[1:]/d[:-1],d[:-1]/d[1:]).max()))
    return dict(size_field='continuous Lipschitz envelope',growth_slope=.3,
                max_adjacent_axis_interval_ratio=ratios)

"""Interactive tetrahedral boundary and cutaway rendering."""
import json
import numpy as np
import plotly.graph_objects as go
import streamlit as st
from cae_tetra import boundary_faces

def tetra_view(folder,t):
    with np.load(folder/'tetra.npz',allow_pickle=False) as data:
        points,tets,bodies=data['points'],data['tetrahedra'],data['bodies']
    parts=json.loads((folder/'geometry.json').read_text())['parts']
    selected=st.selectbox(t('Mesh view','网格视图'),[0]+list(range(1,16)),
        format_func=lambda i:t('All parts','全部部件') if i==0 else parts[i-1]['name'],key='tetra_part')
    cut=st.slider(t('Cavity cutaway (%)','腔长剖切 (%)'),1,100,100,key='tetra_cut')
    edges=st.toggle(t('Element edges','单元边线'),value=True,key='tetra_edges')
    centroid=points[tets].mean(axis=1)
    keep=centroid[:,0]<=points[:,0].min()+np.ptp(points[:,0])*cut/100
    if selected: keep&=bodies==selected
    if not keep.any():
        st.info(t('No elements in this slice. Increase the cutaway fraction.','此剖切范围无单元，请增大比例。'));return
    subset=tets[keep];labels=bodies[keep];faces=boundary_faces(subset,labels)
    triangles=np.array([face for face,_ in faces]);values=[int(labels[parents[0]]) for _,parents in faces]
    fig=go.Figure(go.Mesh3d(x=points[:,0],y=points[:,1],z=points[:,2],
        i=triangles[:,0],j=triangles[:,1],k=triangles[:,2],intensity=values,intensitymode='cell',
        colorscale='Turbo',cmin=1,cmax=15,showscale=False,flatshading=True))
    if edges:
        wire=points[triangles[:,[0,1,2,0]]]
        wire=np.concatenate([wire,np.full((len(wire),1,3),np.nan)],axis=1).reshape(-1,3)
        fig.add_trace(go.Scatter3d(x=wire[:,0],y=wire[:,1],z=wire[:,2],mode='lines',line=dict(color='#263747',width=1),showlegend=False,hoverinfo='skip'))
    fig.update_layout(height=560,margin=dict(l=0,r=0,t=0,b=0),scene=dict(aspectmode='data',
        xaxis_title='Cavity (µm)',yaxis_title='Width (µm)',zaxis_title='Height (µm)'),uirevision=str(folder))
    st.plotly_chart(fig,width='stretch',key='tetra_view')
    st.caption(t('Triangular faces of tetrahedral volume elements. Cutaway reveals the interior mesh.',
                 '显示四面体体单元的三角面；剖切可查看内部网格。'))

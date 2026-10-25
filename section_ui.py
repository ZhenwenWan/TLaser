"""CAD section inspection in physical scale and world coordinates."""
import json
import numpy as np
import plotly.graph_objects as go
import streamlit as st
from cae_mesh import read_mesh

def section_view(folder,t):
    model=json.loads((folder/'section.json').read_text(encoding='utf-8'))
    points,tri,bodies=read_mesh(folder/'mesh')
    view=st.radio(t('Mesh view','网格视图'),['2D','3D'],horizontal=True,key='mesh_view')
    parts={p['body']:p['name'] for p in model['polygons']}
    visible=st.multiselect(t('Visible parts','可见部件'),list(parts),default=list(parts),
        format_func=lambda i:parts[i],key='section_visible_parts')
    edges=st.toggle(t('Element edges','单元边线'),value=True,key='mesh_edges')
    keep=np.isin(bodies,visible);tri=tri[keep];bodies=bodies[keep]
    if not len(tri):
        st.info(t('No parts are visible. Select one or more parts to display the mesh.',
                  '当前没有可见部件。请选择一个或多个部件以显示网格。'))
        return
    if view=='2D':
        import matplotlib.pyplot as plt
        fig,ax=plt.subplots(figsize=(10,5))
        ax.tripcolor(points[:,0],points[:,1],tri,facecolors=bodies,cmap='tab20',edgecolors='#555' if edges else 'none',linewidth=.15)
        used=points[np.unique(tri),:2];lo=used.min(axis=0);hi=used.max(axis=0);pad=np.maximum((hi-lo)*.05,.01)
        ax.set(xlabel='u (µm)',ylabel='v (µm)',aspect='equal',xlim=(lo[0]-pad[0],hi[0]+pad[0]),ylim=(lo[1]-pad[1],hi[1]+pad[1]))
        st.pyplot(fig);plt.close(fig)
    else:
        world=np.array(model['origin'])+points[:,0,None]*model['u']+points[:,1,None]*model['v']
        fig=go.Figure(go.Mesh3d(x=world[:,0],y=world[:,1],z=world[:,2],i=tri[:,0],j=tri[:,1],k=tri[:,2],intensity=bodies,intensitymode='cell',colorscale='Turbo',showscale=False))
        if edges:
            wire=world[tri[:,[0,1,2,0]]];wire=np.concatenate([wire,np.full((len(wire),1,3),np.nan)],axis=1).reshape(-1,3)
            fig.add_trace(go.Scatter3d(x=wire[:,0],y=wire[:,1],z=wire[:,2],mode='lines',line=dict(color='#555',width=1),showlegend=False))
        fig.update_layout(height=500,scene=dict(aspectmode='data',xaxis_title='x (µm)',yaxis_title='y (µm)',zaxis_title='z (µm)'),margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig,width='stretch')
    st.caption(t('True geometric scale. Toggle parts to inspect thin layers or the ridge.', '真实几何比例。可切换部件显示以检查薄层或脊区。'))

"""Focused mesh generation and automatic result presentation."""
import io
import json
import shutil
import zipfile
from pathlib import Path
import streamlit as st
from cae_jobs import ROOT, read_jobs, job_path, start_job, cancel_job
from cae_mesh import scaled_model, read_mesh


def displayed_mesh(jobs):
    """Keep the latest successful mesh visible while another job runs or fails."""
    for ident,request,status in jobs:
        if status['state']=='completed':
            folder=job_path(ident)
            if (folder/'mesh/mesh.nodes').exists() and (folder/'mesh.zip').exists():
                return folder
    return None


def preflight(settings):
    from cae_mesh import mesh_sizes
    checked=dict(settings)
    mesh_sizes(checked)
    if 'scale' in checked and not .5<=checked['scale']<=3.:
        raise ValueError('Invalid legacy element-size scale')
    path=Path(checked['gmsh']).expanduser()
    if not path.is_file():
        raise ValueError('Gmsh executable not found. Set its path before generating the mesh.')
    checked['gmsh']=str(path.resolve())
    scaled_model(checked['lateral_scale'],checked['vertical_scale'])
    return checked


@st.fragment(run_every='2s')
def watch_mesh(ident,t):
    try:
        status=json.loads((job_path(ident)/'status.json').read_text(encoding='utf-8'))
    except (OSError,ValueError):
        st.info(t('Waiting for mesh worker…','等待网格任务…'))
        return
    if status['state'] not in {'queued','running'}:
        st.rerun(scope='app')
    st.info(t('Generating mesh… Results will update automatically.','正在生成网格…结果将自动更新。'))
    if st.button(t('Cancel meshing','取消网格生成'),key='cancel_mesh'):
        cancel_job(ident)
        st.caption(t('Stopping mesh generation…','正在停止网格生成…'))


def render_mesh(c,t):
    from cae_workspace import mesh_view
    jobs=read_jobs('mesh')
    active=next((j for j in jobs if j[2]['state'] in {'queued','running'}),None)
    folder=displayed_mesh(jobs)
    configure,results=st.tabs([t('Configure & run','配置与运行'),t('Visualization & results','可视化与结果')])
    with configure:
        st.caption(t('Element sizes in µm. Target is the ideal size; small features can require smaller elements. Shared material interfaces use identical nodes and edges.',
                     '单元尺寸单位为 µm。目标尺寸为理想值，细小特征可能需要更小单元。材料共享界面使用相同节点与边。'))
        settings={}
        for key,en,cn,default in [('target_size_um','Target size','目标尺寸',.2),
                                  ('min_size_um','Minimum size','最小尺寸',.045),
                                  ('max_size_um','Maximum size','最大尺寸',.65)]:
            settings[key]=st.number_input(t(en,cn)+' (µm)',.005,10.,default,.005,format='%.3f',key='mesh_'+key)
        with st.expander(t('Mesher','网格生成器')):
            settings['gmsh']=st.text_input(t('Gmsh executable','Gmsh 可执行程序'),
                value=shutil.which('gmsh') or 'C:/gmsh/gmsh.exe',key='option_mesh_gmsh')
        settings.update(lateral_scale=1.,vertical_scale=1.)
        if settings is not None:
            try:
                model=scaled_model(settings['lateral_scale'],settings['vertical_scale'])
                b=model['metadata']['physical_bounds_um']
                st.caption(t(f"Cross-section: {b['width_y']:.3f} × {b['height_z']:.3f} µm",
                             f"横截面：{b['width_y']:.3f} × {b['height_z']:.3f} µm"))
            except ValueError as ex:
                st.error(str(ex))
            if st.button(t('Generate mesh','生成网格'),key='run_mesh',type='primary',disabled=active is not None):
                try:
                    checked=preflight(settings)
                    start_job('mesh',checked)
                    st.rerun()
                except (ValueError,OSError,TypeError) as ex:
                    st.error(str(ex))
        if active:
            watch_mesh(active[0],t)
        elif jobs and jobs[0][2]['state'] in {'failed','cancelled'}:
            st.error(t('Mesh generation failed or was cancelled. The previous usable mesh is retained.',
                       '网格生成失败或已取消，保留上一次可用网格。'))
            with st.expander(t('Generation diagnostics','生成诊断')):
                st.write(jobs[0][2].get('stage',''))
                for name in ('solver.log','worker.log'):
                    path=job_path(jobs[0][0])/name
                    if path.exists(): st.code(path.read_text(encoding='utf-8',errors='replace')[-5000:])
    with results:
        mesh=folder/'mesh' if folder else ROOT/'assets/elmer/mesh'
        mesh_view(mesh,t)
        with st.expander(t('Mesh details','网格详情')):
            st.caption(t('Latest generated mesh' if folder else 'Bundled reference mesh',
                         '最近生成的网格' if folder else '内置参考网格'))
            if folder:
                st.json(json.loads((folder/'mesh.json').read_text(encoding='utf-8')))
                st.caption(t('Select this mesh in Simulator: ','在仿真中选择此网格：')+folder.name[:8])
            else:
                xyz,tri,bodies=read_mesh(mesh)
                st.json(dict(nodes=len(xyz),triangles=len(tri),material_regions=len(set(bodies)),dimension=2))
        if folder:
            data=(folder/'mesh.zip').read_bytes()
        else:
            buffer=io.BytesIO()
            with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as archive:
                for path in sorted(mesh.iterdir()):
                    if path.is_file(): archive.write(path,'mesh/'+path.name)
            data=buffer.getvalue()
        st.download_button(t('Download mesh','下载网格'),data,'mesh.zip','application/zip',key='download_mesh')

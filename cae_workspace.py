"""Four independent simulator workspaces with portable configuration snapshots."""
from copy import deepcopy
import io
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import streamlit as st
from cae_jobs import start_job, read_jobs, job_path
from cae_elmer import detect_lasers
from cae_mesh import read_mesh
from device_model import validate_config
from simulator.lasers_longitudinal import DEFAULTS as MULTIPHYSICS


def decode_configuration(data,kind,defaults):
    doc=json.loads(data)
    if doc.get('schema_version')!=1 or doc.get('kind')!=kind or not isinstance(doc.get('settings'),dict):
        raise ValueError('Configuration kind or schema version does not match this section')
    values=doc['settings']
    if 'optical_input_W' in values:
        raise ValueError('Passive-probe configurations cannot be loaded as Lasers active-laser jobs. Create a new configuration.')
    values={**{k:v for k,v in defaults.items() if k in MULTIPHYSICS},**values}
    if kind=='mesh':
        values={**{k:1. for k in ('lateral_scale','vertical_scale') if k in defaults},**values}
    if set(values)!=set(defaults):
        raise ValueError('Configuration fields do not match this section')
    for key,value in values.items():
        if isinstance(defaults[key],dict):
            validate_config(value)
        elif defaults[key] is None:
            if value is not None:
                job_path(value)
        elif type(value) is not type(defaults[key]):
            # JSON integers can represent floating-point values.
            if type(defaults[key]) is float and type(value) is int:
                values[key]=float(value)
            else:
                raise ValueError(f'Invalid type for {key}')
        if isinstance(value,(float,int)) and not np.isfinite(value):
            raise ValueError(f'Nonfinite value for {key}')
        if key in NUMBERS:
            low,high,_,_=NUMBERS[key]
            if not low<=value<=high:
                raise ValueError(f'{key} must be in [{low}, {high}]')
    return values


NUMBERS={
 'longitudinal_tolerance':(1e-7,.01,'Carrier / mirror / optical transport tolerance','载流子／端面／光输运容差'),
 'longitudinal_max_nodes':(401,20001,'Maximum adaptive longitudinal mesh nodes','最大自适应纵向网格节点数'),
 'lateral_scale':(.5,2.,'Lateral geometry scale','横向几何缩放'),
 'vertical_scale':(.5,2.,'Layer geometry scale','层叠几何缩放'),
 'scale':(.5,3.,'Element-size scale','单元尺寸比例'),
 'temperature':(250.,450.,'Temperature / heat sink (K)','温度／热沉 (K)'),
 'p_potential':(-1.,2.,'p-contact potential (V)','p 接触电势 (V)'),
 'frequency':(1e13,1e15,'Optical frequency (Hz)','光频率 (Hz)'),
 'em_drive':(0.,1.,'Prescribed EM current source (solver units)','指定电磁电流源（求解器单位）'),
 'iterations':(3,100,'Maximum transverse iterations','最大横向迭代数'),
 'tolerance':(1e-8,.01,'Transverse tolerance','横向容差'),
 'nodes':(11,401,'Longitudinal cavity nodes','纵向腔体节点数'),
 'outer_iterations':(2,30,'Maximum feedback iterations','最大反馈迭代数'),
 'outer_tolerance':(1e-6,.1,'Relative feedback tolerance','反馈相对容差'),
 'relaxation':(.01,1.,'Feedback relaxation','反馈松弛因子'),
 'absorption_fraction':(.01,1.,'Optical-loss fraction deposited in MQW','沉积至 MQW 的光损耗比例')}


def configuration_panel(kind,defaults,c,t):
    state=f'workspace_config_{kind}'
    if 'optical_input_W' in st.session_state.get(state,{}):
        st.warning(t('The passive-probe configuration has been retired. Lasers active-laser defaults are loaded.',
                     '无源探针配置已停用，现已加载 Lasers 有源激光器默认配置。'))
        st.session_state.pop(state,None)
    st.session_state.setdefault(state,deepcopy(defaults))
    for key,value in defaults.items():
        st.session_state[state].setdefault(key,deepcopy(value))
    def install(values):
        st.session_state[state]=deepcopy(values)
        for key,value in values.items():
            st.session_state[f'option_{kind}_{key}']=json.dumps(value,indent=2) if isinstance(value,dict) else value
    with st.expander(t('Load / save configuration','加载／保存配置')):
        upload=st.file_uploader(t('Configuration JSON','配置 JSON'),type=['json'],key=f'upload_{kind}')
        if st.button(t('Load configuration','加载配置'),key=f'load_{kind}',disabled=upload is None):
            try:
                values=decode_configuration(upload.getvalue(),kind,defaults)
                install(values)
            except (ValueError,TypeError,KeyError) as ex:
                st.error(str(ex))
        jobs=read_jobs(kind)
        if jobs:
            previous=st.selectbox(t('Restore settings from run','从运行恢复设置'),[j[0] for j in jobs],key=f'restore_select_{kind}')
            if st.button(t('Restore run settings','恢复运行设置'),key=f'restore_{kind}'):
                raw=next(j[1]['settings'] for j in jobs if j[0]==previous)
                # Older jobs can lack new options; only load recognized fields.
                merged={**defaults,**{k:v for k,v in raw.items() if k in defaults}}
                try:
                    if 'optical_input_W' in raw:
                        raise ValueError('This saved run used the retired passive-probe model; its settings cannot be restored as an active laser.')
                    install(decode_configuration(json.dumps(dict(schema_version=1,kind=kind,settings=merged)),kind,defaults))
                except (ValueError,TypeError,KeyError) as ex:
                    st.error(str(ex))
    values=deepcopy(st.session_state[state])
    if 'configuration' in defaults and st.button(t('Use current Device model','采用当前器件模型'),key=f'device_{kind}'):
        values['configuration']=deepcopy(c); install(values)
    if kind=='mesh' and st.button(t('Use Geometry scales','采用几何缩放'),key='mesh_use_geometry'):
        values.update(lateral_scale=st.session_state.get('ridge_cad_lateral',1.),
                      vertical_scale=st.session_state.get('ridge_cad_vertical',1.))
        install(values)
    for key in defaults:
        widget=f'option_{kind}_{key}'
        st.session_state.setdefault(widget,json.dumps(values[key],indent=2) if isinstance(values[key],dict) else values[key])
        if key=='configuration':
            with st.expander(t('Device parameters for this solver','本求解器的器件参数')):
                text=st.text_area(t('Device configuration JSON','器件配置 JSON'),height=280,key=widget)
                try:
                    values[key]=validate_config(json.loads(text))
                except (ValueError,TypeError,KeyError) as ex:
                    st.error(str(ex)); return None
        elif key=='mesh_job':
            meshes=[j[0] for j in read_jobs('mesh') if j[2]['state']=='completed']
            chosen=st.session_state[widget]
            if chosen and chosen not in meshes:
                st.error(t('The configured mesh run is missing or incomplete. Generate it or select another mesh.',
                           '配置的网格运行不存在或尚未完成，请生成或选择其他网格。'))
                meshes.append(chosen)
            values[key]=st.selectbox(t('Solver mesh','求解网格'),[None]+meshes,
                format_func=lambda v:'Reference mesh01' if v is None else v[:8],key=widget)
        elif key in NUMBERS:
            low,high,en,cn=NUMBERS[key]
            values[key]=st.number_input(t(en,cn),min_value=low,max_value=high,key=widget,
                                        format='%d' if type(low) is int else '%.8g')
        else:
            label=t('Gmsh executable','Gmsh 可执行程序') if key=='gmsh' else t('Lasers runtime folder','Lasers 运行目录')
            values[key]=st.text_input(label,key=widget)
    st.session_state[state]=deepcopy(values)
    st.download_button(t('Save configuration','保存配置'),json.dumps(dict(schema_version=1,kind=kind,settings=values),indent=2),
                       f'{kind}_configuration.json','application/json',key=f'save_{kind}')
    return values


def longitudinal_view(folder,t):
    result=json.loads((folder/'longitudinal.json').read_text())
    st.caption(f"Temperature: {result['active_temperature_K']:.4f} K")
    z=np.asarray(result['z_grid'])*1e4
    fig,axes=plt.subplots(1,2,figsize=(10,3.5))
    axes[0].plot(z,result['P_plus'],label='Forward'); axes[0].plot(z,result['P_minus'],label='Backward'); axes[0].legend()
    axes[0].set(xlabel='z (µm)',ylabel='Power (W)')
    axes[1].plot(z,result['N']); axes[1].set(xlabel='z (µm)',ylabel='Carriers (cm⁻³)')
    fig.tight_layout(); st.pyplot(fig); plt.close(fig)
    multiphysics='electron_density_cm3' in result
    if 'source_methodology' in result:
        st.caption(t('Lasers active-laser formulation: gain, spontaneous/stimulated emission, mirror reflections and spatial hole burning. Complex EM fields belong to the transverse solver.',
                     'Lasers 有源激光器方法：增益、自发／受激辐射、端面反射和空间烧孔。复电磁场由横向求解器计算。'))
        if result['converged']:
            st.success(t('Carrier balance, optical transport and mirror residuals passed.','载流子平衡、光输运及端面残差达标。'))
        else:
            st.warning(t('Active-laser residuals have not converged.','有源激光器残差尚未收敛。'))
        st.dataframe(result['residual_history'],hide_index=True)
        fig,axes=plt.subplots(1,2,figsize=(10,3))
        axes[0].plot(z,result['g']); axes[0].set(xlabel='z (µm)',ylabel='Material gain (cm⁻¹)')
        axes[1].plot(z,result['photon_density_cm3']); axes[1].set(xlabel='z (µm)',ylabel='Photon density (cm⁻³)')
        fig.tight_layout(); st.pyplot(fig); plt.close(fig)
    st.metric(t('Transmitted probe power (mW)' if multiphysics else 'Both-facet power (mW)',
                '透射探针光功率 (mW)' if multiphysics else '双端面光功率 (mW)'),f"{1000*result['P_opt']:.4g}")
    if multiphysics:
        st.caption(t('Driven passive optical cavity; these fields do not predict self-lasing output. Optical amplitudes are power-normalized (√W).',
                     '受驱动的无源光腔；这些场不预测自激激光输出。光场振幅以功率归一化 (√W)。'))
        if result['converged']:
            st.success(t('1D electrical, thermal and optical feedback residuals passed.','一维电学、热学及光学反馈残差达标。'))
        else:
            st.warning(t('1D multiphysics residuals have not converged.','一维多物理残差尚未收敛。'))
        fig,axes=plt.subplots(2,2,figsize=(10,7))
        axes[0,0].plot(z,result['electron_density_cm3'],label='Electrons')
        axes[0,0].plot(z,result['hole_density_cm3'],label='Holes',linestyle='--'); axes[0,0].legend()
        axes[0,0].set(ylabel='Density (cm⁻³)')
        axes[0,1].plot(z,result['potential_V']); axes[0,1].set(ylabel='Potential (V)')
        axes[1,0].plot(z,result['temperature_K']); axes[1,0].set(ylabel='Temperature (K)')
        axes[1,1].plot(z,result['electric_field_V_cm']); axes[1,1].set(ylabel='Electrical field (V/cm)')
        for ax in axes.flat: ax.set_xlabel('z (µm)')
        fig.tight_layout(); st.pyplot(fig); plt.close(fig)
        wave_z=np.asarray(result['wave_z_cm'])*1e4
        end=min(len(wave_z)-1,500)
        limits=st.slider(t('Optical field window (µm)','光场显示区间 (µm)'),0.,float(wave_z[-1]),
                         (0.,float(wave_z[end])),key=f'wave_window_{folder.name}')
        select=(wave_z>=limits[0])&(wave_z<=limits[1])
        fig,ax=plt.subplots(figsize=(10,3))
        for key in ('EM_real','EM_imag'):
            ax.plot(wave_z[select],np.asarray(result[key])[select],label=key)
        ax.set(xlabel='z (µm)',ylabel='Optical amplitude (√W)'); ax.legend()
        st.pyplot(fig); plt.close(fig)
        st.dataframe(result['residual_history'],hide_index=True)
        data=io.StringIO()
        fields=['electron_density_cm3','hole_density_cm3','potential_V','electric_field_V_cm','temperature_K','photon_density_cm3']
        np.savetxt(data,np.column_stack([z]+[result[k] for k in fields]),delimiter=',',header='z_um,'+','.join(fields),comments='')
        st.download_button(t('Download coupled fields CSV','下载耦合场 CSV'),data.getvalue(),'longitudinal_fields.csv')
        data=io.StringIO()
        np.savetxt(data,np.column_stack((wave_z,result['EM_real'],result['EM_imag'])),delimiter=',',header='z_um,real_sqrt_W,imag_sqrt_W',comments='')
        st.download_button(t('Download optical wave CSV','下载电磁波 CSV'),data.getvalue(),'longitudinal_wave.csv')
    csv=io.StringIO(); np.savetxt(csv,np.column_stack((z,result['N'],result['P_plus'],result['P_minus'])),
        delimiter=',',header='z_um,N_cm-3,P_forward_W,P_backward_W',comments='')
    st.download_button(t('Download longitudinal CSV','下载纵向 CSV'),csv.getvalue(),'longitudinal.csv')
    st.download_button(t('Download 1D results','下载一维结果'),(folder/'longitudinal.json').read_bytes(),'longitudinal.json')


def validation_view(folder,t):
    path=folder/'validation.json'
    if not path.exists():
        st.caption(t('This older run has no validation report. New longitudinal and coupled runs save one automatically.',
                     '此历史运行没有验证报告。新的一维及耦合运行会自动保存验证报告。'))
        return
    report=json.loads(path.read_text(encoding='utf-8'))
    st.markdown(t('#### Numerical validation','#### 数值验证'))
    if report['numerical_checks_passed']:
        st.success(t('Numerical checks passed. This is not measured-device qualification.',
                     '数值检查通过。这不代表实测器件认证。'))
    else:
        st.warning(t('Validation is incomplete: one or more numerical checks failed. Review the table and solver diagnostics.',
                     '验证未完成：一项或多项数值检查未通过。请审阅下表及求解器诊断。'))
    st.dataframe(report['checks'],hide_index=True)
    st.download_button(t('Download validation report','下载验证报告'),path.read_bytes(),
                       'validation.json','application/json',key=f'validation_report_{folder.name}')
    for name in ('reference_comparison.csv','grid_refinement.csv','current_sweep.csv','coupling_history.csv'):
        if (folder/name).exists():
            st.download_button(name,(folder/name).read_bytes(),name,'text/csv')
    if (folder/'validation_curves.png').exists():
        st.image(str(folder/'validation_curves.png'),caption=t('Saved validation curves','已保存的验证曲线'))
    if (folder/'transverse_fields.png').exists():
        st.image(str(folder/'transverse_fields.png'),caption=t('Final transverse fields from the coupled run','耦合运行的最终横向场'))


def mesh_view(folder,t):
    import plotly.graph_objects as go
    xyz,tri,bodies=read_mesh(folder)
    a,b=st.columns(2)
    a.metric(t('Nodes','节点'),len(xyz)); b.metric(t('Elements','单元'),len(tri))
    view=st.radio(t('Mesh view','网格视图'),['2D','3D'],horizontal=True,key='mesh_view')
    edges=st.toggle(t('Element edges','单元边线'),value=True,key='mesh_edges')
    if view=='2D':
        fig,ax=plt.subplots(figsize=(10,4))
        ax.tripcolor(xyz[:,0],xyz[:,1],tri,facecolors=bodies,cmap='tab20',
                     edgecolors='#555' if edges else 'none',linewidth=.15)
        ax.set(xlabel='x (µm)',ylabel='y (µm)',aspect='equal'); st.pyplot(fig); plt.close(fig)
    else:
        fig=go.Figure(go.Mesh3d(x=xyz[:,0],y=xyz[:,1],z=xyz[:,2],i=tri[:,0],j=tri[:,1],k=tri[:,2],
            intensity=bodies,intensitymode='cell',colorscale='Viridis',showscale=False))
        if edges:
            coords=xyz[tri[:,[0,1,2,0]]]
            wire=np.concatenate([coords,np.full((len(tri),1,3),np.nan)],axis=1).reshape(-1,3)
            fig.add_trace(go.Scatter3d(x=wire[:,0],y=wire[:,1],z=wire[:,2],mode='lines',
                                     line=dict(color='#94a3b8',width=1),showlegend=False,hoverinfo='skip'))
        fig.update_layout(height=480,margin=dict(l=0,r=0,t=0,b=0),scene=dict(aspectmode='data',
                          xaxis_title='x (µm)',yaxis_title='y (µm)',zaxis_title='z (µm)'))
        st.plotly_chart(fig,width='stretch',key='mesh_inspection')
    st.caption(t('2D transverse elements; the 3D view provides navigation, not volume meshing.',
                 '采用二维横截面单元；三维视图用于旋转查看，不代表体网格。'))


def render_workspace(c,t,workspace='simulator'):
    from cae_ui import jobs_panel,render_spatial_result
    names=[t('Mesh','网格'),t('Transverse 2D','横向二维'),t('Longitudinal 1D','纵向一维'),t('Coupled 1D–2D','一维–二维耦合')]
    if workspace=='mesh':
        choice=0
        st.caption(t('Generate and inspect the transverse mesh.','生成并查看横向网格。'))
    else:
        if st.session_state.get('simulator_workspace') not in (1,2,3):
            st.session_state['simulator_workspace']=1
        choice=st.radio(t('Solver','求解器'),[1,2,3],format_func=lambda i:names[i],key='simulator_workspace',horizontal=True)
    kind=['mesh','fields','longitudinal','coupled'][choice]
    transverse=dict(lasers_root=detect_lasers(),mesh_job=None,temperature=float(c['operating']['T0_K']),
        p_potential=.57724,frequency=1.934e14,em_drive=0.,iterations=15,tolerance=1e-4,configuration=deepcopy(c))
    longitudinal=dict(temperature=float(c['operating']['T0_K']),frequency=1.934e14,nodes=51,configuration=deepcopy(c),**MULTIPHYSICS)
    defaults=[dict(gmsh='C:/gmsh/gmsh.exe',scale=1.,lateral_scale=1.,vertical_scale=1.),transverse,longitudinal,
              dict(**transverse,nodes=51,outer_iterations=8,outer_tolerance=.01,relaxation=.5,absorption_fraction=1.,**MULTIPHYSICS)][choice]
    with st.expander(t('Model details','模型说明')):
        if choice==0:
            st.caption(t('Mesh the Lasers 11-region transverse geometry. Geometry scales change physical dimensions; element-size scale controls refinement. Hidden CAD parts remain in the mesh. Select the completed mesh in Simulator to use it.',
                         '生成 Lasers 11 区域横截面网格。几何缩放改变物理尺寸，单元尺寸比例控制细化。隐藏部件仍参与网格生成；在仿真中选择已完成网格后生效。'))
        elif choice==1:
            st.caption(t('Independent carrier, potential, thermal and EM field solve. Contact potential is not terminal bias.',
                         '独立求解载流子、电势、温度和电磁场；接触电势不等同端口偏压。'))
        elif choice==2:
            st.caption(t('Lasers Task 1.6: coupled carrier balance and bidirectional optical propagation with gain, spontaneous/stimulated emission and facet reflections. Temperature is a transverse input, not an independent axial heat solve.',
                         'Lasers 任务 1.6：载流子平衡与双向光传播耦合，包含增益、自发／受激辐射及端面反射。温度来自横向输入，不单独求解轴向热方程。'))
        else:
            st.caption(t('Lasers quasi-3D decomposition: transverse electrical/thermal/vector EM fields supply MQW temperature and mesh area to the active longitudinal laser. Optical absorption heat returns to 2D. Active current and confinement remain configured; feedback is averaged.',
                         'Lasers 准三维分解：横向电学／热学／矢量电磁场向纵向有源激光器提供 MQW 温度和网格面积，光吸收热返回二维。注入电流和限制因子采用配置值，反馈采用平均量。'))
    results_tab, configuration_tab=st.tabs([t('Visualization & results','可视化与结果'),
                                            t('Configure & run','配置与运行')])
    with configuration_tab:
        settings=configuration_panel(kind,defaults,c,t)
        if settings is not None and st.button(t('Run configured task','运行配置任务'),key=f'run_{kind}',type='primary'):
            try:
                decode_configuration(json.dumps(dict(schema_version=1,kind=kind,settings=settings)),kind,defaults)
                start_job(kind,settings); st.rerun()
            except (ValueError,OSError,TypeError) as ex:
                st.error(str(ex))
    with results_tab:
        if choice==0:
            evidence=Path(__file__).resolve().parent/'validation/mesh_geometry'
            if (evidence/'validation.json').exists():
                with st.expander(t('Validated mesh examples','已验证网格示例')):
                    report=json.loads((evidence/'validation.json').read_text())
                    st.caption(t('Saved geometric checks, independent of the current settings. These do not validate solver physics.',
                                 '保存的几何检查独立于当前设置，不代表求解器物理精度验证。'))
                    st.image(str(evidence/'mesh_comparison.png'))
                    st.dataframe([dict(case=r['case'],nodes=r['nodes'],elements=r['triangles'],
                        width_um=r['bounds_um']['width_y'],height_um=r['bounds_um']['height_z'],passed=r['passed'])
                        for r in report['cases']],hide_index=True)
                    st.download_button(t('Download mesh validation','下载网格验证'),
                        (evidence/'validation.json').read_bytes(),'mesh_validation.json',key='mesh_validation_download')
        st.markdown(t('#### Visualization & results','#### 可视化与结果'))
        st.caption(t('Select a saved run below. New simulations are started in Configure & run; use Refresh job results when a run finishes.',
                     '在下方选择已保存的运行。在“配置与运行”中启动新仿真，完成后点击“刷新任务结果”。'))
        example=Path(__file__).resolve().parent/'validation/solver_baseline'/kind
        use_example=False
        if choice in (2,3) and (example/'validation.json').exists():
            use_example=st.radio(t('Result source','结果来源'),[False,True],
                format_func=lambda value:t('Included validation example','内置验证示例') if value else t('My simulation runs','我的仿真运行'),
                index=0 if read_jobs(kind) else 1,horizontal=True,key=f'result_source_{kind}')
        if use_example:
            st.info(t('Included numerical validation example. Its saved inputs are independent of your current device settings.',
                      '内置数值验证示例，其保存的输入独立于当前器件设置。'))
            with st.expander(t('Validation example inputs','验证示例输入')):
                st.json(json.loads((example/'request.json').read_text(encoding='utf-8')))
            selected=(example,{'state':'candidate'})
        else:
            selected=jobs_panel(kind,t)
        if not selected:
            if choice==0:
                st.caption(t('Reference mesh · generate a new mesh in Configure & run.',
                             '参考网格 · 在“配置与运行”中生成新网格。'))
                mesh_view(Path(__file__).resolve().parent/'assets/elmer/mesh',t)
                return
            st.info(t('No simulation results are saved for this section in this local checkout. Open Configure & run, set the inputs, and select Run configured task. Then return here and refresh. Git updates include code, not saved simulation results.',
                      '当前本地项目中尚无此模块的仿真结果。请打开“配置与运行”，设置输入并点击“运行配置任务”，然后返回此处刷新。Git 更新包含代码，不包含已保存的仿真结果。'))
            return
        folder,status=selected
        if status['state'] not in {'candidate','completed'}:
            st.info(t('Plots appear when the selected run finishes and produces results. Refresh a running job, choose a completed run, or inspect Settings and logs if the job failed.',
                      '所选运行完成并产生结果后将显示图形。运行中请刷新，也可选择已完成的运行；若失败，请查看“设置与日志”。'))
            return
        if choice in (2,3):
            validation_view(folder,t)
        if choice==0:
            mesh_view(folder/'mesh',t)
            with st.expander(t('Mesh details','网格详情')):
                st.json(json.loads((folder/'mesh.json').read_text()))
            st.download_button(t('Download mesh package','下载网格包'),(folder/'mesh.zip').read_bytes(),'mesh.zip')
        elif choice==1:
            render_spatial_result(folder,t)
        elif choice==2:
            longitudinal_view(folder,t)
        else:
            report=json.loads((folder/'coupling.json').read_text())
            if report['converged']:
                st.success(t('Outer optothermal residuals passed. Inner solver convergence still requires review.',
                             '外层光热残差达标，仍需审阅内部求解器收敛性。'))
            else:
                st.warning(t('Feedback did not converge within the iteration limit.','反馈在迭代上限内未收敛。'))
            st.dataframe(report['history'],hide_index=True)
            st.line_chart({'Heat residual':[row['heat_residual'] for row in report['history']]})
            st.download_button(t('Save coupling report','保存耦合报告'),(folder/'coupling.json').read_bytes(),'coupling.json')
            iteration=st.selectbox(t('Inspect feedback iteration','查看反馈迭代'),[r['folder'] for r in report['history']],index=len(report['history'])-1)
            render_spatial_result(folder/iteration,t)

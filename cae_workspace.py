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
from simulator.longitudinal_multiphysics import DEFAULTS as MULTIPHYSICS


def decode_configuration(data,kind,defaults):
    doc=json.loads(data)
    if doc.get('schema_version')!=1 or doc.get('kind')!=kind or not isinstance(doc.get('settings'),dict):
        raise ValueError('Configuration kind or schema version does not match this section')
    values=doc['settings']
    values={**{k:v for k,v in defaults.items() if k in MULTIPHYSICS},**values}
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
 'axial_bias':(-1.,1.,'Axial potential difference (V)','轴向电势差 (V)'),
 'optical_input_W':(0.,1.,'Incident optical probe power (W)','入射光探针功率 (W)'),
 'thermal_conductivity':(.001,10.,'Axial thermal conductivity (W/cm/K)','轴向热导率 (W/cm/K)'),
 'thermal_sink':(1e3,1e9,'Effective transverse heat conductance (W/cm³/K)','有效横向散热系数 (W/cm³/K)'),
 'refractive_index':(1.5,5.,'Background refractive index','背景折射率'),
 'multiphysics_iterations':(2,100,'Maximum 1D multiphysics iterations','最大一维多物理迭代数'),
 'multiphysics_tolerance':(1e-7,.01,'1D multiphysics residual tolerance','一维多物理残差容差'),
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
                    install(decode_configuration(json.dumps(dict(schema_version=1,kind=kind,settings=merged)),kind,defaults))
                except (ValueError,TypeError,KeyError) as ex:
                    st.error(str(ex))
    values=deepcopy(st.session_state[state])
    if 'configuration' in defaults and st.button(t('Use current Device model','采用当前器件模型'),key=f'device_{kind}'):
        values['configuration']=deepcopy(c); install(values)
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


def render_workspace(c,t):
    from cae_ui import jobs_panel,render_spatial_result
    names=[t('1. Mesher · Lasers / Gmsh','1. 网格生成 · Lasers / Gmsh'),
           t('2. Transverse 2D solver','2. 横向二维求解器'),
           t('3. Longitudinal 1D solver','3. 纵向一维求解器'),
           t('4. 1D-2D two-way coupled solver','4. 一维–二维双向耦合求解器')]
    choice=st.radio(t('Simulator workspace','模拟器工作区'),range(4),format_func=lambda i:names[i],key='simulator_workspace')
    st.markdown('### '+names[choice])
    kind=['mesh','fields','longitudinal','coupled'][choice]
    transverse=dict(lasers_root=detect_lasers(),mesh_job=None,temperature=float(c['operating']['T0_K']),
        p_potential=.57724,frequency=1.934e14,em_drive=0.,iterations=15,tolerance=1e-4,configuration=deepcopy(c))
    longitudinal=dict(temperature=float(c['operating']['T0_K']),frequency=1.934e14,nodes=51,configuration=deepcopy(c),**MULTIPHYSICS)
    defaults=[dict(gmsh='C:/gmsh/gmsh.exe',scale=1.),transverse,longitudinal,
              dict(**transverse,nodes=51,outer_iterations=8,outer_tolerance=.01,relaxation=.5,absorption_fraction=1.,**MULTIPHYSICS)][choice]
    if choice==0:
        st.caption(t('Refine the Lasers 11-region transverse geometry; element-size scale does not change dimensions.',
                     '细化 Lasers 11 区域横截面网格；单元尺寸比例不改变几何尺寸。'))
    elif choice==1:
        st.caption(t('Independent carrier, potential, thermal and EM field solve. Contact potential is not terminal bias.',
                     '独立求解载流子、电势、温度和电磁场；接触电势不等同端口偏压。'))
    elif choice==2:
        st.caption(t('Coupled Poisson + electron/hole drift-diffusion, heat transport and scalar Maxwell waves. Uniform transverse injection, insulating facets and an effective transverse heat sink; optical probe boundaries, not a self-lasing solution.',
                     '耦合泊松方程、电子／空穴漂移扩散、热输运及标量麦克斯韦波动方程。采用均匀横向注入、绝缘端面及有效横向散热；光学边界为探针激励，不是自激激光解。'))
    else:
        st.caption(t('Both solvers include electrical, thermal and wave equations. Cross-dimensional exchange remains MQW temperature ↔ probe absorption heat; current remains configured. This is an averaged optothermal coupling, not a full 3D laser solution.',
                     '两个求解器均包含电学、热学及波动方程。跨维度交换为 MQW 温度 ↔ 探针吸收热，电流采用配置值。这是平均光热耦合，而非完整三维激光解。'))
    settings=configuration_panel(kind,defaults,c,t)
    if settings is not None and st.button(t('Run configured task','运行配置任务'),key=f'run_{kind}',type='primary'):
        try:
            decode_configuration(json.dumps(dict(schema_version=1,kind=kind,settings=settings)),kind,defaults)
            start_job(kind,settings); st.rerun()
        except (ValueError,OSError,TypeError) as ex:
            st.error(str(ex))
    selected=jobs_panel(kind,t)
    if not selected:
        return
    folder,status=selected
    if status['state'] not in {'candidate','completed'}:
        return
    if choice==0:
        xyz,tri,bodies=read_mesh(folder/'mesh')
        st.json(json.loads((folder/'mesh.json').read_text()),expanded=False)
        fig,ax=plt.subplots(figsize=(10,4)); ax.tripcolor(xyz[:,0],xyz[:,1],tri,facecolors=bodies,cmap='tab20',edgecolors='#555',linewidth=.15)
        ax.set(xlabel='x (µm)',ylabel='y (µm)',aspect='equal'); st.pyplot(fig); plt.close(fig)
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

"""CAE job controls and mesh-field postprocessing for the five-section UI."""
import io
import json
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.tri as mtri
import plotly.graph_objects as go
import streamlit as st
from cae_jobs import start_job, read_jobs, job_path, cancel_job
from cae_elmer import detect_lasers, runtime
from cae_fields import read_vtu, available_fields
from cae_training import KEYS, SECTIONS
from device_model import DESIGN_BOUNDS
from cae_mesh import read_mesh


def jobs_panel(kind, t):
    st.button(t("Refresh job results", "刷新任务结果"), key=f"refresh_{kind}")
    jobs = read_jobs(kind)
    if not jobs:
        st.caption(t("No saved jobs yet.", "尚无已保存的任务。"))
        return None
    ids = [job[0] for job in jobs]
    selected = st.selectbox(t("Saved runs", "已保存的运行"), ids, key=f"saved_{kind}",
                            format_func=lambda key: f"{key[:8]} · {next(j[2]['state'] for j in jobs if j[0]==key)}")
    _, request, status = next(j for j in jobs if j[0] == selected)
    folder = job_path(selected)
    st.write(f"{status['state']} · {status['stage']}")
    if (folder/"progress.json").exists():
        try:
            progress = json.loads((folder/"progress.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            progress = {}
        st.caption(str(progress))
        done, total = progress.get("epoch", progress.get("done",0)), progress.get("epochs",progress.get("total",1))
        st.progress(min(1., done/max(1,total)))
    if status["state"] in {"queued", "running"}:
        st.caption(t("The worker continues in the background. Refresh to see progress and completed results.",
                     "任务在后台持续运行。刷新可查看进度与已完成结果。"))
        if st.button(t("Cancel job", "取消任务"), key=f"cancel_{kind}"):
            cancel_job(selected)
            st.info(t("Cancellation requested; the worker will stop safely.", "已请求取消，后台任务将安全停止。"))
    with st.expander(t("Settings and logs", "设置与日志")):
        st.json(request)
        for name in ("worker.log", "solver.log"):
            if (folder/name).exists():
                data = (folder/name).read_bytes()
                st.download_button(name, data, f"{selected[:8]}_{name}", key=f"{kind}_{name}")
                st.code(data[-5000:].decode("utf-8",errors="replace"), language="text")
    return folder, status


def render_field_jobs(c, t):
    from cae_workspace import render_workspace
    render_workspace(c, t)


def render_spatial_result(folder, t):
    report=json.loads((folder/"fields.json").read_text(encoding="utf-8"))
    st.markdown(t('#### Field visualization','#### 空间场可视化'))
    st.warning(t("Solver output available. Review convergence and field ranges before engineering use.",
                 "已生成求解结果，请在工程使用前审阅收敛性与场量范围。"))
    if report.get("warnings"):
        with st.expander(t("Solver diagnostics", "求解器诊断"), expanded=True):
            st.code("\n".join(report["warnings"]), language="text")
    a,b,d=st.columns(3)
    a.metric(t("Mesh nodes", "网格节点"),report["nodes"])
    b.metric(t("Triangles", "三角形"),report["triangles"])
    d.metric(t("Solve time", "求解耗时"),f"{report['elapsed_s']:.1f} s")
    frame=st.select_slider(t("Solver iteration", "求解迭代"),options=report["files"],value=report["files"][-1],
                           format_func=lambda value: Path(value).stem)
    points, triangles, raw=read_vtu(folder/frame)
    phase=st.slider(t("EM phase (degrees)", "电磁相位（度）"),0,360,0,15)
    fields=available_fields(points,triangles,raw,np.deg2rad(phase))
    name=st.selectbox(t("Spatial field", "空间场量"),list(fields))
    values=np.asarray(fields[name])
    st.caption(f"min = {np.min(values):.6g} · max = {np.max(values):.6g}")
    logscale=st.checkbox(t("Logarithmic color scale (positive fields)", "对数色标（正值场）"))
    display=values.copy()
    if logscale:
        if np.any(values<=0):
            st.warning(t("Nonpositive values exist; showing the linear scale.", "存在非正数，显示线性色标。"))
        else:
            display=np.log10(values)
    view=st.radio(t("Field view", "场量视图"),[t("2D contour", "二维云图"),t("3D mesh inspection", "三维网格查看")],horizontal=True)
    xyz=points*1e4  # Elmer Coordinate Scaling=1e-4 converts mesh µm to cm.
    if view==t("2D contour", "二维云图"):
        fig, ax=plt.subplots(figsize=(10,4.5))
        triangulation=mtri.Triangulation(xyz[:,0],xyz[:,1],triangles)
        artist=ax.tripcolor(triangulation,display,shading="gouraud",cmap="viridis")
        ax.set(xlabel="Transverse x (µm)",ylabel="Vertical y (µm)",title=name)
        ax.set_aspect("equal")
        fig.colorbar(artist,ax=ax)
        fig.tight_layout(); st.pyplot(fig); plt.close(fig)
    else:
        fig=go.Figure(go.Mesh3d(x=xyz[:,0],y=xyz[:,1],z=xyz[:,2],i=triangles[:,0],j=triangles[:,1],k=triangles[:,2],
                              intensity=display,colorscale="Viridis",showscale=True))
        fig.update_layout(height=500,scene=dict(aspectmode="data",xaxis_title="x (µm)",yaxis_title="y (µm)",zaxis_title="z (µm)"))
        st.plotly_chart(fig,width="stretch",key="field_mesh")
    table=np.column_stack((xyz,values))
    csv=io.StringIO(); np.savetxt(csv,table,delimiter=",",header="x_um,y_um,z_um,value",comments="")
    st.download_button(t("Download field CSV", "下载场量 CSV"),csv.getvalue(),"field.csv","text/csv")
    st.download_button(t("Download solver VTU", "下载求解器 VTU"),(folder/frame).read_bytes(),Path(frame).name)
    st.download_button(t("Download generated solver case", "下载生成的求解配置"),(folder/"case/case.sif").read_bytes(),"case.sif")
    with st.expander(t('Cross-section probe and iteration history','截面探针与迭代历史')):
        cut=st.slider(t('Horizontal cut y (µm)','水平截面 y (µm)'),float(xyz[:,1].min()),float(xyz[:,1].max()),float(np.median(xyz[:,1])))
        x=np.linspace(xyz[:,0].min(),xyz[:,0].max(),250)
        probe=mtri.LinearTriInterpolator(mtri.Triangulation(xyz[:,0],xyz[:,1],triangles),values)(x,np.full_like(x,cut))
        fig,ax=plt.subplots(figsize=(9,3)); ax.plot(x,probe); ax.set(xlabel='x (µm)',ylabel=name)
        st.pyplot(fig); plt.close(fig)
        csv=io.StringIO(); np.savetxt(csv,np.column_stack((x,probe.filled(np.nan))),delimiter=',',header='x_um,value',comments='')
        st.download_button(t('Download probe CSV','下载探针 CSV'),csv.getvalue(),'probe.csv')
        if st.button(t('Compute field iteration history','计算场量迭代历史')):
            history=[]
            for file in report['files']:
                pts,tris,data=read_vtu(folder/file)
                v=available_fields(pts,tris,data,np.deg2rad(phase))[name]
                history.append(dict(iteration=Path(file).stem,minimum=float(v.min()),maximum=float(v.max())))
            st.dataframe(history,hide_index=True)
    if (folder/'longitudinal.json').exists():
        result=json.loads((folder/'longitudinal.json').read_text())
        if 'electron_density_cm3' in result or 'source_methodology' in result:
            from cae_workspace import longitudinal_view
            st.markdown(t('#### Longitudinal solver results','#### 纵向求解结果'))
            longitudinal_view(folder,t)
            return
        st.markdown(t('#### Longitudinal cavity / spatial hole burning','#### 纵向腔体／空间烧孔'))
        st.caption(f"MQW temperature: {result['active_temperature_K']:.4f} K · {result['current_source']}")
        z=np.asarray(result['z_grid'])*1e4
        fig,axes=plt.subplots(1,2,figsize=(10,3.5))
        axes[0].plot(z,result['P_plus'],label='Forward'); axes[0].plot(z,result['P_minus'],label='Backward'); axes[0].legend()
        axes[0].set(xlabel='z (µm)',ylabel='Optical power (W)')
        axes[1].plot(z,result['N']); axes[1].set(xlabel='z (µm)',ylabel='Carrier density (cm⁻³)')
        fig.tight_layout(); st.pyplot(fig); plt.close(fig)
        st.download_button(t('Download quasi-3D results','下载准三维结果'),(folder/'longitudinal.json').read_bytes(),'longitudinal.json')


def render_training_jobs(c,t):
    st.markdown(t("### Simulation-driven PINN training", "### 仿真驱动的 PINN 训练"))
    st.write(t("Sample the configured design space, call the longitudinal simulator repeatedly, train a PINN, and evaluate independent validation and test sets.",
               "对设计空间采样并重复调用纵向模拟器，训练 PINN，并评估独立验证集与测试集。"))
    st.caption(t("60% training / 20% validation / 20% test. Physical constants are fixed to this saved device. Sampling uses the reduced longitudinal engine; field jobs are separate transverse solves.",
                 "60% 训练／20% 验证／20% 测试。物性常数固定为保存的器件值。采样采用纵向降阶内核，空间场任务为独立横截面求解。"))
    with st.form("pinn_training_job"):
        a,b,d=st.columns(3)
        samples=a.number_input(t("Simulation samples", "仿真样本数"),20,10000,500,20)
        epochs=b.number_input(t("Training epochs", "训练轮数"),5,5000,1000,5)
        seed=d.number_input(t("Random seed", "随机种子"),0,2147483647,42)
        threshold=st.number_input(t("Maximum normalized RMSE per output group", "每组输出最大归一化均方根误差"),.001,1.,.15,.01,format="%.3f")
        ranges={}
        with st.expander(t("Sampling ranges", "采样范围")):
            for key in KEYS:
                low,high=DESIGN_BOUNDS[key]
                ranges[key]=st.slider(key,float(low),float(high),(float(low),float(high)),key=f"train_range_{key}")
        submitted=st.form_submit_button(t("Generate data and train model", "生成数据并训练模型"),type="primary")
    if submitted:
        if any(a>=b for a,b in ranges.values()):
            st.error(t("Each sampling range must have a positive width.", "每个采样范围必须有正宽度。"))
        else:
            start_job("training",dict(configuration=c,samples=samples,epochs=epochs,seed=seed,
                                      ranges=ranges,max_normalized_rmse=threshold))
            st.rerun()
    selected=jobs_panel("training",t)
    if selected is None:
        return
    folder,status=selected
    if (folder/"model/training_history.json").exists():
        history=json.loads((folder/"model/training_history.json").read_text())
        st.line_chart({"Training loss":history})
    if not (folder/"evaluation.json").exists() or status["state"] not in {"completed","candidate"}:
        return
    report=json.loads((folder/"evaluation.json").read_text())
    rows=[{"Split":split,"Output":name,**metrics} for split in ("validation","test")
          for name,metrics in report[split]["groups"].items()]
    st.dataframe(rows,hide_index=True)
    st.caption(t("Errors are relative to simulated targets, not measured-device accuracy.", "误差相对仿真目标计算，不代表实测器件精度。"))
    if report["eligible"]:
        st.success(t("Validation gates passed. Model is available for explicit activation.", "已通过验证门限，可主动选择启用此模型。"))
    else:
        st.warning(t("Validation gates failed. Adjust the domain, sample count, or training settings before activation.",
                     "未通过验证门限。请调整设计域、样本数或训练设置后再启用。"))
    if st.button(t("Use this trained model for prediction", "使用此训练模型进行预测"),disabled=not report["eligible"]):
        st.session_state.ridge_active_model=folder.name
        st.session_state.pop("ridge_pinn_check", None)
        st.rerun()
    st.download_button(t("Download trained model package", "下载训练模型包"),(folder/"trained_model.zip").read_bytes(),"trained_model.zip")
    st.download_button(t("Download simulation dataset", "下载仿真数据集"),(folder/"dataset.npz").read_bytes(),"dataset.npz")
    st.download_button(t("Download validation report", "下载验证报告"),(folder/"evaluation.json").read_bytes(),"evaluation.json")

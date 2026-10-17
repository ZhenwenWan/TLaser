"""Compact shared device view for the two edge-emitter workflows."""
from copy import deepcopy
import json
import numpy as np
import matplotlib.pyplot as plt
import streamlit as st
from device_model import (default_config, validate_config, dumps, loads, surrogate_inputs,
                          DESIGN_BOUNDS, PHYSICAL_BOUNDS, PHYSICAL_UNITS)
from device_geometry import geometry_3d
from device_workflow import simulate, demo_measurements, fit_measurements


def style_plot(fig, axes):
    """Keep the previous dashboard's navy chart palette."""
    fig.set_facecolor("#0d1117")
    for ax in axes:
        ax.set_facecolor("#172a45")
        ax.tick_params(colors="#e6f1ff")
        ax.xaxis.label.set_color("#e6f1ff")
        ax.yaxis.label.set_color("#e6f1ff")
        ax.grid(alpha=.25, color="#8892b0")
        for spine in ax.spines.values():
            spine.set_color("#233554")
        for line, color in zip(ax.lines, ["#ff7b72", "#64ffda"]):
            line.set_color(color)
        legend = ax.get_legend()
        if legend:
            legend.get_frame().set_facecolor("#172a45")
            for label in legend.get_texts():
                label.set_color("#e6f1ff")


def render_device_workflow(surrogate, lang, calibration_mode):
    def t(en, cn):
        return cn if lang == "CN" else en

    st.session_state.setdefault("ridge_config", default_config())
    st.session_state.setdefault("ridge_fit", None)
    st.session_state.setdefault("ridge_applied", False)
    c = deepcopy(st.session_state.ridge_config)

    st.subheader(t("Device model · fixed ridge edge emitter", "器件模型 · 固定脊形边发射激光器"))
    st.caption(t("Steady-state CW preset · reduced facet-mirror model · DFB and EML physics are future extensions.",
                 "稳态 CW 预设 · 简化端面镜模型 · DFB 和 EML 物理模型待扩展。"))
    with st.expander(t("Save / load device configuration", "保存 / 加载器件配置")):
        upload = st.file_uploader(t("Configuration JSON", "配置 JSON"), type=["json"], key="ridge_upload")
        if st.button(t("Load configuration", "加载配置"), disabled=upload is None):
            try:
                st.session_state.ridge_config = loads(upload.getvalue())
                st.session_state.ridge_fit = None
                st.session_state.ridge_applied = False
                for key in DESIGN_BOUNDS:
                    st.session_state.pop(f"ridge_{key}", None)
                st.rerun()
            except (ValueError, TypeError) as ex:
                st.error(str(ex))
        st.download_button(t("Save configuration", "保存配置"), dumps(c), "tlaser_device.json", "application/json")

    controls, view = st.columns([1, 2])
    with controls:
        with st.form("ridge_design"):
            st.markdown(t("**Geometry**", "**几何尺寸**"))
            fields = [("geometry", "L_um", t("Cavity length L (µm)", "腔长 L (µm)"), 10.),
                      ("geometry", "w_um", t("Effective active width w (µm)", "等效有源区宽度 w (µm)"), .1),
                      ("geometry", "d_um", t("Effective active thickness d (µm)", "等效有源层厚度 d (µm)"), .001),
                      ("optical", "R1", t("Rear facet R1", "后端面 R1"), .01),
                      ("optical", "R2", t("Front facet R2", "前端面 R2"), .01),
                      ("operating", "T0_K", t("Ambient temperature (K)", "环境温度 (K)"), 1.),
                      ("operating", "I_active_A", t("Active-region current (A)", "有源区电流 (A)"), .01)]
            edited = deepcopy(c)
            for section, key, label, step in fields:
                low, high = DESIGN_BOUNDS[key]
                edited[section][key] = st.number_input(label, low, high, float(c[section][key]), step,
                                                       key=f"ridge_{key}", format="%.3f")
            submitted = st.form_submit_button(t("Update device", "更新器件"), type="primary")
        if submitted:
            try:
                edited["provenance"] = {"source": "user_design", "estimated_parameters": []}
                st.session_state.ridge_config = validate_config(edited)
                st.session_state.ridge_fit = None
                st.session_state.ridge_applied = False
                st.rerun()
            except ValueError as ex:
                st.error(str(ex))
        st.caption(t("Active current excludes leakage. Thickness is an effective model value, not an epitaxial stack.",
                     "有源区电流不含漏电流。厚度为等效模型参数，不代表完整外延层。"))
        with st.expander(t("Physical model parameters", "物理模型参数")):
            st.table([{"Parameter / 参数": k, "Value / 数值": v, "Unit / 单位": PHYSICAL_UNITS[k]}
                      for k, v in c["physical"].items()])
    with view:
        true_scale = st.toggle(t("True proportions", "真实比例"), key="ridge_true_scale")
        show_context = st.toggle(t("Show substrate and facet coatings", "显示衬底与端面镀膜"), value=True,
                                 key="ridge_show_context")
        exploded = st.slider(t("Layer separation (µm)", "层间展开距离 (µm)"), 0., 8., 0., .5,
                             key="ridge_layer_separation")
        st.plotly_chart(geometry_3d(c, lang, true_scale, show_context, exploded),
                        width="stretch", key="ridge_geometry_3d", theme=None,
                        config={"scrollZoom": True, "displaylogo": False,
                                "modeBarButtonsToAdd": ["orbitRotation", "pan3d", "resetCameraDefault3d"]})
        st.caption(t("Drag to rotate · scroll / pinch to zoom · choose Pan in the toolbar to move · reset camera to restore the view.",
                     "拖动旋转 · 滚轮／双指缩放 · 工具栏选择平移 · 重置相机恢复视角。"))
        st.caption(t("Lasers reference geometry: 15 material parts, 250 µm chip width, 3 µm ridge, 0.08 µm MQW. Cavity length follows the device configuration; other layers retain their source dimensions. Effective solver width/thickness do not redefine the epitaxial stack. Vertical display scale is 12× unless True proportions is enabled. Click legend entries to hide/show parts; double-click to isolate.",
                     "Lasers 参考几何：15 个材料部件，芯片宽 250 µm、脊宽 3 µm、MQW 厚 0.08 µm。腔长随器件配置更新，其他层保留源模型尺寸；求解器等效宽度和厚度不重新定义外延层。未开启真实比例时，纵向显示放大 12 倍。单击图例显隐部件，双击单独查看。"))
        st.markdown(t("[Source geometry · Lasers](https://zhenwenwan.github.io/Pages/Projects/Lasers/index.html)",
                      "[几何来源 · Lasers](https://zhenwenwan.github.io/Pages/Projects/Lasers/index.html)"))
        st.caption(t("Within the documented sampling envelope; model accuracy is not guaranteed by range membership.",
                     "位于文档采样范围内；范围内不代表精度已保证。"))
        fit = st.session_state.ridge_fit
        if fit:
            with st.expander(t("Original / estimated device comparison", "原始 / 估计器件对比"), expanded=True):
                st.caption(t("Geometry was held fixed: the original and estimated outlines are identical.",
                             "几何尺寸固定：原始和估计配置的轮廓相同。"))
                st.table([{"Parameter / 参数": k, "Original / 原始": fit["original"]["physical"][k],
                           "Estimated / 估计": fit["estimated"]["physical"][k],
                           "Change / 变化": fit["estimated"]["physical"][k]-fit["original"]["physical"][k]}
                          for k in PHYSICAL_BOUNDS])

    if not calibration_mode:
        st.markdown(t("### Performance prediction", "### 性能预测"))
        backend = st.radio(t("Prediction source", "预测来源"),
                           ["Nominal PINN / 标称 PINN", "Physical simulator / 物理模拟器"], horizontal=True)
        try:
            if backend.startswith("Nominal"):
                if surrogate is None:
                    st.warning(t("Nominal surrogate is unavailable. Choose the physical simulator.",
                                 "标称代理模型不可用，请选择物理模拟器。"))
                    return
                out = surrogate.predict(**surrogate_inputs(c))
                power, wpe, current, z, n, p = out["P_opt"], out["wpe"], out["I_total"], out["z_grid"], out["N"], out["P"]
                st.caption(t("Nominal seven-input surrogate; fitted constants are not inputs to this model.",
                             "标称七输入代理模型；已拟合物理常数不是此模型的输入。"))
            else:
                applied = st.session_state.ridge_applied and st.session_state.ridge_fit is not None
                active = st.session_state.ridge_fit["estimated"] if applied else c
                out = simulate(active)[0]
                power, wpe, current, z, n, p = out["power_W"], out["wpe"], out["current_total_A"], out["z_um"], out["N"], out["P"]
                st.caption(t("Simulator with accepted fitted constants." if applied else "Simulator with saved configuration constants.",
                             "模拟器使用已接受的拟合常数。" if applied else "模拟器使用当前配置中的常数。"))
            a, b, cc = st.columns(3)
            a.metric(t("Both-facet power", "双端面总光功率"), f"{power*1000:.3f} mW")
            b.metric("WPE", f"{wpe*100:.3f}%")
            cc.metric(t("Terminal current", "端口电流"), f"{current:.4f} A")
            fig, axes = plt.subplots(1, 2, figsize=(10, 3))
            axes[0].plot(z, n/1e18); axes[0].set(xlabel="z (µm)", ylabel="N (10¹⁸ cm⁻³)")
            axes[1].plot(z, p*1000); axes[1].set(xlabel="z (µm)", ylabel="P (mW)")
            style_plot(fig, axes)
            fig.tight_layout(); st.pyplot(fig); plt.close(fig)
        except (ValueError, RuntimeError) as ex:
            st.error(str(ex))
        return

    st.markdown(t("### Inverse calibration · fixed geometry", "### 逆向标定 · 固定几何尺寸"))
    st.info(t("This release requires known active-region current. Ordinary terminal-current LIV uploads need a conversion/model extension before fitting.",
              "本版本需要已知有源区电流。普通端口电流 LIV 数据需先转换或扩展模型。"))
    source = st.radio(t("Measurement source", "测量来源"), ["Upload JSON / 上传 JSON", "Synthetic demo / 合成演示"], horizontal=True)
    measurement = st.file_uploader(t("Measured LIV JSON", "测量 LIV JSON"), type=["json"], key="ridge_measurement") if source.startswith("Upload") else None
    template = {"current_semantics": "active_region", "current_A": [.05, .1, .2, .3, .4],
                "voltage_V": [1.5]*5, "optical_power_W": [.001]*5,
                "metadata": {**c["geometry"], **c["optical"], "T0": c["operating"]["T0_K"], "source": "replace_example_values"}}
    st.download_button(t("Measurement JSON template", "测量 JSON 模板"), json.dumps(template, indent=2), "tlaser_liv_template.json", "application/json")
    selected = st.multiselect(t("Parameters to estimate", "待估计参数"), list(PHYSICAL_BOUNDS), default=["R_series"], key="ridge_selected")
    st.caption(t("Start with a small identifiable subset. Five-parameter LIV fits can be ambiguous.",
                 "建议先选择少量可辨识参数；五参数 LIV 拟合可能不唯一。"))
    if st.button(t("Run calibration", "运行标定"), type="primary"):
        try:
            if source.startswith("Upload") and measurement is None:
                raise ValueError(t("Upload measurements or choose the synthetic demo.", "请上传测量数据或选择合成演示。"))
            with st.spinner(t("Fitting the selected physical parameters…", "正在拟合所选物理参数…")):
                data = json.loads(measurement.getvalue()) if measurement else demo_measurements(c, selected)
                st.session_state.ridge_fit = fit_measurements(c, data, selected)
                st.session_state.ridge_applied = False
            st.rerun()
        except (ValueError, TypeError, RuntimeError) as ex:
            st.error(str(ex))
    fit = st.session_state.ridge_fit
    if fit:
        st.write(t("Optimizer", "优化器"), fit["message"])
        a, b = st.columns(2)
        a.metric(t("Normalized loss before", "拟合前归一化损失"), f"{fit['loss_before']:.6g}")
        b.metric(t("Normalized loss after", "拟合后归一化损失"), f"{fit['loss_after']:.6g}")
        if fit["acceptable"]:
            st.success(t("Converged with improved fit and no detected bound/sensitivity warning. Review before applying.",
                         "已收敛，拟合改善，未发现边界或灵敏度问题。请审阅后应用。"))
        else:
            st.warning(t("Candidate only: convergence, improvement, bounds, or identifiability checks did not pass. It cannot be applied.",
                         "仅为候选结果：收敛、改善、边界或可辨识性检查未通过，不能应用。"))
        with st.expander(t("Fit diagnostics", "拟合诊断")):
            st.json({k: fit[k] for k in ("success", "iterations", "acceptance_loss_limit", "bounds_reached", "sensitivity", "insensitive_parameters", "jacobian_condition")})
            st.caption(t("Local sensitivity is a diagnostic, not proof of unique identification or measured-device accuracy.",
                         "局部灵敏度仅供诊断，不证明参数唯一性或实测器件精度。"))
        currents = np.asarray(fit["measurements"]["current_A"])
        before = simulate(fit["original"], currents)
        after = simulate(fit["estimated"], currents)
        order = np.argsort(currents)
        fig, axes = plt.subplots(1, 2, figsize=(10, 3.5))
        for ax, field, measured, scale, ylabel in [
            (axes[0], "power_W", "optical_power_W", 1000, "Power (mW)"),
            (axes[1], "voltage_V", "voltage_V", 1, "Voltage (V)")]:
            ax.scatter(currents, np.asarray(fit["measurements"][measured])*scale, label="Measured")
            ax.plot(currents[order], np.asarray([o[field] for o in before])[order]*scale, label="Original")
            ax.plot(currents[order], np.asarray([o[field] for o in after])[order]*scale, label="Estimated")
            ax.set(xlabel="Active current (A)", ylabel=ylabel); ax.legend()
        style_plot(fig, axes)
        fig.tight_layout(); st.pyplot(fig); plt.close(fig)
        if st.button(t("Use fitted constants for simulator prediction", "模拟预测使用拟合常数"), disabled=not fit["acceptable"]):
            st.session_state.ridge_applied = True
            st.success(t("Applied. Select physical simulator in the prediction workflow.", "已应用。请在预测界面选择物理模拟器。"))
        st.download_button(t("Save estimated configuration", "保存估计配置"), dumps(fit["estimated"]), "tlaser_estimated_device.json", "application/json")
        st.download_button(t("Save calibration report", "保存标定报告"), json.dumps(fit, indent=2, ensure_ascii=False, allow_nan=False), "tlaser_calibration.json", "application/json")

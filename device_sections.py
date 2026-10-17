"""Simulator and PINN inspection panels for the shared device workspace."""
from copy import deepcopy
import json
from pathlib import Path
from time import perf_counter

import numpy as np
import plotly.graph_objects as go
import streamlit as st
from device_model import default_config, dumps, surrogate_inputs, PHYSICAL_UNITS
from device_workflow import simulate

ROOT = Path(__file__).resolve().parent


def run_sweep(config, low, high, points):
    if not .01 <= low < high <= .5 or not 3 <= points <= 31:
        raise ValueError("Use 0.01 ≤ start < end ≤ 0.5 A and 3–31 samples.")
    currents = np.linspace(low, high, points)
    started = perf_counter()
    results = simulate(config, currents)
    return {"configuration": json.loads(dumps(config)), "elapsed_s": perf_counter()-started,
            "rows": [{"active_current_A": float(i), "terminal_current_A": float(o["current_total_A"]),
                      "power_mW": float(o["power_W"]*1000), "voltage_V": float(o["voltage_V"]),
                      "wpe_percent": float(o["wpe"]*100)} for i, o in zip(currents, results)]}


def compare_nominal(config, surrogate):
    """Compare like-for-like nominal constants, regardless of accepted fit state."""
    baseline = deepcopy(config)
    baseline["physical"] = getattr(surrogate, "physical", default_config()["physical"])
    started = perf_counter()
    predicted = surrogate.predict(**surrogate_inputs(baseline))
    pinn_ms = (perf_counter()-started)*1000
    started = perf_counter()
    physical = simulate(baseline)[0]
    solver_ms = (perf_counter()-started)*1000
    rows = []
    for name, ref, value in [("Power (mW)", physical["power_W"]*1000, predicted["P_opt"]*1000),
                              ("WPE (%)", physical["wpe"]*100, predicted["wpe"]*100),
                              ("Terminal current (A)", physical["current_total_A"], predicted["I_total"])]:
        rows.append({"Metric": name, "Simulator": float(ref), "PINN": float(value),
                     "Absolute difference": float(abs(value-ref))})
    return {"configuration": json.loads(dumps(config)), "nominal_physical": baseline["physical"],
            "pinn_ms": pinn_ms, "solver_ms": solver_ms, "rows": rows}


def render_simulator_core(c, t):
    st.subheader(t("Simulator core", "模拟器内核"))
    st.write(t("Solve longitudinal carrier and photon distributions, then sweep current to generate L-I-V data for this device.",
               "求解器件纵向载流子与光子分布，通过电流扫描生成 L-I-V 数据。"))
    st.caption(t("This sweep uses the reduced longitudinal engine with 51 cavity nodes. Coupled transverse field solves are configured below using the Lasers Elmer runtime.",
                 "此扫描使用 51 个腔轴节点的纵向降阶内核。下方可使用 Lasers Elmer 运行时配置耦合横截面空间场求解。"))
    with st.expander(t("Equations and physical constants", "方程与物理常数")):
        st.latex(r"G_{\mathrm{inj}}-R_{\mathrm{rec}}(N)-R_{\mathrm{stim}}(N,P)=0")
        st.latex(r"\frac{dP^{\pm}}{dz}=\pm\left(\Gamma g(N)-\alpha_i\right)P^{\pm}")
        st.caption(t("Steady-state CW; facet reflectivities set the optical boundary conditions.",
                     "稳态连续波；端面反射率给出光学边界条件。"))
    fit = st.session_state.ridge_fit
    applied = st.session_state.ridge_applied and fit is not None
    active = fit["estimated"] if applied else c
    st.caption(t("Using accepted fitted constants." if applied else "Using saved device constants.",
                 "使用已接受的拟合常数。" if applied else "使用已保存的器件常数。"))
    st.dataframe([{"Parameter / 参数": k, "Value / 数值": v, "Unit / 单位": PHYSICAL_UNITS[k]}
                  for k, v in active["physical"].items()], hide_index=True)
    with st.form("simulator_sweep"):
        a, b, d = st.columns(3)
        low = a.number_input(t("Start current (A)", "起始电流 (A)"), .01, .49, .05, .01, key="sweep_low")
        high = b.number_input(t("End current (A)", "终止电流 (A)"), .02, .5, .4, .01, key="sweep_high")
        points = d.number_input(t("Samples", "采样点数"), 3, 31, 12, key="sweep_points")
        run = st.form_submit_button(t("Run physical simulation", "运行物理仿真"), type="primary")
    if run:
        # A failed rerun must not leave a previous success visible as its result.
        st.session_state.pop("ridge_sweep", None)
        try:
            with st.spinner(t("Solving the current sweep…", "正在求解电流扫描…")):
                st.session_state.ridge_sweep = run_sweep(active, low, high, points)
        except (ValueError, RuntimeError) as ex:
            st.error(str(ex))
    result = st.session_state.get("ridge_sweep")
    if result and result["configuration"] != active:
        st.info(t("Device settings changed. Run the simulation again to refresh the results.",
                  "器件设置已变化，请重新运行仿真。"))
    elif result:
        st.caption(t("Last completed sweep", "上次完成的扫描") + f": {len(result['rows'])} points · {result['elapsed_s']:.3f} s")
        x = [r["active_current_A"] for r in result["rows"]]
        a, b = st.columns(2)
        for column, field, title in [(a, "power_mW", t("Optical power (mW)", "光功率 (mW)")),
                                      (b, "voltage_V", t("Terminal voltage (V)", "端电压 (V)"))]:
            fig = go.Figure(go.Scatter(x=x, y=[r[field] for r in result["rows"]], mode="lines+markers"))
            fig.update_layout(template="plotly_dark", height=300, margin=dict(l=20,r=20,t=30,b=20),
                              title=title, xaxis_title=t("Active current (A)", "有源区电流 (A)"))
            column.plotly_chart(fig, width="stretch", key=f"sweep_{field}")
        st.dataframe(result["rows"], hide_index=True)
        st.download_button(t("Download simulation report", "下载仿真报告"), json.dumps(result, indent=2),
                           "tlaser_simulation.json", "application/json")
        measurement = {"current_semantics": "active_region", "current_A": x,
                       "voltage_V": [r["voltage_V"] for r in result["rows"]],
                       "optical_power_W": [r["power_mW"]/1000 for r in result["rows"]],
                       "metadata": {**active["geometry"], **active["optical"],
                                    "T0": active["operating"]["T0_K"], "source": "synthetic_simulator"}}
        st.download_button(t("Download synthetic L-I-V dataset", "下载合成 L-I-V 数据集"),
                           json.dumps(measurement, indent=2), "tlaser_synthetic_liv.json", "application/json")


def render_pinn_surrogate(c, surrogate, t):
    st.subheader(t("PINN surrogate", "PINN 代理模型"))
    st.write(t("Inspect the active surrogate and compare its prediction with the physical simulator at the saved operating point. Generate and train a new model below.",
               "查看当前代理模型，在保存的工作点与物理模拟器对比预测结果。下方可生成数据并训练新模型。"))
    if surrogate is None:
        st.warning(t("No trained surrogate is loaded. Physical simulation and calibration remain available.",
                     "未加载训练后的代理模型，仍可使用物理仿真与标定。"))
        return
    a, b, d = st.columns(3)
    a.metric(t("Inputs", "输入数"), 7)
    b.metric(t("Outputs", "输出数"), 105)
    d.metric(t("Trainable weights", "模型参数量"), f"{sum(p.numel() for p in surrogate.model.parameters()):,}")
    st.success(t("Trained model loaded · CPU inference", "已加载训练模型 · CPU 推理"))
    st.write(t("7 inputs → 128 → 128 → 128 → 105 outputs: optical power, efficiency, terminal current, and two 51-point profiles.",
               "7 维输入 → 128 → 128 → 128 → 105 维输出：光功率、效率、端口电流以及两组 51 点剖面。"))
    meta_path = ROOT / "data" / "pinn_dataset_metadata.json"
    with st.expander(t("Training data and physics constraints", "训练数据与物理约束")):
        if hasattr(surrogate, "physical"):
            st.json({"sampling_ranges": surrogate.ranges, "fixed_physical_constants": surrogate.physical})
        elif meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            st.write(t("Recorded synthetic training samples", "记录的合成训练样本数"), meta["sample_count"])
            st.dataframe([{"Input / 输入": k, "Min / 下限": v[0], "Max / 上限": v[1]}
                          for k, v in meta["parameter_ranges"].items()], hide_index=True)
        if hasattr(surrogate, "physical"):
            st.latex(r"\mathcal{L}=\mathcal{L}_{data}+\lambda(\mathcal{L}_{carrier}+\mathcal{L}_{photon})+0.02\mathcal{L}_{smooth},\quad\lambda\leq0.005")
        else:
            st.latex(r"\mathcal{L}=\mathcal{L}_{data}+0.05\mathcal{L}_{carrier}+0.05\mathcal{L}_{photon}+1.5\mathcal{L}_{smooth}")
        loss_plot = ROOT / "data" / "pinn_training_loss.png"
        if loss_plot.exists() and not hasattr(surrogate, "physical"):
            st.image(str(loss_plot), caption=t("Saved training history", "已保存的训练历史"))
        st.caption(t("New training jobs save separate model versions; activating a model does not overwrite the bundled checkpoint.",
                     "新训练任务保存独立模型版本，启用模型不会覆盖内置权重。"))
    st.caption(t("Comparison uses the model's fixed training constants. A single operating-point comparison is not measured-device validation or a latency guarantee.",
                 "对比采用模型的固定训练常数。单工作点对比不代表实测器件验证或延迟保证。"))
    if st.button(t("Compare PINN with simulator", "对比 PINN 与模拟器"), key="compare_pinn"):
        st.session_state.pop("ridge_pinn_check", None)
        try:
            with st.spinner(t("Comparing the saved operating point…", "正在对比保存的工作点…")):
                st.session_state.ridge_pinn_check = compare_nominal(c, surrogate)
        except (ValueError, RuntimeError) as ex:
            st.error(str(ex))
    report = st.session_state.get("ridge_pinn_check")
    if report and report["configuration"] != c:
        st.info(t("Device settings changed. Compare again to refresh this report.", "器件设置已变化，请重新对比。"))
    elif report:
        st.dataframe(report["rows"], hide_index=True)
        a, b = st.columns(2)
        a.metric(t("PINN call time", "PINN 调用耗时"), f"{report['pinn_ms']:.2f} ms")
        b.metric(t("Simulator call time", "模拟器调用耗时"), f"{report['solver_ms']:.2f} ms")
        st.download_button(t("Download comparison", "下载对比报告"), json.dumps(report, indent=2),
                           "tlaser_pinn_comparison.json", "application/json")

# -*- coding: utf-8 -*-
import sys
import os
import json
from pathlib import Path
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt

# Set page layout and config
st.set_page_config(
    page_title="TLaser - Digital Twin Control Center",
    layout="wide",
    initial_sidebar_state="expanded"
)

# App directory configuration
APP_DIR = Path(__file__).resolve().parent
sys.path.append(str(APP_DIR / "surrogate"))
sys.path.append(str(APP_DIR / "calibration"))
sys.path.append(str(APP_DIR / "simulator"))

from pinn_surrogate import PINNSurrogate
import calibrate
from vcsel_simulator import VCSELSimulator
from vcsel_validator import validate_vcsel_liv
from vcsel_calibrate import run_vcsel_calibration

# Load surrogate model wrapper
@st.cache_resource
def load_surrogate():
    return PINNSurrogate(APP_DIR)

try:
    surrogate = load_surrogate()
    model_loaded = True
except Exception as e:
    st.error(f"Error loading surrogate model: {e}")
    model_loaded = False

# Bilingual dictionaries with clean character encoding
STRINGS = {
    "EN": {
        "title": "TLaser - Digital Twin Control Center",
        "subtitle": "Physics-Informed Reduced-Order Twin for Telecom Diode Lasers",
        "lang_label": "Language / Select",
        "mode_label": "Mode Selector",
        "mode_dash": "Live Monitoring & Predictions",
        "mode_calib": "Parameter Calibration Loop",
        "geom_section": "Geometry Configuration",
        "R1_label": "Rear Refl R1",
        "R2_label": "Front Refl R2",
        "L_label": "Cavity Length L (um)",
        "T0_label": "Temperature T0 (K)",
        "I_label": "Active Region Current I (A)",
        "w_label": "Ridge Width w (um)",
        "d_label": "Active Thickness d (um)",
        "metrics_header": "Instant Surrogate Metrics",
        "popt_label": "Output Power (mW)",
        "wpe_label": "Wall-Plug Efficiency (WPE)",
        "itot_label": "Total Terminal Current (A)",
        "profile_header": "1D Longitudinal Profiles",
        "n_title": "Carrier Density N(z)",
        "p_title": "Optical Power Profile P(z)",
        "calib_header": "Online Calibration Engine",
        "calib_desc": "Upload real-time measured Light-Current-Voltage (L-I-V) dataset to calibrate unmeasurable physical constants.",
        "calib_btn": "Run Parameter Calibration",
        "calib_success": "Calibration successfully completed!",
        "calib_metrics": "Fitted Parameters",
        "calib_chart_title": "Before vs After Calibration Fit comparison",
        "device_family_label": "Device Family Selector",
        "device_eel": "Edge-emitting Diode Laser",
        "device_vcsel": "VCSEL",
        "vcsel_geom_section": "VCSEL Geometry & Cavity Settings",
        "dap_label": "Aperture Diameter d_ap (um)",
        "rdbr_top_label": "Top DBR Reflectivity R_top",
        "rdbr_bot_label": "Bottom DBR Reflectivity R_bot",
        "rth_label": "Thermal Resistance R_th (K/W)",
        "tambient_label": "Ambient Temperature T0 (K)",
        "qw_thick_label": "Active QW Thickness d_active (nm)",
        "vcsel_current_label": "Operating Current I (mA)",
        "vcsel_metrics_header": "VCSEL Output Metrics",
        "vcsel_popt_label": "Output Power (mW)",
        "vcsel_vterm_label": "Terminal Voltage (V)",
        "vcsel_wpe_label": "Wall-Plug Efficiency (WPE)",
        "vcsel_temp_label": "Junction Temp T_junction (K)",
        "vcsel_ith_label": "Threshold Current I_th (mA)",
        "vcsel_profile_header": "Radial Active Region Profiles",
        "vcsel_n_title": "Radial Carrier Density N(r)",
        "vcsel_p_title": "Steady-State L-I-V Curves"
    },
    "CN": {
        "title": "TLaser 数字孪生主控制中心",
        "subtitle": "基于物理信息神经网络（PINN）的通信级半导体激光器实时建模与标定",
        "lang_label": "Language / 语言选择",
        "mode_label": "模式选择",
        "mode_dash": "实时状态监测与预测",
        "mode_calib": "内部物性参数在线标定",
        "geom_section": "有源区几何结构配置",
        "R1_label": "后腔镜反射率 R1",
        "R2_label": "前腔镜反射率 R2",
        "L_label": "谐振腔长度 L (微米)",
        "T0_label": "工作温度 T0 (K)",
        "I_label": "有源区注入电流 I (A)",
        "w_label": "脊宽 w (微米)",
        "d_label": "有源层厚度 d (微米)",
        "metrics_header": "孪生模型输出指标",
        "popt_label": "输出光功率 (mW)",
        "wpe_label": "电光转换效率 (WPE)",
        "itot_label": "总输入电流 (A)",
        "profile_header": "1D 纵向剖面分布",
        "n_title": "载流子浓度 N(z)",
        "p_title": "光功率分布 P(z)",
        "calib_header": "在线参数标定引擎",
        "calib_desc": "上传实时监测得到的 L-I-V 曲线，标定内部漂移或未知的微观物性常数。",
        "calib_btn": "开始在线参数标定",
        "calib_success": "参数标定已成功收敛！",
        "calib_metrics": "标定拟合参数结果",
        "calib_chart_title": "标定前与标定后拟合质量对比",
        "device_family_label": "激光器器件族选择",
        "device_eel": "边发射半导体激光器 (EEL)",
        "device_vcsel": "垂直腔面发射激光器 (VCSEL)",
        "vcsel_geom_section": "VCSEL 结构与谐振腔参数",
        "dap_label": "氧化孔径 d_ap (微米)",
        "rdbr_top_label": "上 DBR 镜面反射率 R_top",
        "rdbr_bot_label": "下 DBR 镜面反射率 R_bot",
        "rth_label": "热阻 R_th (K/W)",
        "tambient_label": "环境温度 T0 (K)",
        "qw_thick_label": "有源 QW 总厚度 d_active (纳米)",
        "vcsel_current_label": "工作电流 I (毫安)",
        "vcsel_metrics_header": "VCSEL 输出指标",
        "vcsel_popt_label": "输出光功率 (mW)",
        "vcsel_vterm_label": "端电压 (V)",
        "vcsel_wpe_label": "电光转换效率 (WPE)",
        "vcsel_temp_label": "激光器结温 T_junction (K)",
        "vcsel_ith_label": "阈值电流 I_th (mA)",
        "vcsel_profile_header": "径向有源区剖面分布",
        "vcsel_n_title": "径向载流子浓度 N(r)",
        "vcsel_p_title": "稳态 L-I-V 扫描曲线"
    }
}

# Sidebar inputs
st.sidebar.markdown("### Language / 语言 Selection")
lang = st.sidebar.selectbox("Language Selection", ["EN", "CN"], label_visibility="collapsed")
st.sidebar.markdown("---")

txt = STRINGS[lang]

# Device Family Selector
st.sidebar.header(txt["device_family_label"])
device_family = st.sidebar.selectbox("Device Family", [txt["device_eel"], txt["device_vcsel"]], label_visibility="collapsed")
st.sidebar.markdown("---")

# Sidebar App Title
st.sidebar.header(txt["mode_label"])
mode = st.sidebar.radio("Mode", [txt["mode_dash"], txt["mode_calib"]], label_visibility="collapsed")
st.sidebar.markdown("---")

# Main Page Header
st.title(txt["title"])
st.subheader(txt["subtitle"])
st.markdown("---")

if model_loaded:
    # Mode 1: Live Monitoring & Predictions
    if mode == txt["mode_dash"]:
        # 2 columns for inputs and outputs
        col_in, col_out = st.columns([1, 2])
        
        if device_family == txt["device_eel"]:
            with col_in:
                st.markdown(f"### {txt['geom_section']}")
                R1 = st.slider(txt["R1_label"], 0.1, 0.95, 0.90, 0.05)
                R2 = st.slider(txt["R2_label"], 0.05, 0.50, 0.05, 0.01)
                L_um = st.slider(txt["L_label"], 100, 1000, 300, 50)
                T0 = st.slider(txt["T0_label"], 250, 360, 298, 5)
                I_active = st.slider(txt["I_label"], 0.01, 0.50, 0.15, 0.01)
                w_active = st.slider(txt["w_label"], 1.5, 4.0, 2.8, 0.1)
                d_active = st.slider(txt["d_label"], 0.1, 0.5, 0.342, 0.01)
                
                # Predict
                res = surrogate.predict(R1, R2, L_um, T0, I_active, w_active, d_active)
                P_opt = res["P_opt"]
                wpe = res["wpe"]
                I_total = res["I_total"]
                N_prof = res["N"]
                P_prof = res["P"]
                z_grid = res["z_grid"]
                
            with col_out:
                st.markdown(f"### {txt['metrics_header']}")
                m1, m2, m3 = st.columns(3)
                m1.metric(txt["popt_label"], f"{P_opt * 1000.0:.2f} mW")
                m2.metric(txt["wpe_label"], f"{wpe * 100.0:.3f} %")
                m3.metric(txt["itot_label"], f"{I_total:.3f} A")
                
                st.markdown(f"### {txt['profile_header']}")
                fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5), facecolor="#0d1117")
                
                # N(z) plot
                ax1.plot(z_grid, N_prof / 1e18, color="#ff7b72", linewidth=2.5, label="N(z)")
                ax1.set_title(txt["n_title"], color="white", fontsize=11, fontweight="bold")
                ax1.set_xlabel("z Position (um)", color="#8b949e")
                ax1.set_ylabel("N (10^18 cm^-3)", color="#8b949e")
                ax1.grid(True, linestyle="--", alpha=0.3, color="#233554")
                ax1.set_facecolor("#172a45")
                ax1.tick_params(colors="#8b949e")
                for spine in ax1.spines.values():
                    spine.set_color("#30363d")
                    
                # P(z) plot
                ax2.plot(z_grid, P_prof * 1000.0, color="#64ffda", linewidth=2.5, label="P(z)")
                ax2.set_title(txt["p_title"], color="white", fontsize=11, fontweight="bold")
                ax2.set_xlabel("z Position (um)", color="#8b949e")
                ax2.set_ylabel("Optical Power (mW)", color="#8b949e")
                ax2.grid(True, linestyle="--", alpha=0.3, color="#233554")
                ax2.set_facecolor("#172a45")
                ax2.tick_params(colors="#8b949e")
                for spine in ax2.spines.values():
                    spine.set_color("#30363d")
                    
                plt.tight_layout()
                st.pyplot(fig)
                
        else:
            with col_in:
                st.markdown(f"### {txt['vcsel_geom_section']}")
                vcsel_dap = st.slider(txt["dap_label"], 4.0, 12.0, 8.0, 0.5)
                vcsel_r_top = st.slider(txt["rdbr_top_label"], 0.990, 0.998, 0.995, 0.0005)
                vcsel_r_bot = st.slider(txt["rdbr_bot_label"], 0.995, 0.9995, 0.999, 0.0001)
                vcsel_r_th = st.slider(txt["rth_label"], 500.0, 2500.0, 1200.0, 50.0)
                vcsel_t0 = st.slider(txt["tambient_label"], 250.0, 360.0, 298.0, 2.0)
                vcsel_d_nm = st.slider(txt["qw_thick_label"], 10.0, 50.0, 24.0, 2.0)
                vcsel_I = st.slider(txt["vcsel_current_label"], 0.0, 15.0, 6.0, 0.2)
                
                # Simulate
                sim_v = VCSELSimulator(
                    aperture_dia_um=vcsel_dap,
                    R_DBR_top=vcsel_r_top,
                    R_DBR_bottom=vcsel_r_bot,
                    R_th=vcsel_r_th,
                    T_ambient=vcsel_t0,
                    active_thickness_nm=vcsel_d_nm
                )
                res = sim_v.solve_radial_profiles(vcsel_I)
                
                P_opt = res["P_opt_mW"]
                V_term = res["V_term"]
                wpe = res["WPE"]
                T_j = res["T_junction"]
                I_th = res["I_th_mA"]
                
                r_grid = res["r_grid_um"]
                N_profile = res["N"]
                I_profile = res["I_profile"]
                mode_profile = res["mode_profile"]
                
            with col_out:
                st.markdown(f"### {txt['vcsel_metrics_header']}")
                m1, m2, m3, m4, m5 = st.columns(5)
                m1.metric(txt["vcsel_popt_label"], f"{P_opt:.3f} mW")
                m2.metric(txt["vcsel_vterm_label"], f"{V_term:.3f} V")
                m3.metric(txt["vcsel_wpe_label"], f"{wpe * 100.0:.3f} %")
                m4.metric(txt["vcsel_temp_label"], f"{T_j:.2f} K")
                m5.metric(txt["vcsel_ith_label"], f"{I_th:.3f} mA")
                
                st.markdown(f"### {txt['vcsel_profile_header']}")
                fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5), facecolor="#0d1117")
                ax1.set_facecolor("#172a45")
                ax2.set_facecolor("#172a45")
                
                # Helper function for integration
                def trap_int(y, dx):
                    return dx * (np.sum(y) - 0.5 * (y[0] + y[-1]))
                
                # Plot 1: Radial Profiles
                l1, = ax1.plot(r_grid, N_profile / 1e18, color="#ff7b72", linewidth=2.5, label="N (10^18 cm^-3)")
                ax1_twin = ax1.twinx()
                l2, = ax1_twin.plot(r_grid, I_profile, color="#79c0ff", linewidth=2.0, linestyle="--", label="Injected Current")
                l3, = ax1_twin.plot(r_grid, mode_profile, color="#64ffda", linewidth=1.5, linestyle=":", label="LP01 Mode")
                ax1.axvline(x=vcsel_dap/2.0, color="#d29922", linestyle="-.", alpha=0.7, label="Aperture Radius")
                
                ax1.set_title(txt["vcsel_n_title"], color="white", fontsize=11, fontweight="bold")
                ax1.set_xlabel("Radial Position r (um)", color="#8b949e")
                ax1.set_ylabel("Carrier Density (10^18 cm^-3)", color="#8b949e")
                ax1_twin.set_ylabel("Normalized Profile", color="#8b949e")
                ax1.grid(True, linestyle="--", alpha=0.3, color="#233554")
                ax1.tick_params(colors="#8b949e")
                ax1_twin.tick_params(colors="#8b949e")
                
                lines = [l1, l2, l3]
                labels = [line.get_label() for line in lines]
                ax1.legend(lines, labels, loc="upper right", fontsize=8, facecolor="#161b22", edgecolor="#30363d")
                for spine in ax1.spines.values():
                    spine.set_color("#30363d")
                for spine in ax1_twin.spines.values():
                    spine.set_color("#30363d")
                    
                # Plot 2: Steady-State LIV Curves
                sims_currents = np.linspace(0.1, 14.0, 30)
                sims_powers = []
                sims_voltages = []
                for cur_mA in sims_currents:
                    out_c = sim_v.solve_radial_profiles(cur_mA)
                    sims_powers.append(out_c["P_opt_mW"])
                    sims_voltages.append(out_c["V_term"])
                    
                ax2.plot(sims_currents, sims_powers, color="#64ffda", linewidth=2.5, label="Power (mW)")
                ax2_twin = ax2.twinx()
                ax2_twin.plot(sims_currents, sims_voltages, color="#ff7b72", linewidth=2.0, linestyle="--", label="Voltage (V)")
                
                # Operating point marker
                ax2.scatter([vcsel_I], [P_opt], color="#64ffda", s=80, edgecolors="white", zorder=5)
                ax2_twin.scatter([vcsel_I], [V_term], color="#ff7b72", s=80, edgecolors="white", zorder=5)
                
                ax2.set_title(txt["vcsel_p_title"], color="white", fontsize=11, fontweight="bold")
                ax2.set_xlabel("Injected Current (mA)", color="#8b949e")
                ax2.set_ylabel("Output Power (mW)", color="#64ffda")
                ax2_twin.set_ylabel("Terminal Voltage (V)", color="#ff7b72")
                ax2.grid(True, linestyle="--", alpha=0.3, color="#233554")
                ax2.tick_params(colors="#8b949e")
                ax2_twin.tick_params(colors="#8b949e")
                
                for spine in ax2.spines.values():
                    spine.set_color("#30363d")
                for spine in ax2_twin.spines.values():
                    spine.set_color("#30363d")
                    
                plt.tight_layout()
                st.pyplot(fig)
            
    # Mode 2: Calibration Loop
    else:
        st.markdown(f"### {txt['calib_header']}")
        st.write(txt["calib_desc"])
        
        if device_family == txt["device_eel"]:
            cal_path = APP_DIR / "data" / "calibrated_params.json"
            history_path = APP_DIR / "data" / "calibration_history.json"
            
            # 1. Download templates section
            st.markdown("#### 📂 Download Monitored Data Templates")
            csv_template = "Current_A,Voltage_V,Power_W\n0.05,1.02,0.005\n0.10,1.05,0.020\n0.15,1.08,0.040\n0.20,1.10,0.065\n0.25,1.13,0.090\n0.30,1.15,0.115\n0.35,1.18,0.140\n0.40,1.20,0.165"
            json_template = json.dumps({
                "current_A": [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40],
                "voltage_V": [1.02, 1.05, 1.08, 1.10, 1.13, 1.15, 1.18, 1.20],
                "optical_power_W": [0.005, 0.020, 0.040, 0.065, 0.090, 0.115, 0.140, 0.165],
                "metadata": {
                    "R1": 0.90, "R2": 0.05, "L_um": 300.0, "T0": 298.0, "w_um": 2.8, "d_um": 0.342
                }
            }, indent=4)
            
            t_col1, t_col2 = st.columns(2)
            with t_col1:
                st.download_button("Download CSV Template", csv_template, "monitored_liv_template.csv", "text/csv")
            with t_col2:
                st.download_button("Download JSON Template", json_template, "monitored_liv_template.json", "application/json")
                
            st.markdown("---")
            
            # 2. Upload and Auto Calibration section
            st.markdown("#### 🤖 Automated Parameter Calibration")
            uploaded_file = st.file_uploader("Upload monitored LIV data (.json/.csv)", type=["json", "csv"])
            
            if st.button(txt["calib_btn"]):
                with st.spinner("Optimizing digital twin parameters to fit measurement data..."):
                    if uploaded_file is not None:
                        temp_path = APP_DIR / "data" / f"temp_{uploaded_file.name}"
                        with open(temp_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        data_file_arg = str(temp_path)
                    else:
                        data_file_arg = None
                    
                    try:
                        calibrate.run_calibration(
                            data_file=data_file_arg,
                            output_dir=str(APP_DIR / "data"),
                            smoke_test=False
                        )
                        st.success(txt["calib_success"])
                    except Exception as ex:
                        st.error(f"Error during calibration: {ex}")
                    finally:
                        if data_file_arg and os.path.exists(data_file_arg):
                            try:
                                os.remove(data_file_arg)
                            except Exception:
                                pass
                                
            st.markdown("---")
            
            # 3. Interactive Manual Calibration fine-tuning
            st.markdown("#### 🎚️ Manual Calibration Fine-Tuning Overlay")
            enable_manual = st.checkbox("Enable Manual Slider Adjustment")
            
            if enable_manual:
                col_m1, col_m2 = st.columns([1, 2])
                with col_m1:
                    st.markdown("**Adjust Physical Twin Parameters:**")
                    m_alpha_i = st.slider("Internal Loss alpha_i (cm^-1)", 5.0, 20.0, 10.0, 0.1)
                    m_Gamma = st.slider("Confinement Factor Gamma", 0.03, 0.08, 0.05, 0.001)
                    m_C_mult = st.slider("Auger Multiplier C", 0.5, 3.0, 1.0, 0.05)
                    m_R_series = st.slider("Series Resistance Rs (Ohm)", 0.1, 3.0, 1.0, 0.05)
                    m_R_shunt = st.slider("Shunt Resistance Rsh (Ohm)", 50.0, 1000.0, 200.0, 10.0)
                    
                with col_m2:
                    currents_sim = np.linspace(0.05, 0.40, 10)
                    R1 = 0.90
                    R2 = 0.05
                    L_um = 300.0
                    T0 = 298.0
                    w_um = 2.8
                    d_um = 0.342
                    
                    P_sim, V_sim, _ = calibrate.simulate_liv(
                        currents_sim, R1, R2, L_um, T0, w_um, d_um,
                        m_alpha_i, m_Gamma, m_C_mult, m_R_series, m_R_shunt
                    )
                    
                    mon_currents, mon_P, mon_V, _ = calibrate.generate_mock_monitoring_data()
                    
                    fig_m, (ax_m1, ax_m2) = plt.subplots(1, 2, figsize=(11, 4.5), facecolor="#0d1117")
                    
                    ax_m1.scatter(mon_currents, mon_P * 1000.0, color="#ff7b72", marker="o", label="Monitored Data")
                    ax_m1.plot(currents_sim, P_sim * 1000.0, color="#64ffda", linewidth=2.5, label="Manual Slider Fit")
                    ax_m1.set_title("L-I Fit Comparison (Power)", color="white", fontsize=10, fontweight="bold")
                    ax_m1.set_xlabel("Current (A)", color="#8b949e", fontsize=8)
                    ax_m1.set_ylabel("Power (mW)", color="#8b949e", fontsize=8)
                    ax_m1.grid(True, linestyle="--", alpha=0.3, color="#555555")
                    ax_m1.set_facecolor("#172a45")
                    ax_m1.tick_params(colors="white")
                    ax_m1.legend(loc="upper left")
                    for spine in ax_m1.spines.values():
                        spine.set_color("#30363d")
                        
                    ax_m2.scatter(mon_currents, mon_V, color="#ff7b72", marker="o", label="Monitored Data")
                    ax_m2.plot(currents_sim, V_sim, color="#64ffda", linewidth=2.5, label="Manual Slider Fit")
                    ax_m2.set_title("V-I Fit Comparison (Voltage)", color="white", fontsize=10, fontweight="bold")
                    ax_m2.set_xlabel("Current (A)", color="#8b949e", fontsize=8)
                    ax_m2.set_ylabel("Voltage (V)", color="#8b949e", fontsize=8)
                    ax_m2.grid(True, linestyle="--", alpha=0.3, color="#555555")
                    ax_m2.set_facecolor("#172a45")
                    ax_m2.tick_params(colors="white")
                    ax_m2.legend(loc="upper left")
                    for spine in ax_m2.spines.values():
                        spine.set_color("#30363d")
                        
                    plt.tight_layout()
                    st.pyplot(fig_m)
                    
            st.markdown("---")
            
            # 4. Display Calibrated Parameter comparisons & History
            col_res1, col_res2 = st.columns([1, 1])
            
            with col_res1:
                if cal_path.exists():
                    with open(cal_path, "r", encoding="utf-8") as f:
                        cal = json.load(f)
                        
                    st.markdown(f"### {txt['calib_metrics']}")
                    st.write(f"**Last Calibration Run:** {cal.get('timestamp', 'N/A')}")
                    st.write(f"Internal Loss α_i: `{cal['alpha_i']:.4f} cm^-1`")
                    st.write(f"Confinement Factor Γ: `{cal['Gamma']:.5f}`")
                    st.write(f"Auger Multiplier C: `{cal['C_mult']:.4f}`")
                    st.write(f"Series Resistance Rs: `{cal['R_series']:.4f} Ω`")
                    st.write(f"Shunt Resistance Rsh: `{cal['R_shunt']:.2f} Ω`")
                    
                    st.markdown(f"### {txt['calib_chart_title']}")
                    fit_plot_path = APP_DIR / "data" / "calibration_fit.svg"
                    if fit_plot_path.exists():
                        st.image(str(fit_plot_path))
                        
            with col_res2:
                st.markdown("### 📈 Digital Twin Parameter Drift Trends")
                if history_path.exists():
                    try:
                        with open(history_path, "r", encoding="utf-8") as f:
                            hist = json.load(f)
                        if isinstance(hist, list) and len(hist) > 0:
                            runs = np.arange(1, len(hist) + 1)
                            alphas = [r["alpha_i"] for r in hist]
                            gammas = [r["Gamma"] for r in hist]
                            c_mults = [r["C_mult"] for r in hist]
                            r_ser = [r["R_series"] for r in hist]
                            r_sh = [r["R_shunt"] for r in hist]
                            
                            fig_h, axs = plt.subplots(5, 1, figsize=(6, 9), facecolor="#0d1117")
                            
                            axs[0].plot(runs, alphas, marker="o", color="#ff7b72", linewidth=2)
                            axs[0].set_ylabel("alpha_i", color="white", fontsize=8)
                            axs[0].set_title("Fitted Constants History", color="white", fontsize=10, fontweight="bold")
                            
                            axs[1].plot(runs, gammas, marker="s", color="#64ffda", linewidth=2)
                            axs[1].set_ylabel("Gamma", color="white", fontsize=8)
                            
                            axs[2].plot(runs, c_mults, marker="^", color="#ffcc00", linewidth=2)
                            axs[2].set_ylabel("C_mult", color="white", fontsize=8)
                            
                            axs[3].plot(runs, r_ser, marker="v", color="#ff33cc", linewidth=2)
                            axs[3].set_ylabel("Rs (Ohm)", color="white", fontsize=8)
                            
                            axs[4].plot(runs, r_sh, marker="d", color="#58a6ff", linewidth=2)
                            axs[4].set_ylabel("Rsh (Ohm)", color="white", fontsize=8)
                            axs[4].set_xlabel("Calibration Run Index", color="white", fontsize=8)
                            
                            for ax in axs:
                                ax.set_facecolor("#172a45")
                                ax.tick_params(colors="#8b949e", labelsize=7)
                                ax.grid(True, linestyle="--", alpha=0.2, color="#555555")
                                for spine in ax.spines.values():
                                    spine.set_color("#30363d")
                                    
                            plt.tight_layout()
                            st.pyplot(fig_h)
                        else:
                            st.info("No calibration history entries available yet.")
                    except Exception as ex:
                        st.error(f"Error rendering trend chart: {ex}")
                else:
                    st.info("Run parameter calibration to begin tracking historical physical trends.")
                    
        else:
            # VCSEL Calibration Loop
            cal_path = APP_DIR / "data" / "vcsel_calibrated_params.json"
            
            # 1. Download templates section
            st.markdown("#### 📂 Download VCSEL Monitored Data Templates")
            vcsel_json_template = json.dumps({
                "current_mA": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0],
                "voltage_V": [1.51, 1.58, 1.66, 1.74, 1.83, 1.91, 2.00, 2.08, 2.16, 2.24],
                "optical_power_mW": [0.0, 0.05, 0.25, 0.58, 1.02, 1.48, 1.96, 2.38, 2.72, 2.92],
                "metadata": {
                    "device_id": "VCSEL-850-001",
                    "device_family": "vcsel",
                    "aperture_dia_um": 8.0,
                    "T_ambient_K": 298.0,
                    "wavelength_nominal_nm": 850.0
                }
            }, indent=4)
            st.download_button("Download VCSEL JSON Template", vcsel_json_template, "vcsel_monitored_liv_template.json", "application/json")
            
            st.markdown("---")
            
            # 2. Upload and Auto Calibration section
            st.markdown("#### 🤖 Automated VCSEL Parameter Calibration")
            uploaded_file = st.file_uploader("Upload monitored VCSEL LIV data (.json)", type=["json"])
            
            if st.button(txt["calib_btn"]):
                with st.spinner("Optimizing VCSEL digital twin parameters to fit measurement data..."):
                    if uploaded_file is not None:
                        temp_path = APP_DIR / "data" / f"temp_vcsel_{uploaded_file.name}"
                        with open(temp_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        data_file_arg = str(temp_path)
                    else:
                        data_file_arg = None
                    
                    try:
                        # Validate with jsonschema before running optimization
                        if data_file_arg:
                            ok, err_msg = validate_vcsel_liv(data_file_arg)
                            if not ok:
                                raise ValueError(f"VCSEL LIV Schema validation failed: {err_msg}")
                                
                        run_vcsel_calibration(
                            data_file=data_file_arg,
                            output_dir=str(APP_DIR / "data"),
                            smoke_test=False
                        )
                        st.success(txt["calib_success"])
                    except Exception as ex:
                        st.error(f"Error during VCSEL calibration: {ex}")
                    finally:
                        if data_file_arg and os.path.exists(data_file_arg):
                            try:
                                os.remove(data_file_arg)
                            except Exception:
                                pass
                                
            st.markdown("---")
            
            # 3. Interactive Manual Calibration fine-tuning
            st.markdown("#### 🎚️ Manual VCSEL Calibration Fine-Tuning Overlay")
            enable_manual = st.checkbox("Enable Manual Slider Adjustment")
            
            if enable_manual:
                col_m1, col_m2 = st.columns([1, 2])
                with col_m1:
                    st.markdown("**Adjust VCSEL Physical Twin Parameters:**")
                    m_rth = st.slider("Thermal Resistance Rth (K/W)", 500.0, 2500.0, 1200.0, 50.0)
                    m_rs = st.slider("Series Resistance Rs (Ohm)", 20.0, 150.0, 60.0, 1.0)
                    m_rdbr = st.slider("Top DBR Reflectivity R_top", 0.990, 0.998, 0.995, 0.0005)
                    m_amult = st.slider("Recombination Mult A", 0.5, 3.0, 1.0, 0.05)
                    m_cmult = st.slider("Auger Multiplier C", 0.5, 3.0, 1.0, 0.05)
                    
                with col_m2:
                    currents_sim = np.linspace(1.0, 12.0, 20)
                    sim_manual = VCSELSimulator(aperture_dia_um=8.0, R_DBR_top=m_rdbr, R_th=m_rth)
                    sim_manual.R_series = m_rs
                    sim_manual.A_recomb = sim_manual.A_recomb * m_amult
                    sim_manual.C_recomb = sim_manual.C_recomb * m_cmult
                    
                    powers_sim = []
                    voltages_sim = []
                    for cur in currents_sim:
                        out = sim_manual.solve_radial_profiles(cur)
                        powers_sim.append(out["P_opt_mW"])
                        voltages_sim.append(out["V_term"])
                        
                    # Reference mock/measured curves for plotting
                    ref_sim = VCSELSimulator(aperture_dia_um=8.0)
                    ref_sim.R_th = 1500.0
                    ref_sim.R_series = 68.0
                    ref_sim.R_DBR_top = 0.994
                    
                    powers_ref = []
                    voltages_ref = []
                    ref_currents = np.linspace(1.0, 10.0, 10)
                    for cur in ref_currents:
                        out = ref_sim.solve_radial_profiles(cur)
                        powers_ref.append(out["P_opt_mW"])
                        voltages_ref.append(out["V_term"])
                        
                    fig_m, (ax_m1, ax_m2) = plt.subplots(1, 2, figsize=(11, 4.5), facecolor="#0d1117")
                    ax_m1.set_facecolor("#172a45")
                    ax_m2.set_facecolor("#172a45")
                    
                    # Power plot
                    ax_m1.scatter(ref_currents, powers_ref, color="#ff7b72", marker="o", label="Target Data")
                    ax_m1.plot(currents_sim, powers_sim, color="#64ffda", linewidth=2.5, label="Manual Slider Fit")
                    ax_m1.set_title("L-I Fit Comparison (Power)", color="white", fontsize=10, fontweight="bold")
                    ax_m1.set_xlabel("Current (mA)", color="#8b949e", fontsize=8)
                    ax_m1.set_ylabel("Power (mW)", color="#8b949e", fontsize=8)
                    ax_m1.grid(True, linestyle="--", alpha=0.3, color="#555555")
                    ax_m1.tick_params(colors="white")
                    ax_m1.legend(loc="upper left")
                    for spine in ax_m1.spines.values():
                        spine.set_color("#30363d")
                        
                    # Voltage plot
                    ax_m2.scatter(ref_currents, voltages_ref, color="#ff7b72", marker="o", label="Target Data")
                    ax_m2.plot(currents_sim, voltages_sim, color="#64ffda", linewidth=2.5, label="Manual Slider Fit")
                    ax_m2.set_title("V-I Fit Comparison (Voltage)", color="white", fontsize=10, fontweight="bold")
                    ax_m2.set_xlabel("Current (mA)", color="#8b949e", fontsize=8)
                    ax_m2.set_ylabel("Voltage (V)", color="#8b949e", fontsize=8)
                    ax_m2.grid(True, linestyle="--", alpha=0.3, color="#555555")
                    ax_m2.tick_params(colors="white")
                    ax_m2.legend(loc="upper left")
                    for spine in ax_m2.spines.values():
                        spine.set_color("#30363d")
                        
                    plt.tight_layout()
                    st.pyplot(fig_m)
            
            st.markdown("---")
            
            # 4. Display Calibrated parameters comparison
            if cal_path.exists():
                with open(cal_path, "r", encoding="utf-8") as f:
                    cal = json.load(f)
                
                st.markdown(f"### {txt['calib_metrics']}")
                st.write(f"**Optimization Success Status:** `{cal['success']}`")
                st.write(f"Weighted Fit Residual Loss: `{cal['loss']:.6f}`")
                
                vals = cal["calibrated_values"]
                st.write(f"Thermal Resistance Rth: `{vals['R_th_K_W']:.2f} K/W`")
                st.write(f"Series Resistance Rs: `{vals['R_series_Ohm']:.3f} Ω`")
                st.write(f"Top DBR Reflectivity R_top: `{vals['R_DBR_top']:.5f}`")
                st.write(f"Recombination A Multiplier: `{vals['A_recomb_multiplier']:.4f}`")
                st.write(f"Auger Recombination C Multiplier: `{vals['C_recomb_multiplier']:.4f}`")
                
                st.markdown(f"### {txt['calib_chart_title']}")
                fit_plot_path = APP_DIR / "data" / "vcsel_calibration_fit.svg"
                if fit_plot_path.exists():
                    st.image(str(fit_plot_path))
else:
    st.warning("Please verify that surrogate training has completed and saved model weights successfully.")

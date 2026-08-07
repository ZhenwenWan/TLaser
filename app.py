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

from pinn_surrogate import PINNSurrogate
import calibrate

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
        "calib_chart_title": "Before vs After Calibration Fit comparison"
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
        "calib_chart_title": "标定前与标定后拟合质量对比"
    }
}

# Sidebar inputs
st.sidebar.markdown("### Language / 语言 Selection")
lang = st.sidebar.selectbox("Language Selection", ["EN", "CN"], label_visibility="collapsed")
st.sidebar.markdown("---")

txt = STRINGS[lang]

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
            
    # Mode 2: Calibration Loop
    else:
        st.markdown(f"### {txt['calib_header']}")
        st.write(txt["calib_desc"])
        
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
                
                # Call calibrate.main() with arguments directly
                args_list = ["--output-dir", str(APP_DIR / "data")]
                if data_file_arg:
                    args_list += ["--data-file", data_file_arg]
                    
                try:
                    calibrate.main(args_list=args_list)
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
                # Simulate in real-time for visual override check
                currents_sim = np.linspace(0.05, 0.40, 10)
                # Static geometry
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
                
                # Fetch baseline/monitored clean data
                mon_currents, mon_P, mon_V, _ = calibrate.generate_mock_monitoring_data()
                
                fig_m, (ax_m1, ax_m2) = plt.subplots(1, 2, figsize=(11, 4.5), facecolor="#0d1117")
                
                # Power plot
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
                    
                # Voltage plot
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
                with open(cal_path, "r") as f:
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
                    with open(history_path, "r") as f:
                        hist = json.load(f)
                    if isinstance(hist, list) and len(hist) > 0:
                        runs = np.arange(1, len(hist) + 1)
                        alphas = [r["alpha_i"] for r in hist]
                        gammas = [r["Gamma"] for r in hist]
                        c_mults = [r["C_mult"] for r in hist]
                        r_ser = [r["R_series"] for r in hist]
                        r_sh = [r["R_shunt"] for r in hist]
                        
                        fig_h, axs = plt.subplots(5, 1, figsize=(6, 9), facecolor="#0d1117")
                        
                        # Plot trend for each parameter
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
    st.warning("Please verify that surrogate training has completed and saved model weights successfully.")

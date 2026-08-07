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

# Bilingual dictionaries
STRINGS = {
    "EN": {
        "title": "⚡ TLaser Digital Twin Control Center",
        "subtitle": "Physics-Informed Reduced-Order Twin for Telecom Diode Lasers",
        "lang_label": "🌐 Language / 语言",
        "mode_label": "📋 Mode Selector",
        "mode_dash": "📊 Live Monitoring & Predictions",
        "mode_calib": "⚙️ Parameter Calibration Loop",
        "geom_section": "📐 Geometry Config",
        "R1_label": "Rear Refl R1",
        "R2_label": "Front Refl R2",
        "L_label": "Cavity Length L (μm)",
        "T0_label": "Temperature T0 (K)",
        "I_label": "Active Region Current I (A)",
        "w_label": "Ridge Width w (μm)",
        "d_label": "Active Thickness d (μm)",
        "metrics_header": "📈 Instant Surrogate Metrics",
        "popt_label": "Output Power (mW)",
        "wpe_label": "Wall-Plug Efficiency (WPE)",
        "itot_label": "Total Terminal Current (A)",
        "profile_header": "🎛️ 1D Longitudinal Profiles",
        "n_title": "Carrier Density N(z)",
        "p_title": "Optical Power Profile P(z)",
        "calib_header": "🔧 Online Calibration Engine",
        "calib_desc": "Upload real-time measured Light-Current-Voltage (L-I-V) dataset to calibrate unmeasurable physical constants.",
        "calib_btn": "🚀 Run Parameter Calibration",
        "calib_success": "Calibration successfully completed!",
        "calib_metrics": "Fitted Parameters",
        "calib_chart_title": "Before vs After Calibration Fit comparison"
    },
    "CN": {
        "title": "⚡ TLaser 数字孪生主控制中心",
        "subtitle": "基于物理信息神经网络（PINN）的通信级半导体激光器实时建模与标定",
        "lang_label": "🌐 Language / 语言",
        "mode_label": "📋 模式选择",
        "mode_dash": "📊 实时状态监测与预测",
        "mode_calib": "⚙️ 内部物性参数在线标定",
        "geom_section": "📐 有源区几何结构配置",
        "R1_label": "后腔镜反射率 R1",
        "R2_label": "前腔镜反射率 R2",
        "L_label": "谐振腔长度 L (μm)",
        "T0_label": "工作温度 T0 (K)",
        "I_label": "有源区注入电流 I (A)",
        "w_label": "脊宽 w (μm)",
        "d_label": "有源层厚度 d (μm)",
        "metrics_header": "📈 孪生模型输出指标",
        "popt_label": "输出光功率 (mW)",
        "wpe_label": "电光转换效率 (WPE)",
        "itot_label": "总输入电流 (A)",
        "profile_header": "🎛️ 1D 纵向剖面分布",
        "n_title": "载流子浓度 N(z)",
        "p_title": "光功率分布 P(z)",
        "calib_header": "🔧 在线参数标定引擎",
        "calib_desc": "上传实时监测得到的 L-I-V (光强-电流-电压) 曲线，标定内部漂移或未知的微观物性常数。",
        "calib_btn": "🚀 开始在线参数标定",
        "calib_success": "参数标定已成功收敛！",
        "calib_metrics": "标定拟合参数结果",
        "calib_chart_title": "标定前与标定后拟合质量对比"
    }
}

# Sidebar inputs
st.sidebar.markdown("### Language / 语言 Selection")
lang = st.sidebar.selectbox("🌐 Language Selection", ["EN", "CN"], label_visibility="collapsed")
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
            
            # Predict button (runs automatically in real-time)
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
            ax1.set_xlabel("z Position (μm)", color="#8b949e")
            ax1.set_ylabel("N (10^18 cm^-3)", color="#8b949e")
            ax1.grid(True, linestyle="--", alpha=0.3, color="#233554")
            ax1.set_facecolor("#172a45")
            ax1.tick_params(colors="#8b949e")
            for spine in ax1.spines.values():
                spine.set_color("#30363d")
                
            # P(z) plot
            ax2.plot(z_grid, P_prof * 1000.0, color="#64ffda", linewidth=2.5, label="P(z)")
            ax2.set_title(txt["p_title"], color="white", fontsize=11, fontweight="bold")
            ax2.set_xlabel("z Position (μm)", color="#8b949e")
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
        
        # Load calibration parameter history if exists
        cal_path = APP_DIR / "data" / "calibrated_params.json"
        
        # Ingestion interface
        uploaded_file = st.file_uploader("Upload monitored LIV data (.json/.csv)", type=["json", "csv"])
        
        if st.button(txt["calib_btn"]):
            with st.spinner("Optimizing digital twin parameters to fit measurement data..."):
                # Handle file upload or mock data
                if uploaded_file is not None:
                    # Write temporary file
                    temp_path = APP_DIR / "data" / f"temp_{uploaded_file.name}"
                    with open(temp_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    data_file_arg = str(temp_path)
                else:
                    data_file_arg = None
                
                # Mock run calibration (using calibrate script directly)
                # Backup argv
                orig_argv = sys.argv
                sys.argv = [
                    "calibrate.py",
                    "--output-dir", str(APP_DIR / "data")
                ]
                if data_file_arg:
                    sys.argv += ["--data-file", data_file_arg]
                    
                try:
                    calibrate.main()
                    st.success(txt["calib_success"])
                except Exception as ex:
                    st.error(f"Error during calibration: {ex}")
                finally:
                    sys.argv = orig_argv
                    if data_file_arg and os.path.exists(data_file_arg):
                        os.remove(data_file_arg)
                        
        # Display Calibrated Parameter comparisons
        if cal_path.exists():
            with open(cal_path, "r") as f:
                cal = json.load(f)
                
            st.markdown(f"### {txt['calib_metrics']}")
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Internal Loss α_i (cm^-1)", f"{cal['alpha_i']:.4f}")
            c2.metric("Confinement Factor Γ", f"{cal['Gamma']:.5f}")
            c3.metric("Auger Coefficient Mult.", f"{cal['C_mult']:.4f}")
            c4.metric("Series Resistance Rs (Ω)", f"{cal['R_series']:.4f}")
            c5.metric("Shunt Resistance Rsh (Ω)", f"{cal['R_shunt']:.2f}")
            
            st.markdown(f"### {txt['calib_chart_title']}")
            fit_plot_path = APP_DIR / "data" / "calibration_fit.svg"
            if fit_plot_path.exists():
                st.image(str(fit_plot_path))
else:
    st.warning("Please verify that surrogate training has completed and saved model weights successfully.")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate a professional, high-fidelity 5-page Chinese PDF User Manual for TLaser.
"""

from __future__ import annotations
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np

# Setup paths
TLASER_DIR = Path(__file__).resolve().parent
output_pdf_path = TLASER_DIR / "Doc" / "TLaser_User_Manual_CN.pdf"
assets_dir = TLASER_DIR / "docs" / "manual_assets"

# Theme Colors
BG_COLOR = "#0a192f"
PANEL_COLOR = "#172a45"
ACCENT_GREEN = "#64ffda"
ACCENT_RED = "#ff7b72"
TEXT_COLOR = "#ffffff"
MUTED_TEXT = "#8892b0"

# Matplotlib Chinese Font Configuration to prevent square boxes on Windows
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial']
plt.rcParams['axes.unicode_minus'] = False

def add_header(ax, title):
    ax.text(0.05, 0.95, "TLASER 半导体激光器数字孪生系统", color=ACCENT_GREEN, fontsize=10, fontweight="bold", alpha=0.8)
    ax.text(0.05, 0.91, title, color=TEXT_COLOR, fontsize=14, fontweight="bold")
    ax.plot([0.05, 0.95], [0.89, 0.89], color="#233554", transform=ax.transAxes, linewidth=1.5)

def add_footer(ax, page_num):
    ax.plot([0.05, 0.95], [0.08, 0.08], color="#233554", transform=ax.transAxes, linewidth=1.0)
    ax.text(0.05, 0.05, "© 2026 万振文 (仿真与AI专家)。保留所有权利。", color=MUTED_TEXT, fontsize=8)
    ax.text(0.90, 0.05, f"第 {page_num} 页", color=MUTED_TEXT, fontsize=9)

def draw_paragraph(ax, text, x, y, max_len=45, line_height=0.022, color="#e6f1ff", fontsize=9.5):
    lines = []
    i = 0
    while i < len(text):
        lines.append(text[i:i+max_len])
        i += max_len
        
    for line in lines:
        ax.text(x, y, line, color=color, fontsize=fontsize, transform=ax.transAxes, alpha=0.9)
        y -= line_height
    return y

def embed_image(fig, img_path, left, bottom, w, h):
    if img_path.exists():
        img = plt.imread(str(img_path))
        img_ax = fig.add_axes([left, bottom, w, h], facecolor="none")
        img_ax.imshow(img)
        img_ax.axis("off")
    else:
        img_ax = fig.add_axes([left, bottom, w, h], facecolor=PANEL_COLOR)
        img_ax.text(0.5, 0.5, f"资源缺失:\n{img_path.name}", color=ACCENT_RED, ha='center', va='center')
        img_ax.axis("off")

# Initialize PDF compilation
with PdfPages(str(output_pdf_path)) as pdf:
    # ====================================================
    # Page 1: Cover Page
    # ====================================================
    fig = plt.figure(figsize=(8.5, 11), facecolor=BG_COLOR)
    ax = fig.add_axes([0, 0, 1, 1], facecolor="none")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    
    ax.plot([0, 1], [0.85, 0.85], color=PANEL_COLOR, linewidth=3)
    ax.plot([0, 1], [0.15, 0.15], color=PANEL_COLOR, linewidth=3)
    
    ax.text(0.1, 0.68, "TLaser", color=ACCENT_GREEN, fontsize=54, fontweight="bold")
    ax.text(0.1, 0.58, "实时数字孪生与参数标定系统", color=TEXT_COLOR, fontsize=24, fontweight="bold", linespacing=1.3)
    ax.text(0.1, 0.50, "基于物理信息神经网络（PINN）的半导体激光器实时仿真设计平台", color=MUTED_TEXT, fontsize=11, style="italic")
    
    ax.text(0.1, 0.38, "用户使用手册与技术参考指南", color=ACCENT_GREEN, fontsize=11, fontweight="bold", bbox=dict(boxstyle="square,pad=0.5", facecolor=PANEL_COLOR, edgecolor=ACCENT_GREEN, linewidth=1))
    
    ax.text(0.1, 0.28, "适用对象:", color=MUTED_TEXT, fontsize=9, fontweight="bold")
    ax.text(0.1, 0.25, "激光器件设计工程师、光电子学研究人员与系统操作员", color=TEXT_COLOR, fontsize=10.5)
    
    ax.text(0.1, 0.20, "作者及服务范围:", color=MUTED_TEXT, fontsize=9, fontweight="bold")
    ax.text(0.1, 0.17, "万振文 (仿真与AI专家  |  服务: 定制化物理信息神经网络代理求解器)", color=TEXT_COLOR, fontsize=10)
    
    pdf.savefig(fig, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close()
    
    # ====================================================
    # Page 2: Digital Twin Architecture & Mapping
    # ====================================================
    fig = plt.figure(figsize=(8.5, 11), facecolor=BG_COLOR)
    ax = fig.add_axes([0, 0, 1, 1], facecolor="none")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    
    add_header(ax, "1. 数字孪生架构与物理求解器映射")
    
    y = 0.84
    ax.text(0.05, y, "1.1 物理器件与谐振腔离散网格", color=ACCENT_GREEN, fontsize=11, fontweight="bold")
    y -= 0.022
    p1_txt = (
        "通信半导体激光器通过解理面反射镜发出相干光。为了模拟有源区内的纵向载流子复合分布，"
        "需要在 light 传输的纵向 z 轴方向建立一维离散网格。本项目采用 51 点纵向离散网络，"
        "以高保真地捕获因受激辐射消耗而在出光面附近形成的纵向空间烧孔 (SHB) 效应。"
    )
    y = draw_paragraph(ax, p1_txt, 0.05, y)
    
    y -= 0.015
    ax.text(0.05, y, "1.2 7D 几何参扫与模拟数据集生成", color=ACCENT_GREEN, fontsize=11, fontweight="bold")
    y -= 0.022
    p2_txt = (
        "高精度扫参工具在 7D 空间内运行均匀随机扫参：前后反射镜反射率 R1/R2、腔长 L、"
        "散热温度 T0、有源区注入电流、脊宽 w_active 以及有源厚度 d_active。扫参生成的 1500 组"
        "高精度物性数据将被写入本地 data 数据资产文件中。"
    )
    y = draw_paragraph(ax, p2_txt, 0.05, y)

    y -= 0.015
    ax.text(0.05, y, "1.3 高精度物理模拟求解器核心", color=ACCENT_GREEN, fontsize=11, fontweight="bold")
    y -= 0.022
    p3_txt = (
        "底层求解核心是一个耦合了纵向光波导与量子阱载流子速率方程的准三维数值求解器。它作为"
        "TLaser 数字孪生的基准物理源，负责计算非辐射俄歇复合、受激辐射光功率和电光效率。"
    )
    y = draw_paragraph(ax, p3_txt, 0.05, y)
    
    embed_image(fig, assets_dir / "pinn_training_loss.png", 0.15, 0.14, 0.70, 0.22)
    ax.text(0.5, 0.10, "图 1.1: PINN 代理模型训练收敛及物理惩罚损失收敛历史。", color=MUTED_TEXT, fontsize=8, ha='center', style='italic')
    
    add_footer(ax, 2)
    pdf.savefig(fig, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close()
    
    # ====================================================
    # Page 3: Streamlit Interface & Calibration Dashboard
    # ====================================================
    fig = plt.figure(figsize=(8.5, 11), facecolor=BG_COLOR)
    ax = fig.add_axes([0, 0, 1, 1], facecolor="none")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    
    add_header(ax, "2. Streamlit 交互式控制台与在线标定")
    
    y = 0.84
    ax.text(0.05, y, "2.1 实时交互式孪生仿真面板", color=ACCENT_GREEN, fontsize=11, fontweight="bold")
    y -= 0.022
    m1_txt = (
        "Streamlit 仪表盘支持低于 5 毫秒的超低延迟实时扫参。用户通过侧边栏拉动反射率、"
        "温度和有源区微观尺寸，右侧 1D 载流子和光功率剖面图实时自适应更新。平台集成"
        "了中英双语控制台以实现国际化操作。"
    )
    y = draw_paragraph(ax, m1_txt, 0.05, y)
    
    y -= 0.015
    ax.text(0.05, y, "2.2 在线物性常数标定引擎", color=ACCENT_GREEN, fontsize=11, fontweight="bold")
    y -= 0.022
    m2_txt = (
        "由于器件老化与工艺扰动，微观物性常数会发生缓慢漂移。标定引擎通过拟合现场实测的 "
        "L-I-V (光电特性) 曲线，反向校准出精确的内损耗 alpha_i、局域限制因子 Gamma、"
        "俄歇复合乘数、接触电阻 Rs 以及并联漏电电阻 Rsh，支持 JSON 与 CSV 格式文件上传。"
    )
    y = draw_paragraph(ax, m2_txt, 0.05, y)
    
    embed_image(fig, assets_dir / "calibration_fit.png", 0.15, 0.14, 0.70, 0.22)
    ax.text(0.5, 0.10, "图 2.1: 标定前后 L-I (光强) 和 V-I (电压) 曲线与实测数据的拟合质量对比。", color=MUTED_TEXT, fontsize=8, ha='center', style='italic')
    
    add_footer(ax, 3)
    pdf.savefig(fig, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close()
    
    # ====================================================
    # Page 4: Scientific Methodology & Mathematical Formulations
    # ====================================================
    fig = plt.figure(figsize=(8.5, 11), facecolor=BG_COLOR)
    ax = fig.add_axes([0, 0, 1, 1], facecolor="none")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    
    add_header(ax, "3. 科学计算方法与控制方程")
    
    y = 0.84
    ax.text(0.05, y, "3.1 载流子连续性控制微分残差", color=ACCENT_GREEN, fontsize=11, fontweight="bold")
    y -= 0.022
    p5_txt = (
        "PINN 在反向传播中引入了载流子连续性方程：G_inj - R_rec(N) - R_stim(N, P) = 0。"
        "其中注入项包含几何宽厚尺寸：I_active / (q0 * L * w * d)；受激项为 g(N) * P / (A * E_phot)。"
        "残差在 51 点网格上求取均方误差，保证稳态输运特征不产生非物理漂移。"
    )
    y = draw_paragraph(ax, p5_txt, 0.05, y)
    
    y -= 0.015
    ax.text(0.05, y, "3.2 二阶光子波动强度传播残差", color=ACCENT_GREEN, fontsize=11, fontweight="bold")
    y -= 0.022
    p6_txt = (
        "光波纵向传播基于二阶波动微分方程近似：d2P/dz2 - (Gamma * g(z) - alpha_i)^2 * P(z) = 0。"
        "该物理惩罚通过二阶中心差分算子作用于网格内部节点，避免模型产生多余的正反分量预测，"
        "提高泛化稳定性。"
    )
    y = draw_paragraph(ax, p6_txt, 0.05, y)
    
    y -= 0.015
    ax.text(0.05, y, "3.3 PINN 神经网络架构", color=ACCENT_GREEN, fontsize=11, fontweight="bold")
    y -= 0.022
    p7_txt = (
        "神经网络模型采用密连接架构并利用 GELU 激活函数。输入为 7D 特征向量，输出为 105D "
        "一维及空间曲线数值。数据样本在回归训练中被自动缩放归一化在 [0, 1] 空间区间内。"
    )
    y = draw_paragraph(ax, p7_txt, 0.05, y)
    
    rect_phys = plt.Rectangle((0.15, 0.14), 0.70, 0.18, facecolor=PANEL_COLOR, edgecolor="#233554", lw=1.5, transform=ax.transAxes)
    ax.add_patch(rect_phys)
    ax.text(0.5, 0.28, "TLaser 物理约束方程模型", color="#ffffff", fontsize=11, fontweight="bold", ha="center")
    ax.text(0.5, 0.23, "Loss = Loss_Data + w_c * Loss_Carrier + w_p * Loss_Photon + w_s * Loss_Smooth", color=ACCENT_GREEN, fontsize=9.5, fontweight="bold", ha="center", fontfamily="monospace")
    ax.text(0.5, 0.18, "在 51 点网格上严格施加自动微分波动和输运惩罚项。", color=MUTED_TEXT, fontsize=8.5, ha="center")
    
    add_footer(ax, 4)
    pdf.savefig(fig, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close()
    
    # ====================================================
    # Page 5: Setup, Commands & Troubleshooting
    # ====================================================
    fig = plt.figure(figsize=(8.5, 11), facecolor=BG_COLOR)
    ax = fig.add_axes([0, 0, 1, 1], facecolor="none")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    
    add_header(ax, "4. 环境搭建、执行指令与故障排除")
    
    y = 0.84
    ax.text(0.05, y, "4.1 代码执行核心命令清单", color=ACCENT_GREEN, fontsize=11, fontweight="bold")
    y -= 0.022
    
    def draw_code(y_pos, cmd):
        ax.text(0.08, y_pos, "  >  " + cmd, color=ACCENT_GREEN, fontsize=9, fontfamily="monospace")
        return y_pos - 0.025
        
    y = draw_code(y, "python simulator/generate_dataset.py --num-samples 1500")
    y = draw_code(y, "python surrogate/train.py --epochs 600")
    y = draw_code(y, "python calibration/calibrate.py --data-file data/monitored_liv.json")
    y = draw_code(y, "python verify_pipeline.py")
    y = draw_code(y, "python -m streamlit run app.py")
    
    y -= 0.01
    ax.text(0.05, y, "4.2 测试曲线数据格式定义", color=ACCENT_GREEN, fontsize=11, fontweight="bold")
    y -= 0.022
    p8_txt = (
        "JSON 文件必须包含以下字段数组：current_A (电流A)、voltage_V (电压V) 和 optical_power_W (光功率W)。"
        "CSV 文件需要包含表头，数据列按以下顺序排列：电流 (A)、电压 (V)、光功率 (W)。"
    )
    y = draw_paragraph(ax, p8_txt, 0.05, y)
    
    y -= 0.01
    ax.text(0.05, y, "4.3 系统故障排查与维护", color=ACCENT_GREEN, fontsize=11, fontweight="bold")
    y -= 0.022
    p9_txt = (
        "如果 PyTorch 提示显卡报错或 CUDA 缺失，请使用 CPU 专用 whl 地址强制安装 CPU 运行版本。"
        "若加载模型失败，请检查 scales 参数 pinn_scale_params.npz 是否存在于 data/ 资源目录中。"
        "部署前请运行 verify_pipeline.py 自动脚本一键检验各阶段语法与数据形状。"
    )
    y = draw_paragraph(ax, p9_txt, 0.05, y)
    
    rect_author = plt.Rectangle((0.05, 0.14), 0.90, 0.16, facecolor=PANEL_COLOR, edgecolor="#233554", lw=1, transform=ax.transAxes)
    ax.add_patch(rect_author)
    ax.text(0.10, 0.26, "万振文 (仿真与AI物理建模专家)", color="#ffffff", fontsize=11, fontweight="bold")
    ax.text(0.10, 0.22, "商业合作及物理神经网络代理器开发支持联系邮箱: aw4wzw@gmail.com", color=MUTED_TEXT, fontsize=9)
    ax.text(0.10, 0.17, "项目开源代码仓库: https://github.com/ZhenwenWan/TLaser", color=ACCENT_GREEN, fontsize=9, fontfamily="monospace")
    
    add_footer(ax, 5)
    pdf.savefig(fig, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close()

print(f"Compilation complete. Chinese PDF User Manual saved to {output_pdf_path}")

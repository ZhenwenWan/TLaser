# TLaser 用户使用手册

欢迎使用 **TLaser** 通信级半导体激光器数字孪生主控制平台。本手册提供本地安装指南、数学模型公式、数据模拟与模型训练脚本的运行方式，以及在线物性参数标定流程。

---

## 1. 项目简介

TLaser 为通信级半导体激光器二极管建立高保真度的物理数字孪生。通过结合以下三大模块，它有效解决传统网格有限元求解器速度慢、难以满足实时性需求的问题：
1. **Quasi-3D 物理模拟器核心**：求解纵向载流子分布与受激辐射波传播。
2. **物理信息神经网络 (PINN) 代理模型**：在 5 毫秒内将 7D 几何与工作参数映射至 105 维空间剖面分布。
3. **在线 L-I-V 参数标定引擎**：根据现场实测的光强-电流-电压（L-I-V）特征，反向求解内部漂移或未知的物性常数。

---

## 2. 环境搭建

配置本地 Python 虚拟环境以管理依赖库：
```powershell
# 克隆代码仓库
git clone https://github.com/ZhenwenWan/TLaser.git
cd TLaser

# 创建虚拟环境
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # Windows PowerShell 环境下激活

# 安装依赖包
pip install -r requirements.txt
```

### 环境常见问题排查
* **PyTorch CPU 版本安装慢或失败**：在没有 CUDA GPU 的机器上，建议强制拉取 CPU 专用安装包：
  ```powershell
  pip install torch --extra-index-url https://download.pytorch.org/whl/cpu
  ```
* **Matplotlib/OpenCV 报错找不到模块**：请检查终端路径是否正确指向虚拟环境下的解释器 (`.venv\Scripts\python.exe`)。

---

## 3. 高精度模拟数据集生成

数据集生成脚本在 7 维有源区与腔体参数空间内进行均匀随机扫参。

> [!NOTE]
> **模拟器性质**：本项目的模拟核为一个耦合了轴向光波传输与量子阱速率方程的准三维数值求解器。它作为 TLaser 数字孪生体原型的高保真物理数据来源。

### 扫参区间边界
* 镜面反射率：$R_1 \in [0.1, 0.95]$, $R_2 \in [0.05, 0.5]$
* 腔体几何尺寸：长度 $L \in [100, 1000]\,\mu\text{m}$, 脊宽 $w \in [1.5, 4.0]\,\mu\text{m}$, 厚度 $d \in [0.1, 0.5]\,\mu\text{m}$
* 运行环境输入：散热温度 $T_0 \in [250, 360]\,\text{K}$, 注入电流 $I_{\text{active}} \in [0.01, 0.5]\,\text{A}$

### 运行指令
* **生成完整数据集（1500 个样本）**：
  ```powershell
  python simulator/generate_dataset.py --num-samples 1500
  ```
* **执行快速冒烟测试**：
  ```powershell
  python simulator/generate_dataset.py --smoke-test
  ```
数据输出保存在 `data/` 目录下的 `pinn_inputs.npy` 和 `pinn_targets.npy`，同时生成元数据 `pinn_dataset_metadata.json`。

---

## 4. 物理信息神经网络训练

PINN 模型在传统的神经网络损失函数中引入了物理解微分残差罚项。

### 训练损失函数组成
1. **数据回归损失**：预测值与模拟目标值之间的均方误差。
2. **载流子连续性方程残差**：
   $$G_{\text{inj}} - R_{\text{rec}}(N(z)) - R_{\text{stim}}(N(z), P(z)) = 0$$
3. **光子传播微分方程残差（二阶波动近似）**：
   $$\frac{d^2P}{dz^2} - (\Gamma g(z) - \alpha_i)^2 P(z) = 0$$
   *注意：使用二阶波动方程约束总光强 $P(z)$ 是一项被广泛采用的物理简化，它避免了预测复杂的正反向分量波，减小了拟合空间的维度。*
4. **拉普拉斯平滑正则项**：约束空间载流子与光子密度分布的连续平滑度。

### 运行指令
* **执行完整模型训练（600 个 Epoch）**：
  ```powershell
  python surrogate/train.py --epochs 600
  ```
* **执行快速冒烟测试**：
  ```powershell
  python surrogate/train.py --smoke-test
  ```
训练权重保存在 `data/pinn_laser_model.pt`，收敛历史绘图输出在 `data/pinn_training_loss.svg`。

---

## 5. 参数在线标定环路

标定引擎通过极小化测试 LIV 曲线与孪生体预测之间的残差，反向辨识漂移或未知的微观物性常数。

### 数据格式规范
* **JSON 格式文件**：包含 `current_A`, `voltage_V` 以及 `optical_power_W` 数组。
  ```json
  {
    "current_A": [0.05, 0.1, 0.15],
    "voltage_V": [1.02, 1.05, 1.08],
    "optical_power_W": [0.005, 0.02, 0.04]
  }
  ```
* **CSV 格式文件**：包含一行表头，后续数据列按顺序排列：电流 (A)、电压 (V)、光功率 (W)。

### 运行指令
* **基于内置带噪声的测试数据执行标定**：
  ```powershell
  python calibration/calibrate.py
  ```
* **基于外部实测数据执行标定**：
  ```powershell
  python calibration/calibrate.py --data-file data/monitored_liv.json
  ```
标定参数结果保存在 `data/calibrated_params.json`，拟合图保存在 `data/calibration_fit.svg`。

---

## 6. 一键自动化流水线校验

执行以下指令即可一键运行全部冒烟测试以验证环境与代码完整性：
```powershell
python verify_pipeline.py
```

---

## 7. 本地交互可视化面板

执行以下指令以启动实时数字孪生可视化与在线标定控制面板：
```powershell
python -m streamlit run app.py
```
这将在本地 `http://localhost:8501` 建立 Web 页面，支持英文与中文双语一键切换。

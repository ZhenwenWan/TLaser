# TLaser 用户使用手册

欢迎使用 **TLaser** 通信级半导体激光器数字孪生主控制平台。本手册提供本地安装指南、数学模型公式、数据模拟与模型训练脚本的运行方式，以及在线物性参数标定流程。

## 快速启动

在已升级的 TLaser 文件夹中打开 PowerShell，安装依赖后运行：
```powershell
./run_tlaser.ps1
```
手动打开 http://localhost:8501。使用 8502 端口可运行 ./run_tlaser.ps1 -Port 8502。保持终端运行，Ctrl+C 停止服务。配置、保存/加载与排查说明见第 7 节。

---

## 1. 项目简介

更新日期：2026-10-09。TLaser 是固定端面反射镜脊形边发射激光器的简化模型原型，使用稳态 CW 工作点。CW 是工作预设，不是独立架构。当前包含以下模块：
1. **Quasi-3D 物理模拟器核心**：求解纵向载流子分布与受激辐射波传播。
2. **物理信息神经网络 (PINN) 代理模型**：将七个设计与工作输入映射至 105 个输出。当前合成数据模型没有独立留出精度验证，也未证明低于 5 毫秒的端到端响应时间。
3. **在线 L-I-V 参数标定引擎**：根据现场实测的光强-电流-电压（L-I-V）特征，反向求解内部漂移或未知的物性常数。

### 1.1 工程认知映射路径

为了清晰展现 TLaser 在通信光电产业链中的位置，平台建立了从商品级产品到数字孪生参数的完整映射路径：

1. **光模块层**：标准的 SFP/QSFP 光收发模块，是可直接测量的系统硬件。在系统运行中可直接获取其 L-I-V 传感器实测数据。
2. **模块内部组件**：发射光组件 (TOSA)、激光驱动芯片以及热电制冷器 (TEC) 协同控制工作环境。
3. **激光器芯片层**：TOSA 封装内部的 bare laser chip。其几何特征（谐振腔长度 L、有源区脊宽 w 与厚度 d）决定了其电学及光学边界。
4. **正向模型**：使用简化纵向载流子/光学方程、温度相关常数和电学寄生模型；边发射模型没有自热反馈或可执行 FEM/TCAD 耦合。
5. **逆向模型**：估计所选 alpha_i、Gamma、C_mult、R_series、R_shunt；保持几何、端面和温度固定。不估计尺寸或边发射热阻。

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

## 3. 合成数据集生成

数据集生成脚本在 7 维有源区与腔体参数空间内进行均匀随机扫参。

> [!NOTE]
> **模拟器性质**：当前为简化纵向合成模型。采样范围不证明实测器件精度。有源区宽度不等同于已验证的刻蚀脊宽；等效厚度不代表完整外延层。

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
  python simulator/generate_dataset.py --smoke-test --output-dir data/smoke_test
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
   *注意：当前原型使用简化的总功率残差，而非分别预测正反向场分量；这不证明完整场求解精度。*
4. **拉普拉斯平滑正则项**：约束空间载流子与光子密度分布的连续平滑度。

### 运行指令
* **执行完整模型训练（600 个 Epoch）**：
  ```powershell
  python surrogate/train.py --epochs 600
  ```
* **执行快速冒烟测试**：
  ```powershell
  python surrogate/train.py --smoke-test --output-dir data/smoke_test
  ```
训练权重保存在 `data/pinn_laser_model.pt`，收敛历史绘图输出在 `data/pinn_training_loss.svg`。

---

## 5. 参数在线标定环路

新器件流程使用当前所选配置拟合。选择内部物性参数在线标定，再明确选择合成演示或上传 JSON。演示只改变所选参数，不代表实测器件验证。

### 数据格式规范
* **JSON 格式文件**：需要已知有源区电流（A），不能直接使用普通端口电流。需要 5-200 个有限数值点、数组等长、至少五个不同且位于 0.01-0.5 A 的电流值、正电压和非负且有信息量的功率。元数据须匹配所选器件。以下仅示范格式，请替换为测量值：
  ```json
  {
    "current_semantics": "active_region",
    "current_A": [0.05, 0.10, 0.20, 0.30, 0.40],
    "voltage_V": [1.5, 1.6, 1.7, 1.8, 1.9],
    "optical_power_W": [0.001, 0.002, 0.003, 0.004, 0.005],
    "metadata": {
      "L_um": 300.0, "w_um": 2.8, "d_um": 0.342,
      "R1": 0.90, "R2": 0.05, "T0": 298.0
    }
  }
  ```
* 新面板支持 JSON。CSV 属于旧版命令行路径，会静默提供默认几何，并非新的共享器件流程。

### 拟合、比较与应用

建议选择少量参数，默认串联电阻。点击运行标定，查看原始/估计参数、LIV 曲线、优化器状态、拟合前后归一化损失、边界和局部灵敏度。尺寸保持固定，因此两种配置轮廓相同。

只有优化成功、损失改善且低于 0.01、未触及边界或发现不敏感参数、局部 Jacobian 条件数低于 1,000,000 的结果才可应用。这些检查不证明参数全局唯一。失败候选可导出审阅，但不能通过应用按钮应用。

点击模拟预测使用拟合常数，返回预测页并选择物理模拟器。七输入标称 PINN 不接收拟合常数。可下载估计配置和完整标定报告，保留原始/估计快照与测量来源。新会话结果不覆盖旧的共享标定文件。

### 旧版命令行指令
以下旧命令会写入 data/ 下的共享结果，不使用新会话配置。
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

验证共享器件工作流程且不覆盖模型资产，可运行：
```powershell
python -m unittest discover -s tests -p test_device_workflow.py -v
```
七项测试覆盖配置往返、非法数据拒绝、尺寸与后端一致性、已知电阻恢复、固定几何、失败拟合拒绝、语言/流程状态以及演示拟合到应用预测。

以下旧流水线会生成文件并更新验证报告，不是只读精度审计：
```powershell
python verify_pipeline.py
```

---

## 7. 本地交互可视化面板

在已升级 TLaser 项目文件夹中打开 PowerShell，安装依赖后运行：
```powershell
./run_tlaser.ps1
```
手动打开 http://localhost:8501。启动器打印地址，不自动打开浏览器。保持终端运行；Ctrl+C 停止服务。端口已占用时运行：
```powershell
./run_tlaser.ps1 -Port 8502
```
然后打开 http://localhost:8502。开发预览使用 8502，默认端口仍为 8501。在已激活的可用环境中，也可直接运行：
```powershell
python -m streamlit run app.py
```
本项目旧 Windows Store Python 启动器不可用时，脚本可通过 Codex 内置 Python 复用已安装依赖。其他电脑需要可用虚拟环境。若脚本被阻止，请遵守当地执行策略，或使用上述 Python 命令。

### 配置、保存与恢复

在侧栏选择 EN/CN 和边发射半导体激光器；窄屏需展开侧栏。输入 L、等效 w/d、R1/R2、温度和有源区电流，点击更新器件提交。俯视图和横截面同步更新。衬底/包层为固定示意，厚度放大且各方向独立缩放。

展开保存 / 加载器件配置，下载带版本号 JSON。恢复时上传配置并点击加载配置。非法版本、架构、非有限数值和越界输入会被拒绝。切换流程/语言保留配置；更新或加载设计清除原拟合与应用状态。下载文件可长期保存，但浏览器会话不是永久数据库。

预测时选择标称 PINN 或物理模拟器。查看双端面总光功率、WPE、总端口电流和 51 点剖面。有源区电流不含漏电；端口电流包含模型的漏电分量。

### 问题排查与限制

- 缺少依赖：激活可用环境并安装 requirements.txt；旧 VCSEL 导入需要 jsonschema。
- 标称权重不可用：几何与模拟器仍可使用；标称预测需要 data/pinn_laser_model.pt 和 data/pinn_scale_params.npz。
- 元数据不匹配：让所选器件匹配测量，不要为了强行拟合而修改测量标签。
- 背景：重启服务以读取 .streamlit/config.toml。面板、示意图、曲线和 PDF 保持原深蓝配色。
- 数据生成/训练未指定独立输出目录时，会覆盖正式 data/ 资产；上述冒烟命令使用 data/smoke_test。
- DFB 光栅、EML 吸收/调制、几何逆向估计、实测验证、可信收敛证明和独立留出集误差仍待开发。VCSEL 是独立旧版简化演示；当前 LIV 输出不能辨识其 C 乘数。
- 公开项目网页用于展示与说明。计算在本机运行；公开计算托管、认证和多用户存储尚未实现。

"""Stage only TLaser's bilingual public pages/guides; do not alter the site stylesheet."""
from pathlib import Path
import hashlib
import json
import re
from shutil import copyfile

ROOT = Path(__file__).resolve().parent
PAGES = ROOT.parent / "Lasers" / "Pages"
STAGE = ROOT / "web_publish"
STAGE.mkdir(exist_ok=True)
manifest = {}
for language in ("EN", "CN"):
    suffix = "_CN" if language == "CN" else ""
    name = f"TLaser{suffix}.html"
    old = (PAGES/name).read_text(encoding="utf-8")
    old = re.sub(r'        <section class="nav-section" id="device-model-release">[\s\S]*?        </section>\s*', '', old)
    if language == "EN":
        section = '''        <section class="nav-section" id="device-model-release">
            <div class="section-header">
                <h2>Shared device model and updated user guide</h2>
                <p>Local ridge-device release · updated 9 October 2026</p>
            </div>
            <div class="highlight-box">
                <p>Configure cavity length, effective active width/thickness, facets, current and temperature in a fixed ridge template. A labeled top view and cross-section share the same versioned configuration, with JSON save/load.</p>
                <p>Prediction offers a nominal seven-input PINN and a physical simulator. Calibration keeps geometry fixed and compares original/estimated physical parameters and LIV curves. Applying accepted fitted constants changes simulator predictions; the nominal PINN remains nominal.</p>
                <p>Calibration requires known active-region current and matching device metadata. DFB/EML physics and inverse geometry estimation are future extensions. Computation runs locally; this webpage is a presentation and documentation surface.</p>
                <p><a href="TLaser_User_Manual.pdf" style="color: #64ffda;">Download updated user guide (PDF)</a> · <a href="TLaser_User_Manual.md" style="color: #64ffda;">Read Markdown guide</a></p>
            </div>
        </section>

'''
        note = '<p>In the upgraded local TLaser project folder, run <code>./run_tlaser.ps1</code>, then open <code>http://localhost:8501</code>. For another port use <code>./run_tlaser.ps1 -Port 8502</code>. Keep the terminal open; Ctrl+C stops the server. The launcher does not open the browser automatically.</p><p>The shared-device upgrade is currently a local release. If a downloaded checkout does not include the launcher, use the direct command <code>python -m streamlit run app.py</code> for that checkout; it may show the older interface.</p>'
        old = old.replace('<p>Simulate parameter sweeps instantly and run parameter calibration on the interactive dashboard.</p>', note)
        old = old.replace('Computes laser behavior within a 7-dimensional parameter space in under 5 milliseconds to predict performance characteristics before packaging.', 'Predicts reduced-model laser behavior within a seven-input sampling envelope; response latency and measured-device accuracy require separate validation.')
        old = old.replace('<strong>Performance Acceleration:</strong> Prediction latency drops from seconds to <strong>&lt; 5 milliseconds</strong> with an $R^2$ accuracy above <strong>0.997</strong> compared to the high-fidelity simulator.', '<strong>Validation status:</strong> The existing surrogate uses synthetic data. Held-out error and end-to-end latency benchmarks are still required; this release does not establish a sub-5-ms or R² accuracy guarantee.')
        old = old.replace('&lt; 5 milliseconds</td>', 'Benchmark pending</td>')
        old = old.replace('&gt; 0.997</td>', 'Held-out validation pending</td>')
    else:
        section = '''        <section class="nav-section" id="device-model-release">
            <div class="section-header">
                <h2>共享器件模型与新版用户手册</h2>
                <p>本地脊形器件版本 · 更新日期：2026-10-09</p>
            </div>
            <div class="highlight-box">
                <p>在固定脊形模板中设置腔长、等效有源区宽厚、端面、电流和温度。标注尺寸的俯视图与横截面共享带版本号的配置，支持 JSON 保存与加载。</p>
                <p>预测可选标称七输入 PINN 或物理模拟器。标定保持几何固定，比较原始与估计参数及 LIV 曲线。应用已接受的拟合常数会改变模拟预测，标称 PINN 仍保持标称。</p>
                <p>标定需要已知有源区电流和匹配的器件元数据。DFB/EML 物理与几何逆向识别仍待扩展。计算在本机运行，网页用于展示与说明。</p>
                <p><a href="TLaser_User_Manual_CN.pdf" style="color: #64ffda;">下载新版用户手册（PDF）</a> · <a href="TLaser_User_Manual_CN.md" style="color: #64ffda;">阅读 Markdown 手册</a></p>
            </div>
        </section>

'''
        note = '<p>在已升级的本地 TLaser 项目文件夹中运行 <code>./run_tlaser.ps1</code>，再打开 <code>http://localhost:8501</code>。更换端口可用 <code>./run_tlaser.ps1 -Port 8502</code>。保持终端运行，Ctrl+C 停止服务；启动器不自动打开浏览器。</p><p>共享器件升级目前为本地版本。如果下载的仓库未包含启动器，可使用 <code>python -m streamlit run app.py</code> 启动该仓库版本，但可能显示旧界面。</p>'
        old = old.replace('<p>在弹出的浏览器面板中实时调节滑块进行参数分析，或上传实时曲线执行在线物性常数拟合。</p>', note)
        old = old.replace('<strong>计算提速：</strong> 求解延迟从传统的数秒下降到 <strong>&lt; 5 毫秒</strong>，与原高精度数值模拟相比，$R^2$ 拟合相关度保持在 <strong>0.997</strong> 以上。', '<strong>验证状态：</strong> 当前代理模型使用合成数据，仍需独立留出误差和端到端延迟验证；本版本没有确立低于 5 毫秒或 R² 精度保证。')
        old = old.replace('&lt; 5 毫秒</td>', '待基准验证</td>')
        old = old.replace('&gt; 0.997</td>', '独立留出验证待完成</td>')
        old = old.replace('在七维设计参数空间内，对任意设计组合进行毫秒级计算，预测芯片制造完成后的主要性能参数。', '在七输入采样范围内预测简化模型性能；端到端延迟与实测器件精度仍需独立验证。')
    assert old.count('<!-- Quickstart & Installation -->') == 1
    updated = old.replace('<!-- Quickstart & Installation -->', section+'        <!-- Quickstart & Installation -->')
    updated = updated.replace('python -m streamlit run app.py</pre>', './run_tlaser.ps1</pre>')
    source = (PAGES/name).read_text(encoding="utf-8")
    assert re.search(r'<style>[\s\S]*?</style>', source).group() == re.search(r'<style>[\s\S]*?</style>', updated).group()
    (STAGE/name).write_text(updated, encoding="utf-8")
    manifest[name] = hashlib.sha256((PAGES/name).read_bytes()).hexdigest()
    for ext in ("md", "pdf"):
        asset = f"TLaser_User_Manual{suffix}.{ext}"
        copyfile(ROOT/"Doc"/asset, STAGE/asset)
for language in ("EN", "CN"):
    name = "generate_user_manual_pdf" + ("_cn" if language == "CN" else "") + ".py"
    (ROOT/name).write_text(f"from generate_guides import render\n\nif __name__ == '__main__':\n    print(render('{language}'))\n", encoding="utf-8")
(STAGE/"source_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print("Staged bilingual pages and PDF/Markdown guides; all original stylesheet rules retained.")

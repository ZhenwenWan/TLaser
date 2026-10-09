"""Dimension-driven SVG schematic, intentionally not an epitaxial/CAD model."""
from device_model import geometry_model


def schematic(config, lang="EN"):
    model = geometry_model(config)
    dims = model["regions"][0]["dimensions_um"]
    L, w, d = (dims[k] for k in ("L_um", "w_um", "d_um"))
    r1, r2 = (b["reflectivity"] for b in model["boundaries"])
    length = L * 0.45
    width = w * 24.0
    thickness = d * 120.0
    x, y = 65.0, 115.0
    cx, cy = 690.0, 165.0
    labels = ("Top view · cavity axis z", "Cross-section · x–y", "Effective active region",
              "Fixed schematic substrate", "Fixed schematic cladding",
              "Independent display scales; thickness exaggerated. Active width is not a verified etched ridge width.")
    if lang == "CN":
        labels = ("俯视图 · 腔轴 z", "横截面 · x–y", "等效有源区", "固定示意衬底", "固定示意包层",
                  "各方向独立缩放；厚度放大。有源区宽度不等同于已验证的刻蚀脊宽。")
    top, cross, active, substrate, cladding, note = labels
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 370" role="img" aria-label="Ridge laser dimension schematic">
    <defs><marker id="arrow" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto-start-reverse"><path d="M0,0 L6,3 L0,6" fill="#8892b0"/></marker></defs>
    <rect width="1000" height="370" rx="14" fill="#0a192f"/>
    <g font-family="sans-serif" font-size="14" fill="#e6f1ff">
    <text x="45" y="32" font-size="17">{top}</text><text x="635" y="32" font-size="17">{cross}</text>
    <rect x="45" y="65" width="510" height="195" rx="8" fill="#172a45"/>
    <rect x="{x}" y="{y}" width="{length}" height="{width}" fill="#38bdf8" stroke="#0369a1"/>
    <line x1="{x}" y1="{y-8}" x2="{x}" y2="{y+width+8}" stroke="#7c3aed" stroke-width="4"/>
    <line x1="{x+length}" y1="{y-8}" x2="{x+length}" y2="{y+width+8}" stroke="#059669" stroke-width="4"/>
    <text x="65" y="88">Rear R1 = {r1:g}</text><text x="310" y="88">Front R2 = {r2:g}</text>
    <line x1="{x}" y1="285" x2="{x+length}" y2="285" stroke="#667085" marker-start="url(#arrow)" marker-end="url(#arrow)"/>
    <text x="65" y="310">L = {L:g} µm · z →</text>
    <line x1="575" y1="{y}" x2="575" y2="{y+width}" stroke="#667085" marker-start="url(#arrow)" marker-end="url(#arrow)"/>
    <text x="565" y="245">w = {w:g}</text>
    <rect x="635" y="{cy+thickness}" width="300" height="65" fill="#233554"/>
    <text x="650" y="{cy+thickness+38}">{substrate}</text>
    <rect x="635" y="80" width="300" height="85" fill="#172a45"/>
    <text x="650" y="105">{cladding}</text>
    <rect x="{cx}" y="{cy}" width="{width}" height="{thickness}" fill="#38bdf8" stroke="#0369a1"/>
    <line x1="{cx}" y1="140" x2="{cx+width}" y2="140" stroke="#667085" marker-start="url(#arrow)" marker-end="url(#arrow)"/>
    <text x="740" y="130">w = {w:g} µm</text>
    <line x1="{cx+width+25}" y1="{cy}" x2="{cx+width+25}" y2="{cy+thickness}" stroke="#667085" marker-start="url(#arrow)" marker-end="url(#arrow)"/>
    <text x="{cx+width+40}" y="{cy+thickness/2+5}">d = {d:g} µm</text>
    <text x="635" y="305" fill="#64ffda">{active}</text>
    <text x="30" y="350" font-size="12">{note}</text></g></svg>'''

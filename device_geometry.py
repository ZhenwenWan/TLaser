"""Dimension-driven device views with physical active-region coordinates."""
from device_model import geometry_model


def geometry_3d(config, lang="EN", true_scale=False, show_context=True, exploded=0):
    """Render the original Lasers 15-part material geometry, adapting cavity length only.

    Source axes: x=cavity, y=lateral, z=vertical. Effective w/d in the
    reduced solver do not define an epitaxial stack and do not alter these layers.
    """
    import json
    from pathlib import Path
    import plotly.graph_objects as go

    c = geometry_model(config)
    length = c["regions"][0]["dimensions_um"]["L_um"]
    source = json.loads((Path(__file__).parent / "assets" / "lasers_geometry.json").read_text(encoding="utf-8"))
    cn = lang == "CN"
    names = ["InP 衬底", "n-InP 缓冲层", "n-InP 下包层", "下 SCH 波导", "MQW 有源层",
             "上 SCH 波导", "p-InP 脊与包层", "左刻蚀 p-InP 肩部", "右刻蚀 p-InP 肩部",
             "左 SiN 隔离层", "右 SiN 隔离层", "顶部 p 金属条", "背面 n 金属",
             "高反射后端面", "减反射输出端面"]
    fig = go.Figure()
    reference_length = source["parameters"]["length_um"]
    # Equal-height parts share their displacement, preserving left/right symmetry.
    heights = sorted({part["center_um"]["z"] for part in source["parts"][:13]})
    edges = [(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7)]
    for index, part in enumerate(source["parts"]):
        if not show_context and index in (0, 12, 13, 14):
            continue
        center, size = part["center_um"], part["size_um"]
        # Facet coatings retain their source thickness while following the cavity ends.
        cx = center["x"] * length/reference_length if index < 13 else (-1 if index == 13 else 1)*(length/2 + size["x"]/2)
        sx = length if index < 13 else size["x"]
        x0, x1 = cx-sx/2, cx+sx/2
        y0, y1 = center["y"]-size["y"]/2, center["y"]+size["y"]/2
        z0, z1 = center["z"]-size["z"]/2, center["z"]+size["z"]/2
        offset = heights.index(center["z"])*exploded if index < 13 else 0
        x = [x0,x1,x1,x0,x0,x1,x1,x0]
        y = [y0,y0,y1,y1,y0,y0,y1,y1]
        z = [v+offset for v in [z0,z0,z0,z0,z1,z1,z1,z1]]
        name = names[index] if cn else part["name"]
        info = (f"{name}<br>{part['material']}<br>"
                f"{sx:g} × {size['y']:g} × {size['z']:g} µm<br>{part['role']}")
        if index >= 13:
            info += f"<br>R{index-12} = {c['boundaries'][index-13]['reflectivity']:g}"
        group = str(index)
        fig.add_trace(go.Mesh3d(
            name=name, legendgroup=group, showlegend=True, x=x, y=y, z=z,
            i=[0,0,4,4,0,0,1,1,2,2,3,3], j=[1,2,6,7,4,5,5,6,6,7,7,4],
            k=[2,3,5,6,5,1,6,2,7,3,4,0], color=part["color"],
            opacity=.32 if index >= 13 else .86, flatshading=True,
            lighting=dict(ambient=.65, diffuse=.8, specular=.35),
            hovertemplate=info+"<extra></extra>",
            meta=dict(source_part=index, size_um=dict(x=sx, y=size["y"], z=size["z"])),
        ))
        fig.add_trace(go.Scatter3d(
            x=[v for a,b in edges for v in (x[a],x[b],None)],
            y=[v for a,b in edges for v in (y[a],y[b],None)],
            z=[v for a,b in edges for v in (z[a],z[b],None)],
            mode="lines", line=dict(color="#15243a", width=2),
            showlegend=False, legendgroup=group, hoverinfo="skip"))
    # Match the reference viewer's vertical magnification without changing stored coordinates.
    scales = source["metadata"]["visual_scale"]
    ranges = [max(max(t[axis]) for t in fig.data if t.type == "mesh3d")-
              min(min(t[axis]) for t in fig.data if t.type == "mesh3d") for axis in ("x","y","z")]
    ratios = dict(zip(("x","y","z"), [ranges[i]*scales[a] for i,a in enumerate(("x","y","z"))]))
    axes = dict(showbackground=True, backgroundcolor="#0d192b", gridcolor="#233554", color="#b8c8df")
    scene = dict(
        xaxis=dict(axes, title="x · " + ("腔长 (µm)" if cn else "Cavity (µm)")),
        yaxis=dict(axes, title="y · " + ("横向 (µm)" if cn else "Lateral (µm)")),
        zaxis=dict(axes, title="z · " + ("层叠高度 (µm)" if cn else "Layer height (µm)")),
        camera=dict(eye=dict(x=1.6,y=1.6,z=1.1)), dragmode="orbit",
        aspectmode="data" if true_scale else "manual")
    if not true_scale:
        largest = max(ratios.values())
        scene["aspectratio"] = {key: value/largest*2 for key,value in ratios.items()}
    fig.update_layout(scene=scene, height=650, margin=dict(l=0,r=0,t=0,b=0),
                      paper_bgcolor="#0a192f", font=dict(color="#e6f1ff"),
                      legend=dict(orientation="h", y=-.08, x=0, groupclick="togglegroup"),
                      uirevision=f"lasers-{true_scale}-{show_context}-{exploded}")
    return fig


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

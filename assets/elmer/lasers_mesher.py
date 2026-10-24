"""Generate the telecom carrier-dynamics mesh01 with Gmsh and export Elmer mesh files."""

from __future__ import annotations

import argparse
import json
import subprocess
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LASERS_ROOT = ROOT.parents[1]
DEFAULT_MODEL_JSON = LASERS_ROOT / "examples" / "geometry_task_1_1" / "telecom_laser_geo2d_model.json"
DEFAULT_WORK_DIR = ROOT / "mesh01_gmsh"
DEFAULT_OUT_DIR = ROOT / "mesh01"
DEFAULT_GMSH = Path("C:/gmsh/gmsh.exe")


INTERFACE_IDS = {
    (1, 2): 101,
    (2, 3): 102,
    (3, 4): 103,
    (4, 5): 104,
    (5, 6): 105,
    (5, 10): 106,
    (5, 8): 107,
    (6, 10): 108,
    (6, 7): 109,
    (7, 10): 110,
    (8, 10): 111,
    (8, 9): 112,
    (9, 10): 113,
    (10, 11): 114,
}

BODY_NAMES = {
    1: "bottom_n_contact",
    2: "n_inp_lower_cladding",
    3: "lower_sch_waveguide",
    4: "mqw_active_region",
    5: "upper_sch_waveguide",
    6: "left_p_inp_shoulder",
    7: "left_sin_shoulder",
    8: "right_p_inp_shoulder",
    9: "right_sin_shoulder",
    10: "p_inp_ridge",
    11: "top_p_contact",
}

BOUNDARY_NAMES = {
    1: "n_contact",
    2: "p_contact",
    3: "left_symmetry",
    4: "right_symmetry",
    5: "exposed_or_insulated",
    101: "interior_bottom_contact_to_n_cladding",
    102: "interior_n_cladding_to_lower_sch",
    103: "interior_lower_sch_to_mqw",
    104: "interior_mqw_to_upper_sch",
    105: "interior_upper_sch_to_left_shoulder",
    106: "interior_upper_sch_to_ridge",
    107: "interior_upper_sch_to_right_shoulder",
    108: "interior_left_shoulder_to_ridge",
    109: "interior_left_shoulder_to_sin",
    110: "interior_left_sin_to_ridge",
    111: "interior_right_shoulder_to_ridge",
    112: "interior_right_shoulder_to_sin",
    113: "interior_right_sin_to_ridge",
    114: "interior_ridge_to_p_contact",
}

RIGHT_HALF_REGION_IDS = {1, 2, 3, 4, 5, 8, 9, 10, 11}
LEFT_REGION_FOR_RIGHT = {
    1: 1,
    2: 2,
    3: 3,
    4: 4,
    5: 5,
    8: 6,
    9: 7,
    10: 10,
    11: 11,
}


def _close(a: float, b: float, tol: float = 1.0e-9) -> bool:
    return abs(a - b) <= tol


def _point_lc(y: float, z: float, mesh_scale: float = 1.0) -> float:
    scale = max(mesh_scale, 1.0e-12)
    if 1.86 <= z <= 2.12:
        return 0.09 * scale
    if 1.65 <= z <= 2.35:
        return 0.18 * scale
    if -1.65 <= y <= 1.65 and z >= 2.25:
        return 0.22 * scale
    return 0.55 * scale


def _edge_key(a: int, b: int) -> tuple[int, int]:
    return (a, b) if a < b else (b, a)


def _collect_axis_values(rects: list[dict]) -> tuple[list[float], list[float]]:
    ys = set()
    zs = set()
    for rect in rects:
        b = rect["bounds_um"]
        ys.update((round(b["y_min"], 12), round(b["y_max"], 12)))
        zs.update((round(b["z_min"], 12), round(b["z_max"], 12)))
    return sorted(ys), sorted(zs)


def _values_between(values: list[float], lo: float, hi: float) -> list[float]:
    return [value for value in values if lo - 1.0e-9 <= value <= hi + 1.0e-9]


def right_half_model(model: dict) -> dict:
    half = json.loads(json.dumps(model))
    rects = []
    for region_id, rect in enumerate(model["rectangles"], start=1):
        if region_id not in RIGHT_HALF_REGION_IDS:
            continue
        item = json.loads(json.dumps(rect))
        item["id"] = region_id
        b = item["bounds_um"]
        if b["y_min"] < 0.0:
            b["y_min"] = 0.0
            item["size_um"]["width_y"] = b["y_max"] - b["y_min"]
        rects.append(item)
    half["rectangles"] = rects
    half["metadata"]["physical_bounds_um"]["y_min"] = 0.0
    half["metadata"]["physical_bounds_um"]["width_y"] = model["metadata"]["physical_bounds_um"]["y_max"]
    return half


def write_geo(model: dict, geo_path: Path, mesh_scale: float = 1.0, mesh_sizes=None) -> dict:
    rects = model["rectangles"]
    bounds = model["metadata"]["physical_bounds_um"]
    y_values, z_values = _collect_axis_values(rects)
    points: dict[tuple[float, float], int] = {}
    lines: dict[tuple[int, int], int] = {}
    line_to_regions: dict[int, set[int]] = defaultdict(set)
    geo: list[str] = [
        'SetFactory("Built-in");',
        "Mesh.Algorithm = 6;",
        "Mesh.Optimize = 1;",
        "Mesh.OptimizeNetgen = 1;",
        "Mesh.MeshSizeExtendFromBoundary = 1;",
        "Mesh.MeshSizeFromCurvature = 0;",
        "Mesh.MeshSizeFromPoints = 1;",
        f"Mesh.CharacteristicLengthMin = {(mesh_sizes['min_size_um'] if mesh_sizes else 0.045 * mesh_scale):.12g};",
        f"Mesh.CharacteristicLengthMax = {(mesh_sizes['max_size_um'] if mesh_sizes else 0.65 * mesh_scale):.12g};",
    ]

    def point_id(y: float, z: float) -> int:
        key = (round(y, 12), round(z, 12))
        if key not in points:
            points[key] = len(points) + 1
        return points[key]

    for y in y_values:
        for z in z_values:
            point_id(y, z)

    for (y, z), pid in sorted(points.items(), key=lambda item: item[1]):
        geo.append(f"Point({pid}) = {{{y:.12g}, {z:.12g}, 0, {(mesh_sizes['target_size_um'] if mesh_sizes else _point_lc(y, z, mesh_scale)):.12g}}};")

    def line_id(a: int, b: int) -> int:
        key = _edge_key(a, b)
        if key not in lines:
            lines[key] = len(lines) + 1
        lid = lines[key]
        return lid if key == (a, b) else -lid

    surface_geo: list[str] = []
    for fallback_rid, rect in enumerate(rects, start=1):
        rid = rect.get("id", fallback_rid)
        b = rect["bounds_um"]
        y_min, y_max = b["y_min"], b["y_max"]
        z_min, z_max = b["z_min"], b["z_max"]
        loop: list[int] = []
        bottom = _values_between(y_values, y_min, y_max)
        right = _values_between(z_values, z_min, z_max)
        top = list(reversed(bottom))
        left = list(reversed(right))

        for a, c in zip(bottom, bottom[1:]):
            loop.append(line_id(point_id(a, z_min), point_id(c, z_min)))
        for a, c in zip(right, right[1:]):
            loop.append(line_id(point_id(y_max, a), point_id(y_max, c)))
        for a, c in zip(top, top[1:]):
            loop.append(line_id(point_id(a, z_max), point_id(c, z_max)))
        for a, c in zip(left, left[1:]):
            loop.append(line_id(point_id(y_min, a), point_id(y_min, c)))

        for signed_lid in loop:
            line_to_regions[abs(signed_lid)].add(rid)
        loop_id = rid
        surface_id = rid
        surface_geo.append(f"Curve Loop({loop_id}) = {{{', '.join(str(item) for item in loop)}}};")
        surface_geo.append(f"Plane Surface({surface_id}) = {{{loop_id}}};")
        surface_geo.append(f'Physical Surface("{BODY_NAMES[rid]}", {rid}) = {{{surface_id}}};')

    for key, lid in sorted(lines.items(), key=lambda item: item[1]):
        geo.append(f"Line({lid}) = {{{key[0]}, {key[1]}}};")
    geo.extend(surface_geo)

    boundary_lines: dict[int, list[int]] = defaultdict(list)
    point_by_id = {pid: coord for coord, pid in points.items()}
    ridge_half = model["parameters"]["ridge_width_um"] / 2.0
    for key, lid in lines.items():
        regions = sorted(line_to_regions[lid])
        (y0, z0), (y1, z1) = point_by_id[key[0]], point_by_id[key[1]]
        bid = None
        if len(regions) == 1:
            if _close(z0, bounds["z_min"]) and _close(z1, bounds["z_min"]):
                bid = 1
            elif (
                _close(z0, bounds["z_max"])
                and _close(z1, bounds["z_max"])
                and min(y0, y1) >= -ridge_half - 1.0e-9
                and max(y0, y1) <= ridge_half + 1.0e-9
            ):
                bid = 2
            elif _close(y0, bounds["y_min"]) and _close(y1, bounds["y_min"]):
                bid = 3
            elif _close(y0, bounds["y_max"]) and _close(y1, bounds["y_max"]):
                bid = 4
            else:
                bid = 5
        elif len(regions) == 2:
            bid = INTERFACE_IDS.get(tuple(regions))
        if bid is not None:
            boundary_lines[bid].append(lid)

    for bid in sorted(boundary_lines):
        geo.append(
            f'Physical Curve("{BOUNDARY_NAMES[bid]}", {bid}) = '
            f"{{{', '.join(str(item) for item in boundary_lines[bid])}}};"
        )

    geo_path.parent.mkdir(parents=True, exist_ok=True)
    geo_path.write_text("\n".join(geo) + "\n", encoding="utf-8")
    return {"points": points, "lines": lines, "boundary_lines": boundary_lines}


def parse_msh2(msh_path: Path) -> tuple[dict[int, tuple[float, float, float]], list[dict], list[dict]]:
    lines = msh_path.read_text(encoding="utf-8").splitlines()
    nodes: dict[int, tuple[float, float, float]] = {}
    triangles: list[dict] = []
    boundaries: list[dict] = []
    i = 0
    while i < len(lines):
        if lines[i] == "$Nodes":
            count = int(lines[i + 1])
            for row in lines[i + 2 : i + 2 + count]:
                parts = row.split()
                nodes[int(parts[0])] = (float(parts[1]), float(parts[2]), float(parts[3]))
            i += count + 3
            continue
        if lines[i] == "$Elements":
            count = int(lines[i + 1])
            for row in lines[i + 2 : i + 2 + count]:
                parts = [int(item) for item in row.split()]
                eid, etype, ntags = parts[0], parts[1], parts[2]
                tags = parts[3 : 3 + ntags]
                conn = parts[3 + ntags :]
                physical = tags[0] if tags else 0
                if etype == 1 and physical > 0:
                    boundaries.append({"id": eid, "boundary_id": physical, "nodes": conn})
                elif etype == 2 and physical > 0:
                    triangles.append({"id": eid, "body_id": physical, "nodes": conn})
            i += count + 3
            continue
        i += 1
    return nodes, triangles, boundaries


def mirror_half_mesh(
    half_nodes: dict[int, tuple[float, float, float]],
    half_triangles: list[dict],
) -> tuple[dict[int, tuple[float, float, float]], list[dict]]:
    full_nodes: dict[int, tuple[float, float, float]] = {}
    positive_node: dict[int, int] = {}
    negative_node: dict[int, int] = {}

    def add_node(x: float, y: float, z: float) -> int:
        node_id = len(full_nodes) + 1
        full_nodes[node_id] = (round(x, 12), round(y, 12), round(z, 12))
        return node_id

    for old_id in sorted(half_nodes):
        x, y, z = half_nodes[old_id]
        if _close(x, 0.0):
            node_id = add_node(0.0, y, z)
            positive_node[old_id] = node_id
            negative_node[old_id] = node_id
        else:
            positive_node[old_id] = add_node(x, y, z)
            negative_node[old_id] = add_node(-x, y, z)

    full_triangles: list[dict] = []
    for tri in half_triangles:
        full_triangles.append(
            {
                "id": len(full_triangles) + 1,
                "body_id": tri["body_id"],
                "nodes": [positive_node[node] for node in tri["nodes"]],
            }
        )
        full_triangles.append(
            {
                "id": len(full_triangles) + 1,
                "body_id": LEFT_REGION_FOR_RIGHT[tri["body_id"]],
                "nodes": [negative_node[node] for node in reversed(tri["nodes"])],
            }
        )
    return full_nodes, full_triangles


def classify_boundary(
    nodes: dict[int, tuple[float, float, float]],
    edge: tuple[int, int],
    bodies: list[int],
    bounds: dict,
    ridge_half: float,
) -> int | None:
    (x0, y0, _), (x1, y1, _) = nodes[edge[0]], nodes[edge[1]]
    if len(bodies) == 1:
        if _close(y0, bounds["z_min"]) and _close(y1, bounds["z_min"]):
            return 1
        if (
            _close(y0, bounds["z_max"])
            and _close(y1, bounds["z_max"])
            and min(x0, x1) >= -ridge_half - 1.0e-9
            and max(x0, x1) <= ridge_half + 1.0e-9
        ):
            return 2
        if _close(x0, bounds["y_min"]) and _close(x1, bounds["y_min"]):
            return 3
        if _close(x0, bounds["y_max"]) and _close(x1, bounds["y_max"]):
            return 4
        return 5
    if len(bodies) == 2 and bodies[0] != bodies[1]:
        return INTERFACE_IDS.get(tuple(sorted(bodies)))
    return None


def boundaries_from_triangles(
    nodes: dict[int, tuple[float, float, float]],
    triangles: list[dict],
    model: dict,
) -> list[dict]:
    edge_to_triangles: dict[tuple[int, int], list[int]] = defaultdict(list)
    edge_to_bodies: dict[tuple[int, int], list[int]] = defaultdict(list)
    for index, tri in enumerate(triangles, start=1):
        ids = tri["nodes"]
        for a, b in ((ids[0], ids[1]), (ids[1], ids[2]), (ids[2], ids[0])):
            key = _edge_key(a, b)
            edge_to_triangles[key].append(index)
            edge_to_bodies[key].append(tri["body_id"])

    bounds = model["metadata"]["physical_bounds_um"]
    ridge_half = model["parameters"]["ridge_width_um"] / 2.0
    boundaries = []
    for edge in sorted(edge_to_triangles):
        bid = classify_boundary(nodes, edge, edge_to_bodies[edge], bounds, ridge_half)
        if bid is None:
            continue
        attached = edge_to_triangles[edge]
        boundaries.append(
            {
                "id": len(boundaries) + 1,
                "boundary_id": bid,
                "left": attached[0],
                "right": attached[1] if len(attached) > 1 else 0,
                "nodes": list(edge),
            }
        )
    return boundaries


def write_elmer_mesh(
    nodes: dict[int, tuple[float, float, float]],
    triangles: list[dict],
    boundaries: list[dict],
    out_dir: Path,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    header = [
        f"{len(nodes)} {len(triangles)} {len(boundaries)}",
        "2",
        f"202 {len(boundaries)}",
        f"303 {len(triangles)}",
    ]
    (out_dir / "mesh.header").write_text("\n".join(header) + "\n", encoding="utf-8")

    node_lines = []
    for nid in sorted(nodes):
        x, y, z = nodes[nid]
        node_lines.append(f"{nid} -1 {x:.12g} {y:.12g} {z:.12g}")
    (out_dir / "mesh.nodes").write_text("\n".join(node_lines) + "\n", encoding="utf-8")

    element_lines = []
    for index, tri in enumerate(triangles, start=1):
        ids = tri["nodes"]
        element_lines.append(f"{index} {tri['body_id']} 303 {ids[0]} {ids[1]} {ids[2]}")
    (out_dir / "mesh.elements").write_text("\n".join(element_lines) + "\n", encoding="utf-8")

    boundary_lines = []
    for index, item in enumerate(boundaries, start=1):
        ids = item["nodes"]
        left = item["left"]
        right = item["right"]
        boundary_lines.append(f"{index} {item['boundary_id']} {left} {right} 202 {ids[0]} {ids[1]}")
    (out_dir / "mesh.boundary").write_text("\n".join(boundary_lines) + "\n", encoding="utf-8")

    body_ids = sorted({tri["body_id"] for tri in triangles})
    boundary_ids = sorted({item["boundary_id"] for item in boundaries})
    mesh_names = ["! ----- names for bodies -----"]
    for body_id in body_ids:
        mesh_names.append(f"$ {BODY_NAMES.get(body_id, f'body_{body_id}')} = {body_id}")
    mesh_names.append("! ----- names for boundaries -----")
    for boundary_id in boundary_ids:
        mesh_names.append(f"$ {BOUNDARY_NAMES[boundary_id]} = {boundary_id}")
    (out_dir / "mesh.names").write_text("\n".join(mesh_names) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-json", type=Path, default=DEFAULT_MODEL_JSON)
    parser.add_argument("--work-dir", type=Path, default=DEFAULT_WORK_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--gmsh", type=Path, default=DEFAULT_GMSH)
    parser.add_argument("--mesh-scale", type=float, default=1.0, help="multiply all Gmsh characteristic lengths by this factor")
    args = parser.parse_args()

    model = json.loads(args.model_json.read_text(encoding="utf-8"))
    half_model = right_half_model(model)
    geo_path = args.work_dir / "telecom_laser_mesh01.geo"
    msh_path = args.work_dir / "telecom_laser_mesh01.msh"
    write_geo(half_model, geo_path, args.mesh_scale)
    subprocess.run(
        [
            str(args.gmsh),
            str(geo_path),
            "-2",
            "-format",
            "msh2",
            "-o",
            str(msh_path),
        ],
        check=True,
    )
    half_nodes, half_triangles, _ = parse_msh2(msh_path)
    nodes, triangles = mirror_half_mesh(half_nodes, half_triangles)
    boundaries = boundaries_from_triangles(nodes, triangles, model)
    write_elmer_mesh(nodes, triangles, boundaries, args.out_dir)
    print(f"Gmsh mesh: {msh_path}")
    print(f"Elmer mesh: {args.out_dir}")
    print(f"nodes={len(nodes)} triangles={len(triangles)} boundaries={len(boundaries)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Read Elmer VTU arrays and derive electrostatic fields on actual triangles."""
import base64
import re
import xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np


def read_vtu(path):
    raw = Path(path).read_bytes()
    start = raw.find(b"<AppendedData")
    payload = None
    if start >= 0:
        header = raw[:start] + b"</VTKFile>"
        end_tag = raw.index(b">", start) + 1
        content = raw[end_tag:raw.rindex(b"</AppendedData>")].lstrip()
        if not content.startswith(b"_"):
            raise ValueError("Missing appended VTU sentinel")
        content = content[1:]
        payload = base64.b64decode(content) if b'encoding="base64"' in raw[start:end_tag] else content
    else:
        header = raw
    root = ET.fromstring(header)
    if root.get("compressor"):
        raise ValueError("Compressed VTU is unsupported; export uncompressed Elmer VTU.")
    endian = ">" if root.get("byte_order") == "BigEndian" else "<"
    header_type = np.dtype(endian + ("u8" if root.get("header_type") == "UInt64" else "u4"))
    types = {"Float64": "f8", "Float32": "f4", "Int32": "i4", "Int64": "i8", "UInt8": "u1"}

    def array(node):
        dtype = np.dtype(endian + types[node.get("type")])
        if node.get("format", "ascii") == "ascii":
            values = np.fromstring(node.text or "", sep=" ", dtype=dtype)
        else:
            if node.get("format") == "appended":
                if payload is None:
                    raise ValueError("Missing VTU payload")
                data = payload[int(node.get("offset")):]
            elif node.get("format") == "binary":
                data = base64.b64decode(node.text or "")
            else:
                raise ValueError("Unsupported VTU encoding")
            count = int(np.frombuffer(data[:header_type.itemsize], dtype=header_type)[0])
            if count > len(data)-header_type.itemsize:
                raise ValueError("Truncated VTU array")
            values = np.frombuffer(data[header_type.itemsize:header_type.itemsize+count], dtype=dtype).copy()
        components = int(node.get("NumberOfComponents", "1"))
        return values.reshape(-1, components) if components > 1 else values

    piece = root.find(".//Piece")
    points = array(piece.find("Points/DataArray"))
    cells = {node.get("Name"): array(node) for node in piece.findall("Cells/DataArray")}
    triangles, previous = [], 0
    for offset, kind in zip(cells["offsets"], cells["types"]):
        vertices = cells["connectivity"][previous:offset]
        if kind == 5 and len(vertices) == 3:
            triangles.append(vertices)
        previous = offset
    fields = {node.get("Name").lower(): array(node) for node in piece.findall("PointData/DataArray")}
    if not triangles or not np.isfinite(points).all():
        raise ValueError("Expected a finite triangular mesh")
    return points, np.asarray(triangles, dtype=int), fields


def potential_gradient(points, triangles, potential):
    """Area-weighted nodal -grad(Psi), coordinates in cm, output V/cm."""
    xy = points[:, :2]
    vertices = xy[triangles]
    a = vertices[:, 1] - vertices[:, 0]
    b = vertices[:, 2] - vertices[:, 0]
    det = a[:, 0]*b[:, 1] - a[:, 1]*b[:, 0]
    if np.any(np.abs(det) < 1e-30):
        raise ValueError("Degenerate triangle in field mesh")
    delta = potential[triangles[:, 1:]] - potential[triangles[:, 0, None]]
    gradient = -np.column_stack(((delta[:, 0]*b[:, 1]-delta[:, 1]*a[:, 1])/det,
                                 (a[:, 0]*delta[:, 1]-b[:, 0]*delta[:, 0])/det))
    out, weights = np.zeros((len(points), 2)), np.zeros(len(points))
    for i in range(3):
        np.add.at(out, triangles[:, i], gradient*np.abs(det[:, None]))
        np.add.at(weights, triangles[:, i], np.abs(det))
    return out / np.maximum(weights[:, None], 1e-30)


def available_fields(points, triangles, fields, phase=0.):
    result = {}
    carrier = fields.get("carriers")
    if carrier is not None and carrier.ndim == 2 and carrier.shape[1] >= 3:
        result.update({"Potential (V)": carrier[:, 0], "Electrons (cm⁻³)": carrier[:, 1],
                       "Holes (cm⁻³)": carrier[:, 2]})
        e = potential_gradient(points, triangles, carrier[:, 0])
        result["Electrostatic |E| (V/cm), derived"] = np.linalg.norm(e, axis=1)
    if "temperature" in fields:
        result["Temperature (K)"] = fields["temperature"]
    if "photonpopulation" in fields:
        result["Photon population (solver units)"] = fields["photonpopulation"]
    # Expose all solved EM components verbatim, with no fabricated field amplitudes.
    for name, values in fields.items():
        if name in {"carriers", "temperature", "photonpopulation"}:
            continue
        if values.ndim == 1:
            result[name + " (solver units)"] = values
        else:
            result[name + " magnitude (solver units)"] = np.linalg.norm(values, axis=1)
            for i in range(values.shape[1]):
                result[f"{name} [{i+1}] (solver units)"] = values[:, i]
    for name, values in fields.items():
        if " re" in name and name.replace(" re", " im") in fields:
            imag = fields[name.replace(" re", " im")]
            instantaneous = values*np.cos(phase) - imag*np.sin(phase)
            if instantaneous.ndim == 1:
                result[name.replace(" re", " phase") + " (solver units)"] = instantaneous
            else:
                for i in range(instantaneous.shape[1]):
                    result[name.replace(" re", " phase") + f" [{i+1}] (solver units)"] = instantaneous[:, i]
    return result

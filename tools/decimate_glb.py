"""Write a lighter copy of a .glb: every mesh reduced to about a target triangle count, with smooth normals.

For props seen small or many times over (OBTRAN 001's skull field: 89 skulls), where the full model would be
millions of triangles on a phone. Geometry only: materials, UVs and textures are dropped, as props are shaded
by the page's own ink grade.

Usage: python3 tools/decimate_glb.py in.glb out.glb [triangles, default 3000] [--keep-border]
Needs: numpy, pyfqmr (pip install pyfqmr).
"""
import json
import struct
import sys

import numpy as np
import pyfqmr

COMP = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
SIZE = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


def read_glb(path):
    b = open(path, "rb").read()
    jl = struct.unpack("<I", b[12:16])[0]
    gl = json.loads(b[20:20 + jl])
    o = 20 + jl
    bl = struct.unpack("<I", b[o:o + 4])[0]
    blob = b[o + 8:o + 8 + bl]
    return gl, blob


def accessor(gl, blob, i):
    a = gl["accessors"][i]
    v = gl["bufferViews"][a["bufferView"]]
    n, k = a["count"], SIZE[a["type"]]
    off = v.get("byteOffset", 0) + a.get("byteOffset", 0)
    return np.frombuffer(blob, COMP[a["componentType"]], n * k, off).reshape(n, k) if k > 1 else np.frombuffer(blob, COMP[a["componentType"]], n, off)


def normals(v, f):
    n = np.zeros_like(v)
    fn = np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]])
    for k in range(3):
        np.add.at(n, f[:, k], fn)
    return (n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)).astype(np.float32)


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    src, dst = sys.argv[1], sys.argv[2]
    target = int(sys.argv[3]) if len(sys.argv) > 3 else 3000
    gl, blob = read_glb(src)
    parts, views, accs, meshes = [], [], [], []

    def add(arr, target_kind, typ, ctype):
        off = sum(len(p) for p in parts)
        data = arr.tobytes()
        parts.append(data + b"\0" * ((-len(data)) % 4))
        views.append({"buffer": 0, "byteOffset": off, "byteLength": len(data), "target": target_kind})
        a = {"bufferView": len(views) - 1, "componentType": ctype, "count": len(arr), "type": typ}
        if typ == "VEC3":
            a["min"], a["max"] = arr.min(0).tolist(), arr.max(0).tolist()
        accs.append(a)
        return len(accs) - 1

    for m in gl["meshes"]:
        prims = []
        for p in m["primitives"]:
            v = accessor(gl, blob, p["attributes"]["POSITION"]).astype(np.float64)
            f = accessor(gl, blob, p["indices"]).reshape(-1, 3).astype(np.int64)
            s = pyfqmr.Simplify()
            s.setMesh(v, f)
            s.simplify_mesh(target_count=target, aggressiveness=7, preserve_border="--keep-border" in sys.argv, verbose=0)
            v2, f2, _ = s.getMesh()
            v2, f2 = v2.astype(np.float32), f2.astype(np.uint32)
            print(f"{m.get('name', 'mesh')}: {len(f)} -> {len(f2)} triangles")
            prims.append({"attributes": {"POSITION": add(v2, 34962, "VEC3", 5126), "NORMAL": add(normals(v2, f2), 34962, "VEC3", 5126)},
                          "indices": add(f2.reshape(-1), 34963, "SCALAR", 5125)})
        meshes.append({"name": m.get("name", "mesh"), "primitives": prims})
    out = {"asset": {"version": "2.0", "generator": "obtran tools/decimate_glb.py"}, "scene": 0, "scenes": gl["scenes"],
           "nodes": gl["nodes"], "meshes": meshes, "accessors": accs, "bufferViews": views}
    body = b"".join(parts)
    out["buffers"] = [{"byteLength": len(body)}]
    js = json.dumps(out, separators=(",", ":")).encode()
    js += b" " * ((-len(js)) % 4)
    with open(dst, "wb") as fh:
        fh.write(struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(body)))
        fh.write(struct.pack("<II", len(js), 0x4E4F534A) + js)
        fh.write(struct.pack("<II", len(body), 0x004E4942) + body)
    print(f"wrote {dst} {(28 + len(js) + len(body)) / 1e3:.0f} KB")


if __name__ == "__main__":
    main()

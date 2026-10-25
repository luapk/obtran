"""Read the polygon meshes out of a Maya binary scene (.mb) and write them as a .glb, without Maya.

Maya's binary files are IFF (FOR8 groups, 4-byte tags, 8-byte big-endian sizes, data padded to 4 bytes).
Each mesh node (a DMSH group, named by its CREA chunk) keeps its final shape in a MESH chunk on the 'o'
attribute, laid out as (all big-endian, worked out from OBTRAN 001's pod scene, Maya 2020):

  'o\\0', one flags byte,
  u32 n, n float32: vertex positions (x, y, z),
  u32 n, n u32: edges as vertex pairs (the top three bits of each are flags),
  u32 n, n u32: faces as a run of edge indices; bit 31 = the edge runs backwards, bits 29 and 30 both set
                = the last edge of its face; a face corner is the start vertex of each edge as walked,
  u32 n, n float32: a normal per face corner,
  u32 colour sets (0), u32 uv sets (1), u32 (0),
  the uv set's name ('map1\\0'), u32 n, n float32: uvs,
  u32 n, n u32: a uv index per face corner, then five u32 zeros.

Transforms come from each XFRM group's t, r (radians, XYZ order) and s chunks; meshes are placed under
their transform's parent chain up to (not including) the root named by --root, so the result keeps the
model's own scale and axes (Maya is Y up and right handed, like glTF).

Usage:
  python3 tools/mb_to_glb.py scene.mb out.glb --root ALIEN_POD \\
      --material "Pod_GEO=base:a.jpg,normal:b.jpg,roughness:c.jpg,metallic:d.jpg,emissive:e.jpg" \\
      --material "head*,Eyelid*,Eyrlid*=base:f.jpg,normal:g.jpg,roughness:h.jpg" [--size 2048] [--skip data_rings]
Needs: numpy, Pillow.
"""
import fnmatch
import io
import json
import math
import struct
import sys

import numpy as np
from PIL import Image


def chunks(d, start, end):
    o = start
    while o + 16 <= end:
        tag = d[o:o + 4]
        if not all(32 <= c < 127 for c in tag):  # alignment slack between groups
            o += 4
            continue
        size = struct.unpack(">Q", d[o + 8:o + 16])[0]
        yield tag, o + 16, size
        o = (o + 16 + size + 3) & ~3


def walk(d, start, end, depth, out):
    for tag, body, size in chunks(d, start, end):
        if tag[:3] in (b"FOR", b"LIS", b"CAT", b"PRO"):
            out.append((depth, tag, d[body:body + 4], body, size))
            walk(d, body + 4, body + size, depth + 1, out)
        else:
            out.append((depth, tag, None, body, size))


def u32(b, o):
    return struct.unpack(">I", b[o:o + 4])[0]


def decode_mesh(b):
    o = b.index(b"\0") + 2
    n = u32(b, o); o += 4
    verts = np.frombuffer(b, ">f4", n, o).reshape(-1, 3).astype(np.float32); o += 4 * n
    n = u32(b, o); o += 4
    ed = np.frombuffer(b, ">u4", n, o) & 0x1FFFFFFF; o += 4 * n
    edges = ed.reshape(-1, 2)
    n = u32(b, o); o += 4
    fe = np.frombuffer(b, ">u4", n, o); o += 4 * n
    n = u32(b, o); o += 4
    normals = np.frombuffer(b, ">f4", n, o).reshape(-1, 3).astype(np.float32); o += 4 * n
    o += 12
    o = b.index(b"\0", o) + 1
    n = u32(b, o); o += 4
    uvs = np.frombuffer(b, ">f4", n, o).reshape(-1, 2).astype(np.float32); o += 4 * n
    n = u32(b, o); o += 4
    uvi = np.frombuffer(b, ">u4", n, o).astype(np.int64)
    e = (fe & 0x1FFFFFFF).astype(np.int64)
    rev = (fe >> 31).astype(bool)
    corner_v = np.where(rev, edges[e, 1], edges[e, 0]).astype(np.int64)
    last = ((fe >> 29) & 3) == 3
    ends = np.nonzero(last)[0]
    starts = np.concatenate([[0], ends[:-1] + 1])
    if len(normals) != len(corner_v) or len(uvi) != len(corner_v):
        raise ValueError("face corners, normals and uv indices disagree")
    return dict(verts=verts, corner_v=corner_v, normals=normals, uvs=uvs, uvi=uvi, starts=starts, ends=ends)


def read_scene(path):
    d = open(path, "rb").read()
    if d[:4] != b"FOR8":
        raise ValueError("not a 64 bit Maya binary file")
    out = []
    walk(d, 0, len(d), 0, out)
    nodes, cur = {}, None
    for i, (depth, tag, typ, body, size) in enumerate(out):
        if tag == b"CREA":
            parts = d[body:body + size].split(b"\0")
            name = parts[0][1:].decode("latin1")
            parent = parts[1].decode("latin1") if len(parts) > 1 and parts[1][:1] not in (b"",) else ""
            gtyp = next((out[j][2] for j in range(i - 1, -1, -1) if out[j][2] is not None and out[j][0] == depth - 1), None)
            cur = nodes.setdefault(name, {"type": gtyp, "parent": parent})
        elif cur is not None and tag == b"DBL3":
            a = d[body:body + size]
            k = a.index(b"\0")
            key = a[:k].decode("latin1")
            if key in ("t", "r", "s") and size >= k + 26:
                cur[key] = struct.unpack(">3d", a[k + 2:k + 26])
        elif cur is not None and tag == b"MESH":
            cur["mesh"] = d[body:body + size]
    return nodes


def euler_xyz_quat(r):
    cx, cy, cz = (math.cos(a / 2) for a in r)
    sx, sy, sz = (math.sin(a / 2) for a in r)
    # Maya's XYZ order applies X first: q = qz * qy * qx
    return [sx * cy * cz - cx * sy * sz, cx * sy * cz + sx * cy * sz, cx * cy * sz - sx * sy * cz, cx * cy * cz + sx * sy * sz]


def texture_bytes(path, size, mode="RGB"):
    im = Image.open(path).convert(mode)
    if size and im.width > size:
        im = im.resize((size, size), Image.LANCZOS)
    buf = io.BytesIO()
    im.convert("RGB").save(buf, "JPEG", quality=88)
    return buf.getvalue()


def metal_rough(rough, metal, size):
    r = Image.open(rough).convert("L")
    m = Image.open(metal).convert("L") if metal else Image.new("L", r.size, 0)
    if size and r.width > size:
        r = r.resize((size, size), Image.LANCZOS)
    m = m.resize(r.size, Image.LANCZOS)
    rgb = Image.merge("RGB", (Image.new("L", r.size, 255), r, m))  # glTF: G roughness, B metallic
    buf = io.BytesIO()
    rgb.save(buf, "JPEG", quality=90)
    return buf.getvalue()


def main():
    args = sys.argv[1:]
    if len(args) < 2:
        sys.exit(__doc__)
    src, dst = args[0], args[1]
    opt = lambda k, dflt=None: args[args.index(k) + 1] if k in args else dflt
    root = opt("--root")
    size = int(opt("--size", "2048"))
    skip = opt("--skip", "")
    mats = [args[i + 1] for i, a in enumerate(args) if a == "--material"]
    nodes = read_scene(src)

    bin_parts, views, accessors, images, textures, materials, meshes, gl_nodes = [], [], [], [], [], [], [], []

    def add_view(data, target=None):
        off = sum(len(p) for p in bin_parts)
        pad = (-off) % 4
        if pad:
            bin_parts.append(b"\0" * pad)
            off += pad
        bin_parts.append(data)
        v = {"buffer": 0, "byteOffset": off, "byteLength": len(data)}
        if target:
            v["target"] = target
        views.append(v)
        return len(views) - 1

    def add_accessor(arr, ctype, typ, target):
        view = add_view(arr.tobytes(), target)
        a = {"bufferView": view, "componentType": ctype, "count": len(arr), "type": typ}
        if typ == "VEC3" and ctype == 5126:
            a["min"] = arr.min(axis=0).tolist()
            a["max"] = arr.max(axis=0).tolist()
        accessors.append(a)
        return len(accessors) - 1

    def add_image(data):
        images.append({"bufferView": add_view(data), "mimeType": "image/jpeg"})
        textures.append({"source": len(images) - 1})
        return {"index": len(textures) - 1}

    mat_index = {}
    for spec in mats:
        pats, _, maps = spec.partition("=")
        m = dict(kv.split(":", 1) for kv in maps.split(","))
        gm = {"name": pats.split(",")[0].strip("*"), "pbrMetallicRoughness": {"metallicFactor": 1.0, "roughnessFactor": 1.0}}
        if "base" in m:
            gm["pbrMetallicRoughness"]["baseColorTexture"] = add_image(texture_bytes(m["base"], size))
        if "roughness" in m:
            gm["pbrMetallicRoughness"]["metallicRoughnessTexture"] = add_image(metal_rough(m["roughness"], m.get("metallic"), size // 2))
        if "metallic" not in m:
            gm["pbrMetallicRoughness"]["metallicFactor"] = 0.0
        if "normal" in m:
            gm["normalTexture"] = add_image(texture_bytes(m["normal"], size))
        if "emissive" in m:
            gm["emissiveTexture"] = add_image(texture_bytes(m["emissive"], size // 2))
            gm["emissiveFactor"] = [1, 1, 1]
        materials.append(gm)
        for p in pats.split(","):
            mat_index[p.strip()] = len(materials) - 1

    def chain(name):
        out = []
        while name and name in nodes and name != root:
            out.append(name)
            name = nodes[name]["parent"]
        return out

    for name, n in nodes.items():
        if "mesh" not in n or (skip and skip in name):
            continue
        xform = n["parent"]
        try:
            m = decode_mesh(n["mesh"])
        except Exception as e:  # meshes in a format this reader does not know
            print(f"skip {name}: {e}")
            continue
        # unique corners by (vertex, uv, normal)
        nrm = np.round(m["normals"] * 512).astype(np.int64)
        key = np.stack([m["corner_v"], m["uvi"], nrm[:, 0], nrm[:, 1], nrm[:, 2]], axis=1)
        uniq, inv = np.unique(key, axis=0, return_inverse=True)
        inv = inv.reshape(-1)
        first = np.zeros(len(uniq), np.int64)
        first[inv[::-1]] = np.arange(len(inv))[::-1]
        pos = m["verts"][m["corner_v"][first]]
        nor = m["normals"][first]
        nor /= np.maximum(np.linalg.norm(nor, axis=1, keepdims=True), 1e-8)
        uv = m["uvs"][m["uvi"][first]].copy()
        uv[:, 1] = 1.0 - uv[:, 1]
        tris = []
        for s, e in zip(m["starts"], m["ends"]):
            for k in range(s + 1, e):
                tris.append((inv[s], inv[k], inv[k + 1]))
        idx = np.asarray(tris, np.uint32).reshape(-1)
        prim = {"attributes": {"POSITION": add_accessor(pos.astype(np.float32), 5126, "VEC3", 34962),
                               "NORMAL": add_accessor(nor.astype(np.float32), 5126, "VEC3", 34962),
                               "TEXCOORD_0": add_accessor(uv.astype(np.float32), 5126, "VEC2", 34962)},
                "indices": add_accessor(idx, 5125, "SCALAR", 34963)}
        short = xform.split(":")[-1]
        mi = next((i for p, i in mat_index.items() if fnmatch.fnmatch(short, p)), None)
        if mi is not None:
            prim["material"] = mi
        meshes.append({"name": short, "primitives": [prim]})
        # the transform chain from the root down to this mesh
        parent = None
        for tn in reversed(chain(xform)):
            t = nodes[tn]
            gn = {"name": tn.split(":")[-1]}
            if "t" in t: gn["translation"] = list(t["t"])
            if "r" in t: gn["rotation"] = euler_xyz_quat(t["r"])
            if "s" in t: gn["scale"] = list(t["s"])
            gl_nodes.append(gn)
            idx_n = len(gl_nodes) - 1
            if parent is not None:
                gl_nodes[parent].setdefault("children", []).append(idx_n)
            parent = idx_n
        gl_nodes[parent]["mesh"] = len(meshes) - 1
        print(f"{short}: {len(m['verts'])} vertices, {len(m['starts'])} faces -> {len(pos)} corners, {len(idx) // 3} triangles")

    tops = [i for i in range(len(gl_nodes)) if not any(i in g.get("children", []) for g in gl_nodes)]
    gl_nodes.append({"name": root or "root", "children": tops})
    blob = b"".join(bin_parts)
    blob += b"\0" * ((-len(blob)) % 4)
    gltf = {"asset": {"version": "2.0", "generator": "obtran tools/mb_to_glb.py"}, "scene": 0,
            "scenes": [{"nodes": [len(gl_nodes) - 1]}], "nodes": gl_nodes, "meshes": meshes,
            "materials": materials, "textures": textures, "images": images, "samplers": [{"magFilter": 9729, "minFilter": 9987}],
            "accessors": accessors, "bufferViews": views, "buffers": [{"byteLength": len(blob)}]}
    for t in textures:
        t["sampler"] = 0
    js = json.dumps(gltf, separators=(",", ":")).encode()
    js += b" " * ((-len(js)) % 4)
    with open(dst, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(blob)))
        f.write(struct.pack("<II", len(js), 0x4E4F534A) + js)
        f.write(struct.pack("<II", len(blob), 0x004E4942) + blob)
    print(f"wrote {dst} {(12 + 16 + len(js) + len(blob)) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()

"""A lighter copy of a textured .glb for the page: the geometry as it is (positions, normals, uvs), only the base colour
texture, resized and re-encoded as JPEG. The page shades textured props itself (shade: texture, its own lighting), so
the metal, roughness and normal maps are not used.

Usage: python3 tools/slim_glb.py in.glb out.glb [texture size, default 1024]
Needs: numpy, Pillow.
"""
import io
import json
import struct
import sys

from PIL import Image

sys.path.insert(0, __import__("os").path.dirname(__file__))
import decimate_glb as D  # noqa: E402


def main():
    src, dst = sys.argv[1], sys.argv[2]
    size = int(sys.argv[3]) if len(sys.argv) > 3 else 1024
    gl, blob = D.read_glb(src)
    parts, views, accs = [], [], []

    def add_bytes(data, target=None):
        off = sum(len(p) for p in parts)
        parts.append(data + b"\0" * ((-len(data)) % 4))
        v = {"buffer": 0, "byteOffset": off, "byteLength": len(data)}
        if target: v["target"] = target
        views.append(v)
        return len(views) - 1

    meshes = []
    for m in gl["meshes"]:
        prims = []
        for p in m["primitives"]:
            attrs = {}
            for k in ("POSITION", "NORMAL", "TEXCOORD_0"):
                if k not in p["attributes"]: continue
                a = gl["accessors"][p["attributes"][k]]
                arr = D.accessor(gl, blob, p["attributes"][k])
                acc = {"bufferView": add_bytes(arr.tobytes(), 34962), "componentType": a["componentType"], "count": a["count"], "type": a["type"]}
                if "min" in a: acc["min"], acc["max"] = a["min"], a["max"]
                accs.append(acc); attrs[k] = len(accs) - 1
            ia = gl["accessors"][p["indices"]]
            idx = D.accessor(gl, blob, p["indices"])
            accs.append({"bufferView": add_bytes(idx.tobytes(), 34963), "componentType": ia["componentType"], "count": ia["count"], "type": "SCALAR"})
            prims.append({"attributes": attrs, "indices": len(accs) - 1, "material": 0})
        meshes.append({"name": m.get("name", "mesh"), "primitives": prims})
    mat = gl["materials"][0]
    ti = mat["pbrMetallicRoughness"]["baseColorTexture"]["index"]
    img = gl["images"][gl["textures"][ti]["source"]]
    bv = gl["bufferViews"][img["bufferView"]]
    im = Image.open(io.BytesIO(blob[bv.get("byteOffset", 0):bv.get("byteOffset", 0) + bv["byteLength"]])).convert("RGB")
    im.thumbnail((size, size), Image.LANCZOS)
    buf = io.BytesIO(); im.save(buf, "JPEG", quality=86)
    iv = add_bytes(buf.getvalue())
    out = {"asset": {"version": "2.0", "generator": "obtran tools/slim_glb.py"}, "scene": 0, "scenes": gl["scenes"], "nodes": gl["nodes"],
           "meshes": meshes, "accessors": accs, "bufferViews": views,
           "images": [{"bufferView": iv, "mimeType": "image/jpeg"}], "samplers": [{"magFilter": 9729, "minFilter": 9987}],
           "textures": [{"source": 0, "sampler": 0}],
           "materials": [{"pbrMetallicRoughness": {"baseColorTexture": {"index": 0}, "metallicFactor": 0.2, "roughnessFactor": 0.8}, "doubleSided": True}]}
    body = b"".join(parts)
    out["buffers"] = [{"byteLength": len(body)}]
    js = json.dumps(out, separators=(",", ":")).encode(); js += b" " * ((-len(js)) % 4)
    with open(dst, "wb") as fh:
        fh.write(struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(body)))
        fh.write(struct.pack("<II", len(js), 0x4E4F534A) + js)
        fh.write(struct.pack("<II", len(body), 0x004E4942) + body)
    print(f"wrote {dst} {(28 + len(js) + len(body)) / 1e6:.2f} MB, texture {im.size}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Reads the Unity project AssetRipper exported from Granny 4 End Game and writes what the remake needs.

    python3 report.py <exported unity project> <work dir> <out dir>

<out>/report.md               overview: game, APK, Unity version, scenes, lights, scripts, materials, textures
<out>/scenes/<scene>.json     every object of each scene: world position, rotation, scale, mesh, materials,
                              components, script fields (to rebuild the same layout and gameplay)
<out>/materials.json          material -> shader, textures, colour
<out>/textures/*.jpg          contact sheets of the textures (to see the style and pick real replacements)
<out>/code/                   the game's own scripts as AssetRipper exported them
<out>/main_scene.txt          name of the scene with the house (for the Blender renders)
"""
import collections
import glob
import json
import math
import os
import re
import shutil
import sys

import yaml
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))
from unity_ids import dll_classes_from_rea  # noqa: E402

Loader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
HDR = re.compile(r"^--- !u!(\d+) &(-?\d+)( stripped)?[^\n]*$", re.M)
GUID = re.compile(r"guid: ([0-9a-fA-F]{32})")   # quoted before parsing: YAML would read some guids as numbers
BUILTIN_MESH = {10202: "Cube", 10206: "Cylinder", 10207: "Sphere", 10208: "Capsule", 10209: "Plane", 10210: "Quad"}
COMPONENT_NAMES = {
    20: "Camera", 23: "MeshRenderer", 33: "MeshFilter", 54: "Rigidbody", 64: "MeshCollider", 65: "BoxCollider",
    82: "AudioSource", 81: "AudioListener", 95: "Animator", 108: "Light", 111: "Animation", 114: "MonoBehaviour",
    120: "LineRenderer", 135: "SphereCollider", 136: "CapsuleCollider", 137: "SkinnedMeshRenderer",
    143: "CharacterController", 146: "WheelCollider", 153: "ConfigurableJoint", 195: "NavMeshAgent",
    198: "ParticleSystem", 199: "ParticleSystemRenderer", 205: "LODGroup", 208: "NavMeshObstacle",
    212: "SpriteRenderer", 215: "ReflectionProbe", 220: "LightProbeGroup", 222: "CanvasRenderer", 223: "Canvas",
    225: "CanvasGroup", 59: "HingeJoint", 4: "Transform", 224: "RectTransform", 58: "CircleCollider2D",
    61: "BoxCollider2D", 50: "Rigidbody2D", 102: "TextMesh", 96: "TrailRenderer", 192: "OcclusionArea",
    1183024399: "LookAtConstraint", 331: "SpriteMask", 1660057539: "SortingGroup", 210: "SortingGroup",
}
MAX_FIELD_ITEMS = 12
# Unity UI fields worth keeping: texts, images, button/toggle/slider events (the game methods they call)
UI_FIELDS = {"m_text", "m_Text", "m_OnClick", "m_OnValueChanged", "m_Sprite", "m_Color", "m_fontSize", "m_FontData",
             "m_Value", "m_MinValue", "m_MaxValue", "m_IsOn", "m_Interactable", "m_fontAsset", "m_Options",
             "m_PersistentCalls", "m_Calls"}


def log(*a):
    print("[report]", *a, flush=True)


def read_text(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def unity_docs(path):
    """Yields (class id, file id, stripped, type name, body dict) for every object in a Unity YAML file."""
    text = read_text(path)
    parts = HDR.split(text)
    for i in range(1, len(parts) - 3, 4):
        cid, fid, stripped, body = int(parts[i]), int(parts[i + 1]), bool(parts[i + 2]), parts[i + 3]
        try:
            d = yaml.load(GUID.sub(r'guid: "\1"', body), Loader=Loader)
        except Exception:  # noqa: BLE001
            d = None
        if isinstance(d, dict) and len(d) == 1:
            typ, val = next(iter(d.items()))
        else:
            typ, val = "?", d
        yield cid, fid, stripped, typ, (val if isinstance(val, dict) else {})


def first_doc(path):
    for d in unity_docs(path):
        return d
    return None


def guid_map(root):
    out = {}
    for dp, _dn, fn in os.walk(os.path.join(root, "Assets")):
        for f in fn:
            if not f.endswith(".meta"):
                continue
            p = os.path.join(dp, f)
            try:
                with open(p, encoding="utf-8", errors="replace") as fh:
                    for line in fh:
                        if line.startswith("guid:"):
                            out[line.split(":", 1)[1].strip()] = os.path.relpath(p[:-5], root)
                            break
            except OSError:
                pass
    return out


def ref_of(v):
    if isinstance(v, dict) and "fileID" in v:
        return int(v.get("fileID") or 0), v.get("guid")
    return 0, None


def vec(v, keys="xyz", default=0.0):
    if not isinstance(v, dict):
        return [default] * len(keys)
    return [float(v.get(k, default) or 0.0) for k in keys]


# --- small 3D math (Unity: left-handed, quaternion x y z w) -------------------------------------------------------
def q_mul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return [aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw,
            aw * bw - ax * bx - ay * by - az * bz]


def q_rot(q, v):
    x, y, z, w = q
    vx, vy, vz = v
    tx = 2 * (y * vz - z * vy)
    ty = 2 * (z * vx - x * vz)
    tz = 2 * (x * vy - y * vx)
    return [vx + w * tx + (y * tz - z * ty), vy + w * ty + (z * tx - x * tz), vz + w * tz + (x * ty - y * tx)]


def q_euler(q):
    """Unity-style euler angles (degrees, Z then X then Y)."""
    x, y, z, w = q
    sinx = 2 * (w * x - y * z)
    sinx = max(-1.0, min(1.0, sinx))
    ex = math.degrees(math.asin(sinx))
    ey = math.degrees(math.atan2(2 * (w * y + x * z), 1 - 2 * (x * x + y * y)))
    ez = math.degrees(math.atan2(2 * (w * z + x * y), 1 - 2 * (x * x + z * z)))
    return [round(ex % 360, 2), round(ey % 360, 2), round(ez % 360, 2)]


def r3(v):
    return [round(a, 3) for a in v]


def simple(v, depth=0):
    """Keeps a script field readable: numbers, strings, bools, vectors, short lists, object references."""
    if depth > 6:
        return "..."
    if isinstance(v, (int, float, bool)) or v is None:
        return v
    if isinstance(v, str):
        return v[:200]
    if isinstance(v, dict):
        if "fileID" in v:
            return {"ref": int(v.get("fileID") or 0), **({"guid": v["guid"]} if v.get("guid") else {})}
        return {k: simple(x, depth + 1) for k, x in list(v.items())[:MAX_FIELD_ITEMS]}
    if isinstance(v, list):
        out = [simple(x, depth + 1) for x in v[:MAX_FIELD_ITEMS]]
        if len(v) > MAX_FIELD_ITEMS:
            out.append("... %d items" % len(v))
        return out
    return str(v)[:100]


class Project:
    def __init__(self, root, dll_classes=None):
        self.root = root
        self.guids = guid_map(root)
        self.mat_cache = {}
        self.dll_classes = dll_classes or {}

    def path_of(self, guid):
        return self.guids.get(guid or "")

    def name_of(self, guid, file_id=0):
        p = self.path_of(guid)
        if p:
            return os.path.splitext(os.path.basename(p))[0]
        if guid == "0000000000000000e000000000000000" and file_id in BUILTIN_MESH:
            return "builtin:" + BUILTIN_MESH[file_id]
        if guid == "0000000000000000f000000000000000" and file_id in (45, 46):
            return {46: "builtin:Standard", 45: "builtin:Standard (Specular setup)"}[file_id]
        if guid and guid.startswith("0000000000000000"):
            return "builtin:%s" % file_id
        return None

    def material(self, guid):
        if guid in self.mat_cache:
            return self.mat_cache[guid]
        p = self.path_of(guid)
        info = {"name": self.name_of(guid) or guid, "path": p}
        if p and p.endswith(".mat") and os.path.exists(os.path.join(self.root, p)):
            doc = first_doc(os.path.join(self.root, p))
            if doc:
                body = doc[4]
                sid, sguid = ref_of(body.get("m_Shader"))
                info["shader"] = self.name_of(sguid, sid) or ("builtin:%s" % sid)
                info["keywords"] = body.get("m_ShaderKeywords") or body.get("m_ValidKeywords")
                props = body.get("m_SavedProperties") or {}

                def pairs(v):
                    """m_TexEnvs / m_Floats / m_Colors come as a list of one-key maps, a list of first/second pairs
                    or a plain mapping, depending on the Unity version and the exporter."""
                    if isinstance(v, dict):
                        return list(v.items())
                    out = []
                    for item in v or []:
                        if not isinstance(item, dict):
                            continue
                        if "first" in item:
                            f = item.get("first")
                            out.append((f.get("name") if isinstance(f, dict) else f, item.get("second")))
                        elif len(item) == 1:
                            out.append(next(iter(item.items())))
                    return out

                tex = {}
                for name, val in pairs(props.get("m_TexEnvs")):
                    tid, tguid = ref_of((val or {}).get("m_Texture") if isinstance(val, dict) else None)
                    if tguid:
                        tex[name] = {"texture": self.path_of(tguid) or tguid,
                                     "scale": vec((val or {}).get("m_Scale"), "xy", 1.0),
                                     "offset": vec((val or {}).get("m_Offset"), "xy", 0.0)}
                info["textures"] = tex
                cols = {k: vec(v, "rgba", 1.0) for k, v in pairs(props.get("m_Colors"))}
                info["colors"] = {k: r3(v) for k, v in cols.items()
                                  if k in ("_Color", "_BaseColor", "_EmissionColor", "_TintColor", "_SpecColor")}
                floats = dict(pairs(props.get("m_Floats")))
                info["floats"] = {k: v for k, v in floats.items()
                                  if k in ("_Glossiness", "_Smoothness", "_Metallic", "_Mode", "_Cutoff", "_Surface",
                                           "_BumpScale", "_AlphaClip", "_Blend", "_Cull")}
        self.mat_cache[guid] = info
        return info


def script_name(proj, mono):
    sid, sguid = ref_of(mono.get("m_Script"))
    p = proj.path_of(sguid)
    if p and p.endswith(".cs"):
        return os.path.splitext(os.path.basename(p))[0]
    if p:
        cls = proj.dll_classes.get(os.path.basename(p), {}).get(sid)
        return cls or "%s#%s" % (os.path.basename(p), sid)
    return "script:%s" % (sguid or sid)


def parse_scene(proj, path):
    docs = {}
    for cid, fid, stripped, typ, body in unity_docs(path):
        docs[fid] = (cid, typ, body)
    gos, tr_of_go, comps = {}, {}, collections.defaultdict(list)
    render, lights = {}, []
    for fid, (cid, typ, body) in docs.items():
        if cid == 1:
            gos[fid] = body
        elif cid in (4, 224):
            go, _ = ref_of(body.get("m_GameObject"))
            tr_of_go[go] = fid
        elif cid == 104:
            render = body
        if cid not in (1, 4, 224):
            go, _ = ref_of(body.get("m_GameObject"))
            if go:
                comps[go].append(fid)

    world = {}

    def world_of(tfid, depth=0):
        if tfid in world:
            return world[tfid]
        cid, typ, t = docs.get(tfid, (0, "", {}))
        lp, lr, ls = vec(t.get("m_LocalPosition")), vec(t.get("m_LocalRotation"), "xyzw", 0.0), vec(t.get("m_LocalScale"), "xyz", 1.0)
        if lr == [0.0, 0.0, 0.0, 0.0]:
            lr = [0.0, 0.0, 0.0, 1.0]
        father, _ = ref_of(t.get("m_Father"))
        if father and father in docs and depth < 200:
            pp, pr, ps = world_of(father, depth + 1)
            scaled = [lp[0] * ps[0], lp[1] * ps[1], lp[2] * ps[2]]
            rp = q_rot(pr, scaled)
            res = ([pp[0] + rp[0], pp[1] + rp[1], pp[2] + rp[2]], q_mul(pr, lr), [ps[0] * ls[0], ps[1] * ls[1], ps[2] * ls[2]])
        else:
            res = (lp, lr, ls)
        world[tfid] = res
        return res

    def path_name(go_fid, depth=0):
        t = docs.get(tr_of_go.get(go_fid, 0), (0, "", {}))[2]
        father, _ = ref_of(t.get("m_Father"))
        name = (gos.get(go_fid) or {}).get("m_Name") or "?"
        if father and depth < 60:
            fgo, _ = ref_of(docs.get(father, (0, "", {}))[2].get("m_GameObject"))
            if fgo in gos:
                return path_name(fgo, depth + 1) + "/" + str(name)
        return str(name)

    names_by_id = {fid: str((g.get("m_Name") or "?")) for fid, g in gos.items()}

    def resolve(v):
        if isinstance(v, dict) and "ref" in v and not v.get("guid"):
            target = v["ref"]
            if target in names_by_id:
                return "obj:" + names_by_id[target]
            c = docs.get(target)
            if c:
                go, _ = ref_of(c[2].get("m_GameObject"))
                if go in names_by_id:
                    return "%s:%s" % (COMPONENT_NAMES.get(c[0], c[1]), names_by_id[go])
            return None if target == 0 else v
        if isinstance(v, dict) and v.get("guid"):
            return "asset:" + (proj.name_of(v["guid"], v.get("ref", 0)) or v["guid"])
        if isinstance(v, dict):
            return {k: resolve(x) for k, x in v.items()}
        if isinstance(v, list):
            return [resolve(x) for x in v]
        return v

    objects = []
    for fid, g in gos.items():
        tfid = tr_of_go.get(fid)
        pos, rot, scl = world_of(tfid) if tfid else ([0, 0, 0], [0, 0, 0, 1], [1, 1, 1])
        o = {"id": fid, "name": str(g.get("m_Name") or "?"), "path": path_name(fid),
             "active": bool(g.get("m_IsActive", 1)), "layer": g.get("m_Layer", 0), "tag": g.get("m_TagString"),
             "static": g.get("m_StaticEditorFlags", 0), "pos": r3(pos), "rot": q_euler(rot), "scale": r3(scl)}
        kinds, scripts = [], []
        for cf in comps.get(fid, []):
            cid, typ, body = docs[cf]
            kind = COMPONENT_NAMES.get(cid, typ)
            if cid == 33:
                mid, mguid = ref_of(body.get("m_Mesh"))
                o["mesh"] = proj.name_of(mguid, mid) or ("scene:%s" % mid if mid else None)
            elif cid in (23, 137):
                o["materials"] = [proj.material(ref_of(m)[1])["name"] if ref_of(m)[1] else None
                                  for m in body.get("m_Materials") or []]
                if cid == 137:
                    mid, mguid = ref_of(body.get("m_Mesh"))
                    o["mesh"] = proj.name_of(mguid, mid)
                if body.get("m_LightmapIndex", 65535) not in (65535, -1, None):
                    o["lightmapped"] = True
            elif cid == 108:
                light = {"type": {0: "spot", 1: "directional", 2: "point", 3: "area"}.get(body.get("m_Type"), body.get("m_Type")),
                         "color": r3(vec(body.get("m_Color"), "rgba", 1.0)), "intensity": body.get("m_Intensity"),
                         "range": body.get("m_Range"), "spot": body.get("m_SpotAngle"),
                         "shadows": (body.get("m_Shadows") or {}).get("m_Type"),
                         "mode": body.get("m_Lightmapping"), "pos": r3(pos), "object": o["name"]}
                o["light"] = light
                lights.append(light)
            elif cid == 114:
                sname = script_name(proj, body)
                fields = {k: simple(v) for k, v in body.items()
                          if (not k.startswith("m_") or k in UI_FIELDS) and k not in ("serializedVersion",)}
                scripts.append({"script": sname, "enabled": bool(body.get("m_Enabled", 1)),
                                "fields": resolve(fields)})
                kind = sname
            elif cid in (65, 135, 136, 64, 143):
                if cid == 65:
                    o.setdefault("colliders", []).append({"box": r3(vec(body.get("m_Size"), "xyz", 1.0)),
                                                          "center": r3(vec(body.get("m_Center"))),
                                                          "trigger": bool(body.get("m_IsTrigger"))})
                else:
                    o.setdefault("colliders", []).append({"type": kind, "trigger": bool(body.get("m_IsTrigger"))})
            elif cid == 82:
                cid2, cguid = ref_of(body.get("m_audioClip"))
                o.setdefault("audio", []).append(proj.name_of(cguid, cid2))
            elif cid == 95:
                cid2, cguid = ref_of(body.get("m_Controller"))
                o["animator"] = proj.name_of(cguid, cid2)
            kinds.append(kind)
        o["components"] = kinds
        if scripts:
            o["scripts"] = scripts
        objects.append(o)
    rs = {}
    if render:
        rs = {"fog": bool(render.get("m_Fog")), "fog_color": r3(vec(render.get("m_FogColor"), "rgba", 0.0)),
              "fog_mode": render.get("m_FogMode"), "fog_density": render.get("m_FogDensity"),
              "fog_start": render.get("m_LinearFogStart"), "fog_end": render.get("m_LinearFogEnd"),
              "ambient_mode": render.get("m_AmbientMode"),
              "ambient_sky": r3(vec(render.get("m_AmbientSkyColor"), "rgba", 0.0)),
              "ambient_equator": r3(vec(render.get("m_AmbientEquatorColor"), "rgba", 0.0)),
              "ambient_ground": r3(vec(render.get("m_AmbientGroundColor"), "rgba", 0.0)),
              "ambient_intensity": render.get("m_AmbientIntensity"),
              "skybox": proj.name_of(ref_of(render.get("m_SkyboxMaterial"))[1])}
    return objects, rs, lights


def build_scenes(root):
    path = os.path.join(root, "ProjectSettings", "EditorBuildSettings.asset")
    out = []
    if os.path.exists(path):
        doc = first_doc(path)
        for s in (doc[4].get("m_Scenes") or []) if doc else []:
            out.append({"path": s.get("path"), "enabled": bool(s.get("enabled", 1))})
    return out


def player_settings(root):
    path = os.path.join(root, "ProjectSettings", "ProjectSettings.asset")
    if not os.path.exists(path):
        return {}
    doc = first_doc(path)
    b = doc[4] if doc else {}
    keys = ("productName", "companyName", "bundleVersion", "defaultScreenOrientation", "m_ActiveColorSpace",
            "AndroidMinSdkVersion", "AndroidTargetSdkVersion", "applicationIdentifier", "scriptingBackend",
            "m_StereoRenderingPath", "defaultScreenWidth", "defaultScreenHeight", "m_RenderingPath",
            "m_MobileRenderingPath", "graphicsJobs", "AndroidTargetArchitectures")
    return {k: b.get(k) for k in keys if k in b}


def contact_sheet(paths, title, out, cols=8, cell=160):
    if not paths:
        return
    try:
        font = ImageFont.load_default(size=13)
    except TypeError:
        font = ImageFont.load_default()
    rows = math.ceil(len(paths) / cols)
    sheet = Image.new("RGB", (cols * cell, rows * (cell + 30) + 34), (24, 24, 26))
    d = ImageDraw.Draw(sheet)
    d.text((8, 8), title, fill=(240, 240, 240), font=font)
    for i, (p, label) in enumerate(paths):
        x, y = (i % cols) * cell, 34 + (i // cols) * (cell + 30)
        try:
            im = Image.open(p)
            w, h = im.size
            im = im.convert("RGBA")
            im.thumbnail((cell - 8, cell - 8))
            bg = Image.new("RGBA", im.size, (90, 90, 96, 255))
            bg.alpha_composite(im)
            sheet.paste(bg.convert("RGB"), (x + 4 + (cell - 8 - im.size[0]) // 2, y + 4 + (cell - 8 - im.size[1]) // 2))
            d.text((x + 4, y + cell - 2), ("%s" % label)[:22], fill=(220, 220, 220), font=font)
            d.text((x + 4, y + cell + 12), "%dx%d" % (w, h), fill=(150, 150, 150), font=font)
        except Exception as e:  # noqa: BLE001
            d.text((x + 4, y + 60), "unreadable", fill=(255, 80, 80), font=font)
            log("thumbnail failed", p, e)
    sheet.save(out, quality=82)


def project_root(path):
    """AssetRipper writes the project into <out>/ExportedProject; accept either folder."""
    for cand in [path, os.path.join(path, "ExportedProject")] + sorted(glob.glob(os.path.join(path, "*"))):
        if os.path.isdir(os.path.join(cand, "Assets")) and os.path.isdir(os.path.join(cand, "ProjectSettings")):
            return cand
    return path


def main():
    root, work, outd = project_root(sys.argv[1]), sys.argv[2], sys.argv[3]
    log("project:", root)
    os.makedirs(os.path.join(outd, "scenes"), exist_ok=True)
    os.makedirs(os.path.join(outd, "textures"), exist_ok=True)
    dll_classes = {}
    rea_path = os.path.join(work, "rea_il2cpp.json")
    if os.path.exists(rea_path):
        try:
            with open(rea_path, encoding="utf-8") as f:
                dll_classes = dll_classes_from_rea(json.load(f))
            with open(os.path.join(outd, "dll_classes.json"), "w", encoding="utf-8") as f:
                json.dump({k: {str(i): c for i, c in v.items()} for k, v in dll_classes.items()
                           if not k.startswith(("mscorlib", "System", "Mono."))}, f, indent=0)
            log("script ids for %d assemblies" % len(dll_classes))
        except Exception as e:  # noqa: BLE001
            log("rea answer not usable:", e)
    proj = Project(root, dll_classes)
    log("assets with guids:", len(proj.guids))

    def jload(p):
        try:
            with open(p, encoding="utf-8") as f:
                return json.load(f)
        except Exception:  # noqa: BLE001
            return {}

    gj, apk = jload(os.path.join(work, "gamejolt.json")), jload(os.path.join(work, "apk_info.json"))
    version_txt = os.path.join(root, "ProjectSettings", "ProjectVersion.txt")
    unity_version = read_text(version_txt).strip() if os.path.exists(version_txt) else apk.get("unity_version")
    ps = player_settings(root)

    # inventory
    by_ext, size_by_ext = collections.Counter(), collections.Counter()
    for dp, _dn, fn in os.walk(os.path.join(root, "Assets")):
        for f in fn:
            if f.endswith(".meta"):
                continue
            ext = os.path.splitext(f)[1].lower() or "(none)"
            by_ext[ext] += 1
            size_by_ext[ext] += os.path.getsize(os.path.join(dp, f))

    order = build_scenes(root)
    scene_files = sorted(glob.glob(os.path.join(root, "Assets", "**", "*.unity"), recursive=True))
    scenes = []
    for sf in scene_files:
        rel = os.path.relpath(sf, root)
        try:
            objects, rs, lights = parse_scene(proj, sf)
        except Exception as e:  # noqa: BLE001
            log("scene failed", rel, e)
            continue
        name = os.path.splitext(os.path.basename(sf))[0]
        meshes = [o for o in objects if o.get("mesh")]
        safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", name)
        with open(os.path.join(outd, "scenes", safe + ".json"), "w", encoding="utf-8") as f:
            json.dump({"scene": rel, "render_settings": rs, "objects": objects}, f, indent=0, separators=(",", ":"))
        idx = next((i for i, s in enumerate(order) if s.get("path") == rel), None)
        scenes.append({"name": name, "file": rel, "safe": safe, "build_index": idx, "objects": len(objects),
                       "meshes": len(meshes), "lights": lights, "render": rs, "data": objects})
        log("scene %s: %d objects, %d meshes, %d lights" % (name, len(objects), len(meshes), len(lights)))

    main_scene = max(scenes, key=lambda s: s["meshes"], default=None)
    if main_scene:
        with open(os.path.join(outd, "main_scene.txt"), "w") as f:
            f.write(main_scene["name"] + "\n")

    # materials used by the scenes, with their textures
    mat_use = collections.Counter()
    for s in scenes:
        for o in s["data"]:
            for m in o.get("materials") or []:
                if m:
                    mat_use[m] += 1
    mats = [m for m in proj.mat_cache.values()]
    with open(os.path.join(outd, "materials.json"), "w", encoding="utf-8") as f:
        json.dump(sorted(mats, key=lambda m: -mat_use.get(m["name"], 0)), f, indent=1)

    # textures: the ones on materials (by use), then the rest (menus, sprites, UI)
    tex_use = collections.Counter()
    for m in mats:
        for t in (m.get("textures") or {}).values():
            if isinstance(t.get("texture"), str) and not re.fullmatch(r"[0-9a-f]{32}", t["texture"]):
                tex_use[t["texture"]] += mat_use.get(m["name"], 0) or 1
    images = [p for p in glob.glob(os.path.join(root, "Assets", "**", "*"), recursive=True)
              if p.lower().endswith((".png", ".jpg", ".jpeg", ".tga", ".exr"))]
    rel_images = {os.path.relpath(p, root): p for p in images}
    used = [(rel_images[t], os.path.splitext(os.path.basename(t))[0]) for t, _ in tex_use.most_common() if t in rel_images]
    used_set = {p for p, _ in used}
    rest = sorted((p for p in images if p not in used_set), key=lambda p: -os.path.getsize(p))
    sheets = []
    for i in range(0, min(len(used), 192), 48):
        out = os.path.join(outd, "textures", "materials_%d.jpg" % (i // 48 + 1))
        contact_sheet(used[i:i + 48], "Textures on the game's materials (most used first) %d-%d" % (i + 1, min(i + 48, len(used))), out)
        sheets.append(out)
    for i in range(0, min(len(rest), 96), 48):
        out = os.path.join(outd, "textures", "other_%d.jpg" % (i // 48 + 1))
        contact_sheet([(p, os.path.splitext(os.path.basename(p))[0]) for p in rest[i:i + 48]],
                      "Other images (menus, UI, sprites), biggest first %d-%d" % (i + 1, min(i + 48, len(rest))), out)
        sheets.append(out)

    # the game's own scripts
    code_out = os.path.join(outd, "code")
    os.makedirs(code_out, exist_ok=True)
    script_dirs = [d for d in glob.glob(os.path.join(root, "Assets", "Scripts", "*")) if os.path.isdir(d)]
    game_scripts = []
    for d in script_dirs:
        base = os.path.basename(d)
        if base.lower().startswith("assembly-csharp"):
            dest = os.path.join(code_out, base)
            shutil.copytree(d, dest, dirs_exist_ok=True, ignore=shutil.ignore_patterns("*.meta", "*.asmdef"))
            game_scripts += [os.path.relpath(p, code_out) for p in glob.glob(os.path.join(dest, "**", "*.cs"), recursive=True)]
    other_assemblies = sorted(os.path.basename(d) for d in script_dirs if not os.path.basename(d).lower().startswith("assembly-csharp"))

    audio = sorted(os.path.basename(p) for p in glob.glob(os.path.join(root, "Assets", "**", "*"), recursive=True)
                   if p.lower().endswith((".ogg", ".wav", ".mp3", ".m4a", ".aif")))
    fonts = sorted(os.path.basename(p) for p in glob.glob(os.path.join(root, "Assets", "**", "*"), recursive=True)
                   if p.lower().endswith((".ttf", ".otf", ".fontsettings")))
    manifest = os.path.join(root, "Packages", "manifest.json")
    packages = sorted((jload(manifest).get("dependencies") or {}).keys()) if os.path.exists(manifest) else []

    # ---- inventory: plugin DLLs, shaders, MonoBehaviour assets, prefabs, animation, tags and layers ----
    def rels(pattern):
        return sorted(os.path.relpath(p, root) for p in glob.glob(os.path.join(root, pattern), recursive=True))

    plugins = rels("Assets/**/*.dll")
    shaders = []
    for rp in rels("Assets/**/*.shader"):
        m = re.search(r'Shader\s+"([^"]+)"', read_text(os.path.join(root, rp))[:2000])
        shaders.append({"file": rp, "name": m.group(1) if m else None, "guid": next((g for g, q in proj.guids.items() if q == rp), None)})
    mono_assets = []
    for rp in rels("Assets/**/*.asset"):
        if rp.startswith(("Assets/Mesh/", "Assets/NavMeshData/", "Assets/AnimationClip/")) or os.path.getsize(os.path.join(root, rp)) > 3_000_000:
            continue
        d = first_doc(os.path.join(root, rp))
        if d and d[0] == 114:
            mono_assets.append({"file": rp, "name": d[4].get("m_Name"), "script": script_name(proj, d[4])})
    prefabs = []
    for rp in rels("Assets/**/*.prefab"):
        try:
            docs = list(unity_docs(os.path.join(root, rp)))
        except Exception:  # noqa: BLE001
            continue
        names = [b.get("m_Name") for cid, _f, _s, _t, b in docs if cid == 1]
        scr = sorted({script_name(proj, b) for cid, _f, _s, _t, b in docs if cid == 114})
        prefabs.append({"file": rp, "objects": len(names), "root": names[0] if names else None, "scripts": scr})
    tags = {}
    tm = os.path.join(root, "ProjectSettings", "TagManager.asset")
    if os.path.exists(tm):
        d = first_doc(tm)
        if d:
            tags = {"tags": d[4].get("tags"), "layers": [(i, l) for i, l in enumerate(d[4].get("layers") or []) if l]}
    inventory = {"plugins": plugins, "shaders": shaders, "mono_assets": mono_assets, "prefabs": prefabs,
                 "controllers": rels("Assets/**/*.controller"), "animations": rels("Assets/**/*.anim"),
                 "timelines": rels("Assets/**/*.playable"), "tags_layers": tags,
                 "sprites": len(rels("Assets/Sprite/**/*")), "texture2d_raw": rels("Assets/**/*.texture2d")[:200]}
    with open(os.path.join(outd, "inventory.json"), "w", encoding="utf-8") as f:
        json.dump(inventory, f, indent=1)

    samples = os.path.join(outd, "samples")
    os.makedirs(samples, exist_ok=True)

    def sample(rp, limit=400_000):
        src = os.path.join(root, rp)
        if os.path.exists(src):
            dst = os.path.join(samples, rp.replace("/", "__"))
            with open(src, "rb") as fi, open(dst, "wb") as fo:
                fo.write(fi.read(limit))
    for rp in ("ProjectSettings/TagManager.asset", "ProjectSettings/GraphicsSettings.asset",
               "ProjectSettings/QualitySettings.asset", "ProjectSettings/EditorBuildSettings.asset",
               "ProjectSettings/InputManager.asset", "ProjectSettings/DynamicsManager.asset", "Packages/manifest.json"):
        sample(rp)
    for name, _n in mat_use.most_common(3):
        m = next((x for x in mats if x["name"] == name), None)
        if m and m.get("path"):
            sample(m["path"])
    if shaders:
        sample(shaders[0]["file"], 6000)
    for a in mono_assets:
        if any(k in str(a["script"]) for k in ("UniversalRenderPipelineAsset", "UniversalRendererData", "VolumeProfile")):
            sample(a["file"], 120_000)
    for pf in prefabs:
        if any(k in " ".join(pf["scripts"]) for k in ("GrannyAI", "Nosferatu")):
            sample(pf["file"])

    # ---- report.md ----
    L = ["# Granny 4 End Game - what is inside", ""]
    if gj:
        L += ["**Game Jolt:** %s by %s (%s) - %s" % (gj.get("title"), gj.get("developer"),
                                                     gj.get("developer_url") or "", gj.get("url")),
              "**File:** %s (version %s)" % ((gj.get("build") or {}).get("file"), (gj.get("build") or {}).get("version")), ""]
    L += ["## APK", "", "| | |", "|---|---|"]
    for k in ("label", "package", "versionName", "versionCode", "minSdk", "targetSdk", "abis", "backend", "unity_version"):
        if apk.get(k):
            L.append("| %s | %s |" % (k, apk[k]))
    L += ["| exported project | %s |" % unity_version.replace("\n", " ") if unity_version else "", ""]
    if ps:
        L += ["**Player settings:** " + ", ".join("%s=%s" % kv for kv in ps.items()), ""]
    if packages:
        L += ["**Packages:** " + ", ".join(packages), ""]
    L += ["## Scenes", "", "| build # | scene | objects | meshes | lights |", "|---|---|---|---|---|"]
    for s in sorted(scenes, key=lambda s: (s["build_index"] is None, s["build_index"] or 0, s["name"])):
        L.append("| %s | %s%s | %d | %d | %d |" % ("" if s["build_index"] is None else s["build_index"], s["name"],
                                                   " **(house)**" if s is main_scene else "", s["objects"], s["meshes"], len(s["lights"])))
    L.append("")
    for s in scenes:
        data = s["data"]
        if not data:
            continue
        L += ["## Scene: %s" % s["name"], ""]
        if s["render"]:
            r = s["render"]
            L.append("- fog: %s (mode %s, colour %s, density %s, linear %s-%s)" % (r["fog"], r["fog_mode"], r["fog_color"],
                                                                                 r["fog_density"], r["fog_start"], r["fog_end"]))
            L.append("- ambient: mode %s, sky %s, equator %s, ground %s, intensity %s, skybox %s" % (
                r["ambient_mode"], r["ambient_sky"], r["ambient_equator"], r["ambient_ground"], r["ambient_intensity"], r["skybox"]))
        meshes = [o for o in data if o.get("mesh") and o["active"]]
        if meshes:
            xs = sorted(o["pos"][0] for o in meshes)
            ys = sorted(o["pos"][1] for o in meshes)
            zs = sorted(o["pos"][2] for o in meshes)
            q = lambda a, f: a[min(len(a) - 1, int(f * len(a)))]  # noqa: E731
            L.append("- layout (5-95%% of mesh positions): x %.1f..%.1f, y %.1f..%.1f, z %.1f..%.1f (metres)" % (
                q(xs, .05), q(xs, .95), q(ys, .05), q(ys, .95), q(zs, .05), q(zs, .95)))
            lm = sum(1 for o in meshes if o.get("lightmapped"))
            L.append("- %d active meshes, %d use baked lightmaps" % (len(meshes), lm))
        if s["lights"]:
            kinds = collections.Counter(l["type"] for l in s["lights"])
            L.append("- lights: " + ", ".join("%d %s" % (n, k) for k, n in kinds.items()))
            for l in s["lights"][:12]:
                L.append("  - %s `%s` colour %s intensity %s range %s shadows %s at %s" % (
                    l["type"], l["object"], l["color"][:3], l["intensity"], l["range"], l["shadows"], l["pos"]))
        scr = collections.defaultdict(list)
        for o in data:
            for sc in o.get("scripts") or []:
                scr[sc["script"]].append(o["name"])
        if scr:
            L.append("- scripts on objects:")
            for k, objs in sorted(scr.items(), key=lambda kv: -len(kv[1]))[:60]:
                ex = ", ".join(sorted(set(objs))[:6])
                L.append("  - `%s` x%d (%s)" % (k, len(objs), ex))
        names = collections.Counter(re.sub(r"\s*\(\d+\)$", "", o["name"]) for o in data)
        L.append("- most common object names: " + ", ".join("%s x%d" % kv for kv in names.most_common(40)))
        roots = [o for o in data if "/" not in o["path"]]
        L.append("- top level: " + ", ".join(o["name"] for o in roots[:60]))
        L.append("")
    L += ["## Materials", "", "%d materials; most used:" % len(mats), ""]
    for name, n in mat_use.most_common(40):
        m = next((x for x in mats if x["name"] == name), {})
        main = (m.get("textures") or {}).get("_MainTex") or (m.get("textures") or {}).get("_BaseMap") or {}
        L.append("- `%s` x%d - shader %s - texture %s - colour %s" % (
            name, n, m.get("shader"), os.path.basename(str(main.get("texture", "-"))), (m.get("colors") or {}).get("_Color")))
    L += ["", "## Textures", ""]
    L += ["![%s](textures/%s)" % (os.path.basename(p), os.path.basename(p)) for p in sheets]
    L += ["", "## Code", "", "Game scripts (%d): %s" % (len(game_scripts), ", ".join(sorted(game_scripts)[:200])), "",
          "Other assemblies: " + ", ".join(other_assemblies[:60]), ""]
    L += ["## Sounds (%d)" % len(audio), "", ", ".join(audio[:300]), "", "## Fonts", "", ", ".join(fonts) or "-", ""]
    L += ["## Project inventory", "", "**Plugin DLLs:** " + ", ".join(os.path.basename(p) for p in plugins), "",
          "**Shaders (%d):** " % len(shaders) + ", ".join(str(x["name"]) for x in shaders), "",
          "**MonoBehaviour assets:**", ""]
    L += ["- `%s` - %s" % (a["name"], a["script"]) for a in mono_assets[:80]]
    L += ["", "**Prefabs:**", ""]
    L += ["- `%s` (%d objects) - %s" % (os.path.basename(p["file"]), p["objects"], ", ".join(p["scripts"])[:400]) for p in prefabs]
    L += ["", "**Animator controllers:** " + ", ".join(os.path.basename(p) for p in inventory["controllers"]),
          "", "**Animations:** " + ", ".join(os.path.basename(p) for p in inventory["animations"]),
          "", "**Timelines:** " + ", ".join(os.path.basename(p) for p in inventory["timelines"]),
          "", "**Tags:** %s" % (tags.get("tags"),), "", "**Layers:** %s" % (tags.get("layers"),), ""]
    L += ["## Files by type", "", "| type | files | MB |", "|---|---|---|"]
    for ext, n in by_ext.most_common(30):
        L.append("| %s | %d | %.1f |" % (ext, n, size_by_ext[ext] / 1e6))
    L.append("")
    with open(os.path.join(outd, "report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(x for x in L if x is not None))
    info = {"gamejolt": gj, "apk": apk, "unity_version": unity_version, "player_settings": ps, "packages": packages,
            "scenes": [{k: v for k, v in s.items() if k != "data"} for s in scenes],
            "main_scene": main_scene["name"] if main_scene else None, "audio": audio, "fonts": fonts,
            "game_scripts": game_scripts, "other_assemblies": other_assemblies}
    with open(os.path.join(outd, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, indent=1)
    log("report written: %d scenes, %d materials, %d textures, %d scripts" % (len(scenes), len(mats), len(images), len(game_scripts)))


if __name__ == "__main__":
    main()

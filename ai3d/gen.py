"""Chaya - AI 3D models from free Hugging Face Spaces (no account): a product-style picture of each object from
FLUX.1-schnell (Apache-2.0), then a textured 3D model from TRELLIS (MIT) - Hunyuan3D-2 as a second choice.

    python3 gen.py <models.json> <out dir> [names...]      (--probe: print the Spaces' APIs and stop)
"""
import json
import os
import shutil
import sys
import time
import traceback

from gradio_client import Client, handle_file

IMG_SPACES = ["black-forest-labs/FLUX.1-schnell"]
TRELLIS_SPACES = ["trellis-community/TRELLIS", "JeffreyXiang/TRELLIS"]
HUNYUAN_SPACES = ["tencent/Hunyuan3D-2"]
STYLE = (", a single object, the whole object in view with empty space around it, three-quarter view from slightly above, "
         "centered, isolated on a plain white background, soft even studio light, photorealistic product photo, real materials, "
         "sharp detail")


def endpoints(client):
    try:
        return client.view_api(return_format="dict", print_info=False)["named_endpoints"]
    except Exception:   # noqa: BLE001
        return {}


def call(client, api, eps, **kw):
    """predict() with the keywords this endpoint knows, defaults for the rest."""
    ep = eps.get(api)
    if ep is None:
        raise RuntimeError("no endpoint %s (has %s)" % (api, list(eps)))
    args = {}
    for p in ep["parameters"]:
        n = p.get("parameter_name")
        if n in kw:
            args[n] = kw[n]
        elif p.get("parameter_has_default"):
            args[n] = p.get("parameter_default")
    return client.predict(api_name=api, **args)


def first_file(x):
    if isinstance(x, str) and os.path.exists(x):
        return x
    if isinstance(x, dict):
        for k in ("value", "path", "name"):
            if k in x and isinstance(x[k], str) and os.path.exists(x[k]):
                return x[k]
    if isinstance(x, (list, tuple)):
        for y in x:
            f = first_file(y)
            if f:
                return f
    return None


def find_ext(x, exts):
    if isinstance(x, str) and os.path.exists(x) and x.lower().endswith(exts):
        return x
    if isinstance(x, dict):
        for v in x.values():
            f = find_ext(v, exts)
            if f:
                return f
    if isinstance(x, (list, tuple)):
        for y in x:
            f = find_ext(y, exts)
            if f:
                return f
    return None


def picture(prompt, seed, out_png):
    last = None
    for sp in IMG_SPACES:
        try:
            c = Client(sp, verbose=False)
            eps = endpoints(c)
            api = "/infer" if "/infer" in eps else list(eps)[0]
            r = call(c, api, eps, prompt=prompt + STYLE, seed=seed, randomize_seed=False, width=1024, height=1024,
                     num_inference_steps=4)
            f = first_file(r)
            if f:
                shutil.copy(f, out_png)
                return out_png
            last = "no image in %r" % (r,)
        except Exception as e:   # noqa: BLE001
            last = repr(e)
            print("   picture via %s failed: %s" % (sp, last[:300]))
    raise RuntimeError(last)


def trellis(png, out_glb, seed):
    last = None
    for sp in TRELLIS_SPACES:
        try:
            c = Client(sp, verbose=False)
            eps = endpoints(c)
            if "/start_session" in eps:
                call(c, "/start_session", eps)
            img = png
            if "/preprocess_image" in eps:
                img = first_file(call(c, "/preprocess_image", eps, image=handle_file(png))) or png
            kw = dict(image=handle_file(img), multiimages=[], is_multiimage=False, seed=seed, ss_guidance_strength=7.5,
                      ss_sampling_steps=12, slat_guidance_strength=3.0, slat_sampling_steps=12, multiimage_algo="stochastic",
                      mesh_simplify=0.9, texture_size=1024)
            if "/generate_and_extract_glb" in eps:
                r = call(c, "/generate_and_extract_glb", eps, **kw)
            else:
                call(c, "/image_to_3d", eps, **kw)
                r = call(c, "/extract_glb", eps, **kw)
            f = find_ext(r, (".glb",))
            if f:
                shutil.copy(f, out_glb)
                return sp
            last = "no glb in %r" % (r,)
        except Exception as e:   # noqa: BLE001
            last = repr(e)
            print("   TRELLIS via %s failed: %s" % (sp, last[:400]))
    raise RuntimeError(last)


def hunyuan(png, prompt, out_glb, seed):
    last = None
    for sp in HUNYUAN_SPACES:
        try:
            c = Client(sp, verbose=False)
            eps = endpoints(c)
            api = "/generation_all" if "/generation_all" in eps else "/shape_generation"
            r = call(c, api, eps, caption=None, image=handle_file(png), steps=30, guidance_scale=5.0, seed=seed,
                     octree_resolution=256, check_box_rembg=True, num_chunks=8000, randomize_seed=False)
            files = [x for x in (r if isinstance(r, (list, tuple)) else [r])]
            glbs = [first_file(x) for x in files]
            glbs = [g for g in glbs if g and g.endswith((".glb", ".obj", ".ply"))]
            if glbs:
                shutil.copy(glbs[-1], out_glb)          # the textured one comes last
                return sp
            last = "no mesh in %r" % (r,)
        except Exception as e:   # noqa: BLE001
            last = repr(e)
            print("   Hunyuan3D via %s failed: %s" % (sp, last[:400]))
    raise RuntimeError(last)


def main():
    if "--probe" in sys.argv:
        for sp in IMG_SPACES + TRELLIS_SPACES + HUNYUAN_SPACES:
            try:
                c = Client(sp, verbose=False)
                print("=====", sp)
                for k, v in endpoints(c).items():
                    print("  ", k, [(p.get("parameter_name"), p.get("parameter_default")) for p in v["parameters"]])
            except Exception as e:   # noqa: BLE001
                print("XXXXX", sp, repr(e)[:300])
    models = json.load(open(sys.argv[1]))
    out = sys.argv[2]
    names = [a for a in sys.argv[3:] if not a.startswith("--")]
    os.makedirs(out, exist_ok=True)
    report = {}
    for name, m in models.items():
        if names and name not in names:
            continue
        t0 = time.time()
        png, glb = os.path.join(out, name + ".png"), os.path.join(out, name + ".glb")
        print("==> %s: %s" % (name, m["prompt"]))
        try:
            picture(m["prompt"], int(m.get("seed", 7)), png)
            print("   picture ok (%.0fs)" % (time.time() - t0))
        except Exception as e:   # noqa: BLE001
            report[name] = "picture failed: " + str(e)[:200]
            continue
        if "--pictures-only" in sys.argv:
            report[name] = "picture ok"
            continue
        try:
            by = trellis(png, glb, int(m.get("seed", 7)))
        except Exception:   # noqa: BLE001
            try:
                by = hunyuan(png, m["prompt"], glb, int(m.get("seed", 7)))
            except Exception as e:   # noqa: BLE001
                traceback.print_exc()
                report[name] = "3d failed: " + str(e)[:200]
                continue
        report[name] = "ok via %s, %.0f KB, %.0fs" % (by, os.path.getsize(glb) / 1024, time.time() - t0)
        print("   " + report[name])
    json.dump(report, open(os.path.join(out, "report_%s.json" % (names[0] if names else "all")), "w"), indent=1)
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()

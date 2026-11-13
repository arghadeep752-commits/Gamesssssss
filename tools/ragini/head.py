"""Ragini's head: a gaunt woman's skull with a dropped, screaming jaw, wide staring eyes, a long hooked nose,
hollow cheeks and temples. Sculpted with signed distance fields (tools/common/sdf.py).
The eyes and the teeth are separate meshes (their own materials)."""
import math

import numpy as np

from sdf import Shape, frame, rot_x, rot_y

V3 = lambda *a: np.array(a, float)      # noqa: E731
H = "head"
J = "jaw"
EYE_Z = 1.6025
EYE_X = 0.030
EYE_Y = -0.0745
EYE_R = 0.0118


def build_head(b):
    jaw_R = rot_x(math.radians(12.0))
    # ---------------------------------------------------------------- skull and face masses
    b.ell(V3(0, 0.018, 1.618), V3(0.0705, 0.090, 0.091), H, k=0.03)                    # cranium
    b.ell(V3(0, 0.055, 1.600), V3(0.061, 0.050, 0.068), H, k=0.03)                     # back of the skull
    b.ell(V3(0, -0.030, 1.642), V3(0.062, 0.053, 0.056), H, k=0.03)                    # forehead
    b.ell(V3(0, -0.047, 1.568), V3(0.047, 0.045, 0.050), H, k=0.03)                    # mid face
    b.ell(V3(0, -0.066, 1.6225), V3(0.050, 0.014, 0.010), H, k=0.02, tag="brow")
    for s in (1, -1):
        b.ell(V3(s * 0.030, -0.0715, 1.6245), V3(0.018, 0.008, 0.006), H, k=0.012, R=frame([s * 0.25, -1, 0], [0, 0, 1]), tag="brow")
        b.ell(V3(s * 0.048, -0.0575, 1.584), V3(0.020, 0.016, 0.0115), H, k=0.02,
              R=frame([s * 0.45, -1, 0.05], [0, 0, 1]), tag="cheekbone")
    # ---------------------------------------------------------------- lower jaw (dropped open)
    b.ell(V3(0, -0.022, 1.510), V3(0.035, 0.042, 0.029), J, k=0.018, R=jaw_R)
    for s in (1, -1):
        b.ell(V3(s * 0.044, 0.002, 1.526), V3(0.0085, 0.015, 0.018), J, k=0.015)          # angle of the jaw
        b.cone(V3(s * 0.044, 0.004, 1.518), V3(s * 0.014, -0.057, 1.474), 0.0080, 0.0090, J, k=0.014)
    b.ell(V3(0, -0.061, 1.468), V3(0.0165, 0.013, 0.014), J, k=0.012, tag="chin")
    b.ell(V3(0, -0.0565, 1.478), V3(0.017, 0.0110, 0.011), J, k=0.012)
    # ---------------------------------------------------------------- nose: long, thin, a little hooked
    b.cone(V3(0, -0.0780, 1.609), V3(0, -0.0955, 1.5715), 0.0050, 0.0068, H, k=0.01, tag="nose")
    b.ell(V3(0, -0.0905, 1.592), V3(0.0058, 0.0042, 0.006), H, k=0.006, tag="nose")      # the hook
    b.sph(V3(0, -0.0972, 1.5668), 0.0078, H, k=0.008, tag="nose")
    for s in (1, -1):
        b.ell(V3(s * 0.0100, -0.0885, 1.5615), V3(0.0066, 0.0078, 0.0058), H, k=0.008, tag="nose")
    b.ell(V3(0, -0.0775, 1.5385), V3(0.022, 0.012, 0.0135), H, k=0.015)                  # above the upper lip
    # ---------------------------------------------------------------- ears (mostly under the hair)
    for s in (1, -1):
        b.ell(V3(s * 0.0725, 0.008, 1.585), V3(0.018, 0.028, 0.008), H, k=0.008, R=frame([s, 0.2, 0], [0, -0.3, 1]))
    # ---------------------------------------------------------------- carving
    for s in (1, -1):
        b.ell(V3(s * 0.0545, -0.071, 1.546), V3(0.017, 0.019, 0.024), H, k=0.03, op="sub")            # hollow cheeks
        b.ell(V3(s * 0.0725, -0.030, 1.622), V3(0.009, 0.018, 0.019), H, k=0.02, op="sub")            # sunken temples
        b.ell(V3(s * EYE_X, -0.082, 1.6035), V3(0.0195, 0.017, 0.0148), H, k=0.012, op="sub")         # eye sockets
        b.ell(V3(s * 0.0062, -0.0955, 1.5585), V3(0.0032, 0.0038, 0.0022), H, k=0.002, op="sub")      # nostrils
        b.sph(V3(s * 0.080, 0.004, 1.581), 0.0068, H, k=0.004, op="sub")                              # ear bowl
    b.ell(V3(0, -0.066, 1.508), V3(0.0165, 0.050, 0.022), H, k=0.008, op="sub")                        # the open mouth
    # ---------------------------------------------------------------- lids: a wide, unblinking stare
    for s in (1, -1):
        b.ell(V3(s * EYE_X, -0.0750, 1.6178), V3(0.0145, 0.0112, 0.0074), H, k=0.005,
              R=frame([s * 0.12, -1, 0.15], [0, 0, 1]), tag="lid")
        b.ell(V3(s * EYE_X, -0.0752, 1.5920), V3(0.0130, 0.0102, 0.0046), H, k=0.004,
              R=frame([s * 0.12, -1, -0.1], [0, 0, 1]), tag="lid")
        b.marks["eye." + ("L" if s > 0 else "R")] = V3(s * EYE_X, EYE_Y, EYE_Z)
    # ---------------------------------------------------------------- lips stretched around the scream
    b.ell(V3(0, -0.0855, 1.5315), V3(0.010, 0.0055, 0.0038), H, k=0.005, tag="lip")
    b.ell(V3(0, -0.0708, 1.4862), V3(0.0100, 0.0046, 0.0031), J, k=0.006, tag="lip")
    for s in (1, -1):
        b.ell(V3(s * 0.0115, -0.0835, 1.5290), V3(0.0092, 0.0050, 0.0034), H, k=0.005, R=rot_y(s * 0.30), tag="lip")
        b.ell(V3(s * 0.0118, -0.0700, 1.4882), V3(0.0080, 0.0044, 0.0028), J, k=0.006, R=rot_y(-s * 0.30), tag="lip")
        b.sph(V3(s * 0.0185, -0.0752, 1.5085), 0.0030, H, k=0.006, tag="lip")
    b.ell(V3(0, -0.064, 1.508), V3(0.0145, 0.050, 0.0175), H, k=0.003, op="sub")                        # keep it open
    b.ell(V3(0, -0.046, 1.4905), V3(0.0130, 0.022, 0.0052), J, k=0.006, tag="tongue")
    b.marks["mouth"] = V3(0, -0.086, 1.508)
    b.marks["head_top"] = V3(0, 0.018, 1.709)

    # ---------------------------------------------------------------- teeth (separate mesh): yellowed, the canines long
    rng = np.random.default_rng(13)
    for row, (zc, bone, sign) in enumerate(((1.5305, H, -1), (1.4885, J, 1))):
        n = 10
        for i in range(n):
            u = (i + 0.5) / n * 2 - 1
            ang = u * 1.3
            x = 0.0165 * math.sin(ang)
            y = (-0.0780 if row == 0 else -0.0655) + 0.0125 * (1 - math.cos(ang))
            canine = abs(abs(u) - 0.5) < 0.11
            L = (0.0125 if canine else 0.0078 + 0.0016 * rng.random()) * (1.0 if row == 0 else 0.8)
            root = V3(x, y, zc - sign * 0.002)
            tip = root + V3(0.0004 * rng.standard_normal(), -0.001, sign * L)
            if canine:
                b.cone(root, tip, 0.0030, 0.0006, bone, k=0.0015, group="teeth")
            else:
                Rt = frame(tip - root, [x, -0.03, 0])
                b.ell((root + tip) / 2, V3(0.0032, 0.0016, L * 0.55), bone, k=0.0015, R=Rt, group="teeth")
    # ---------------------------------------------------------------- eyes (separate mesh)
    for s in (1, -1):
        b.eyes.append(Shape("sphere", op="add", k=0.0, bone=H, c=V3(s * EYE_X, EYE_Y, EYE_Z), r=EYE_R))

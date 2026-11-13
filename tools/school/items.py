"""The things you pick up, modelled at real size (numpy Geo, origin at the object's centre, lying flat):
the claw hammer, the main door key, the office key and the store room key (each with its cardboard tag)."""
import math

import numpy as np

from geo import Geo, rot_x, rot_y, rot_z


def hammer():
    """A carpenter's claw hammer: hardwood handle, forged steel head with a round striking face and a split claw."""
    g = Geo("item_hammer")
    # handle along +x, slightly oval and swelling towards the grip end
    prof = [(0.0, -0.16), (0.013, -0.16), (0.016, -0.15), (0.0165, -0.09), (0.0145, 0.0), (0.0125, 0.08), (0.012, 0.13),
            (0.0, 0.135)]
    g.lathe(prof, (0, 0, 0), "wood_handle", seg=14, axis=rot_y(90))
    for i in range(len(g.V)):
        v = g.V[i]
        g.V[i] = np.array([v[0], v[1] * 1.25, v[2]])
    # head at the +x end, across the handle (along y)
    hx = 0.145
    g.box((hx, 0.0, 0.0), (0.034, 0.05, 0.028), "steel")
    g.cyl((hx, -0.025, 0.0), (hx, -0.06, 0.0), 0.0135, "steel", seg=16, r1=0.0145)
    g.cyl((hx, -0.06, 0.0), (hx, -0.068, 0.0), 0.0145, "steel_face", seg=16, r1=0.0135)
    # the claw: two tapering, curving tines
    for s in (-1, 1):
        prev = np.array([hx, 0.025, s * 0.006])
        for k in range(6):
            t = (k + 1) / 6
            ang = t * 0.9
            p = np.array([hx - 0.035 * (1 - math.cos(ang)) * 0.6, 0.025 + 0.075 * math.sin(ang), s * (0.006 + 0.004 * t)])
            g.cyl(prev, p, 0.0085 * (1 - 0.6 * (t - 1 / 6)), "steel", seg=8, r1=0.0085 * (1 - 0.6 * t))
            prev = p
    g.box((hx + 0.018, 0.0, 0.0), (0.004, 0.022, 0.016), "wood_handle")      # wedge in the eye
    return g


def _key(name, length, bow_r, bit_w, mat, tag_mat=None, ornate=False):
    g = Geo(name)
    # bow (ring), shank along +x, bit at the end
    bowc = np.array([-length / 2 + bow_r, 0, 0])
    seg = 20
    for k in range(seg):
        a0 = 2 * math.pi * k / seg
        a1 = 2 * math.pi * (k + 1) / seg
        p0 = bowc + np.array([math.cos(a0) * bow_r, math.sin(a0) * bow_r, 0])
        p1 = bowc + np.array([math.cos(a1) * bow_r, math.sin(a1) * bow_r, 0])
        g.cyl(p0, p1, bow_r * 0.22, mat, seg=8)
    if ornate:
        for k in range(6):
            a = 2 * math.pi * k / 6
            p = bowc + np.array([math.cos(a) * bow_r * 1.25, math.sin(a) * bow_r * 1.25, 0])
            g.cyl(p - np.array([0, 0, 0.002]), p + np.array([0, 0, 0.002]), bow_r * 0.22, mat, seg=8)
    s0 = bowc + np.array([bow_r * 1.1, 0, 0])
    s1 = np.array([length / 2, 0, 0])
    g.cyl(s0, s1, bow_r * 0.2, mat, seg=10)
    g.cyl(s0, s0 + np.array([0.008, 0, 0]), bow_r * 0.3, mat, seg=10)
    bx = length / 2 - bit_w * 0.7
    g.box((bx, -bit_w * 0.55, 0), (bit_w, bit_w * 1.1, bow_r * 0.35), mat)
    g.box((bx - bit_w * 0.2, -bit_w * 1.2, 0), (bit_w * 0.35, bit_w * 0.5, bow_r * 0.35), mat)
    if tag_mat:
        # a cardboard tag on a loop of string through the bow
        tg = Geo()
        tg.box((0, 0, 0), (0.045, 0.026, 0.0012), tag_mat)
        tg.transform(R=rot_z(-35), T=bowc + np.array([-bow_r - 0.03, -0.022, 0]))
        g.merge(tg)
        g.cyl(bowc + np.array([-bow_r, 0, 0]), bowc + np.array([-bow_r - 0.015, -0.01, 0]), 0.0008, "string", seg=4)
    return g


def keys():
    return {
        "item_main_key": _key("item_main_key", 0.125, 0.017, 0.016, "iron_old", ornate=True),
        "item_office_key": _key("item_office_key", 0.062, 0.009, 0.009, "brass", tag_mat="tag_white"),
        "item_store_key": _key("item_store_key", 0.07, 0.01, 0.01, "iron_old", tag_mat="tag_yellow"),
    }


def all_items():
    out = {"item_hammer": hammer()}
    out.update(keys())
    return out

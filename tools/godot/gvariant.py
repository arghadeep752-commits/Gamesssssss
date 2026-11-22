"""Godot 4 binary Variant encoder (the format of bytes_to_var / FileAccess.get_var), so the Python tools can hand
meshes, arrays and tables straight to the game without any parsing in GDScript.

    encode(value) -> bytes

Values: None, bool, int, float, str, list/tuple (Array), dict (Dictionary) and the typed wrappers below for the
packed arrays (numpy arrays inside).
"""
import struct

import numpy as np

NIL, BOOL, INT, FLOAT, STRING = 0, 1, 2, 3, 4
DICTIONARY, ARRAY = 27, 28
PACKED_BYTE, PACKED_INT32, PACKED_INT64, PACKED_FLOAT32 = 29, 30, 31, 32
PACKED_STRING, PACKED_VECTOR2, PACKED_VECTOR3, PACKED_COLOR = 34, 35, 36, 37
FLAG_64 = 1 << 16


class Packed:
    """A numpy array that goes out as one of Godot's packed arrays."""

    def __init__(self, kind, data):
        self.kind = kind
        self.data = data


def V3(a):
    return Packed(PACKED_VECTOR3, np.ascontiguousarray(np.asarray(a, "<f4").reshape(-1, 3)))


def V2(a):
    return Packed(PACKED_VECTOR2, np.ascontiguousarray(np.asarray(a, "<f4").reshape(-1, 2)))


def COLORS(a):
    return Packed(PACKED_COLOR, np.ascontiguousarray(np.asarray(a, "<f4").reshape(-1, 4)))


def I32(a):
    return Packed(PACKED_INT32, np.ascontiguousarray(np.asarray(a, "<i4").reshape(-1)))


def F32(a):
    return Packed(PACKED_FLOAT32, np.ascontiguousarray(np.asarray(a, "<f4").reshape(-1)))


def BYTES(a):
    return Packed(PACKED_BYTE, np.ascontiguousarray(np.asarray(a, np.uint8).reshape(-1)))


def _pad4(b):
    return b + b"\0" * ((4 - len(b) % 4) % 4)


def encode(v):
    out = []
    _enc(v, out)
    return b"".join(out)


def _enc(v, out):
    if v is None:
        out.append(struct.pack("<I", NIL))
    elif isinstance(v, bool):
        out.append(struct.pack("<II", BOOL, 1 if v else 0))
    elif isinstance(v, (int, np.integer)):
        v = int(v)
        if -2 ** 31 <= v < 2 ** 31:
            out.append(struct.pack("<Ii", INT, v))
        else:
            out.append(struct.pack("<Iq", INT | FLAG_64, v))
    elif isinstance(v, (float, np.floating)):
        out.append(struct.pack("<If", FLOAT, float(v)))
    elif isinstance(v, str):
        b = v.encode("utf-8")
        out.append(struct.pack("<II", STRING, len(b)) + _pad4(b))
    elif isinstance(v, Packed):
        d = v.data
        if v.kind == PACKED_BYTE:
            out.append(struct.pack("<II", PACKED_BYTE, d.size) + _pad4(d.tobytes()))
        else:
            out.append(struct.pack("<II", v.kind, d.shape[0]) + d.tobytes())
    elif isinstance(v, dict):
        out.append(struct.pack("<II", DICTIONARY, len(v)))
        for k, x in v.items():
            _enc(k, out)
            _enc(x, out)
    elif isinstance(v, (list, tuple)):
        out.append(struct.pack("<II", ARRAY, len(v)))
        for x in v:
            _enc(x, out)
    else:
        raise TypeError("can't encode %r" % type(v))

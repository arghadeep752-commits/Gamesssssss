"""Unity id helpers shared by the extraction report and the Unity project preparation.

script_file_id(namespace, name): the fileID Unity gives a MonoBehaviour class inside a compiled assembly
(MD4 of "s\\0\\0\\0" + namespace + name, first 4 bytes little-endian), the same algorithm AssetRipper uses.
"""
import struct


def md4(data: bytes) -> bytes:
    def f(x, y, z):
        return (x & y) | (~x & z)

    def g(x, y, z):
        return (x & y) | (x & z) | (y & z)

    def h(x, y, z):
        return x ^ y ^ z

    def rotl(v, s):
        v &= 0xFFFFFFFF
        return ((v << s) | (v >> (32 - s))) & 0xFFFFFFFF

    msg = bytearray(data)
    bit_len = (len(data) * 8) & 0xFFFFFFFFFFFFFFFF
    msg.append(0x80)
    while len(msg) % 64 != 56:
        msg.append(0)
    msg += struct.pack("<Q", bit_len)
    regs = [0x67452301, 0xEFCDAB89, 0x98BADCFE, 0x10325476]
    r1 = [(i, (3, 7, 11, 19)[i % 4]) for i in range(16)]
    r2 = [(k, (3, 5, 9, 13)[n % 4]) for n, k in enumerate((0, 4, 8, 12, 1, 5, 9, 13, 2, 6, 10, 14, 3, 7, 11, 15))]
    r3 = [(k, (3, 9, 11, 15)[n % 4]) for n, k in enumerate((0, 8, 4, 12, 2, 10, 6, 14, 1, 9, 5, 13, 3, 11, 7, 15))]
    for off in range(0, len(msg), 64):
        x = struct.unpack("<16I", msg[off:off + 64])
        a, b, c, d = regs
        for fn, rounds, add in ((f, r1, 0), (g, r2, 0x5A827999), (h, r3, 0x6ED9EBA1)):
            for n, (k, s) in enumerate(rounds):
                step = n % 4
                if step == 0:
                    a = rotl(a + fn(b, c, d) + x[k] + add, s)
                elif step == 1:
                    d = rotl(d + fn(a, b, c) + x[k] + add, s)
                elif step == 2:
                    c = rotl(c + fn(d, a, b) + x[k] + add, s)
                else:
                    b = rotl(b + fn(c, d, a) + x[k] + add, s)
        regs = [(regs[0] + a) & 0xFFFFFFFF, (regs[1] + b) & 0xFFFFFFFF,
                (regs[2] + c) & 0xFFFFFFFF, (regs[3] + d) & 0xFFFFFFFF]
    return struct.pack("<4I", *regs)


def script_file_id(namespace: str, name: str) -> int:
    digest = md4(b"s\0\0\0" + (namespace or "").encode("utf-8") + name.encode("utf-8"))
    return struct.unpack("<i", digest[:4])[0]


def dll_classes_from_rea(rea_json):
    """{assembly file name: {fileID: 'Namespace.Class'}} from rea's IL2CPP metadata answer (top-level classes)."""
    nr = rea_json.get("normalized_result", rea_json)
    types = nr.get("types") or []
    out = {}
    for im in nr.get("images") or []:
        start, count = im.get("type_start"), im.get("type_count")
        if not isinstance(start, int) or not isinstance(count, int):
            continue
        table = {}
        for ti in range(start, min(start + count, len(types))):
            t = types[ti]
            if t.get("declaring_type", -1) not in (-1, None):
                continue
            ns, name = t.get("namespace") or "", t.get("name") or ""
            if not name or name.startswith("<"):
                continue
            table[script_file_id(ns, name)] = (ns + "." + name) if ns else name
        out[im.get("name")] = table
    return out


if __name__ == "__main__":
    assert md4(b"").hex() == "31d6cfe0d16ae931b73c59d7e0c089c0"
    assert md4(b"abc").hex() == "a448017aaf21d8525fc10ae87aa6729d"
    print("UnityEngine.UI.Image", script_file_id("UnityEngine.UI", "Image"))

"""Make a periodic texture (herringbone floor) tile seamlessly without ghosting.

The pattern repeats every (px, py) pixels. The extra pixels beyond one period are
used as an overlap; a minimum-error seam (dynamic programming) is cut through it so
the switch from one copy to the other runs along the dark gaps between planks.
"""
import sys
import numpy as np
from PIL import Image


def seam_cols(cost):
    """cost[h, ov] -> for each row the column where we switch (min-cost vertical path)."""
    h, ov = cost.shape
    acc = cost.copy()
    back = np.zeros((h, ov), dtype=np.int64)
    for y in range(1, h):
        prev = acc[y - 1]
        left = np.r_[np.inf, prev[:-1]]
        right = np.r_[prev[1:], np.inf]
        stack = np.vstack([left, prev, right])
        idx = np.argmin(stack, axis=0)
        acc[y] += stack[idx, np.arange(ov)]
        back[y] = np.arange(ov) + idx - 1
    path = np.zeros(h, dtype=np.int64)
    path[-1] = int(np.argmin(acc[-1]))
    for y in range(h - 1, 0, -1):
        path[y - 1] = back[y, path[y]]
    return path


def wrap_x(img, px, feather=2):
    h, w, _ = img.shape
    ov = w - px
    A = img[:, px:px + ov]          # what follows the right edge
    B = img[:, :ov]                 # the original left edge
    cost = ((A - B) ** 2).sum(2)
    cost[:, :3] += 1e9              # keep the seam away from the very border
    cost[:, -3:] += 1e9
    path = seam_cols(cost)
    out = img[:, :px].copy()
    cols = np.arange(ov)[None, :]
    t = np.clip((cols - path[:, None]) / (2.0 * feather) + 0.5, 0, 1)[..., None]  # 0 -> A, 1 -> B
    out[:, :ov] = A * (1 - t) + B * t
    return out


def main():
    src, dst, px, py = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
    img = np.asarray(Image.open(src).convert("RGB")).astype(np.float64)
    img = wrap_x(img, px)
    img = wrap_x(img.transpose(1, 0, 2), py).transpose(1, 0, 2)
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).save(dst)
    print("tile", img.shape[1], "x", img.shape[0])


if __name__ == "__main__":
    main()

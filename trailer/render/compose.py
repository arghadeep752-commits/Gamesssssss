#!/usr/bin/env python3
"""Render the trailer timeline.
  compose.py range T0 T1 OUT.mp4 [--scale S]     render [T0,T1) to video (no audio)
  compose.py stills OUTDIR T [T ...] [--scale S]  render single frames as JPEG for review
  compose.py plan N                               print N segment ranges split at hard cuts
"""
import subprocess
import sys

import numpy as np

import fx


def args_scale(argv):
    if "--scale" in argv:
        i = argv.index("--scale")
        s = float(argv[i + 1])
        del argv[i:i + 2]
        return s
    return 1.0


class Timeline:
    def __init__(self):
        import shots
        self.shots = shots.build_edl()
        self.total = shots.TOTAL

    def active(self, T):
        return [s for s in self.shots if s.start <= T < s.end]

    def frame(self, T, fidx):
        act = self.active(T)
        for s in self.shots:
            if s.opened and s not in act and T >= s.end:
                s.close()
        if not act:
            img = np.zeros((fx.H, fx.W, 3), np.float32)
        else:
            imgs = []
            for s in act:
                if not s.opened:
                    s.open(T - s.start)
                imgs.append(s.render(T - s.start))
            if len(imgs) == 1:
                img = imgs[0]
            else:
                a, b = act[0], act[-1]
                span = max(1e-3, a.end - b.start)
                w = fx.smooth((T - b.start) / span)
                img = imgs[0] * (1 - w) + imgs[-1] * w
        img = fx.grain(img, fidx, 0.022)
        return fx.u8(img)

    def close_all(self):
        for s in self.shots:
            if s.opened:
                s.close()

    def cuts(self):
        """Times where no two shots overlap (safe split points)."""
        pts = sorted({round(s.start, 3) for s in self.shots})
        safe = []
        for p in pts:
            if len([s for s in self.shots if s.start < p < s.end]) == 0:
                safe.append(p)
        return safe


def render_range(t0, t1, out, crf=13):
    tl = Timeline()
    f0, f1 = int(round(t0 * fx.FPS)), int(round(t1 * fx.FPS))
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", f"{fx.W}x{fx.H}", "-r", str(fx.FPS), "-i", "-", "-c:v", "libx264",
                            "-preset", "medium", "-crf", str(crf), "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for f in range(f0, f1):
        T = f / fx.FPS
        enc.stdin.write(tl.frame(T, f).tobytes())
        if f % 48 == 0:
            print(f"t={T:.1f}", flush=True)
    enc.stdin.close()
    enc.wait()
    tl.close_all()


def render_stills(outdir, times):
    import os
    from PIL import Image
    os.makedirs(outdir, exist_ok=True)
    for T in times:
        tl = Timeline()          # fresh timeline so stock readers seek correctly
        f = int(round(T * fx.FPS))
        img = tl.frame(f / fx.FPS, f)
        tl.close_all()
        Image.fromarray(img).save(f"{outdir}/still_{T:07.2f}.jpg", quality=86)
        print("still", T, flush=True)


def main():
    argv = sys.argv[1:]
    fx.init(args_scale(argv))
    cmd = argv[0]
    if cmd == "range":
        render_range(float(argv[1]), float(argv[2]), argv[3])
    elif cmd == "stills":
        render_stills(argv[1], [float(x) for x in argv[2:]])
    elif cmd == "plan":
        n = int(argv[1])
        tl = Timeline()
        cuts = tl.cuts() + [tl.total]
        target = [tl.total * k / n for k in range(1, n)]
        chosen = [0.0]
        for tg in target:
            best = min(cuts, key=lambda c: abs(c - tg))
            if best > chosen[-1]:
                chosen.append(best)
        chosen.append(tl.total)
        print(" ".join(f"{a}:{b}" for a, b in zip(chosen[:-1], chosen[1:])))


if __name__ == "__main__":
    main()

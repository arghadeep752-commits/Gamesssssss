using UnityEngine;

namespace GridProto
{
    /// <summary>Data that comes with the Blender-made house: the light probe grid (baked light around moving
    /// objects), camera viewpoints used by the cloud test, and the indoor volumes.</summary>
    public class HouseData : ScriptableObject
    {
        public Vector3 probeOrigin;
        public Vector3 probeSpacing = Vector3.one;
        public int nx, ny, nz;
        public float[] probes;            // per probe: +X -X +Y -Y +Z -Z, RGB each (18 floats)
        public string[] viewNames;
        public Vector3[] viewPositions;   // eye positions
        public float[] viewYaw;
        public float[] viewPitch;
        public Bounds[] interiors;

        static readonly Vector3[] Dirs = { Vector3.right, Vector3.left, Vector3.up, Vector3.down, Vector3.forward, Vector3.back };
        public static Vector3 Dir(int i) { return Dirs[i]; }

        /// <summary>Trilinear lookup of the six directional light values at a world position.</summary>
        public void Sample(Vector3 p, Color[] result)
        {
            for (int k = 0; k < 6; k++) result[k] = Color.black;
            if (probes == null || probes.Length < 18 || nx < 1) { for (int k = 0; k < 6; k++) result[k] = new Color(0.5f, 0.5f, 0.5f); return; }
            Vector3 g = new Vector3((p.x - probeOrigin.x) / probeSpacing.x, (p.y - probeOrigin.y) / probeSpacing.y, (p.z - probeOrigin.z) / probeSpacing.z);
            int x0 = Mathf.Clamp(Mathf.FloorToInt(g.x), 0, Mathf.Max(0, nx - 2));
            int y0 = Mathf.Clamp(Mathf.FloorToInt(g.y), 0, Mathf.Max(0, ny - 2));
            int z0 = Mathf.Clamp(Mathf.FloorToInt(g.z), 0, Mathf.Max(0, nz - 2));
            float fx = nx > 1 ? Mathf.Clamp01(g.x - x0) : 0f;
            float fy = ny > 1 ? Mathf.Clamp01(g.y - y0) : 0f;
            float fz = nz > 1 ? Mathf.Clamp01(g.z - z0) : 0f;
            for (int c = 0; c < 8; c++)
            {
                int ix = Mathf.Min(x0 + (c & 1), nx - 1), iy = Mathf.Min(y0 + ((c >> 1) & 1), ny - 1), iz = Mathf.Min(z0 + ((c >> 2) & 1), nz - 1);
                float w = ((c & 1) != 0 ? fx : 1f - fx) * (((c >> 1) & 1) != 0 ? fy : 1f - fy) * (((c >> 2) & 1) != 0 ? fz : 1f - fz);
                if (w <= 0f) continue;
                int b = ((iz * ny + iy) * nx + ix) * 18;
                for (int k = 0; k < 6; k++)
                {
                    result[k].r += probes[b + k * 3] * w;
                    result[k].g += probes[b + k * 3 + 1] * w;
                    result[k].b += probes[b + k * 3 + 2] * w;
                }
            }
        }

        public bool IsInside(Vector3 p)
        {
            if (interiors == null) return false;
            foreach (Bounds b in interiors) if (b.Contains(p)) return true;
            return false;
        }
    }
}

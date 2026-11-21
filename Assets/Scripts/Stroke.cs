using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

namespace TradersMadness
{
    /// <summary>
    /// Smooth outline shapes for the HUD: circles (the highlight rings, the centre dot) and the rounded box behind
    /// the settings gear. Drawn as a band of triangles with a one-unit soft edge on both sides, so they stay smooth
    /// on any screen without multisampling.
    /// </summary>
    public class Stroke : MaskableGraphic
    {
        public float radius = 30f;       // circle radius, or corner radius of the box
        public float width = 3f;
        public bool box;                 // rounded rectangle filling the rect instead of a circle
        public int segments = 48;

        public void Set(float r, float w)
        {
            if (Mathf.Abs(r - radius) < 0.01f && Mathf.Abs(w - width) < 0.01f) return;
            radius = r;
            width = w;
            SetVerticesDirty();
        }

        protected override void OnPopulateMesh(VertexHelper vh)
        {
            vh.Clear();
            var pts = new List<Vector2>();
            var nrm = new List<Vector2>();
            if (!box)
            {
                for (int i = 0; i < segments; i++)
                {
                    float a = i * Mathf.PI * 2f / segments;
                    var d = new Vector2(Mathf.Cos(a), Mathf.Sin(a));
                    pts.Add(d * radius);
                    nrm.Add(d);
                }
            }
            else
            {
                Rect r = rectTransform.rect;
                float cr = Mathf.Min(radius, Mathf.Min(r.width, r.height) * 0.5f);
                Vector2[] centres =
                {
                    new Vector2(r.xMax - cr, r.yMax - cr), new Vector2(r.xMin + cr, r.yMax - cr),
                    new Vector2(r.xMin + cr, r.yMin + cr), new Vector2(r.xMax - cr, r.yMin + cr),
                };
                int per = Mathf.Max(3, segments / 4);
                for (int c = 0; c < 4; c++)
                    for (int i = 0; i <= per; i++)
                    {
                        float a = (c * 90f + i * 90f / per) * Mathf.Deg2Rad;
                        var d = new Vector2(Mathf.Cos(a), Mathf.Sin(a));
                        pts.Add(centres[c] + d * cr);
                        nrm.Add(d);
                    }
            }
            float hw = width * 0.5f;
            const float soft = 1f;
            Color32 solid = color;
            Color32 clear = color;
            clear.a = 0;
            float[] offs = { -hw - soft, -hw, hw, hw + soft };
            Color32[] cols = { clear, solid, solid, clear };
            int n = pts.Count;
            for (int i = 0; i < n; i++)
                for (int k = 0; k < 4; k++)
                    vh.AddVert(pts[i] + nrm[i] * offs[k], cols[k], Vector2.zero);
            for (int i = 0; i < n; i++)
            {
                int j = (i + 1) % n;
                for (int k = 0; k < 3; k++)
                {
                    int a0 = i * 4 + k, a1 = i * 4 + k + 1, b0 = j * 4 + k, b1 = j * 4 + k + 1;
                    vh.AddTriangle(a0, b0, b1);
                    vh.AddTriangle(a0, b1, a1);
                }
            }
        }
    }
}

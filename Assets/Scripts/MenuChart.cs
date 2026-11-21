using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

namespace TradersMadness
{
    /// <summary>
    /// The live candlestick chart behind the main menu: green and red candles scrolling left, a moving average, the
    /// grid and the last-price line. Drawn as UI triangles, so it is sharp on every screen.
    /// </summary>
    public class MenuChart : MaskableGraphic
    {
        public int count = 64;
        public float speed = 0.55f;          // candles per second
        public float crash = 0.58f;          // >0.5: the price drifts down
        public float alpha = 0.55f;
        readonly List<float> price = new List<float>();
        float scroll;
        System.Random rng = new System.Random(7);

        protected override void Awake()
        {
            base.Awake();
            raycastTarget = false;
            float v = 100f;
            price.Clear();
            for (int i = 0; i < count + 2; i++)
            {
                v *= 1f + (float)(rng.NextDouble() - crash) * 0.05f;
                price.Add(v);
            }
        }

        void Update()
        {
            scroll += Time.unscaledDeltaTime * speed;
            while (scroll >= 1f)
            {
                scroll -= 1f;
                price.RemoveAt(0);
                float last = price[price.Count - 1];
                float nv = last * (1f + (float)(rng.NextDouble() - crash) * 0.06f);
                if (nv < 20f) nv = 100f + (float)rng.NextDouble() * 20f;      // a "recovery", then down again
                price.Add(nv);
            }
            SetVerticesDirty();
        }

        void Quad(VertexHelper vh, float x0, float y0, float x1, float y1, Color32 c)
        {
            int i = vh.currentVertCount;
            vh.AddVert(new Vector3(x0, y0), c, Vector2.zero);
            vh.AddVert(new Vector3(x0, y1), c, Vector2.zero);
            vh.AddVert(new Vector3(x1, y1), c, Vector2.zero);
            vh.AddVert(new Vector3(x1, y0), c, Vector2.zero);
            vh.AddTriangle(i, i + 1, i + 2);
            vh.AddTriangle(i + 2, i + 3, i);
        }

        void Seg(VertexHelper vh, Vector2 a, Vector2 b, float w, Color32 c)
        {
            Vector2 d = (b - a);
            if (d.sqrMagnitude < 1e-6f) return;
            Vector2 n = new Vector2(-d.y, d.x).normalized * (w * 0.5f);
            int i = vh.currentVertCount;
            vh.AddVert(a - n, c, Vector2.zero);
            vh.AddVert(a + n, c, Vector2.zero);
            vh.AddVert(b + n, c, Vector2.zero);
            vh.AddVert(b - n, c, Vector2.zero);
            vh.AddTriangle(i, i + 1, i + 2);
            vh.AddTriangle(i + 2, i + 3, i);
        }

        protected override void OnPopulateMesh(VertexHelper vh)
        {
            vh.Clear();
            Rect r = rectTransform.rect;
            if (price.Count < 3) return;
            byte a8 = (byte)(255 * alpha);
            var grid = new Color32(30, 60, 70, (byte)(a8 * 0.5f));
            for (int k = 1; k < 8; k++)
            {
                float y = r.yMin + r.height * k / 8f;
                Quad(vh, r.xMin, y - 0.5f, r.xMax, y + 0.5f, grid);
            }
            for (int k = 1; k < 12; k++)
            {
                float x = r.xMin + r.width * k / 12f;
                Quad(vh, x - 0.5f, r.yMin, x + 0.5f, r.yMax, grid);
            }
            float lo = float.MaxValue, hi = float.MinValue;
            foreach (float v in price) { lo = Mathf.Min(lo, v); hi = Mathf.Max(hi, v); }
            float pad = (hi - lo) * 0.2f + 0.01f;
            lo -= pad;
            hi += pad;
            float top = r.yMax - r.height * 0.06f, bot = r.yMin + r.height * 0.08f;
            float cw = r.width / count;
            System.Func<float, float> Y = v => bot + (v - lo) / (hi - lo) * (top - bot);
            var up = new Color32(30, 240, 125, a8);
            var down = new Color32(250, 45, 60, a8);
            for (int i = 1; i < price.Count; i++)
            {
                float o = price[i - 1], c = price[i];
                float x = r.xMin + (i - 1 - scroll) * cw + cw * 0.5f;
                if (x < r.xMin - cw || x > r.xMax + cw) continue;
                float wick = Mathf.Abs(c - o) * 0.7f + (hi - lo) * 0.012f;
                Color32 col = c >= o ? up : down;
                Quad(vh, x - 1f, Y(Mathf.Min(o, c) - wick), x + 1f, Y(Mathf.Max(o, c) + wick), col);
                float y0 = Y(Mathf.Min(o, c)), y1 = Mathf.Max(Y(Mathf.Max(o, c)), y0 + 2f);
                Quad(vh, x - cw * 0.32f, y0, x + cw * 0.32f, y1, col);
                // volume
                float vol = Mathf.Abs(c - o) / (hi - lo);
                Quad(vh, x - cw * 0.32f, r.yMin, x + cw * 0.32f, r.yMin + 6f + vol * r.height * 0.5f, new Color32(col.r, col.g, col.b, (byte)(a8 * 0.35f)));
            }
            // moving average
            var amber = new Color32(255, 190, 50, (byte)(a8 * 0.9f));
            Vector2 prev = Vector2.zero;
            bool has = false;
            for (int i = 6; i < price.Count; i++)
            {
                float m = 0f;
                for (int j = 0; j < 6; j++) m += price[i - j];
                m /= 6f;
                var p = new Vector2(r.xMin + (i - 1 - scroll) * cw + cw * 0.5f, Y(m));
                if (has) Seg(vh, prev, p, 2f, amber);
                prev = p;
                has = true;
            }
            // last price line
            float last = price[price.Count - 1];
            Color32 lc = last >= price[price.Count - 2] ? up : down;
            lc.a = (byte)(a8 * 0.6f);
            float ly = Y(last);
            for (float x = r.xMin; x < r.xMax; x += 14f) Quad(vh, x, ly - 0.75f, x + 7f, ly + 0.75f, lc);
        }
    }
}

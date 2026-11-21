using UnityEngine;

namespace TradersMadness
{
    /// <summary>
    /// The pictures on the trader's six monitors, drawn in code: candlestick charts that keep crashing, a falling
    /// price line, an order book, a heat map, an oscillator and a wall of red positions. They tick along once a
    /// second while the trading room has power.
    /// </summary>
    public class Screens : MonoBehaviour
    {
        public bool running;
        const int W = 256, H = 160, N = 40;
        readonly Texture2D[] tex = new Texture2D[6];
        readonly Color32[][] px = new Color32[6][];
        readonly float[][] series = new float[3][];
        readonly float[][] heat = new float[1][];
        float tickT;
        System.Random rng;

        static readonly Color32 Bg = new Color32(6, 10, 16, 255);
        static readonly Color32 Grid = new Color32(22, 32, 44, 255);
        static readonly Color32 Up = new Color32(30, 230, 120, 255);
        static readonly Color32 Down = new Color32(245, 50, 60, 255);
        static readonly Color32 Amber = new Color32(255, 190, 40, 255);
        static readonly Color32 Blue = new Color32(70, 150, 255, 255);
        static readonly Color32 Dim = new Color32(60, 80, 100, 255);

        void Awake()
        {
            rng = new System.Random(UnityEngine.Random.Range(0, 1 << 30));
            for (int k = 0; k < 6; k++)
            {
                tex[k] = new Texture2D(W, H, TextureFormat.RGBA32, false);
                tex[k].wrapMode = TextureWrapMode.Clamp;
                tex[k].filterMode = FilterMode.Bilinear;
                px[k] = new Color32[W * H];
            }
            for (int s = 0; s < 3; s++)
            {
                series[s] = new float[N + 1];
                float v = 100f;
                for (int i = 0; i <= N; i++)
                {
                    v *= 1f + (float)(rng.NextDouble() - 0.56) * 0.06f;
                    series[s][i] = v;
                }
            }
            heat[0] = new float[48];
            for (int i = 0; i < heat[0].Length; i++) heat[0][i] = (float)(rng.NextDouble() * 2 - 1.3);
            DrawAll();
        }

        public Texture2D Tex(int k) { return tex[Mathf.Clamp(k, 0, 5)]; }

        void Update()
        {
            if (!running) return;
            tickT -= Time.deltaTime;
            if (tickT > 0f) return;
            tickT = 1f;
            for (int s = 0; s < 3; s++)
            {
                float[] a = series[s];
                for (int i = 0; i < N; i++) a[i] = a[i + 1];
                a[N] = a[N - 1] * (1f + (float)(rng.NextDouble() - 0.58) * 0.07f);
                if (a[N] < 5f) a[N] = 100f;
            }
            for (int i = 0; i < heat[0].Length; i++)
                heat[0][i] = Mathf.Clamp(heat[0][i] + (float)(rng.NextDouble() - 0.55) * 0.4f, -1.5f, 1f);
            DrawAll();
        }

        void DrawAll()
        {
            Candles(0, series[0], true);
            LineChart(1, series[1]);
            OrderBook(2);
            Candles(3, series[2], false);
            Heat(4);
            Positions(5);
            for (int k = 0; k < 6; k++)
            {
                tex[k].SetPixels32(px[k]);
                tex[k].Apply(false);
            }
        }

        // ------------------------------------------------------------------------------------------ drawing
        void Clear(int k)
        {
            Color32[] p = px[k];
            for (int i = 0; i < p.Length; i++) p[i] = Bg;
            for (int y = 16; y < H; y += 24) Hline(k, 0, W - 1, y, Grid);
            for (int x = 0; x < W; x += 32) Vline(k, x, 0, H - 18, Grid);
            Rect(k, 0, H - 14, W - 1, H - 1, new Color32(14, 22, 32, 255));     // title bar
            Rect(k, 4, H - 10, 40, H - 5, k % 2 == 0 ? Amber : Blue);
            Rect(k, 46, H - 10, 70, H - 5, Dim);
        }

        void Rect(int k, int x0, int y0, int x1, int y1, Color32 c)
        {
            Color32[] p = px[k];
            if (x0 > x1) { int t = x0; x0 = x1; x1 = t; }
            if (y0 > y1) { int t = y0; y0 = y1; y1 = t; }
            x0 = Mathf.Clamp(x0, 0, W - 1); x1 = Mathf.Clamp(x1, 0, W - 1);
            y0 = Mathf.Clamp(y0, 0, H - 1); y1 = Mathf.Clamp(y1, 0, H - 1);
            for (int y = y0; y <= y1; y++)
                for (int x = x0; x <= x1; x++) p[y * W + x] = c;
        }

        void Hline(int k, int x0, int x1, int y, Color32 c) { Rect(k, x0, y, x1, y, c); }
        void Vline(int k, int x, int y0, int y1, Color32 c) { Rect(k, x, y0, x, y1, c); }

        void Line(int k, int x0, int y0, int x1, int y1, Color32 c)
        {
            int dx = Mathf.Abs(x1 - x0), dy = -Mathf.Abs(y1 - y0);
            int sx = x0 < x1 ? 1 : -1, sy = y0 < y1 ? 1 : -1, err = dx + dy;
            while (true)
            {
                Rect(k, x0, y0, x0, y0 + 1, c);
                if (x0 == x1 && y0 == y1) break;
                int e2 = 2 * err;
                if (e2 >= dy) { err += dy; x0 += sx; }
                if (e2 <= dx) { err += dx; y0 += sy; }
            }
        }

        static void Range(float[] a, out float lo, out float hi)
        {
            lo = float.MaxValue; hi = float.MinValue;
            foreach (float v in a) { lo = Mathf.Min(lo, v); hi = Mathf.Max(hi, v); }
            float pad = (hi - lo) * 0.15f + 0.01f;
            lo -= pad; hi += pad;
        }

        void Candles(int k, float[] a, bool volume)
        {
            Clear(k);
            float lo, hi;
            Range(a, out lo, out hi);
            int top = H - 20, bot = volume ? 34 : 6;
            float cw = (float)W / N;
            for (int i = 1; i <= N; i++)
            {
                float o = a[i - 1], c = a[i];
                float wick = Mathf.Abs(c - o) * 0.6f + (hi - lo) * 0.01f;
                int x = Mathf.RoundToInt((i - 0.5f) * cw);
                int yo = bot + Mathf.RoundToInt((o - lo) / (hi - lo) * (top - bot));
                int yc = bot + Mathf.RoundToInt((c - lo) / (hi - lo) * (top - bot));
                int yh = bot + Mathf.RoundToInt((Mathf.Max(o, c) + wick - lo) / (hi - lo) * (top - bot));
                int yl = bot + Mathf.RoundToInt((Mathf.Min(o, c) - wick - lo) / (hi - lo) * (top - bot));
                Color32 col = c >= o ? Up : Down;
                Vline(k, x, yl, yh, col);
                Rect(k, x - 2, Mathf.Min(yo, yc), x + 2, Mathf.Max(yo, yc) + 1, col);
                if (volume)
                {
                    int vh = 4 + Mathf.RoundToInt(Mathf.Abs(c - o) / (hi - lo) * 140f);
                    Rect(k, x - 2, 4, x + 2, 4 + Mathf.Min(vh, 26), new Color32((byte)(col.r / 2), (byte)(col.g / 2), (byte)(col.b / 2), 255));
                }
            }
            // moving average
            int px0 = -1, py0 = -1;
            for (int i = 5; i <= N; i++)
            {
                float m = 0f;
                for (int j = 0; j < 5; j++) m += a[i - j];
                m /= 5f;
                int x = Mathf.RoundToInt((i - 0.5f) * cw);
                int y = bot + Mathf.RoundToInt((m - lo) / (hi - lo) * (top - bot));
                if (px0 >= 0) Line(k, px0, py0, x, y, Amber);
                px0 = x; py0 = y;
            }
            // last price marker
            int yl2 = bot + Mathf.RoundToInt((a[N] - lo) / (hi - lo) * (top - bot));
            Hline(k, 0, W - 1, yl2, a[N] >= a[N - 1] ? new Color32(20, 120, 70, 255) : new Color32(140, 30, 36, 255));
        }

        void LineChart(int k, float[] a)
        {
            Clear(k);
            float lo, hi;
            Range(a, out lo, out hi);
            int top = H - 20, bot = 6;
            int px0 = -1, py0 = -1;
            for (int i = 0; i <= N; i++)
            {
                int x = Mathf.RoundToInt(i * (W - 1f) / N);
                int y = bot + Mathf.RoundToInt((a[i] - lo) / (hi - lo) * (top - bot));
                for (int yy = bot; yy < y; yy += 2) px[k][yy * W + Mathf.Clamp(x, 0, W - 1)] = new Color32(60, 16, 22, 255);
                if (px0 >= 0) Line(k, px0, py0, x, y, Down);
                px0 = x; py0 = y;
            }
        }

        void OrderBook(int k)
        {
            Clear(k);
            int rows = 12;
            for (int r = 0; r < rows; r++)
            {
                int y = 8 + r * 11;
                float bid = (float)rng.NextDouble(), ask = (float)rng.NextDouble();
                Rect(k, W / 2 - 2 - Mathf.RoundToInt(bid * (W / 2 - 10)), y, W / 2 - 2, y + 7, new Color32(18, 110, 60, 255));
                Rect(k, W / 2 + 2, y, W / 2 + 2 + Mathf.RoundToInt(ask * (W / 2 - 10)), y + 7, new Color32(130, 26, 34, 255));
            }
            Vline(k, W / 2, 4, H - 18, Dim);
        }

        void Heat(int k)
        {
            Clear(k);
            float[] h = heat[0];
            int cols = 8, rws = 6;
            int cwid = (W - 8) / cols, chei = (H - 24) / rws;
            for (int i = 0; i < h.Length; i++)
            {
                int cx = i % cols, cy = i / cols;
                float v = h[i];
                Color32 c = v >= 0 ? new Color32(20, (byte)(90f + 140f * Mathf.Clamp01(v)), 60, 255)
                                   : new Color32((byte)(110f + 140f * Mathf.Clamp01(-v)), 24, 32, 255);
                Rect(k, 4 + cx * cwid + 1, 4 + cy * chei + 1, 4 + (cx + 1) * cwid - 2, 4 + (cy + 1) * chei - 2, c);
            }
        }

        void Positions(int k)
        {
            Clear(k);
            for (int r = 0; r < 10; r++)
            {
                int y = H - 26 - r * 13;
                bool loss = rng.NextDouble() < 0.86;
                Rect(k, 6, y, 60, y + 7, Dim);
                Rect(k, 70, y, 120, y + 7, new Color32(40, 56, 70, 255));
                int w = 20 + rng.Next(90);
                Rect(k, W - 8 - w, y, W - 8, y + 7, loss ? Down : Up);
            }
        }
    }
}

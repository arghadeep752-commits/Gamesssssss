using UnityEngine;

namespace GridProto
{
    /// <summary>Crisp UI sprites drawn in code from signed distance fields (no image files).</summary>
    public static class UISprites
    {
        delegate float Sdf(float x, float y);

        static Sprite circle, ring, rounded, dot, jump, crouch, door, pause;

        public static Sprite Circle { get { if (circle == null) circle = Make(256, (x, y) => SdCircle(x, y, 0.47f), 0); return circle; } }
        public static Sprite Ring { get { if (ring == null) ring = Make(256, (x, y) => SdRing(x, y, 0.46f, 0.022f), 0); return ring; } }
        public static Sprite Rounded { get { if (rounded == null) rounded = Make(96, (x, y) => SdBox(x, y, 0.49f, 0.49f, 0.24f), 32); return rounded; } }
        public static Sprite Dot { get { if (dot == null) dot = Make(32, (x, y) => SdCircle(x, y, 0.36f), 0); return dot; } }
        public static Sprite JumpIcon { get { if (jump == null) jump = Make(128, JumpSdf, 0); return jump; } }
        public static Sprite CrouchIcon { get { if (crouch == null) crouch = Make(128, (x, y) => JumpSdf(x, -y), 0); return crouch; } }
        public static Sprite DoorIcon { get { if (door == null) door = Make(128, DoorSdf, 0); return door; } }
        public static Sprite PauseIcon { get { if (pause == null) pause = Make(128, PauseSdf, 0); return pause; } }

        static float JumpSdf(float x, float y)
        {
            float a = Chevron(x, y, 0.13f, 0.25f, 0.19f, 0.075f);
            float b = Chevron(x, y, -0.13f, 0.25f, 0.19f, 0.075f);
            return Mathf.Min(a, b);
        }

        static float DoorSdf(float x, float y)
        {
            float frame = Mathf.Abs(SdBox(x, y, 0.2f, 0.34f, 0.03f)) - 0.028f;
            float knob = SdCircle(x - 0.1f, y + 0.02f, 0.042f);
            return Mathf.Min(frame, knob);
        }

        static float PauseSdf(float x, float y)
        {
            return Mathf.Min(SdBox(x - 0.1f, y, 0.05f, 0.22f, 0.025f), SdBox(x + 0.1f, y, 0.05f, 0.22f, 0.025f));
        }

        static float Chevron(float x, float y, float centerY, float halfWidth, float height, float thickness)
        {
            float tip = centerY + height * 0.5f;
            float bottom = centerY - height * 0.5f;
            return Mathf.Min(Segment(x, y, -halfWidth, bottom, 0f, tip, thickness),
                             Segment(x, y, halfWidth, bottom, 0f, tip, thickness));
        }

        static float SdCircle(float x, float y, float r)
        {
            return Mathf.Sqrt(x * x + y * y) - r;
        }

        static float SdRing(float x, float y, float r, float width)
        {
            return Mathf.Abs(Mathf.Sqrt(x * x + y * y) - r) - width * 0.5f;
        }

        static float SdBox(float x, float y, float hx, float hy, float r)
        {
            float qx = Mathf.Abs(x) - hx + r;
            float qy = Mathf.Abs(y) - hy + r;
            float ox = Mathf.Max(qx, 0f);
            float oy = Mathf.Max(qy, 0f);
            return Mathf.Sqrt(ox * ox + oy * oy) + Mathf.Min(Mathf.Max(qx, qy), 0f) - r;
        }

        static float Segment(float x, float y, float ax, float ay, float bx, float by, float thickness)
        {
            float pax = x - ax, pay = y - ay, bax = bx - ax, bay = by - ay;
            float h = Mathf.Clamp01((pax * bax + pay * bay) / (bax * bax + bay * bay));
            float dx = pax - bax * h, dy = pay - bay * h;
            return Mathf.Sqrt(dx * dx + dy * dy) - thickness * 0.5f;
        }

        static Sprite Make(int size, Sdf sdf, int border)
        {
            var tex = new Texture2D(size, size, TextureFormat.RGBA32, true);
            tex.name = "ui_sprite_" + size;
            tex.wrapMode = TextureWrapMode.Clamp;
            tex.filterMode = FilterMode.Trilinear;
            var pixels = new Color32[size * size];
            float inv = 1f / size;
            for (int j = 0; j < size; j++)
            {
                for (int i = 0; i < size; i++)
                {
                    float x = (i + 0.5f) * inv - 0.5f;
                    float y = (j + 0.5f) * inv - 0.5f;
                    float d = sdf(x, y) * size;                 // distance in pixels
                    float a = Mathf.Clamp01(0.5f - d / 1.3f);    // ~1 px anti-aliased edge
                    pixels[j * size + i] = new Color32(255, 255, 255, (byte)Mathf.RoundToInt(a * 255f));
                }
            }
            tex.SetPixels32(pixels);
            tex.Apply(true, true);
            var rect = new Rect(0f, 0f, size, size);
            var pivot = new Vector2(0.5f, 0.5f);
            if (border > 0)
                return Sprite.Create(tex, rect, pivot, 100f, 0, SpriteMeshType.FullRect, new Vector4(border, border, border, border));
            return Sprite.Create(tex, rect, pivot, 100f, 0, SpriteMeshType.FullRect);
        }
    }
}

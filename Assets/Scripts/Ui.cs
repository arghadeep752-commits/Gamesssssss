using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Events;
using UnityEngine.EventSystems;
using UnityEngine.UI;

namespace Moulika
{
    /// <summary>
    /// Builds the game's interface in code, like the Godot version did. The canvas is 720 units high whatever the
    /// screen (the width follows the screen's shape), so every size and position matches the Godot layout.
    /// Positions given as "y" are fractions of the screen height measured from the top, as Godot anchors are.
    /// </summary>
    public static class Ui
    {
        public const float RefH = 720f;
        public static Font chalk;      // DK Midnight Chalker, the game's font
        public static Font title;      // Baby Doll, the game's name
        public const float ChalkScale = 1.4f;   // the chalk font draws small for its size
        public static bool chalkScaled = true;  // false when the chalk font is missing and Oswald stands in

        public static int Sz(Font f, int size)
        {
            return f != null && f == chalk && chalkScaled ? Mathf.RoundToInt(size * ChalkScale) : size;
        }

        public static Canvas MakeCanvas(string name, int order)
        {
            var go = new GameObject(name);
            var canvas = go.AddComponent<Canvas>();
            canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            canvas.sortingOrder = order;
            canvas.pixelPerfect = false;
            var scaler = go.AddComponent<CanvasScaler>();
            scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            scaler.referenceResolution = new Vector2(1280f, RefH);
            scaler.screenMatchMode = CanvasScaler.ScreenMatchMode.MatchWidthOrHeight;
            scaler.matchWidthOrHeight = 1f;
            go.AddComponent<GraphicRaycaster>();
            return canvas;
        }

        public static RectTransform Node(Transform parent, string name)
        {
            var go = new GameObject(name, typeof(RectTransform));
            go.layer = 5;
            var rt = (RectTransform)go.transform;
            rt.SetParent(parent, false);
            return rt;
        }

        public static void Full(RectTransform rt)
        {
            rt.anchorMin = Vector2.zero;
            rt.anchorMax = Vector2.one;
            rt.offsetMin = Vector2.zero;
            rt.offsetMax = Vector2.zero;
            rt.pivot = new Vector2(0.5f, 0.5f);
        }

        /// <summary>Top-left anchored node: position in 720-high units, y measured downwards.</summary>
        public static void TopLeft(RectTransform rt, float x, float y, float w, float h)
        {
            rt.anchorMin = new Vector2(0f, 1f);
            rt.anchorMax = new Vector2(0f, 1f);
            rt.pivot = new Vector2(0f, 1f);
            rt.anchoredPosition = new Vector2(x, -y);
            rt.sizeDelta = new Vector2(w, h);
        }

        /// <summary>Centre of the node at a top-left based point.</summary>
        public static void Centre(RectTransform rt, Vector2 p, Vector2 size)
        {
            rt.anchorMin = new Vector2(0f, 1f);
            rt.anchorMax = new Vector2(0f, 1f);
            rt.pivot = new Vector2(0.5f, 0.5f);
            rt.anchoredPosition = new Vector2(p.x, -p.y);
            rt.sizeDelta = size;
        }

        public static Image Rect(Transform parent, Color c, string name = "Rect")
        {
            RectTransform rt = Node(parent, name);
            Full(rt);
            var img = rt.gameObject.AddComponent<Image>();
            img.color = c;
            img.raycastTarget = false;
            return img;
        }

        public static Text Label(Transform parent, Font f, int size, Color c, string name = "Label")
        {
            RectTransform rt = Node(parent, name);
            Full(rt);
            var t = rt.gameObject.AddComponent<Text>();
            t.font = f;
            t.fontSize = Sz(f, size);
            t.color = c;
            t.alignment = TextAnchor.MiddleCenter;
            t.horizontalOverflow = HorizontalWrapMode.Wrap;
            t.verticalOverflow = VerticalWrapMode.Overflow;
            t.raycastTarget = false;
            t.supportRichText = true;
            return t;
        }

        /// <summary>Godot _text: a centred line whose top sits at y (fraction of the height from the top).</summary>
        public static Text TextAt(Transform parent, string s, Font f, int size, Color c, float y, float spacing = 0f)
        {
            Text t = Label(parent, f, size, c, "Text " + s);
            RectTransform rt = t.rectTransform;
            rt.anchorMin = new Vector2(0f, 1f - y);
            rt.anchorMax = new Vector2(1f, 1f - y);
            rt.pivot = new Vector2(0.5f, 1f);
            rt.anchoredPosition = Vector2.zero;
            rt.sizeDelta = new Vector2(0f, t.fontSize * 1.4f);
            t.alignment = TextAnchor.UpperCenter;
            t.horizontalOverflow = HorizontalWrapMode.Overflow;
            t.text = spacing > 0f ? Spaced(s, spacing) : s;
            return t;
        }

        /// <summary>Letter spacing for titles (Godot FontVariation.spacing_glyph): thin spaces between letters.</summary>
        public static string Spaced(string s, float spacing)
        {
            string gap = spacing >= 6f ? "  " : " ";
            var parts = new List<string>();
            foreach (char ch in s) parts.Add(ch.ToString());
            return string.Join(gap, parts.ToArray());
        }

        public static void Divider(Transform parent, float y, float w)
        {
            Image r = Rect(parent, new Color(0.55f, 0.03f, 0.03f, 0.85f), "Divider");
            RectTransform rt = r.rectTransform;
            rt.anchorMin = new Vector2(0.5f, 1f - y);
            rt.anchorMax = new Vector2(0.5f, 1f - y);
            rt.pivot = new Vector2(0.5f, 1f);
            rt.anchoredPosition = Vector2.zero;
            rt.sizeDelta = new Vector2(w, 2f);
        }

        /// <summary>Godot _button: flat text button, light grey, red while pressed.</summary>
        public static Button Button(Transform parent, string s, float y, UnityAction onClick, int size = 46, float halfWidth = 220f)
        {
            RectTransform rt = Node(parent, "Button " + s);
            rt.anchorMin = new Vector2(0.5f, 1f - y);
            rt.anchorMax = new Vector2(0.5f, 1f - y);
            rt.pivot = new Vector2(0.5f, 1f);
            rt.anchoredPosition = Vector2.zero;
            rt.sizeDelta = new Vector2(halfWidth * 2f, size * 1.7f * (chalk != null ? 1.15f : 1f));
            var hit = rt.gameObject.AddComponent<Image>();
            hit.color = new Color(0f, 0f, 0f, 0f);      // invisible, catches the touch
            var b = rt.gameObject.AddComponent<Button>();
            Text t = Label(rt, chalk, size, Color.white, "Text");
            t.text = s;
            t.horizontalOverflow = HorizontalWrapMode.Overflow;
            b.targetGraphic = t;
            ColorBlock cb = b.colors;
            cb.normalColor = new Color(0.86f, 0.86f, 0.86f, 1f);
            cb.highlightedColor = new Color(0.86f, 0.86f, 0.86f, 1f);
            cb.selectedColor = new Color(0.86f, 0.86f, 0.86f, 1f);
            cb.pressedColor = new Color(0.78f, 0.06f, 0.05f, 1f);
            cb.disabledColor = new Color(0.4f, 0.4f, 0.4f, 1f);
            cb.colorMultiplier = 1f;
            cb.fadeDuration = 0.05f;
            b.colors = cb;
            var nav = new Navigation();
            nav.mode = Navigation.Mode.None;
            b.navigation = nav;
            if (onClick != null) b.onClick.AddListener(onClick);
            return b;
        }

        public static Texture2D Dot(int r)
        {
            var tex = new Texture2D(r * 2, r * 2, TextureFormat.RGBA32, false);
            var px = new Color32[r * r * 4];
            for (int y = 0; y < r * 2; y++)
                for (int x = 0; x < r * 2; x++)
                {
                    float d = new Vector2(x - r + 0.5f, y - r + 0.5f).magnitude;
                    byte a = (byte)(Mathf.Clamp01(r - 1f - d + 0.5f) * 255f);
                    px[y * r * 2 + x] = new Color32(255, 255, 255, a);
                }
            tex.SetPixels32(px);
            tex.Apply();
            tex.wrapMode = TextureWrapMode.Clamp;
            return tex;
        }

        static Sprite whiteSprite;
        public static Sprite White()
        {
            if (whiteSprite == null)
            {
                var t = new Texture2D(4, 4, TextureFormat.RGBA32, false);
                var px = new Color32[16];
                for (int i = 0; i < 16; i++) px[i] = new Color32(255, 255, 255, 255);
                t.SetPixels32(px);
                t.Apply();
                whiteSprite = Sprite.Create(t, new Rect(0, 0, 4, 4), new Vector2(0.5f, 0.5f), 100f);
            }
            return whiteSprite;
        }

        /// <summary>Godot _slider: grey track, red filled part, white round grabber, value written under it.</summary>
        public static Slider Slider(Transform parent, float y, float value, float min, float max, Action<float> changed)
        {
            RectTransform rt = Node(parent, "Slider");
            rt.anchorMin = new Vector2(0.5f, 1f - y);
            rt.anchorMax = new Vector2(0.5f, 1f - y);
            rt.pivot = new Vector2(0.5f, 1f);
            rt.anchoredPosition = Vector2.zero;
            rt.sizeDelta = new Vector2(520f, 60f);
            var hit = rt.gameObject.AddComponent<Image>();
            hit.color = new Color(0f, 0f, 0f, 0f);

            RectTransform bg = Node(rt, "Track");
            bg.anchorMin = new Vector2(0f, 0.5f);
            bg.anchorMax = new Vector2(1f, 0.5f);
            bg.sizeDelta = new Vector2(0f, 8f);
            var bgi = bg.gameObject.AddComponent<Image>();
            bgi.sprite = White();
            bgi.color = new Color(0.35f, 0.35f, 0.35f, 1f);
            bgi.raycastTarget = false;

            RectTransform fillArea = Node(rt, "Fill Area");
            fillArea.anchorMin = new Vector2(0f, 0.5f);
            fillArea.anchorMax = new Vector2(1f, 0.5f);
            fillArea.sizeDelta = new Vector2(0f, 8f);
            RectTransform fill = Node(fillArea, "Fill");
            fill.anchorMin = Vector2.zero;
            fill.anchorMax = new Vector2(0f, 1f);
            fill.sizeDelta = Vector2.zero;
            var fi = fill.gameObject.AddComponent<Image>();
            fi.sprite = White();
            fi.color = new Color(0.8f, 0.1f, 0.08f, 1f);
            fi.raycastTarget = false;

            RectTransform handleArea = Node(rt, "Handle Area");
            Full(handleArea);
            handleArea.offsetMin = new Vector2(11f, 0f);
            handleArea.offsetMax = new Vector2(-11f, 0f);
            RectTransform handle = Node(handleArea, "Handle");
            handle.sizeDelta = new Vector2(44f, 44f);
            handle.anchorMin = new Vector2(0f, 0.5f);
            handle.anchorMax = new Vector2(0f, 0.5f);
            var hi = handle.gameObject.AddComponent<RawImage>();
            hi.texture = Dot(32);
            hi.color = Color.white;

            var s = rt.gameObject.AddComponent<Slider>();
            s.fillRect = fill;
            s.handleRect = handle;
            s.targetGraphic = hi;
            s.direction = UnityEngine.UI.Slider.Direction.LeftToRight;
            s.minValue = min;
            s.maxValue = max;
            s.wholeNumbers = false;
            var nav = new Navigation();
            nav.mode = Navigation.Mode.None;
            s.navigation = nav;
            s.value = value;
            if (changed != null) s.onValueChanged.AddListener(v => changed(v));
            return s;
        }

        public static void EnsureEventSystem()
        {
            if (UnityEngine.Object.FindFirstObjectByType<EventSystem>() != null) return;
            var go = new GameObject("EventSystem");
            go.AddComponent<EventSystem>();
            go.AddComponent<StandaloneInputModule>();
        }
    }

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

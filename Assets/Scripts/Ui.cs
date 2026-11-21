using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Events;
using UnityEngine.EventSystems;
using UnityEngine.UI;

namespace TradersMadness
{
    /// <summary>
    /// Builds the game's interface in code, styled like a trading terminal: near-black panels, thin green outlines,
    /// red for danger, monospace numbers. The canvas is 720 units high whatever the screen (the width follows the
    /// screen's shape). Positions given as "y" are fractions of the screen height measured from the top.
    /// </summary>
    public static class Ui
    {
        public const float RefH = 720f;
        public static Font title;     // Bebas Neue: the game's name and big words
        public static Font ui;        // Rajdhani SemiBold: buttons, labels, messages
        public static Font bold;      // Rajdhani Bold
        public static Font mono;      // Share Tech Mono: numbers, tickers, the PC screen, keypads

        public static readonly Color Bg = new Color(0.016f, 0.02f, 0.026f, 1f);
        public static readonly Color Panel = new Color(0.03f, 0.04f, 0.05f, 0.94f);
        public static readonly Color Green = new Color(0.12f, 0.95f, 0.5f, 1f);
        public static readonly Color GreenDim = new Color(0.12f, 0.95f, 0.5f, 0.35f);
        public static readonly Color Red = new Color(0.98f, 0.18f, 0.24f, 1f);
        public static readonly Color Amber = new Color(1f, 0.72f, 0.18f, 1f);
        public static readonly Color Text = new Color(0.9f, 0.93f, 0.92f, 1f);
        public static readonly Color TextDim = new Color(0.55f, 0.62f, 0.6f, 1f);

        public static void LoadFonts()
        {
            Font builtin = null;
            try { builtin = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf"); } catch (Exception) { }
            ui = Resources.Load<Font>("Fonts/Rajdhani-SemiBold") ?? builtin;
            bold = Resources.Load<Font>("Fonts/Rajdhani-Bold") ?? ui;
            title = Resources.Load<Font>("Fonts/BebasNeue-Regular") ?? Resources.Load<Font>("Fonts/Anton-Regular") ?? bold;
            mono = Resources.Load<Font>("Fonts/ShareTechMono-Regular") ?? ui;
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

        /// <summary>Centre of the node relative to the middle of the screen (x right, y down, canvas units).</summary>
        public static void Mid(RectTransform rt, float x, float y, float w, float h)
        {
            rt.anchorMin = new Vector2(0.5f, 0.5f);
            rt.anchorMax = new Vector2(0.5f, 0.5f);
            rt.pivot = new Vector2(0.5f, 0.5f);
            rt.anchoredPosition = new Vector2(x, -y);
            rt.sizeDelta = new Vector2(w, h);
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
            t.fontSize = size;
            t.color = c;
            t.alignment = TextAnchor.MiddleCenter;
            t.horizontalOverflow = HorizontalWrapMode.Wrap;
            t.verticalOverflow = VerticalWrapMode.Overflow;
            t.raycastTarget = false;
            t.supportRichText = true;
            return t;
        }

        /// <summary>A centred line whose top sits at y (fraction of the height from the top).</summary>
        public static Text TextAt(Transform parent, string s, Font f, int size, Color c, float y)
        {
            Text t = Label(parent, f, size, c, "Text " + s);
            RectTransform rt = t.rectTransform;
            rt.anchorMin = new Vector2(0f, 1f - y);
            rt.anchorMax = new Vector2(1f, 1f - y);
            rt.pivot = new Vector2(0.5f, 1f);
            rt.anchoredPosition = Vector2.zero;
            rt.sizeDelta = new Vector2(0f, size * 1.4f);
            t.alignment = TextAnchor.UpperCenter;
            t.horizontalOverflow = HorizontalWrapMode.Overflow;
            t.text = s;
            return t;
        }

        /// <summary>Text box at a position relative to the screen middle.</summary>
        public static Text TextMid(Transform parent, string s, Font f, int size, Color c, float x, float y, float w, float h,
                                   TextAnchor align = TextAnchor.MiddleCenter)
        {
            Text t = Label(parent, f, size, c, "Text");
            Mid(t.rectTransform, x, y, w, h);
            t.alignment = align;
            t.text = s;
            return t;
        }

        public static Stroke Outline(Transform parent, Color c, float width = 2f, float radius = 3f, string name = "Outline")
        {
            RectTransform rt = Node(parent, name);
            Full(rt);
            var s = rt.gameObject.AddComponent<Stroke>();
            s.box = true;
            s.radius = radius;
            s.width = width;
            s.color = c;
            s.raycastTarget = false;
            return s;
        }

        /// <summary>A dark panel with a thin outline, centred at (x, y) from the screen middle.</summary>
        public static RectTransform PanelAt(Transform parent, float x, float y, float w, float h, Color outline, string name = "Panel")
        {
            RectTransform rt = Node(parent, name);
            Mid(rt, x, y, w, h);
            var img = rt.gameObject.AddComponent<Image>();
            img.color = Panel;
            img.raycastTarget = true;
            Outline(rt, outline, 2f, 4f);
            return rt;
        }

        /// <summary>Terminal button: dark box, green outline, "&gt; LABEL"; it fills green while pressed.</summary>
        public static Button TermButton(Transform parent, string s, float x, float y, float w, float h, UnityAction onClick,
                                        int size = 34, Color? accent = null)
        {
            Color ac = accent ?? Green;
            RectTransform rt = Node(parent, "Button " + s);
            Mid(rt, x, y, w, h);
            var bg = rt.gameObject.AddComponent<Image>();
            bg.sprite = White();
            bg.color = Color.white;
            var b = rt.gameObject.AddComponent<Button>();
            b.targetGraphic = bg;
            ColorBlock cb = b.colors;
            var dark = new Color(0.03f, 0.05f, 0.05f, 0.82f);
            cb.normalColor = dark;
            cb.highlightedColor = dark;
            cb.selectedColor = dark;
            cb.pressedColor = new Color(ac.r * 0.55f, ac.g * 0.55f, ac.b * 0.55f, 0.95f);
            cb.disabledColor = new Color(0.5f, 0.5f, 0.5f, 1f);
            cb.colorMultiplier = 1f;
            cb.fadeDuration = 0.05f;
            b.colors = cb;
            Outline(rt, new Color(ac.r, ac.g, ac.b, 0.85f), 2f, 3f);
            // a bright tick on the left edge
            RectTransform tick = Node(rt, "Tick");
            tick.anchorMin = new Vector2(0f, 0.18f);
            tick.anchorMax = new Vector2(0f, 0.82f);
            tick.pivot = new Vector2(0f, 0.5f);
            tick.sizeDelta = new Vector2(5f, 0f);
            tick.anchoredPosition = new Vector2(6f, 0f);
            var ti = tick.gameObject.AddComponent<Image>();
            ti.color = ac;
            ti.raycastTarget = false;
            Text t = Label(rt, ui, size, Text, "Text");
            t.text = s;
            t.horizontalOverflow = HorizontalWrapMode.Overflow;
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
                whiteSprite = Sprite.Create(t, new UnityEngine.Rect(0, 0, 4, 4), new Vector2(0.5f, 0.5f), 100f);
            }
            return whiteSprite;
        }

        /// <summary>Slider: dark track, green filled part, white round grabber.</summary>
        public static Slider MakeSlider(Transform parent, float x, float y, float w, float value, float min, float max, Action<float> changed)
        {
            RectTransform rt = Node(parent, "Slider");
            Mid(rt, x, y, w, 56f);
            var hit = rt.gameObject.AddComponent<Image>();
            hit.color = new Color(0f, 0f, 0f, 0f);

            RectTransform bg = Node(rt, "Track");
            bg.anchorMin = new Vector2(0f, 0.5f);
            bg.anchorMax = new Vector2(1f, 0.5f);
            bg.sizeDelta = new Vector2(0f, 6f);
            var bgi = bg.gameObject.AddComponent<Image>();
            bgi.sprite = White();
            bgi.color = new Color(0.2f, 0.24f, 0.24f, 1f);
            bgi.raycastTarget = false;

            RectTransform fillArea = Node(rt, "Fill Area");
            fillArea.anchorMin = new Vector2(0f, 0.5f);
            fillArea.anchorMax = new Vector2(1f, 0.5f);
            fillArea.sizeDelta = new Vector2(0f, 6f);
            RectTransform fill = Node(fillArea, "Fill");
            fill.anchorMin = Vector2.zero;
            fill.anchorMax = new Vector2(0f, 1f);
            fill.sizeDelta = Vector2.zero;
            var fi = fill.gameObject.AddComponent<Image>();
            fi.sprite = White();
            fi.color = Green;
            fi.raycastTarget = false;

            RectTransform handleArea = Node(rt, "Handle Area");
            Full(handleArea);
            handleArea.offsetMin = new Vector2(11f, 0f);
            handleArea.offsetMax = new Vector2(-11f, 0f);
            RectTransform handle = Node(handleArea, "Handle");
            handle.sizeDelta = new Vector2(40f, 40f);
            handle.anchorMin = new Vector2(0f, 0.5f);
            handle.anchorMax = new Vector2(0f, 0.5f);
            var hi = handle.gameObject.AddComponent<RawImage>();
            hi.texture = Dot(32);
            hi.color = Color.white;

            var s = rt.gameObject.AddComponent<Slider>();
            s.fillRect = fill;
            s.handleRect = handle;
            s.targetGraphic = hi;
            s.direction = Slider.Direction.LeftToRight;
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

        public static string Money(double v)
        {
            return (v < 0 ? "-$" : "+$") + Math.Abs(v).ToString("#,##0.00", System.Globalization.CultureInfo.InvariantCulture);
        }
    }
}

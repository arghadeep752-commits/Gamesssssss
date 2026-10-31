using System;
using UnityEngine;
using UnityEngine.Events;
using UnityEngine.UI;

namespace RealFPS
{
    /// <summary>Helpers that build the uGUI interface in code.</summary>
    public static class UIKit
    {
        public static readonly Color PanelColor = new Color(0.04f, 0.05f, 0.06f, 0.72f);
        public static readonly Color ButtonColor = new Color(0.08f, 0.1f, 0.11f, 0.78f);
        public static readonly Color Accent = new Color(0.98f, 0.78f, 0.42f, 1f);
        public static readonly Color TextColor = new Color(0.96f, 0.96f, 0.94f, 1f);
        public static readonly Color DimText = new Color(0.82f, 0.84f, 0.84f, 0.85f);

        public static RectTransform Rect(Transform parent, string name)
        {
            var go = new GameObject(name, typeof(RectTransform));
            go.layer = 5; // UI
            var rt = (RectTransform)go.transform;
            rt.SetParent(parent, false);
            return rt;
        }

        public static RectTransform Place(this RectTransform rt, Vector2 anchor, Vector2 pivot, Vector2 pos, Vector2 size)
        {
            rt.anchorMin = rt.anchorMax = anchor;
            rt.pivot = pivot;
            rt.anchoredPosition = pos;
            rt.sizeDelta = size;
            return rt;
        }

        public static RectTransform Stretch(this RectTransform rt, float left = 0, float right = 0, float bottom = 0, float top = 0)
        {
            rt.anchorMin = Vector2.zero;
            rt.anchorMax = Vector2.one;
            rt.pivot = new Vector2(0.5f, 0.5f);
            rt.offsetMin = new Vector2(left, bottom);
            rt.offsetMax = new Vector2(-right, -top);
            return rt;
        }

        public static Image Img(Transform parent, string name, Sprite sprite, Color color, bool raycast = false)
        {
            RectTransform rt = Rect(parent, name);
            var img = rt.gameObject.AddComponent<Image>();
            img.sprite = sprite;
            img.color = color;
            img.raycastTarget = raycast;
            if (sprite != null && sprite.border.sqrMagnitude > 0f) img.type = Image.Type.Sliced;
            return img;
        }

        public static Text Label(Transform parent, string name, string text, int size, Color color,
                                 TextAnchor align = TextAnchor.MiddleCenter, Font font = null, bool shadow = true)
        {
            RectTransform rt = Rect(parent, name);
            var t = rt.gameObject.AddComponent<Text>();
            t.font = font != null ? font : GameAssets.I.uiFont;
            t.text = text;
            t.fontSize = size;
            t.color = color;
            t.alignment = align;
            t.raycastTarget = false;
            t.horizontalOverflow = HorizontalWrapMode.Overflow;
            t.verticalOverflow = VerticalWrapMode.Overflow;
            if (shadow)
            {
                var s = rt.gameObject.AddComponent<Shadow>();
                s.effectColor = new Color(0f, 0f, 0f, 0.55f);
                s.effectDistance = new Vector2(2f, -2f);
            }
            return t;
        }

        public static Button Btn(Transform parent, string name, string label, Vector2 size, UnityAction onClick, int fontSize = 34)
        {
            Image bg = Img(parent, name, GameAssets.I.rounded, ButtonColor, true);
            bg.rectTransform.sizeDelta = size;
            var b = bg.gameObject.AddComponent<Button>();
            ColorBlock cb = b.colors;
            cb.normalColor = Color.white;
            cb.highlightedColor = Color.white;
            cb.pressedColor = new Color(1f, 0.85f, 0.6f, 1f);
            cb.selectedColor = Color.white;
            cb.fadeDuration = 0.08f;
            b.colors = cb;
            b.targetGraphic = bg;
            b.onClick.AddListener(() => Sfx.Play2D(GameAssets.I.uiClick, 0.45f));
            if (onClick != null) b.onClick.AddListener(onClick);
            Text t = Label(bg.transform, "Label", label, fontSize, TextColor, TextAnchor.MiddleCenter, GameAssets.I.uiFontBold, false);
            t.rectTransform.Stretch(16, 16, 0, 0);
            var nav = b.navigation;
            nav.mode = Navigation.Mode.None;
            b.navigation = nav;
            return b;
        }

        public static void SetLabel(Button b, string text)
        {
            var t = b.GetComponentInChildren<Text>();
            if (t != null) t.text = text;
        }

        public static Slider Slider(Transform parent, string name, Vector2 size, float min, float max, float value, Action<float> onChange)
        {
            RectTransform root = Rect(parent, name);
            root.sizeDelta = size;
            Image bg = Img(root, "Background", GameAssets.I.rounded, new Color(1f, 1f, 1f, 0.16f));
            bg.rectTransform.Stretch(0, 0, size.y * 0.38f, size.y * 0.38f);
            RectTransform fillArea = Rect(root, "Fill Area").Stretch(0, size.y * 0.5f, size.y * 0.38f, size.y * 0.38f);
            Image fill = Img(fillArea, "Fill", GameAssets.I.rounded, Accent);
            fill.rectTransform.Stretch(0, -size.y * 0.5f, 0, 0);
            RectTransform handleArea = Rect(root, "Handle Area").Stretch(size.y * 0.5f, size.y * 0.5f, 0, 0);
            Image handle = Img(handleArea, "Handle", GameAssets.I.circle, Color.white, true);
            handle.rectTransform.sizeDelta = new Vector2(size.y * 1.1f, 0f);
            handle.rectTransform.anchorMin = new Vector2(0f, 0f);
            handle.rectTransform.anchorMax = new Vector2(0f, 1f);
            var s = root.gameObject.AddComponent<Slider>();
            s.fillRect = fill.rectTransform;
            s.handleRect = handle.rectTransform;
            s.targetGraphic = handle;
            s.direction = UnityEngine.UI.Slider.Direction.LeftToRight;
            s.minValue = min;
            s.maxValue = max;
            s.value = value;
            var nav = s.navigation;
            nav.mode = Navigation.Mode.None;
            s.navigation = nav;
            if (onChange != null) s.onValueChanged.AddListener(v => onChange(v));
            // a bigger invisible touch area
            Image hit = Img(root, "TouchArea", null, new Color(0, 0, 0, 0), true);
            hit.rectTransform.Stretch(-10, -10, -18, -18);
            hit.transform.SetAsFirstSibling();
            return s;
        }

        public static void Fit(RectTransform rt)
        {
            rt.anchorMin = Vector2.zero;
            rt.anchorMax = Vector2.one;
            rt.offsetMin = rt.offsetMax = Vector2.zero;
        }
    }
}

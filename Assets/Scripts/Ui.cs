using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

namespace Danga
{
    /// <summary>Builds the interface in code (uGUI): boxes, pictures, text, buttons.</summary>
    public static class Ui
    {
        public static Font font, display, body, title;
        public static Canvas canvas;
        public static RectTransform root;
        static readonly Dictionary<string, Sprite> sprites = new Dictionary<string, Sprite>();
        public static readonly Vector2 TL = new Vector2(0, 1), TR = new Vector2(1, 1), BL = new Vector2(0, 0), BR = new Vector2(1, 0),
                                       C = new Vector2(0.5f, 0.5f), T = new Vector2(0.5f, 1), B = new Vector2(0.5f, 0), L = new Vector2(0, 0.5f), R = new Vector2(1, 0.5f);
        public static readonly Color Saffron = new Color(1f, 0.6f, 0.1f), Green = new Color(0.25f, 0.8f, 0.3f), Red = new Color(0.92f, 0.22f, 0.18f),
                                     Blue = new Color(0.2f, 0.5f, 0.95f), Dark = new Color(0.08f, 0.08f, 0.1f, 0.88f), Yellow = new Color(1f, 0.85f, 0.15f);

        public static void Init()
        {
            font = Resources.Load<Font>("Fonts/UIFont");
            display = Resources.Load<Font>("Fonts/DisplayFont");
            body = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            if (font == null) font = body;
            if (display == null) display = font;
            title = Resources.Load<Font>("Fonts/TitleFont");
            if (title == null) title = display;
            var go = new GameObject("UI");
            canvas = go.AddComponent<Canvas>();
            canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            canvas.sortingOrder = 10;
            var sc = go.AddComponent<CanvasScaler>();
            sc.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            sc.referenceResolution = new Vector2(1920, 1080);
            sc.matchWidthOrHeight = 1f;
            go.AddComponent<GraphicRaycaster>();
            root = go.GetComponent<RectTransform>();
            if (EventSystem.current == null)
            {
                var es = new GameObject("EventSystem");
                es.AddComponent<EventSystem>();
                es.AddComponent<StandaloneInputModule>();
            }
        }

        public static Sprite S(string name)
        {
            Sprite s;
            if (sprites.TryGetValue(name, out s)) return s;
            s = Resources.Load<Sprite>("UI/" + name);
            sprites[name] = s;
            return s;
        }

        public static RectTransform Box(Transform parent, string name, Vector2 anchor, Vector2 pos, Vector2 size)
        {
            var go = new GameObject(name, typeof(RectTransform));
            var rt = go.GetComponent<RectTransform>();
            rt.SetParent(parent, false);
            rt.anchorMin = rt.anchorMax = rt.pivot = anchor;
            rt.anchoredPosition = pos;
            rt.sizeDelta = size;
            return rt;
        }

        public static RectTransform Fill(Transform parent, string name, float inset = 0f)
        {
            var go = new GameObject(name, typeof(RectTransform));
            var rt = go.GetComponent<RectTransform>();
            rt.SetParent(parent, false);
            rt.anchorMin = Vector2.zero;
            rt.anchorMax = Vector2.one;
            rt.offsetMin = new Vector2(inset, inset);
            rt.offsetMax = new Vector2(-inset, -inset);
            return rt;
        }

        public static Image Img(Transform parent, string sprite, Color c, Vector2 anchor, Vector2 pos, Vector2 size)
        {
            var rt = Box(parent, sprite ?? "img", anchor, pos, size);
            var im = rt.gameObject.AddComponent<Image>();
            im.sprite = sprite != null ? S(sprite) : null;
            im.color = c;
            im.raycastTarget = false;
            if (sprite == "panel" || sprite == "pill") im.type = Image.Type.Sliced;
            return im;
        }

        public static Image Panel(Transform parent, Color c, Vector2 anchor, Vector2 pos, Vector2 size)
        {
            var im = Img(parent, "panel", c, anchor, pos, size);
            im.raycastTarget = true;
            return im;
        }

        public static Text Txt(Transform parent, string s, int size, Color c, TextAnchor align, Vector2 anchor, Vector2 pos, Vector2 box, Font f = null, bool outline = true)
        {
            var rt = Box(parent, "txt", anchor, pos, box);
            var t = rt.gameObject.AddComponent<Text>();
            t.font = f ?? font;
            t.text = s;
            t.fontSize = size;
            t.color = c;
            t.alignment = align;
            t.horizontalOverflow = HorizontalWrapMode.Wrap;
            t.verticalOverflow = VerticalWrapMode.Overflow;
            t.raycastTarget = false;
            t.supportRichText = true;
            if (outline)
            {
                var o = rt.gameObject.AddComponent<Outline>();
                o.effectColor = new Color(0, 0, 0, 0.85f);
                o.effectDistance = new Vector2(2.5f, -2.5f);
            }
            return t;
        }

        /// <summary>A round, domed button (tinted) with a white icon and an optional label under it.</summary>
        public static HoldBtn Round(Transform parent, string icon, string label, Color c, Vector2 anchor, Vector2 pos, float size, Action click = null)
        {
            // white means the GTA-style dark glass circle; any other colour tints the light button
            bool glass = c.r > 0.9f && c.g > 0.9f && c.b > 0.9f;
            var im = Img(parent, glass ? "btn_round" : "btn_light", c, anchor, pos, new Vector2(size, size));
            im.raycastTarget = true;
            im.name = "btn_" + (icon ?? label);
            var hb = im.gameObject.AddComponent<HoldBtn>();
            hb.onClick = click;
            hb.image = im;
            hb.baseColor = c;
            if (icon != null)
            {
                var ic = Img(im.transform, "i_" + icon, Color.white, C, Vector2.zero, new Vector2(size * 0.56f, size * 0.56f));
                var sh = ic.gameObject.AddComponent<Shadow>();
                sh.effectColor = new Color(0, 0, 0, 0.5f);
                sh.effectDistance = new Vector2(2, -3);
                hb.icon = ic;
            }
            if (label != null)
                hb.label = Txt(im.transform, label, Mathf.RoundToInt(size * (icon != null ? 0.2f : 0.3f)), Color.white, TextAnchor.MiddleCenter, icon != null ? B : C,
                               icon != null ? new Vector2(0, -size * 0.2f) : Vector2.zero, new Vector2(size * 1.6f, size * 0.4f));
            return hb;
        }

        /// <summary>A wide rounded button with text (menus, shops).</summary>
        public static HoldBtn Wide(Transform parent, string label, Color c, Vector2 anchor, Vector2 pos, Vector2 size, Action click, int fontSize = 0)
        {
            var im = Img(parent, null, c, anchor, pos, size);
            im.raycastTarget = true;
            im.name = "btn_" + label;
            var hb = im.gameObject.AddComponent<HoldBtn>();
            hb.onClick = click;
            hb.image = im;
            hb.baseColor = c;
            hb.label = Txt(im.transform, label, fontSize > 0 ? fontSize : Mathf.RoundToInt(size.y * 0.5f), Color.white, TextAnchor.MiddleCenter, C, new Vector2(0, 2), size);
            return hb;
        }

        public static void Clear(Transform t)
        {
            for (int i = t.childCount - 1; i >= 0; i--) UnityEngine.Object.Destroy(t.GetChild(i).gameObject);
        }
    }

    /// <summary>A button that knows when it is held down (pedals, fire) and when it is tapped.</summary>
    public class HoldBtn : MonoBehaviour, IPointerDownHandler, IPointerUpHandler, IPointerExitHandler
    {
        public bool held;
        public Action onClick, onDown;
        public Image image, icon;
        public Text label;
        public Color baseColor;
        int pointer = -99;

        public void OnPointerDown(PointerEventData e)
        {
            held = true;
            pointer = e.pointerId;
            if (image != null) image.color = baseColor * 0.75f + new Color(0, 0, 0, 0.25f);
            transform.localScale = Vector3.one * 0.94f;
            if (onDown != null) onDown();
        }

        public void OnPointerUp(PointerEventData e)
        {
            if (e.pointerId != pointer) return;
            bool was = held;
            Release();
            if (was && onClick != null && RectTransformUtility.RectangleContainsScreenPoint((RectTransform)transform, e.position, null))
            {
                GameAudio.Ui("ui_click", 0.5f);
                onClick();
            }
        }

        public void OnPointerExit(PointerEventData e)
        {
            // pedals keep working while the finger slides a little; only a tap needs to end inside
        }

        void Release()
        {
            held = false;
            pointer = -99;
            if (image != null) image.color = baseColor;
            transform.localScale = Vector3.one;
        }

        void OnDisable() { Release(); }

        public void SetColor(Color c)
        {
            baseColor = c;
            if (image != null && !held) image.color = c;
        }
    }

    /// <summary>The movement joystick: appears where the thumb lands in the left part of the screen.</summary>
    public class Stick : MonoBehaviour, IPointerDownHandler, IDragHandler, IPointerUpHandler
    {
        public RectTransform baseRt, knob;
        public Vector2 value;
        Vector2 home;
        int pointer = -99;
        const float Radius = 120f;

        public void Setup(RectTransform b, RectTransform k)
        {
            baseRt = b;
            knob = k;
            home = b.anchoredPosition;
        }

        public void OnPointerDown(PointerEventData e)
        {
            pointer = e.pointerId;
            Vector2 lp;
            RectTransformUtility.ScreenPointToLocalPointInRectangle((RectTransform)baseRt.parent, e.position, null, out lp);
            baseRt.localPosition = lp;
            OnDrag(e);
        }

        public void OnDrag(PointerEventData e)
        {
            if (e.pointerId != pointer) return;
            Vector2 lp;
            RectTransformUtility.ScreenPointToLocalPointInRectangle(baseRt, e.position, null, out lp);
            Vector2 v = Vector2.ClampMagnitude(lp, Radius);
            knob.anchoredPosition = v;
            value = v / Radius;
            if (value.magnitude < 0.12f) value = Vector2.zero;
        }

        public void OnPointerUp(PointerEventData e)
        {
            if (e.pointerId != pointer) return;
            pointer = -99;
            value = Vector2.zero;
            knob.anchoredPosition = Vector2.zero;
            baseRt.anchoredPosition = home;
        }

        void OnDisable()
        {
            pointer = -99;
            value = Vector2.zero;
            if (knob != null) knob.anchoredPosition = Vector2.zero;
            if (baseRt != null) baseRt.anchoredPosition = home;
        }
    }

    /// <summary>Dragging anywhere else turns the camera.</summary>
    public class LookPad : MonoBehaviour, IPointerDownHandler, IDragHandler, IPointerUpHandler
    {
        int pointer = -99;
        public void OnPointerDown(PointerEventData e) { if (pointer == -99) pointer = e.pointerId; }
        public void OnDrag(PointerEventData e)
        {
            if (e.pointerId != pointer || Cam.I == null) return;
            float k = 1080f / Mathf.Max(1f, Screen.height);
            Cam.I.look += e.delta * k;
        }
        public void OnPointerUp(PointerEventData e) { if (e.pointerId == pointer) pointer = -99; }
        void OnDisable() { pointer = -99; }
    }
}

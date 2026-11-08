using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

namespace GridProto
{
    /// <summary>Movement joystick that appears wherever the left thumb touches down.</summary>
    public class FloatingJoystick : MonoBehaviour, IPointerDownHandler, IDragHandler, IPointerUpHandler
    {
        public RectTransform zone;      // pivot (0,0)
        public RectTransform baseRect;  // anchored at the zone's bottom-left corner
        public RectTransform knob;      // anchored at the base centre
        public Graphic ring;
        public CanvasGroup group;
        public float radius = 120f;
        public Vector2 restPosition = new Vector2(300f, 270f);
        public Color ringIdle = new Color(1f, 1f, 1f, 0.55f);
        public Color ringRun = new Color(1f, 0.78f, 0.35f, 0.95f);

        const int None = int.MinValue;
        int pointerId = None;

        void OnEnable() { Release(); }
        void OnDisable() { Release(); }
        void OnApplicationPause(bool paused) { if (paused) Release(); }

        public void OnPointerDown(PointerEventData e)
        {
            if (pointerId != None) return;
            pointerId = e.pointerId;
            Vector2 local;
            if (zone != null && RectTransformUtility.ScreenPointToLocalPointInRectangle(zone, e.position, e.pressEventCamera, out local))
            {
                Vector2 size = zone.rect.size;
                float m = radius + 24f;
                local.x = Mathf.Clamp(local.x, m, Mathf.Max(m, size.x - m));
                local.y = Mathf.Clamp(local.y, m, Mathf.Max(m, size.y - m));
                baseRect.anchoredPosition = local;
            }
            if (group != null) group.alpha = 1f;
            UpdateKnob(e);
        }

        public void OnDrag(PointerEventData e)
        {
            if (e.pointerId == pointerId) UpdateKnob(e);
        }

        public void OnPointerUp(PointerEventData e)
        {
            if (e.pointerId == pointerId) Release();
        }

        void UpdateKnob(PointerEventData e)
        {
            if (baseRect == null || knob == null) return;
            Vector2 local;
            if (!RectTransformUtility.ScreenPointToLocalPointInRectangle(baseRect, e.position, e.pressEventCamera, out local)) return;
            Vector2 offset = Vector2.ClampMagnitude(local, radius);
            knob.anchoredPosition = offset;
            Vector2 v = offset / radius;
            float magnitude = v.magnitude;
            const float deadZone = 0.1f;
            TouchState.Move = magnitude < deadZone ? Vector2.zero : v / magnitude * Mathf.InverseLerp(deadZone, 1f, magnitude);
        }

        void Release()
        {
            pointerId = None;
            TouchState.Move = Vector2.zero;
            if (knob != null) knob.anchoredPosition = Vector2.zero;
            if (baseRect != null) baseRect.anchoredPosition = restPosition;
            if (group != null) group.alpha = 0.55f;
        }

        void Update()
        {
            if (ring == null) return;
            bool running = pointerId != None && TouchState.Move.magnitude > 0.92f && TouchState.Move.y > 0.55f;
            ring.color = Color.Lerp(ring.color, running ? ringRun : ringIdle, 1f - Mathf.Exp(-12f * Time.unscaledDeltaTime));
        }
    }
}

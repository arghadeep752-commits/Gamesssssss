using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

namespace GridProto
{
    /// <summary>On-screen button that fires the moment it is touched (no waiting for release).</summary>
    public class TouchButton : MonoBehaviour, IPointerDownHandler, IPointerUpHandler
    {
        public System.Action onPress;
        public Graphic fill;
        public Color normalColor = new Color(0f, 0f, 0f, 0.38f);
        public Color pressedColor = new Color(1f, 1f, 1f, 0.3f);

        public bool IsHeld { get; private set; }

        float scale = 1f, appliedScale = 1f;

        public void OnPointerDown(PointerEventData e)
        {
            IsHeld = true;
            if (onPress != null) onPress();
        }

        public void OnPointerUp(PointerEventData e)
        {
            IsHeld = false;
        }

        void OnDisable()
        {
            IsHeld = false;
            scale = appliedScale = 1f;
            transform.localScale = Vector3.one;
            if (fill != null) fill.color = normalColor;
        }

        void Update()
        {
            scale = Mathf.Lerp(scale, IsHeld ? 0.9f : 1f, 1f - Mathf.Exp(-25f * Time.unscaledDeltaTime));
            if (Mathf.Abs(scale - appliedScale) > 0.0005f)
            {
                appliedScale = scale;
                transform.localScale = new Vector3(scale, scale, 1f);
            }
            if (fill != null) fill.color = IsHeld ? pressedColor : normalColor;
        }
    }
}

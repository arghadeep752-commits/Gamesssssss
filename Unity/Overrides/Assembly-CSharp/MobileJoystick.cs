using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

/// <summary>On-screen movement joystick: drag inside the ring, the knob follows the finger (clamped to the ring).</summary>
public class MobileJoystick : MonoBehaviour, IDragHandler, IEventSystemHandler, IPointerUpHandler, IPointerDownHandler
{
    private Image joystickBackground;
    private Image joystickHandle;
    private Vector2 inputVector;

    public float Horizontal => inputVector.x;
    public float Vertical => inputVector.y;

    private void Start()
    {
        joystickBackground = GetComponent<Image>();
        foreach (Transform child in transform)
        {
            var img = child.GetComponent<Image>();
            if (img != null) { joystickHandle = img; break; }
        }
    }

    public void OnDrag(PointerEventData eventData)
    {
        if (joystickBackground == null) return;
        RectTransform bg = joystickBackground.rectTransform;
        if (!RectTransformUtility.ScreenPointToLocalPointInRectangle(bg, eventData.position, eventData.pressEventCamera, out Vector2 local))
            return;
        Vector2 size = bg.rect.size;
        Vector2 pivotOffset = new Vector2((bg.pivot.x - 0.5f) * size.x, (bg.pivot.y - 0.5f) * size.y);
        Vector2 fromCentre = local + pivotOffset;
        Vector2 v = new Vector2(fromCentre.x / (size.x * 0.5f), fromCentre.y / (size.y * 0.5f));
        inputVector = v.magnitude > 1f ? v.normalized : v;
        if (joystickHandle != null)
            joystickHandle.rectTransform.anchoredPosition = new Vector2(inputVector.x * size.x * 0.4f, inputVector.y * size.y * 0.4f);
    }

    public void OnPointerDown(PointerEventData eventData)
    {
        OnDrag(eventData);
    }

    public void OnPointerUp(PointerEventData eventData)
    {
        inputVector = Vector2.zero;
        if (joystickHandle != null) joystickHandle.rectTransform.anchoredPosition = Vector2.zero;
    }

    public float GetInputDistance()
    {
        return inputVector.magnitude;
    }

    private void OnDisable()
    {
        inputVector = Vector2.zero;
        if (joystickHandle != null) joystickHandle.rectTransform.anchoredPosition = Vector2.zero;
    }
}

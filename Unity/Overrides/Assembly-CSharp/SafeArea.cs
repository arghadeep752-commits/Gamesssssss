using UnityEngine;

/// <summary>Keeps a UI panel inside the phone's safe area (away from notches and rounded corners).</summary>
public class SafeArea : MonoBehaviour
{
    private RectTransform rectTransform;
    private Rect lastSafeArea;
    private ScreenOrientation lastOrientation;

    private void Awake()
    {
        rectTransform = GetComponent<RectTransform>();
        ApplySafeArea();
    }

    private void Update()
    {
        if (Screen.safeArea != lastSafeArea || Screen.orientation != lastOrientation) ApplySafeArea();
    }

    private void ApplySafeArea()
    {
        if (rectTransform == null) return;
        Rect safe = Screen.safeArea;
        lastSafeArea = safe;
        lastOrientation = Screen.orientation;
        if (Screen.width <= 0 || Screen.height <= 0) return;
        Vector2 min = safe.position;
        Vector2 max = safe.position + safe.size;
        min.x /= Screen.width; min.y /= Screen.height;
        max.x /= Screen.width; max.y /= Screen.height;
        rectTransform.anchorMin = min;
        rectTransform.anchorMax = max;
    }
}

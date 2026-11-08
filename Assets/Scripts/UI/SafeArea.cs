using UnityEngine;

namespace GridProto
{
    /// <summary>Keeps the buttons clear of the camera hole / notch and rounded corners.</summary>
    [RequireComponent(typeof(RectTransform))]
    public class SafeArea : MonoBehaviour
    {
        RectTransform rectTransform;
        Rect lastArea;
        int lastWidth, lastHeight;

        void Awake()
        {
            rectTransform = GetComponent<RectTransform>();
            Apply();
        }

        void Update()
        {
            if (Screen.safeArea != lastArea || Screen.width != lastWidth || Screen.height != lastHeight) Apply();
        }

        void Apply()
        {
            Rect area = Screen.safeArea;
            lastArea = area;
            lastWidth = Screen.width;
            lastHeight = Screen.height;
            if (Screen.width <= 0 || Screen.height <= 0) return;
            rectTransform.anchorMin = new Vector2(area.xMin / Screen.width, area.yMin / Screen.height);
            rectTransform.anchorMax = new Vector2(area.xMax / Screen.width, area.yMax / Screen.height);
            rectTransform.offsetMin = Vector2.zero;
            rectTransform.offsetMax = Vector2.zero;
        }
    }
}

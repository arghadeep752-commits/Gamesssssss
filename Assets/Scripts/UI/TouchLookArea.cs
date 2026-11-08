using UnityEngine;
using UnityEngine.EventSystems;

namespace GridProto
{
    /// <summary>Right side of the screen: drag to look around.</summary>
    public class TouchLookArea : MonoBehaviour, IPointerDownHandler, IDragHandler, IPointerUpHandler
    {
        const int None = int.MinValue;
        int pointerId = None;
        Vector2 last;

        public void OnPointerDown(PointerEventData e)
        {
            if (pointerId != None) return;
            pointerId = e.pointerId;
            last = e.position;
        }

        public void OnDrag(PointerEventData e)
        {
            if (e.pointerId != pointerId) return;
            TouchState.LookDelta += e.position - last;
            last = e.position;
        }

        public void OnPointerUp(PointerEventData e)
        {
            if (e.pointerId == pointerId) pointerId = None;
        }

        void OnDisable() { pointerId = None; }
        void OnApplicationPause(bool paused) { if (paused) pointerId = None; }
    }
}

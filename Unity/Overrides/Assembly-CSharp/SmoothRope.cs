using UnityEngine;

/// <summary>A sagging rope drawn between two points (balloon to anchor).</summary>
public class SmoothRope : MonoBehaviour
{
    [Header("Rope Connections")]
    public Transform topPoint;
    public Transform bottomPoint;

    [Header("Rope Appearance")]
    public int segments;
    public float ropeSag;

    private LineRenderer lineRenderer;

    private void Start()
    {
        lineRenderer = GetComponent<LineRenderer>();
        if (lineRenderer == null) { lineRenderer = gameObject.AddComponent<LineRenderer>(); lineRenderer.widthMultiplier = 0.03f; }
        if (segments < 2) segments = 20;
        lineRenderer.positionCount = segments + 1;
        lineRenderer.useWorldSpace = true;
    }

    private void Update()
    {
        if (topPoint == null || bottomPoint == null || lineRenderer == null) return;
        if (lineRenderer.positionCount != segments + 1) lineRenderer.positionCount = segments + 1;
        Vector3 a = topPoint.position;
        Vector3 b = bottomPoint.position;
        float length = Vector3.Distance(a, b);
        for (int i = 0; i <= segments; i++)
        {
            float t = i / (float)segments;
            Vector3 p = Vector3.Lerp(a, b, t);
            p.y -= Mathf.Sin(t * Mathf.PI) * ropeSag * length;
            lineRenderer.SetPosition(i, p);
        }
    }
}

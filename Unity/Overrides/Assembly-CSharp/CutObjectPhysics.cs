using UnityEngine;

/// <summary>The cut chain tips over sideways and falls instead of dropping straight down.</summary>
public class CutObjectPhysics : MonoBehaviour
{
    [Header("Sideways Fall Settings")]
    public float sidewaysForce;
    public float tipTorque;

    private Rigidbody rb;

    private void Awake()
    {
        rb = GetComponent<Rigidbody>();
    }

    public void TriggerSidewaysFall(Vector3 cutterPosition)
    {
        if (rb == null) rb = gameObject.AddComponent<Rigidbody>();
        rb.isKinematic = false;
        rb.useGravity = true;
        Vector3 away = transform.position - cutterPosition;
        away.y = 0f;
        if (away.sqrMagnitude < 0.001f) away = transform.right;
        rb.AddForce(away.normalized * sidewaysForce, ForceMode.Impulse);
        rb.AddTorque(Vector3.Cross(Vector3.up, away.normalized) * tipTorque, ForceMode.Impulse);
    }
}

using UnityEngine;

/// <summary>The held item sways a little when looking around and bobs while walking, like in Granny.</summary>
public class ItemSway : MonoBehaviour
{
    [Header("Player & Camera Tracking")]
    public Transform playerTransform;
    public Transform playerCamera;

    private Rigidbody playerRigidbody;
    private CharacterController playerController;
    private Vector3 lastPlayerPosition;

    [Header("Sway Settings (Looking Around)")]
    public float swayAmount;
    public float maxSwayAmount;
    public float swaySmoothness;

    [Header("Bobbing Settings (Walking)")]
    public float bobSpeed;
    public float bobAmount;

    [Header("Wall Collision Avoidance (Anti-Clip)")]
    public LayerMask obstacleLayers;
    public float detectDistance;
    public Vector3 wallPullOffset;
    public Vector3 wallRotationOffset;

    private Vector3 initialPosition;
    private Quaternion initialRotation;
    private float bobTimer;
    private Quaternion lastCameraRotation;

    private void Start()
    {
        initialPosition = transform.localPosition;
        initialRotation = transform.localRotation;
        if (playerCamera == null && transform.parent != null) playerCamera = transform.parent;
        if (playerTransform == null)
        {
            var p = GameSave.PlayerObject();
            if (p != null) playerTransform = p.transform;
        }
        if (playerTransform != null)
        {
            playerRigidbody = playerTransform.GetComponent<Rigidbody>();
            playerController = playerTransform.GetComponent<CharacterController>();
            lastPlayerPosition = playerTransform.position;
        }
        if (playerCamera != null) lastCameraRotation = playerCamera.rotation;
        if (swaySmoothness <= 0f) swaySmoothness = 8f;
        if (maxSwayAmount <= 0f) maxSwayAmount = 0.06f;
    }

    private void Update()
    {
        float dt = Time.deltaTime;
        if (dt <= 0f) return;
        Vector3 targetPos = initialPosition;
        Quaternion targetRot = initialRotation;

        if (playerCamera != null)
        {
            Quaternion delta = Quaternion.Inverse(lastCameraRotation) * playerCamera.rotation;
            lastCameraRotation = playerCamera.rotation;
            Vector3 e = delta.eulerAngles;
            float yaw = e.y > 180f ? e.y - 360f : e.y;
            float pitch = e.x > 180f ? e.x - 360f : e.x;
            float sx = Mathf.Clamp(-yaw * swayAmount * 0.02f, -maxSwayAmount, maxSwayAmount);
            float sy = Mathf.Clamp(pitch * swayAmount * 0.02f, -maxSwayAmount, maxSwayAmount);
            targetPos += new Vector3(sx, sy, 0f);
        }

        if (playerTransform != null)
        {
            Vector3 moved = playerTransform.position - lastPlayerPosition;
            lastPlayerPosition = playerTransform.position;
            moved.y = 0f;
            float speed = moved.magnitude / dt;
            if (speed > 0.2f && bobSpeed > 0f)
            {
                bobTimer += dt * bobSpeed;
                targetPos += new Vector3(Mathf.Cos(bobTimer * 0.5f) * bobAmount * 0.5f, Mathf.Sin(bobTimer) * bobAmount, 0f);
            }
            else bobTimer = 0f;
        }

        if (detectDistance > 0f && playerCamera != null && obstacleLayers.value != 0)
        {
            if (Physics.Raycast(playerCamera.position, playerCamera.forward, out RaycastHit hit, detectDistance, obstacleLayers, QueryTriggerInteraction.Ignore))
            {
                float k = 1f - hit.distance / detectDistance;
                targetPos += wallPullOffset * k;
                targetRot *= Quaternion.Euler(wallRotationOffset * k);
            }
        }

        float t = 1f - Mathf.Exp(-swaySmoothness * dt);
        transform.localPosition = Vector3.Lerp(transform.localPosition, targetPos, t);
        transform.localRotation = Quaternion.Slerp(transform.localRotation, targetRot, t);
    }

    private void OnDrawGizmosSelected()
    {
        if (playerCamera == null) return;
        Gizmos.color = Color.yellow;
        Gizmos.DrawLine(playerCamera.position, playerCamera.position + playerCamera.forward * detectDistance);
    }
}

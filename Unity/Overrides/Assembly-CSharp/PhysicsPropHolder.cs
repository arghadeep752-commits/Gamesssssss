using System.Collections;
using UnityEngine;

/// <summary>A painting that drops off the wall when the player walks right past it; Granny hears the crash.</summary>
public class PhysicsPropHolder : MonoBehaviour
{
    [Header("Audio Settings")]
    public AudioSource audioSource;
    public AudioClip fallSound;

    [Header("AI Alert Settings")]
    public float alertRange;

    [Header("Trap Trigger Settings")]
    public float triggerDistance;
    public LayerMask obstacleLayers;

    [Header("Automatic Reset Settings")]
    public float autoResetDelay;

    private bool hasFallenFromWall;
    private bool hasLandedOnGround;
    private Vector3 initialPosition;
    private Quaternion initialRotation;
    private Rigidbody rb;
    private Coroutine resetCoroutine;
    private Transform player;

    private void Awake()
    {
        rb = GetComponent<Rigidbody>();
        if (rb == null) rb = GetComponentInChildren<Rigidbody>();
        initialPosition = transform.position;
        initialRotation = transform.rotation;
        if (audioSource == null) audioSource = GetComponent<AudioSource>();
        FreezeOnWall();
    }

    private void FreezeOnWall()
    {
        if (rb != null) { rb.isKinematic = true; rb.useGravity = true; }
    }

    private void Update()
    {
        if (hasFallenFromWall) return;
        if (player == null) { GameObject p = GameSave.PlayerObject(); if (p != null) player = p.transform; else return; }
        float d = Vector3.Distance(player.position, transform.position);
        if (d > (triggerDistance > 0f ? triggerDistance : 1f) + 0.6f) return;
        if (obstacleLayers.value != 0 && Physics.Linecast(transform.position, player.position, obstacleLayers, QueryTriggerInteraction.Ignore)) return;
        MakePaintingFall();
    }

    public void MakePaintingFall()
    {
        if (hasFallenFromWall) return;
        hasFallenFromWall = true;
        hasLandedOnGround = false;
        if (rb != null) { rb.isKinematic = false; rb.AddForce(transform.forward * 0.5f + Vector3.down, ForceMode.Impulse); }
        else StartCoroutine(SimpleFall());
    }

    private IEnumerator SimpleFall()
    {
        Vector3 start = transform.position;
        Vector3 end = start + Vector3.down * 1.2f;
        if (Physics.Raycast(start, Vector3.down, out RaycastHit hit, 4f, Physics.DefaultRaycastLayers, QueryTriggerInteraction.Ignore)) end = hit.point + Vector3.up * 0.05f;
        float t = 0f;
        while (t < 0.5f) { t += Time.deltaTime; transform.position = Vector3.Lerp(start, end, (t / 0.5f) * (t / 0.5f)); yield return null; }
        OnLanded();
    }

    private void OnCollisionEnter(Collision collision)
    {
        if (!hasFallenFromWall || hasLandedOnGround) return;
        OnLanded();
    }

    private void OnLanded()
    {
        if (hasLandedOnGround) return;
        hasLandedOnGround = true;
        if (audioSource != null && fallSound != null) audioSource.PlayOneShot(fallSound);
        GrannyAI g = GrannyAI.Instance;
        if (g != null && Vector3.Distance(g.transform.position, transform.position) <= (alertRange > 0f ? alertRange : 20f)) g.HearNoise(transform.position, "painting");
        if (resetCoroutine != null) StopCoroutine(resetCoroutine);
        resetCoroutine = StartCoroutine(AutoResetRoutine());
    }

    private IEnumerator AutoResetRoutine()
    {
        yield return new WaitForSeconds(autoResetDelay > 0f ? autoResetDelay : 7f);
        ResetToInitialPosition();
    }

    public void ResetToInitialPosition()
    {
        if (rb != null) { rb.isKinematic = true; rb.linearVelocity = Vector3.zero; rb.angularVelocity = Vector3.zero; }
        transform.SetPositionAndRotation(initialPosition, initialRotation);
        hasFallenFromWall = false;
        hasLandedOnGround = false;
    }

    private void OnDrawGizmosSelected()
    {
        Gizmos.color = Color.magenta;
        Gizmos.DrawWireSphere(transform.position, triggerDistance);
    }
}

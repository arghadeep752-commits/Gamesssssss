using System.Collections;
using UnityEngine;

/// <summary>A lamp, chair or table that crashes down when bumped: Granny hears it; it is back in place a few seconds later.</summary>
public class DistractionObject : MonoBehaviour
{
    [Header("Reset Settings")]
    public float resetDelay;
    public float returnSpeed;

    [Header("Audio Settings")]
    public AudioClip crashSound;
    public float noiseVelocityThreshold;

    private float soundAlertRadius = 30f;
    private Rigidbody rb;
    private AudioSource audioSource;
    private Vector3 originalLocalPosition;
    private Quaternion originalLocalRotation;
    private Transform originalParent;
    private bool hasCrashed;
    private bool isResetting;
    private float startTime;

    private void Start()
    {
        rb = GetComponent<Rigidbody>();
        audioSource = GetComponent<AudioSource>();
        if (audioSource == null) { audioSource = gameObject.AddComponent<AudioSource>(); audioSource.spatialBlend = 1f; audioSource.playOnAwake = false; }
        originalParent = transform.parent;
        originalLocalPosition = transform.localPosition;
        originalLocalRotation = transform.localRotation;
        startTime = Time.time;
        if (noiseVelocityThreshold <= 0f) noiseVelocityThreshold = 1.5f;
    }

    private void OnCollisionEnter(Collision collision)
    {
        if (hasCrashed || isResetting || Time.time - startTime < 2f) return;
        if (collision.relativeVelocity.magnitude < noiseVelocityThreshold) return;
        if (collision.collider.GetComponentInParent<CharacterController>() != null) return;
        hasCrashed = true;
        PlayCrashNoise();
        AlertGrannyAI();
        StartCoroutine(StartResetTimer());
    }

    private void PlayCrashNoise()
    {
        if (crashSound != null) audioSource.PlayOneShot(crashSound);
    }

    private void AlertGrannyAI()
    {
        GrannyAI g = GrannyAI.Instance;
        if (g != null && Vector3.Distance(g.transform.position, transform.position) <= soundAlertRadius) g.HearNoise(transform.position, name);
    }

    private IEnumerator StartResetTimer()
    {
        yield return new WaitForSeconds(Mathf.Max(1f, resetDelay));
        isResetting = true;
        if (rb != null) rb.isKinematic = true;
        Vector3 targetWorldPosition = originalParent != null ? originalParent.TransformPoint(originalLocalPosition) : originalLocalPosition;
        Quaternion targetWorldRotation = originalParent != null ? originalParent.rotation * originalLocalRotation : originalLocalRotation;
        float speed = returnSpeed > 0f ? returnSpeed : 10f;
        while ((transform.position - targetWorldPosition).sqrMagnitude > 0.0004f)
        {
            transform.position = Vector3.Lerp(transform.position, targetWorldPosition, 1f - Mathf.Exp(-speed * 0.5f * Time.deltaTime));
            transform.rotation = Quaternion.Slerp(transform.rotation, targetWorldRotation, 1f - Mathf.Exp(-speed * 0.5f * Time.deltaTime));
            yield return null;
        }
        transform.SetPositionAndRotation(targetWorldPosition, targetWorldRotation);
        if (rb != null) { rb.isKinematic = false; rb.linearVelocity = Vector3.zero; rb.angularVelocity = Vector3.zero; }
        hasCrashed = false;
        isResetting = false;
    }
}

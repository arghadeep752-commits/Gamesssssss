using UnityEngine;

/// <summary>The doorbell tripwire: walking through it rings the bell and Granny comes to look.</summary>
public class TripwireTrap : MonoBehaviour
{
    [Header("Audio Settings")]
    public AudioClip bellSound;

    [Header("Cooldown Settings")]
    public float triggerCooldown;

    private AudioSource audioSource;
    private float nextAllowedTriggerTime;

    private void Start()
    {
        audioSource = GetComponent<AudioSource>();
        if (audioSource == null) { audioSource = gameObject.AddComponent<AudioSource>(); audioSource.spatialBlend = 1f; audioSource.playOnAwake = false; }
    }

    private void OnTriggerEnter(Collider other)
    {
        if (Time.time < nextAllowedTriggerTime || other.GetComponentInParent<FPSController>() == null) return;
        TriggerTheBell();
    }

    private void TriggerTheBell()
    {
        nextAllowedTriggerTime = Time.time + Mathf.Max(0.5f, triggerCooldown);
        if (bellSound != null) audioSource.PlayOneShot(bellSound);
        GrannyAI.AlertAll(transform.position, "doorbell");
    }
}

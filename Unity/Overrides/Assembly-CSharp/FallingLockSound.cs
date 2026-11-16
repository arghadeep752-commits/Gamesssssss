using UnityEngine;

/// <summary>A lock knocked off the main door clanks when it hits the floor.</summary>
public class FallingLockSound : MonoBehaviour
{
    public AudioSource audioSource;
    public AudioClip floorImpactSound;

    private bool hasLanded;

    private void OnCollisionEnter(Collision collision)
    {
        if (hasLanded || collision.relativeVelocity.magnitude < 0.5f) return;
        var rb = GetComponent<Rigidbody>();
        if (rb != null && rb.isKinematic) return;
        hasLanded = true;
        if (audioSource == null) audioSource = GetComponent<AudioSource>();
        if (audioSource != null && floorImpactSound != null) audioSource.PlayOneShot(floorImpactSound);
    }
}

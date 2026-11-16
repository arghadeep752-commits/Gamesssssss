using UnityEngine;

/// <summary>
/// An item the player can pick up (keys, hammer, chain cutter, tape...). When it hits something hard enough it makes
/// a sound and Granny hears it - unless it lands on silent ground (grass), where it only makes a soft thud.
/// </summary>
public class InteractableItem : MonoBehaviour
{
    [Header("Item Info")]
    public string itemName;

    [Header("Multi-Hold Point Setting")]
    public string targetHoldPointName;

    [Header("Audio Settings")]
    public AudioClip pickupSound;
    public AudioClip dropSound;

    [Header("Silent Ground (e.g. grass outside)")]
    public float silentGroundVolume;

    [Header("Impact Settings")]
    public float minImpactSpeed;
    public float noiseCooldown;

    [HideInInspector]
    public bool isHeld;

    private AudioSource myAudioSource;
    private float lastNoiseTime = -100f;
    private float spawnTime;

    private void Awake()
    {
        myAudioSource = GetComponent<AudioSource>();
        if (myAudioSource == null)
        {
            myAudioSource = gameObject.AddComponent<AudioSource>();
            myAudioSource.playOnAwake = false;
            myAudioSource.spatialBlend = 1f;
            myAudioSource.minDistance = 1.5f;
            myAudioSource.maxDistance = 25f;
        }
        if (minImpactSpeed <= 0f) minImpactSpeed = 1.2f;
        if (noiseCooldown <= 0f) noiseCooldown = 0.6f;
        spawnTime = Time.time;
    }

    public virtual void UseItem()
    {
    }

    private void OnCollisionEnter(Collision collision)
    {
        if (isHeld || Time.time - spawnTime < 1.5f) return;
        if (collision.relativeVelocity.magnitude < minImpactSpeed) return;
        if (Time.time - lastNoiseTime < noiseCooldown) return;
        if (collision.collider != null && collision.collider.GetComponentInParent<CharacterController>() != null) return;
        lastNoiseTime = Time.time;
        Vector3 point = collision.contactCount > 0 ? collision.GetContact(0).point : transform.position;
        bool silent = SilentGroundZone.IsSilentAt(point);
        if (dropSound != null && myAudioSource != null)
        {
            float volume = silent ? silentGroundVolume : 1f;
            if (volume > 0f) myAudioSource.PlayOneShot(dropSound, volume);
        }
        if (!silent) GrannyAI.AlertAll(transform.position, "item " + itemName);
    }
}

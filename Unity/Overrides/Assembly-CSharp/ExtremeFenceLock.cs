using UnityEngine;

/// <summary>The Extreme-mode fence: removed when the lever is pulled.</summary>
public class ExtremeFenceLock : MonoBehaviour
{
    [Header("Audio Settings")]
    public AudioSource audioSource;
    public AudioClip fenceOpeningSound;

    private void Start()
    {
        if (audioSource == null) audioSource = GetComponent<AudioSource>();
    }

    public void UnlockAndRemoveFence()
    {
        if (fenceOpeningSound != null) DimnightUtil.PlayAt(fenceOpeningSound, transform.position);
        Debug.Log("Extreme Fence Lock Disappeared!");
        gameObject.SetActive(false);
    }
}

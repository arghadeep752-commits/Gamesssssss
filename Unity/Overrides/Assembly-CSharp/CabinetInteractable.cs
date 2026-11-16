using UnityEngine;

/// <summary>A cabinet drawer or door that slides out along its Z axis.</summary>
public class CabinetInteractable : MonoBehaviour
{
    [Header("Sliding Movement Settings (Z-Axis)")]
    public float openDistance;
    public float doorSpeed;

    [Header("Audio")]
    public AudioClip openSound;
    public AudioClip closeSound;
    public bool isOpen;

    private bool isMoving;
    private AudioSource myAudioSource;
    private Vector3 closedPosition;
    private Vector3 openPosition;
    private Vector3 targetPosition;

    private void Start()
    {
        myAudioSource = GetComponent<AudioSource>();
        if (myAudioSource == null) { myAudioSource = gameObject.AddComponent<AudioSource>(); myAudioSource.spatialBlend = 1f; myAudioSource.playOnAwake = false; }
        closedPosition = transform.localPosition;
        openPosition = closedPosition + Vector3.forward * openDistance;
        targetPosition = isOpen ? openPosition : closedPosition;
        transform.localPosition = targetPosition;
    }

    private void Update()
    {
        if (!isMoving) return;
        transform.localPosition = Vector3.MoveTowards(transform.localPosition, targetPosition, Mathf.Max(0.1f, doorSpeed) * Time.deltaTime);
        if ((transform.localPosition - targetPosition).sqrMagnitude < 0.000001f) { transform.localPosition = targetPosition; isMoving = false; }
    }

    public void Interact(string heldItemName)
    {
        isOpen = !isOpen;
        targetPosition = isOpen ? openPosition : closedPosition;
        isMoving = true;
        AudioClip c = isOpen ? openSound : closeSound;
        if (c != null) myAudioSource.PlayOneShot(c);
    }
}

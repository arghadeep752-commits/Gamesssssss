using UnityEngine;

/// <summary>A drawer that slides in and out when the hand button is pressed near it.</summary>
public class DrawerPivotAnimation : MonoBehaviour
{
    private bool isOpen;

    [Header("Movement Settings")]
    public float openDistance;
    public float slideSpeed;

    [Header("Audio Settings")]
    public AudioSource audioSource;
    public AudioClip openSound;
    public AudioClip closeSound;

    [Header("Mobile UI Settings")]
    public GameObject handButtonUI;
    public float interactionDistance;

    private Vector3 closedPosition;
    private Vector3 openPosition;
    private Vector3 targetPosition;
    private Transform playerTransform;

    private void Start()
    {
        closedPosition = transform.localPosition;
        openPosition = closedPosition + Vector3.forward * openDistance;
        targetPosition = closedPosition;
        GameObject p = GameSave.PlayerObject();
        if (p != null) playerTransform = p.transform;
        if (audioSource == null) audioSource = GetComponent<AudioSource>();
    }

    private void Update()
    {
        if (transform.localPosition != targetPosition)
            transform.localPosition = Vector3.MoveTowards(transform.localPosition, targetPosition, Mathf.Max(0.1f, slideSpeed) * Time.deltaTime);
    }

    public void Interact()
    {
        isOpen = !isOpen;
        targetPosition = isOpen ? openPosition : closedPosition;
        AudioClip c = isOpen ? openSound : closeSound;
        if (c != null) { if (audioSource != null) audioSource.PlayOneShot(c); else DimnightUtil.PlayAt(c, transform.position); }
        Debug.Log("Drawer Pivot Interacted! Open state: " + isOpen);
    }
}

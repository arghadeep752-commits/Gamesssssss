using UnityEngine;

/// <summary>A drawer that slides out on its local Z axis.</summary>
public class GrannyDrawer : MonoBehaviour
{
    [Header("Movement Configuration")]
    public float slideDistance;
    public float speed;

    [Header("Audio Settings")]
    public AudioSource audioSource;
    public AudioClip openSound;
    public AudioClip closeSound;

    private bool isOpen;
    private Vector3 closedPosition;
    private Vector3 openPosition;
    private Vector3 targetPosition;

    private void Start()
    {
        closedPosition = transform.localPosition;
        openPosition = closedPosition + Vector3.forward * slideDistance;
        targetPosition = closedPosition;
        if (audioSource == null) audioSource = GetComponent<AudioSource>();
    }

    private void Update()
    {
        if (transform.localPosition != targetPosition)
            transform.localPosition = Vector3.MoveTowards(transform.localPosition, targetPosition, Mathf.Max(0.1f, speed) * Time.deltaTime);
    }

    public void ToggleDrawer()
    {
        isOpen = !isOpen;
        targetPosition = isOpen ? openPosition : closedPosition;
        AudioClip c = isOpen ? openSound : closeSound;
        if (c != null) { if (audioSource != null) audioSource.PlayOneShot(c); else DimnightUtil.PlayAt(c, transform.position); }
        Debug.Log("Drawer toggled! Open state: " + isOpen);
    }
}

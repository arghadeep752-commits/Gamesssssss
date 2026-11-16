using System.Collections;
using UnityEngine;

/// <summary>The bookshelf slides aside once the Secret Book is put back in its slot, opening the secret room.</summary>
public class SecretBookshelfDoor : MonoBehaviour
{
    [Header("Linked Lock")]
    public EscapeLockElement lockElement;

    [Header("Movement Settings")]
    public Vector3 slideOffset;
    public float slideSpeed;

    [Header("Audio")]
    public AudioSource bookshelfAudioSource;
    public AudioClip scrapingSound;

    private Vector3 closedPosition;
    private Vector3 openPosition;
    private bool standardSequenceTriggered;

    private void Start()
    {
        closedPosition = transform.position;
        openPosition = closedPosition + transform.TransformDirection(slideOffset);
    }

    private void Update()
    {
        if (standardSequenceTriggered || lockElement == null || !lockElement.IsEffectivelyUnlocked()) return;
        standardSequenceTriggered = true;
        StartCoroutine(SlideOpenRoutine());
    }

    private IEnumerator SlideOpenRoutine()
    {
        if (scrapingSound != null)
        {
            if (bookshelfAudioSource != null) bookshelfAudioSource.PlayOneShot(scrapingSound);
            else DimnightUtil.PlayAt(scrapingSound, transform.position);
        }
        float elapsedTime = 0f;
        Vector3 startPos = transform.position;
        float duration = Mathf.Max(0.2f, Vector3.Distance(startPos, openPosition) / Mathf.Max(0.01f, slideSpeed));
        while (elapsedTime < duration)
        {
            elapsedTime += Time.deltaTime;
            transform.position = Vector3.Lerp(startPos, openPosition, Mathf.SmoothStep(0f, 1f, elapsedTime / duration));
            yield return null;
        }
        transform.position = openPosition;
        foreach (UnityEngine.AI.NavMeshObstacle o in GetComponentsInChildren<UnityEngine.AI.NavMeshObstacle>()) o.carving = true;
    }
}

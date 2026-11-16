using System.Collections;
using UnityEngine;

/// <summary>The coffin lid: a door like the others, but the first time it opens a swarm of bats flies out.</summary>
public class CoffinDoorInteractable : DoorInteractable
{
    [Header("Jumpscare Settings")]
    public ParticleSystem batJumpscareSystem;
    public AudioClip jumpscareAudioClip;

    private bool hasTriggeredScare;

    private void Awake()
    {
        StartCoroutine(CheckForDoorOpenRoutine());
    }

    private IEnumerator CheckForDoorOpenRoutine()
    {
        while (!hasTriggeredScare)
        {
            if (isOpen)
            {
                TriggerBatJumpscare();
                yield break;
            }
            yield return null;
        }
    }

    private void TriggerBatJumpscare()
    {
        if (hasTriggeredScare) return;
        hasTriggeredScare = true;
        if (batJumpscareSystem != null)
        {
            batJumpscareSystem.gameObject.SetActive(true);
            batJumpscareSystem.Play(true);
        }
        if (jumpscareAudioClip != null)
        {
            var src = GetComponent<AudioSource>();
            if (src != null) src.PlayOneShot(jumpscareAudioClip);
            else AudioSource.PlayClipAtPoint(jumpscareAudioClip, transform.position);
        }
    }
}

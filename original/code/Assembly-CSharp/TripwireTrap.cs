using UnityEngine;

[RequireComponent(typeof(AudioSource))]
public class TripwireTrap : MonoBehaviour
{
	[Header("Audio Settings")]
	[Tooltip("The bell chime sound effect clip")]
	public AudioClip bellSound;

	[Header("Cooldown Settings")]
	[Tooltip("Time in seconds before the trap can be triggered again")]
	public float triggerCooldown;

	private AudioSource audioSource;

	private float nextAllowedTriggerTime;

	private void Start()
	{
	}

	private void OnTriggerEnter(Collider other)
	{
	}

	private void TriggerTheBell()
	{
	}
}

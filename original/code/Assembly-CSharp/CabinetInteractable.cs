using UnityEngine;

[RequireComponent(typeof(AudioSource))]
public class CabinetInteractable : MonoBehaviour
{
	[Header("Sliding Movement Settings (Z-Axis)")]
	[Tooltip("How far out on the Z axis the cabinet drawer or door slides open")]
	public float openDistance;

	public float doorSpeed;

	[Header("Audio")]
	public AudioClip openSound;

	public AudioClip closeSound;

	[HideInInspector]
	public bool isOpen;

	private bool isMoving;

	private AudioSource myAudioSource;

	private Vector3 closedPosition;

	private Vector3 openPosition;

	private Vector3 targetPosition;

	private void Start()
	{
	}

	private void Update()
	{
	}

	public void Interact(string heldItemName)
	{
	}
}

using UnityEngine;

public class DrawerPivotAnimation : MonoBehaviour
{
	private bool isOpen;

	[Tooltip("How far out the drawer slides. Use a negative value if it goes backwards.")]
	[Header("Movement Settings")]
	public float openDistance;

	public float slideSpeed;

	[Header("Audio Settings")]
	public AudioSource audioSource;

	public AudioClip openSound;

	public AudioClip closeSound;

	[Tooltip("Drag your on-screen InteractButton here")]
	[Header("Mobile UI Settings")]
	public GameObject handButtonUI;

	[Tooltip("How close the player needs to be to see the button")]
	public float interactionDistance;

	private Vector3 closedPosition;

	private Vector3 openPosition;

	private Vector3 targetPosition;

	private Transform playerTransform;

	private void Start()
	{
	}

	private void Update()
	{
	}

	public void Interact()
	{
	}
}

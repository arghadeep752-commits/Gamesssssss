using UnityEngine;

public class GrannyDrawer : MonoBehaviour
{
	[Tooltip("How far out the drawer slides on its local Z axis")]
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
	}

	private void Update()
	{
	}

	public void ToggleDrawer()
	{
	}
}

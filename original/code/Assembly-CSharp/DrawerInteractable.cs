using System.Collections.Generic;
using UnityEngine;

[RequireComponent(typeof(AudioSource))]
public class DrawerInteractable : MonoBehaviour
{
	private class HeldEntry
	{
		public Rigidbody rb;

		public InteractableItem item;

		public bool wasKinematic;
	}

	[Header("Drawer Movement Settings")]
	[Tooltip("How far forward the drawer pulls out along its local Z-axis")]
	public float openDistance;

	[Tooltip("How fast the drawer slides open and closed")]
	public float slideSpeed;

	[Header("Drawer Audio Profiles")]
	public AudioClip openSound;

	public AudioClip closeSound;

	[Header("Items Inside The Drawer")]
	[Tooltip("Items inside this box are held by the drawer: they stay still and move with it when it opens/closes. Shown as a YELLOW box in the Scene view when the drawer is selected. Leave Size at 0,0,0 to fit it to the drawer automatically.")]
	public Vector3 contentsCenter;

	public Vector3 contentsSize;

	[Tooltip("Shrinks the automatic box a little so it only covers the INSIDE of the drawer (1 = full drawer size)")]
	[Range(0.5f, 1f)]
	public float autoBoxShrink;

	[Tooltip("An item the player drops into the open drawer is grabbed once it has nearly stopped moving")]
	public float settleSpeed;

	private bool isOpen;

	private AudioSource myAudioSource;

	private Vector3 closedLocalPosition;

	private Vector3 openLocalPosition;

	private Vector3 targetLocalPosition;

	private readonly List<HeldEntry> heldItems;

	private Vector3 lastWorldPosition;

	private float scanTimer;

	private readonly Collider[] overlapBuffer;

	private void Start()
	{
	}

	private void Update()
	{
	}

	public void Interact()
	{
	}

	private void CaptureItemsInside(bool evenIfMoving)
	{
	}

	private bool IsAlreadyHeld(Rigidbody rb)
	{
		return false;
	}

	private void AutoFitContentsBox()
	{
	}

	private void OnDrawGizmosSelected()
	{
	}
}

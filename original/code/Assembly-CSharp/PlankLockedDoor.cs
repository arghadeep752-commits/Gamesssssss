using UnityEngine;

public class PlankLockedDoor : DoorInteractable
{
	[Header("Plank Blocker Reference")]
	[Tooltip("Drag the 'doorlockplank' object here. If left blank, it will auto-find it in your child objects!")]
	public DoorPlankComponent blockingPlank;

	private void Awake()
	{
	}

	public new void Interact(string heldItemName)
	{
	}
}

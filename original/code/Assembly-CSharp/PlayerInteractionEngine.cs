using UnityEngine;

public class PlayerInteractionEngine : MonoBehaviour
{
	[Header("Detection Settings")]
	public float reachDistance;

	[Header("Mobile UI Link")]
	public GameObject mobileHandButton;

	public GameObject hideInButtonReference;

	[Header("Inventory Link")]
	public string currentlyHeldItem;

	private GameObject targetedObject;

	private DoorPlankComponent activePlank;

	private PlankLockedDoorInteractable activePlankDoor;

	private DoorInteractable activeDoor;

	private DoorLockComponent activeLock;

	private MainDoorEscape activeMasterDoor;

	private GrannyDrawer activeDrawer;

	private HidingSpot activeHidingSpot;

	private HotAirBalloonEscape activeBalloon;

	private RopeAnchorInteraction activeRopeAnchor;

	private void Start()
	{
	}

	private void Update()
	{
	}

	private void ClearTargets()
	{
	}

	private void ExecuteInteraction()
	{
	}

	public void OnHandButtonTapped()
	{
	}
}

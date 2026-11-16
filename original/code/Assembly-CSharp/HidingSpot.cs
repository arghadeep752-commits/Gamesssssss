using UnityEngine;

public class HidingSpot : MonoBehaviour
{
	public enum HidingType
	{
		Bed = 0,
		Locker = 1,
		Coffin = 2,
		Car = 3
	}

	[Header("Configuration")]
	public HidingType spotType;

	[Tooltip("The exact point where the PLAYER (root) is placed while hiding. Its blue arrow (forward) is the center of the view.")]
	public Transform hidePosition;

	[Header("Granny (Car only, optional)")]
	[Tooltip("Optional: where Granny stands to pull the player out of the CAR. Leave empty and she goes to the side the player got in from automatically.")]
	public Transform grannyApproachPoint;

	[Header("Camera")]
	[Tooltip("Camera near clip while under a BED. Lower it (e.g. 0.03) if you can see through the bed frame / mattress while turning.")]
	public float bedNearClipPlane;

	[Tooltip("DRAG YOUR DROP BUTTON HERE FROM THE HIERARCHY")]
	[Header("UI Reference")]
	public GameObject dropButton;

	[Header("Animations (Optional)")]
	public Animator doorAnimator;

	public string openTriggerName;

	public string closeTriggerName;

	private Camera playerCamera;

	private float originalNearClip;

	private bool isInsideSpot;

	[HideInInspector]
	public float rotationY;

	private void Awake()
	{
	}

	public void PlayOpenAnimation()
	{
	}

	public void PlayCloseAnimation()
	{
	}

	public void OnEnterHidingSpot()
	{
	}

	public void OnExitHidingSpot()
	{
	}

	public void ForceHideDropButton()
	{
	}

	private bool CheckIfPlayerHasItem()
	{
		return false;
	}

	private void SetHandItemsActive(bool isActive)
	{
	}

	private void SetDropButtonActive(bool isActive)
	{
	}

	private void FindDropButtonInScene()
	{
	}

	public void OnHoverEnter()
	{
	}

	public void OnHoverExit()
	{
	}
}

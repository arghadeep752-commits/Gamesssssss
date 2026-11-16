using UnityEngine;

public class HidingSpotDistanceTracker : MonoBehaviour
{
	[Tooltip("How close the player needs to be (in meters) to see the Hide Button")]
	[Header("Distance Settings")]
	public float activationDistance;

	private HidingSpot hidingSpot;

	private Transform playerTransform;

	private PlayerHidingController hidingController;

	private bool playerIsClose;

	private bool wasHidingLastFrame;

	private void Start()
	{
	}

	private void Update()
	{
	}

	private bool CheckIfPlayerIsHiding()
	{
		return false;
	}

	private void OnDisable()
	{
	}
}

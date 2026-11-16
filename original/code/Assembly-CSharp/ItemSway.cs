using UnityEngine;

public class ItemSway : MonoBehaviour
{
	[Header("Player & Camera Tracking")]
	public Transform playerTransform;

	public Transform playerCamera;

	private Rigidbody playerRigidbody;

	private CharacterController playerController;

	private Vector3 lastPlayerPosition;

	[Header("Sway Settings (Looking Around)")]
	public float swayAmount;

	public float maxSwayAmount;

	public float swaySmoothness;

	[Header("Bobbing Settings (Walking)")]
	public float bobSpeed;

	public float bobAmount;

	[Header("Wall Collision Avoidance (Anti-Clip)")]
	public LayerMask obstacleLayers;

	public float detectDistance;

	public Vector3 wallPullOffset;

	public Vector3 wallRotationOffset;

	private Vector3 initialPosition;

	private Quaternion initialRotation;

	private float bobTimer;

	private void Start()
	{
	}

	private void Update()
	{
	}

	private void OnDrawGizmosSelected()
	{
	}
}

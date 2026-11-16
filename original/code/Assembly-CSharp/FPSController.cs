using UnityEngine;

public class FPSController : MonoBehaviour
{
	public float moveSpeed;

	public float mouseSensitivity;

	public float gravity;

	[Header("Mobile Setup")]
	public MobileJoystick joystick;

	[Header("Mobile Look (touch)")]
	[Tooltip("Touch look speed multiplier. The settings slider sets Mouse Sensitivity; left/right and up/down always use the SAME value.")]
	public float touchLookScale;

	[Range(0f, 40f)]
	[Tooltip("Smooths out small finger jitter. 0 = no smoothing (raw), 20 = very light, 10 = softer.")]
	public float touchLookSmoothing;

	[Header("Frame Rate (mobile)")]
	[Tooltip("Android/iOS run games at 30 FPS unless told otherwise. 60 = much smoother camera. 0 = leave Unity's default.")]
	public int mobileTargetFrameRate;

	private int lookFingerId;

	private Vector2 smoothedTouchDelta;

	private CharacterController controller;

	private Camera cam;

	private float xRotation;

	private Vector3 velocity;

	private PlayerHidingController hidingController;

	private bool isFirstFrameAfterEnable;

	private void Start()
	{
	}

	private void OnEnable()
	{
	}

	public void ResetGravityVelocity()
	{
	}

	private void Update()
	{
	}

	public void ResetMovementState()
	{
	}
}

using UnityEngine;

namespace TMPro.Examples
{
	public class CameraController : MonoBehaviour
	{
		public enum CameraModes
		{
			Follow = 0,
			Isometric = 1,
			Free = 2
		}

		private Transform cameraTransform;

		private Transform dummyTarget;

		public Transform CameraTarget;

		public float FollowDistance;

		public float MaxFollowDistance;

		public float MinFollowDistance;

		public float ElevationAngle;

		public float MaxElevationAngle;

		public float MinElevationAngle;

		public float OrbitalAngle;

		public CameraModes CameraMode;

		public bool MovementSmoothing;

		public bool RotationSmoothing;

		private bool previousSmoothing;

		public float MovementSmoothingValue;

		public float RotationSmoothingValue;

		public float MoveSensitivity;

		private Vector3 currentVelocity;

		private Vector3 desiredPosition;

		private float mouseX;

		private float mouseY;

		private Vector3 moveVector;

		private float mouseWheel;

		private const string event_SmoothingValue = "Slider - Smoothing Value";

		private const string event_FollowDistance = "Slider - Camera Zoom";

		private void Awake()
		{
		}

		private void Start()
		{
		}

		private void LateUpdate()
		{
		}

		private void GetPlayerInput()
		{
		}
	}
}

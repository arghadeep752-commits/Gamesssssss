using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.CompilerServices;
using UnityEngine;

[DefaultExecutionOrder(-200)]
public class PlayerHidingController : MonoBehaviour
{
	[CompilerGenerated]
	private sealed class _003CTransitionToPoint_003Ed__53 : IEnumerator<object>, IEnumerator, IDisposable
	{
		private int _003C_003E1__state;

		private object _003C_003E2__current;

		public PlayerHidingController _003C_003E4__this;

		public Vector3 targetPos;

		public Quaternion targetRot;

		public Action onComplete;

		private float _003Ctime_003E5__2;

		private Vector3 _003CstartPos_003E5__3;

		private Quaternion _003CstartRot_003E5__4;

		object IEnumerator<object>.Current
		{
			[DebuggerHidden]
			get
			{
				return null;
			}
		}

		object IEnumerator.Current
		{
			[DebuggerHidden]
			get
			{
				return null;
			}
		}

		[DebuggerHidden]
		public _003CTransitionToPoint_003Ed__53(int _003C_003E1__state)
		{
		}

		[DebuggerHidden]
		void IDisposable.Dispose()
		{
		}

		private bool MoveNext()
		{
			return false;
		}

		bool IEnumerator.MoveNext()
		{
			//ILSpy generated this explicit interface implementation from .override directive in MoveNext
			return this.MoveNext();
		}

		[DebuggerHidden]
		void IEnumerator.Reset()
		{
		}
	}

	[Header("Bed Item Drop Settings")]
	[Tooltip("Drag an empty GameObject placed on the floor directly in front of THIS bed spot.")]
	public Transform dropSpawnPoint;

	[Header("UI Setup")]
	public GameObject mobileHidingButton;

	public GameObject mobileCoffinButton;

	public GameObject mobileCarButton;

	[Header("UI Controls")]
	public GameObject joystickUI;

	public GameObject crouchButtonUI;

	[Tooltip("Drag your Settings Button GameObject here")]
	public GameObject settingsButtonUI;

	[Header("Camera Configuration")]
	[Tooltip("Drag your Main Camera here")]
	public Transform playerCamera;

	private const float HORIZONTAL_LOOK_LIMIT = 90f;

	[Tooltip("While hiding, the camera is kept at STANDING height, so it sits at the exact same spot under the bed / in the coffin whether the player was standing or crouching")]
	[Header("Same Camera Height (Standing & Crouching)")]
	public bool holdStandingCameraHeight;

	[Tooltip("How fast (meters per second) the camera moves to standing height when a crouching player hides")]
	public float cameraHeightBlendSpeed;

	[Header("Smooth Look While Hiding")]
	[Tooltip("How quickly the view follows your finger while hiding. Higher = snappier, lower = smoother.")]
	[Range(5f, 40f)]
	public float lookSmoothing;

	[Header("Transition Settings")]
	public float transitionSpeed;

	private bool isHiding;

	private bool isExiting;

	private bool exitLocked;

	private Vector3 preHidePosition;

	private Quaternion preHideRotation;

	private HidingSpot nearbySpot;

	private HidingSpot currentSpot;

	private CharacterController characterController;

	private FPSController fpsControllerScript;

	private Quaternion originalCameraLocalRotation;

	private float rotationY;

	private Vector3 standingCameraLocalPos;

	private bool hasSavedCameraPose;

	private Quaternion hidingLookRot;

	private Vector3 heldCameraLocalPos;

	private int lookFingerId;

	public static PlayerHidingController ActiveHidingBed { get; private set; }

	public bool IsCurrentlyHiding => false;

	public bool IsExiting => false;

	public Vector3 PreHidePosition => default;

	public void SetExitLocked(bool locked)
	{
	}

	private void Awake()
	{
	}

	private void Start()
	{
	}

	public void SetNearbyHidingSpot(HidingSpot spot)
	{
	}

	public void ClearNearbyHidingSpot(HidingSpot spot)
	{
	}

	public void OnHidingButtonTapped()
	{
	}

	public void OnCoffinButtonTapped()
	{
	}

	public void OnCarButtonTapped()
	{
	}

	public void EnterHiding(HidingSpot spot)
	{
	}

	private void ExitHiding()
	{
	}

	private void ToggleActiveInteractionButton(bool state)
	{
	}

	private void Update()
	{
	}

	private float ReadHidingLookInput()
	{
		return 0f;
	}

	private void LateUpdate()
	{
	}

	[IteratorStateMachine(typeof(_003CTransitionToPoint_003Ed__53))]
	private IEnumerator TransitionToPoint(Vector3 targetPos, Quaternion targetRot, Action onComplete)
	{
		return null;
	}

	public void ForceResetHidingState()
	{
	}

	private void FindSettingsButton()
	{
	}
}

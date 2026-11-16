using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.CompilerServices;
using UnityEngine;
using UnityEngine.UI;

public class MobileCrouchController : MonoBehaviour
{
	[CompilerGenerated]
	private sealed class _003CCameraOnlyTransition_003Ed__28 : IEnumerator<object>, IEnumerator, IDisposable
	{
		private int _003C_003E1__state;

		private object _003C_003E2__current;

		public MobileCrouchController _003C_003E4__this;

		private float _003CtargetCameraY_003E5__2;

		private float _003CcurrentCameraY_003E5__3;

		private float _003Celapsed_003E5__4;

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
		public _003CCameraOnlyTransition_003Ed__28(int _003C_003E1__state)
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

	[Header("Setup References")]
	public Transform playerCamera;

	[Tooltip("Drag your Crouch UI Button here from the Canvas")]
	public Button crouchButton;

	[Tooltip("Drag your main player movement script here (e.g., FirstPersonController)")]
	[Header("Movement Script Reference")]
	public MonoBehaviour playerMovementScript;

	[Header("Button Sprite Configuration")]
	public Sprite standingSprite;

	public Sprite crouchingSprite;

	[Header("Camera Height Configuration")]
	public float timeToCrouch;

	[Tooltip("Only used as a fallback if the camera has no local Y position to read at Start (should basically never happen). The real standing height is always read from the camera itself, not forced to this value.")]
	public float standingLocalY;

	[Tooltip("How far DOWN (in meters) the camera drops below the real standing height when crouching. This is a relative offset now, not an absolute height - so crouch always matches your actual rig, whatever its real standing height is.")]
	public float crouchDropAmount;

	[Header("Collider Height Configuration")]
	public float standingColliderHeight;

	public float crouchingColliderHeight;

	[Header("Speed Settings")]
	public float standingMovementSpeed;

	public float crouchingMovementSpeed;

	[Tooltip("Select layers that block player (Exclude Player layer)")]
	[Header("Obstacle Detection Mask")]
	public LayerMask obstacleLayers;

	private bool isCrouching;

	private Image buttonImage;

	private CapsuleCollider playerCollider;

	private CharacterController playerController;

	private PlayerHidingController hidingController;

	private float originalStandingY;

	private bool inputLocked;

	public bool IsCrouching => false;

	private void Awake()
	{
	}

	private void Start()
	{
	}

	private void Update()
	{
	}

	public void ToggleCrouch()
	{
	}

	public float StandUpForDeath()
	{
		return 0f;
	}

	public void SetInputLocked(bool locked)
	{
	}

	[IteratorStateMachine(typeof(_003CCameraOnlyTransition_003Ed__28))]
	private IEnumerator CameraOnlyTransition()
	{
		return null;
	}

	private void UpdateColliderDimensions(float targetHeight)
	{
	}

	private bool IsCeilingBlocking()
	{
		return false;
	}

	public void ForceStandReset()
	{
	}

	private void ApplyMovementSpeed(float newSpeed)
	{
	}

	private bool TrySetSpeed(MonoBehaviour script, float speedValue)
	{
		return false;
	}
}

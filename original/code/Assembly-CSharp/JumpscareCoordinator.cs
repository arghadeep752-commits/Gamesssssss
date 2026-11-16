using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Reflection;
using System.Runtime.CompilerServices;
using UnityEngine;
using UnityEngine.AI;

[DefaultExecutionOrder(3000)]
public class JumpscareCoordinator : MonoBehaviour
{
	public enum PlayerHidingState
	{
		None = 0,
		InCoffin = 1,
		UnderBed = 2
	}

	[CompilerGenerated]
	private sealed class _003CBedHeadContactRoutine_003Ed__68 : IEnumerator<object>, IEnumerator, IDisposable
	{
		private int _003C_003E1__state;

		private object _003C_003E2__current;

		public JumpscareCoordinator _003C_003E4__this;

		public float duration;

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
		public _003CBedHeadContactRoutine_003Ed__68(int _003C_003E1__state)
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

	[CompilerGenerated]
	private sealed class _003CExecuteKillSequence_003Ed__69 : IEnumerator<object>, IEnumerator, IDisposable
	{
		private int _003C_003E1__state;

		private object _003C_003E2__current;

		public JumpscareCoordinator _003C_003E4__this;

		private float _003CfadeDurationOverride_003E5__2;

		private NavMeshAgent _003CmainAgent_003E5__3;

		private float _003CforceAlignTime_003E5__4;

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
		public _003CExecuteKillSequence_003Ed__69(int _003C_003E1__state)
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

	[CompilerGenerated]
	private sealed class _003CNaturalFallToFloor_003Ed__66 : IEnumerator<object>, IEnumerator, IDisposable
	{
		private int _003C_003E1__state;

		private object _003C_003E2__current;

		public JumpscareCoordinator _003C_003E4__this;

		private Quaternion _003CstartRot_003E5__2;

		private float _003CrestY_003E5__3;

		private float _003CtotalDrop_003E5__4;

		private Vector3 _003CknockDirection_003E5__5;

		private Vector3 _003Cpos_003E5__6;

		private float _003CverticalSpeed_003E5__7;

		private float _003ChorizontalSpeed_003E5__8;

		private float _003CmaxProgress_003E5__9;

		private int _003Cbounces_003E5__10;

		private bool _003Clanded_003E5__11;

		private float _003CsettleTimer_003E5__12;

		private float _003CsafetyTimer_003E5__13;

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
		public _003CNaturalFallToFloor_003Ed__66(int _003C_003E1__state)
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

	public static JumpscareCoordinator Instance;

	[Header("Player References")]
	public Transform playerTransform;

	public Transform playerCamera;

	[Tooltip("Assign the script handling your camera mouse/touch sensitivity here to lock it.")]
	public MonoBehaviour cameraLookScript;

	[Header("Granny Standard References")]
	public Animator grannyAnimator;

	public Transform grannyTransform;

	public AudioSource grannyAudioSource;

	[Tooltip("Assign the custom Animator controller attached to your specialized bed 1 jumpscare rig/model.")]
	[Header("Granny Bed 1 Special References")]
	public Animator bedGrannyAnimator;

	[Tooltip("Fallback only. The main way to set where the player looks is the 'Head Look Target' slot on Granny's GrannyAI script. This is only used if that slot is empty and her head bone can't be found automatically.")]
	public Transform bedLookTarget;

	[Header("Granny Bed 2 Special References")]
	[Tooltip("Assign the custom Animator controller attached to your specialized bed 2 jumpscare rig/model.")]
	public Animator bed2GrannyAnimator;

	[Tooltip("If the bed 2 sequence uses a specific look target position, assign it here.")]
	public Transform bed2LookTarget;

	[Tooltip("Assign the custom Animator controller attached to your specialized bed 3 jumpscare rig/model.")]
	[Header("Granny Bed 3 Special References")]
	public Animator bed3GrannyAnimator;

	[Tooltip("If the bed 3 sequence uses a specific look target position, assign it here.")]
	public Transform bed3LookTarget;

	[Header("Jumpscare Assets")]
	public AudioClip standardHitSound;

	public AudioClip coffinJumpscareSound;

	public AudioClip bedJumpscareSound;

	[Header("Timing Customization")]
	public float delayBeforeFloorFall;

	[Tooltip("Total length of the bed attack animation before transitioning to the next day.")]
	public float bedKillAnimationDuration;

	[Tooltip("Additional delay (black screen hold) after the bed attack animation before reloading the day.")]
	public float delayAfterBedKill;

	[Header("Bed Death Fade")]
	[Tooltip("ON: the screen starts fading to black 'Bed Death Fade Delay' seconds after the bed death animation starts. OFF: the old timing (Bed Kill Animation Duration + Delay After Bed Kill).")]
	public bool useBedDeathFadeTiming;

	[Tooltip("Seconds after the bed death animation STARTS until the screen begins fading to black.")]
	public float bedDeathFadeDelay;

	[Tooltip("How long the bed death fade to black takes (seconds). 0 = use the DayManager's 'Death Fade In Duration'.")]
	public float bedDeathFadeDuration;

	[Header("Natural Fall (standing / coffin / car kill)")]
	[Tooltip("How hard the player is pulled to the floor. Higher = faster, heavier fall.")]
	public float fallGravity;

	[Tooltip("How high the camera ends up above the floor once the player is lying down.")]
	public float lyingCameraHeight;

	[Tooltip("How far the view rolls over while falling (75 = almost lying on his side).")]
	public float fallRollAngle;

	[Tooltip("The head snaps back / looks up a little while falling.")]
	public float fallPitchUp;

	[Tooltip("How fast the player is knocked backwards (away from Granny) when hit.")]
	public float knockbackSpeed;

	[Tooltip("How quickly the knockback slows down.")]
	public float knockbackDeceleration;

	[Range(0f, 0.6f)]
	[Tooltip("How much the player bounces when he hits the floor (0 = no bounce).")]
	public float bounceRestitution;

	[Tooltip("Time the view rests on the floor after landing (seconds).")]
	public float fallSettleTime;

	[Tooltip("How fast the view turns to her head. Higher = faster. (The head itself is set on Granny's GrannyAI script: 'Head Look Target'.)")]
	[Header("Look At Granny's Head (until she hits him)")]
	public float lookAtGrannyTurnSpeed;

	[Tooltip("BED death only: how long (seconds) the player looks at her head after she drops down for the kill. After this the contact is cut and his view stays exactly where it is. Must be shorter than 'Bed Kill Animation Duration'.")]
	public float bedHeadContactDuration;

	[Header("UI Blackout & Lock")]
	public CanvasGroup gameHUD;

	public GameObject mobileControlsCanvas;

	[HideInInspector]
	public PlayerHidingState currentHidingState;

	private bool hasPullOutPoint;

	private Vector3 pullOutPoint;

	private bool isRotationLocked;

	private Quaternion lockedCameraRotation;

	private Quaternion lockedPlayerRotation;

	private bool isFallPoseHeld;

	private Vector3 heldCamPos;

	private Quaternion heldCamRot;

	private Vector3 heldRootPos;

	private float heldUntilTime;

	private MonoBehaviour killFpsRef;

	private PlayerWakeUp cachedWakeUp;

	private FieldInfo wakingField;

	private bool isBedViewHeld;

	private bool isHeadTracking;

	private Transform grannyFaceTarget;

	private bool faceTargetSearched;

	private GrannyAI cachedGrannyAI;

	public void SetPullOutPoint(Vector3 point)
	{
	}

	private void Awake()
	{
	}

	private void LateUpdate()
	{
	}

	public void StartKillSequence()
	{
	}

	private bool IsActorCollider(Transform t)
	{
		return false;
	}

	private float FindFloorHeightBelow(Vector3 fromPos, out bool found)
	{
		found = default;
		return 0f;
	}

	private bool IsBlockedHorizontally(Vector3 origin, Vector3 direction, float distance)
	{
		return false;
	}

	private bool IsPlayerWakingUp()
	{
		return false;
	}

	private bool ShouldReleaseHeldPose()
	{
		return false;
	}

	private GrannyAI GetGrannyAI()
	{
		return null;
	}

	private Vector3 GetGrannyLookPoint()
	{
		return default;
	}

	private Transform FindGrannyFaceTarget()
	{
		return null;
	}

	[IteratorStateMachine(typeof(_003CNaturalFallToFloor_003Ed__66))]
	private IEnumerator NaturalFallToFloor()
	{
		return null;
	}

	private void DropPlayerHeldItemAtCurrentPosition()
	{
	}

	[IteratorStateMachine(typeof(_003CBedHeadContactRoutine_003Ed__68))]
	private IEnumerator BedHeadContactRoutine(float duration)
	{
		return null;
	}

	[IteratorStateMachine(typeof(_003CExecuteKillSequence_003Ed__69))]
	private IEnumerator ExecuteKillSequence()
	{
		return null;
	}
}

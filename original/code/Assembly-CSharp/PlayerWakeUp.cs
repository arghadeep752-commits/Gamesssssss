using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.CompilerServices;
using TMPro;
using UnityEngine;
using UnityEngine.Events;
using UnityEngine.UI;

[DefaultExecutionOrder(1000)]
public class PlayerWakeUp : MonoBehaviour
{
	[CompilerGenerated]
	private sealed class _003CFadeOverlay_003Ed__53 : IEnumerator<object>, IEnumerator, IDisposable
	{
		private int _003C_003E1__state;

		private object _003C_003E2__current;

		public PlayerWakeUp _003C_003E4__this;

		public float startAlpha;

		public float endAlpha;

		public float duration;

		private float _003Celapsed_003E5__2;

		private Color _003Ccol_003E5__3;

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
		public _003CFadeOverlay_003Ed__53(int _003C_003E1__state)
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
	private sealed class _003CGrannyRightSideWakeUpSequence_003Ed__52 : IEnumerator<object>, IEnumerator, IDisposable
	{
		private int _003C_003E1__state;

		private object _003C_003E2__current;

		public PlayerWakeUp _003C_003E4__this;

		private PlayerHidingController _003ChidingCtrl_003E5__2;

		private Vector3 _003CstandingLocalPos_003E5__3;

		private Quaternion _003CstandingLocalRot_003E5__4;

		private Transform _003CcamParent_003E5__5;

		private Vector3 _003CbedPos_003E5__6;

		private Vector3 _003CbedRight_003E5__7;

		private Quaternion _003CbedLyingRot_003E5__8;

		private float _003CrollElapsed_003E5__9;

		private Vector3 _003CsideRestPos_003E5__10;

		private Quaternion _003CsideRestRot_003E5__11;

		private float _003Celapsed_003E5__12;

		private float _003CsettleElapsed_003E5__13;

		private float _003CtextFadeElapsed_003E5__14;

		private Color _003CtextColor_003E5__15;

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
		public _003CGrannyRightSideWakeUpSequence_003Ed__52(int _003C_003E1__state)
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
	private sealed class _003CHoldWithBreathing_003Ed__50 : IEnumerator<object>, IEnumerator, IDisposable
	{
		private int _003C_003E1__state;

		private object _003C_003E2__current;

		public PlayerWakeUp _003C_003E4__this;

		public Vector3 basePos;

		public Quaternion baseRot;

		public float duration;

		private float _003Cheld_003E5__2;

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
		public _003CHoldWithBreathing_003Ed__50(int _003C_003E1__state)
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
	private sealed class _003CInputLockEnforcer_003Ed__46 : IEnumerator<object>, IEnumerator, IDisposable
	{
		private int _003C_003E1__state;

		private object _003C_003E2__current;

		public PlayerWakeUp _003C_003E4__this;

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
		public _003CInputLockEnforcer_003Ed__46(int _003C_003E1__state)
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
	private sealed class _003CLyingBreathing_003Ed__49 : IEnumerator<object>, IEnumerator, IDisposable
	{
		private int _003C_003E1__state;

		private object _003C_003E2__current;

		public PlayerWakeUp _003C_003E4__this;

		public Vector3 basePos;

		public Quaternion baseRot;

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
		public _003CLyingBreathing_003Ed__49(int _003C_003E1__state)
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

	public MonoBehaviour fpsController;

	public Image blinkOverlay;

	public TMP_Text dayTextMesh;

	[Header("Bed Wake Up Setup")]
	[Tooltip("Empty GameObject placed on the pillow at eye level. Only its POSITION and Y ROTATION are used. Blue arrow (forward) = toward the FEET of the bed. Green arrow (right) = the side the player rolls to and gets out from.")]
	public Transform bedWakeUpPoint;

	[Tooltip("Camera pitch while lying on the back. Negative = looking UP at the ceiling (-80 is almost straight up).")]
	public float lyingLookUpPitch;

	[Tooltip("How long the player stares at the ceiling (eyes open) before turning")]
	public float lookUpHoldTime;

	[Tooltip("How long the roll from the back onto the RIGHT side takes")]
	public float rollToSideDuration;

	[Tooltip("How long the player rests on the right side before getting up")]
	public float sidePauseTime;

	[Tooltip("How far the body rolls over (90 = fully on the side)")]
	public float sideRollAngle;

	[Tooltip("Called the moment the player is fully awake and gameplay begins")]
	public UnityEvent onWakeUpComplete;

	[Header("Item Hold Points Setup")]
	[Tooltip("Drag ALL your individual item hold points from under Main Camera into this list")]
	public List<GameObject> allItemHoldPoints;

	[Header("Granny Style Input Restrictions")]
	[Tooltip("Drag the script component that handles player looking/camera rotation here")]
	public MonoBehaviour screenRotationScript;

	[Tooltip("Drag the UI GameObject that holds your mobile movement joysticks here")]
	public GameObject joystickUIContainer;

	[Tooltip("Drag the UI Button GameObject for crouching here")]
	public GameObject crouchButtonUI;

	[Tooltip("Drag your bed interaction button/icon Image here to hold it disabled until standing up")]
	public Image bedHideButtonImage;

	[Header("Cinematic Timings")]
	public float riseDuration;

	public AudioClip wakeUpGroan;

	[Tooltip("How long the camera 'catches its balance' after standing up (seconds)")]
	[Header("Granny Wake Up Feel (optional tuning)")]
	public float settleDuration;

	[Tooltip("Strength of the dizzy head sway while getting up (0 = none, 1 = default, 2 = drunk)")]
	public float dizzySwayAmount;

	[Tooltip("Narrow the field of view when the eyes first open, then widen as vision focuses")]
	public bool useEyeFocusFov;

	[Tooltip("How many degrees the FOV is squeezed while eyes are heavy")]
	public float squintFovReduction;

	private AudioSource audioSource;

	private Coroutine activeWakeUpRoutine;

	private Vector3 originalStandingLocalPos;

	private bool hasSavedOriginalPos;

	private GameObject currentlyHeldItemPoint;

	private bool isWakingUp;

	private bool lyingPhaseActive;

	private Button cachedBedHideButton;

	private Camera playerCam;

	private float originalFov;

	private bool hasSavedFov;

	private bool bodyRotationCaptured;

	private Quaternion lockedBodyRotation;

	private bool camPoseRemembered;

	private Vector3 rememberedCamPos;

	private Quaternion rememberedCamRot;

	private void Awake()
	{
	}

	private void OnEnable()
	{
	}

	public void ResetWakeUpState()
	{
	}

	private void OnDrawGizmosSelected()
	{
	}

	private void ApplyInputLock()
	{
	}

	private void Update()
	{
	}

	private void LateUpdate()
	{
	}

	private void RememberCamPose()
	{
	}

	[IteratorStateMachine(typeof(_003CInputLockEnforcer_003Ed__46))]
	private IEnumerator InputLockEnforcer()
	{
		return null;
	}

	private void ApplyPoseWithBreathing(Vector3 basePos, Quaternion baseRot, float weight)
	{
	}

	private static float Dt()
	{
		return 0f;
	}

	[IteratorStateMachine(typeof(_003CLyingBreathing_003Ed__49))]
	private IEnumerator LyingBreathing(Vector3 basePos, Quaternion baseRot)
	{
		return null;
	}

	[IteratorStateMachine(typeof(_003CHoldWithBreathing_003Ed__50))]
	private IEnumerator HoldWithBreathing(Vector3 basePos, Quaternion baseRot, float duration)
	{
		return null;
	}

	private static float Seg(float t, float a, float b)
	{
		return 0f;
	}

	[IteratorStateMachine(typeof(_003CGrannyRightSideWakeUpSequence_003Ed__52))]
	private IEnumerator GrannyRightSideWakeUpSequence()
	{
		return null;
	}

	[IteratorStateMachine(typeof(_003CFadeOverlay_003Ed__53))]
	private IEnumerator FadeOverlay(float startAlpha, float endAlpha, float duration)
	{
		return null;
	}
}

using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.CompilerServices;
using UnityEngine;

public class HotAirBalloonEscape : MonoBehaviour
{
	[CompilerGenerated]
	private sealed class _003CInflateBalloonRoutine_003Ed__43 : IEnumerator<object>, IEnumerator, IDisposable
	{
		private int _003C_003E1__state;

		private object _003C_003E2__current;

		public HotAirBalloonEscape _003C_003E4__this;

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
		public _003CInflateBalloonRoutine_003Ed__43(int _003C_003E1__state)
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
	private sealed class _003CNormalEscapeRoutine_003Ed__45 : IEnumerator<object>, IEnumerator, IDisposable
	{
		private int _003C_003E1__state;

		private object _003C_003E2__current;

		public HotAirBalloonEscape _003C_003E4__this;

		private float _003Ctimer_003E5__2;

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
		public _003CNormalEscapeRoutine_003Ed__45(int _003C_003E1__state)
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
	private sealed class _003CRopeCrashRoutine_003Ed__46 : IEnumerator<object>, IEnumerator, IDisposable
	{
		private int _003C_003E1__state;

		private object _003C_003E2__current;

		public HotAirBalloonEscape _003C_003E4__this;

		private Vector3 _003CstartPos_003E5__2;

		private Vector3 _003CpeakPos_003E5__3;

		private float _003Celapsed_003E5__4;

		private Vector3 _003CcrashAirPos_003E5__5;

		private Vector3 _003CgroundTarget_003E5__6;

		private Quaternion _003CinitialRot_003E5__7;

		private Quaternion _003CcrashRotTarget_003E5__8;

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
		public _003CRopeCrashRoutine_003Ed__46(int _003C_003E1__state)
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

	[Header("Item Checklists")]
	public bool isRepairedWithTape;

	public bool hasGasCylinder;

	public bool isIgnitedWithLighter;

	public bool ropesCutWithChainCutter;

	[Header("Setup References")]
	[Tooltip("Drag the Animator controller component attached to the fabric here")]
	public Animator balloonFabricAnimator;

	[Tooltip("Drag your BurnerFire_Particles object here!")]
	public ParticleSystem burnerFlameParticles;

	public GameObject burnerFlameEffect;

	public Transform player;

	[Header("Granny Management")]
	[Tooltip("Drag your Granny/Enemy GameObject here")]
	public GameObject grannyObject;

	[Tooltip("An empty GameObject in the scene where Granny should spawn after the balloon crashes")]
	public Transform grannyRespawnPoint;

	[Tooltip("Drag your screen-fader UI panel Animator here")]
	[Header("UI & Fade Cutscene Settings")]
	public Animator screenFadeAnimator;

	[Tooltip("Drag your touch control buttons/joystick UI Canvas group here")]
	public GameObject gameplayUI;

	[Header("Inflation Settings")]
	public float inflationDuration;

	[Tooltip("Drag the deactivated Cylinder model inside the basket here")]
	[Header("Setup References")]
	public GameObject basketCylinderVisual;

	[Header("Normal Flight Settings")]
	public string escapeSceneName;

	public string mainMenuSceneName;

	public float riseSpeed;

	public float forwardSpeed;

	public float escapeDuration;

	[Header("Rope Visual Link")]
	public GameObject dynamicRopeObject;

	[Tooltip("Drag a new Camera created inside the basket here for the crash view")]
	[Header("Crash Sequence Settings")]
	public GameObject crashCutsceneCamera;

	[Tooltip("The animation clip state name to trigger on the balloon fabric when ropes fail")]
	public string fabricCrashAnimationState;

	public float crashRiseHeight;

	[Tooltip("How long the balloon slowly drifts upward before falling (in seconds)")]
	public float riseDuration;

	[Tooltip("How many seconds the descent/fall to earth lasts. Increase this for a slower, heavy descent!")]
	public float fallDuration;

	public GameObject explosionParticles;

	[Tooltip("Drag your continuous loop smoke particle system here")]
	public GameObject ruinedSmokeParticles;

	[Tooltip("Drag the healthy/working visual balloon fabric mesh here to hide it on crash")]
	public GameObject balloonVisualMesh;

	[Tooltip("Drag your wrecked/deflated static balloon mesh layout here. It will only turn ON after the crash!")]
	public GameObject crashedBalloonVisualMesh;

	[Tooltip("An empty object on the grass where the player wakes up after the explosion")]
	public Transform wakeUpPoint;

	public AudioClip crashSound;

	private AudioSource audioSource;

	private bool isWorkingAndInflated;

	private bool sequenceStarted;

	private bool isDestroyed;

	private GameObject mainPlayerCameraObject;

	private void Start()
	{
	}

	public bool IsDestroyed()
	{
		return false;
	}

	public void UseTape()
	{
	}

	public void InsertCylinder()
	{
	}

	public void UseLighter()
	{
	}

	private void DisappearGranny()
	{
	}

	public void CutRopes()
	{
	}

	[IteratorStateMachine(typeof(_003CInflateBalloonRoutine_003Ed__43))]
	private IEnumerator InflateBalloonRoutine()
	{
		return null;
	}

	public void TriggerLaunchAttempt()
	{
	}

	[IteratorStateMachine(typeof(_003CNormalEscapeRoutine_003Ed__45))]
	private IEnumerator NormalEscapeRoutine()
	{
		return null;
	}

	[IteratorStateMachine(typeof(_003CRopeCrashRoutine_003Ed__46))]
	private IEnumerator RopeCrashRoutine()
	{
		return null;
	}

	private void RespawnGrannyAfterCrash()
	{
	}

	private void LockPlayerToBasket()
	{
	}
}

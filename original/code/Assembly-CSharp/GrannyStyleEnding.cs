using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.CompilerServices;
using UnityEngine;

public class GrannyStyleEnding : MonoBehaviour
{
	[CompilerGenerated]
	private sealed class _003CFadeCanvas_003Ed__21 : IEnumerator<object>, IEnumerator, IDisposable
	{
		private int _003C_003E1__state;

		private object _003C_003E2__current;

		public CanvasGroup cg;

		public float startAlpha;

		public float endAlpha;

		public float duration;

		private float _003Celapsed_003E5__2;

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
		public _003CFadeCanvas_003Ed__21(int _003C_003E1__state)
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
	private sealed class _003CIntroThenCinematicRoutine_003Ed__17 : IEnumerator<object>, IEnumerator, IDisposable
	{
		private int _003C_003E1__state;

		private object _003C_003E2__current;

		public GrannyStyleEnding _003C_003E4__this;

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
		public _003CIntroThenCinematicRoutine_003Ed__17(int _003C_003E1__state)
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
	private sealed class _003CMoveCameraRoutine_003Ed__18 : IEnumerator<object>, IEnumerator, IDisposable
	{
		private int _003C_003E1__state;

		private object _003C_003E2__current;

		public GrannyStyleEnding _003C_003E4__this;

		private Vector3 _003CstartPosition_003E5__2;

		private Vector3 _003CendPosition_003E5__3;

		private float _003Celapsed_003E5__4;

		private float _003Cduration_003E5__5;

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
		public _003CMoveCameraRoutine_003Ed__18(int _003C_003E1__state)
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
	private sealed class _003CTriggerFilmyOverlaysRoutine_003Ed__20 : IEnumerator<object>, IEnumerator, IDisposable
	{
		private int _003C_003E1__state;

		private object _003C_003E2__current;

		public GrannyStyleEnding _003C_003E4__this;

		private float _003CstartVolume_003E5__2;

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
		public _003CTriggerFilmyOverlaysRoutine_003Ed__20(int _003C_003E1__state)
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

	[Header("Movement Targets")]
	public Transform cameraEndTarget;

	public Transform grannyTarget;

	[Header("Cinematic Movement")]
	[Tooltip("How long (in seconds) the camera takes to glide from its start position to the end target. Higher = slower, smoother.")]
	public float cameraTravelDuration;

	[Tooltip("How strongly the camera keeps looking at Granny while it moves. Lower = smoother, more delayed tracking.")]
	public float lookRotationSpeed;

	[Header("Filmy Timing Controls")]
	[Range(0f, 1f)]
	[Tooltip("The text and black screen will start fading in when the camera has covered this fraction (0-1) of its travel, while it's still moving!")]
	public float startFadeProgressThreshold;

	[Header("UI Canvas Groups (For Fading)")]
	public CanvasGroup endTextCanvasGroup;

	public CanvasGroup screenFadeCanvasGroup;

	[Header("Audio Configurations")]
	public AudioSource audioSource;

	public AudioClip endSceneSoundtrack;

	[Header("Intro Black Screen")]
	[Tooltip("Dedicated audio source for the footstep intro sound. If left empty, the main audioSource will be used instead.")]
	public AudioSource footstepAudioSource;

	public AudioClip footstepSound;

	[Tooltip("How long the black screen holds with footsteps playing before the scene is revealed.")]
	public float introBlackScreenDuration;

	[Tooltip("These animators are kicked off only once the intro black screen has fully faded out.")]
	[Header("Enemy Animations")]
	public Animator enemyOneAnimator;

	public Animator enemyTwoAnimator;

	[Tooltip("Name of the trigger parameter on each enemy's Animator Controller used to start their animation.")]
	public string enemyAnimationTrigger;

	[Header("Scene Transition")]
	public string mainMenuSceneName;

	private float _travelProgress;

	private void Start()
	{
	}

	[IteratorStateMachine(typeof(_003CIntroThenCinematicRoutine_003Ed__17))]
	private IEnumerator IntroThenCinematicRoutine()
	{
		return null;
	}

	[IteratorStateMachine(typeof(_003CMoveCameraRoutine_003Ed__18))]
	private IEnumerator MoveCameraRoutine()
	{
		return null;
	}

	[IteratorStateMachine(typeof(_003CTriggerFilmyOverlaysRoutine_003Ed__20))]
	private IEnumerator TriggerFilmyOverlaysRoutine()
	{
		return null;
	}

	[IteratorStateMachine(typeof(_003CFadeCanvas_003Ed__21))]
	private IEnumerator FadeCanvas(CanvasGroup cg, float startAlpha, float endAlpha, float duration)
	{
		return null;
	}
}

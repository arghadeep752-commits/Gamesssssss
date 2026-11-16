using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.CompilerServices;
using UnityEngine;

public class GameBackgroundOST : MonoBehaviour
{
	[CompilerGenerated]
	private sealed class _003CFadeMusicIn_003Ed__19 : IEnumerator<object>, IEnumerator, IDisposable
	{
		private int _003C_003E1__state;

		private object _003C_003E2__current;

		public GameBackgroundOST _003C_003E4__this;

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
		public _003CFadeMusicIn_003Ed__19(int _003C_003E1__state)
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
	private sealed class _003CFadeMusicOut_003Ed__20 : IEnumerator<object>, IEnumerator, IDisposable
	{
		private int _003C_003E1__state;

		private object _003C_003E2__current;

		public GameBackgroundOST _003C_003E4__this;

		private float _003CstartVolume_003E5__2;

		private float _003Celapsed_003E5__3;

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
		public _003CFadeMusicOut_003Ed__20(int _003C_003E1__state)
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

	[Header("Audio Setup")]
	public AudioSource ostAudioSource;

	public float targetVolume;

	public float fadeDuration;

	[Header("Music Setting")]
	[Tooltip("When the player turns music back ON in the settings, the soundtrack starts again straight away (in a loop).")]
	public bool restartWhenTurnedOn;

	private Coroutine fadeRoutine;

	private bool gameWantsMusic;

	public static GameBackgroundOST Instance { get; private set; }

	private void Awake()
	{
	}

	private void Start()
	{
	}

	private void OnEnable()
	{
	}

	private void OnDisable()
	{
	}

	private void HandleMusicChanged(bool on)
	{
	}

	public void StartBackgroundMusic()
	{
	}

	public void StopBackgroundMusic()
	{
	}

	private void FadeOutAndStop()
	{
	}

	private void StartFade(IEnumerator routine)
	{
	}

	[IteratorStateMachine(typeof(_003CFadeMusicIn_003Ed__19))]
	private IEnumerator FadeMusicIn()
	{
		return null;
	}

	[IteratorStateMachine(typeof(_003CFadeMusicOut_003Ed__20))]
	private IEnumerator FadeMusicOut()
	{
		return null;
	}
}

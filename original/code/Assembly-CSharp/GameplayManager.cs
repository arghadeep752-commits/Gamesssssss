using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.CompilerServices;
using UnityEngine;

public class GameplayManager : MonoBehaviour
{
	[CompilerGenerated]
	private sealed class _003CResetDaySequence_003Ed__17 : IEnumerator<object>, IEnumerator, IDisposable
	{
		private int _003C_003E1__state;

		private object _003C_003E2__current;

		private Transform _003CpTransform_003E5__2;

		private CharacterController _003CcharController_003E5__3;

		private MonoBehaviour _003CfpsController_003E5__4;

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
		public _003CResetDaySequence_003Ed__17(int _003C_003E1__state)
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

	[Header("Difficulty Tuning")]
	public string currentDifficulty;

	[Header("Atmosphere Modifiers")]
	public GameObject darkerModeFogVolume;

	public Color darkerModeAmbientColor;

	public Color normalAmbientColor;

	[Header("Map Modifiers")]
	public GameObject extraLocksObject;

	[Header("Extreme Mode Exclusive Modifiers")]
	public GameObject extremeFenceObject;

	public GameObject extremeLeverObject;

	public GameObject extremeHandleObject;

	[Header("Audio Settings")]
	public AudioSource houseMusicSource;

	public static GameplayManager Instance { get; private set; }

	private void Awake()
	{
	}

	private void Start()
	{
	}

	public void OnPlayerCaught()
	{
	}

	public void OnPlayerCaught(float fadeDurationOverride)
	{
	}

	[IteratorStateMachine(typeof(_003CResetDaySequence_003Ed__17))]
	public IEnumerator ResetDaySequence()
	{
		return null;
	}

	private void LoadGameSettings()
	{
	}

	private void OnEnable()
	{
	}

	private void OnDisable()
	{
	}

	private void OnMusicSettingChanged(bool on)
	{
	}

	private void ApplyHouseMusic(bool on, bool atStart)
	{
	}

	private void ApplyDifficultySettings()
	{
	}

	private void ApplyDarkerMode(bool enabled)
	{
	}
}

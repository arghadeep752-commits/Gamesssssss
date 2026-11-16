using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.CompilerServices;
using UnityEngine;

public class OutdoorAmbientZone : MonoBehaviour
{
	[CompilerGenerated]
	private sealed class _003CFadeAudio_003Ed__23 : IEnumerator<object>, IEnumerator, IDisposable
	{
		private int _003C_003E1__state;

		private object _003C_003E2__current;

		public OutdoorAmbientZone _003C_003E4__this;

		public float targetVolume;

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
		public _003CFadeAudio_003Ed__23(int _003C_003E1__state)
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

	[Tooltip("The AudioSource playing the cricket/outdoor sound effect")]
	[Header("Audio References")]
	public AudioSource ambientAudioSource;

	[Header("Fade Settings")]
	[Tooltip("How fast the outdoor ambient sound fades in/out when transitioning")]
	public float fadeDuration;

	[Range(0f, 1f)]
	public float maxVolume;

	[Header("Player Detection")]
	[Tooltip("Optional: drag the Player here. If empty, the object tagged 'Player' is used.")]
	public Transform player;

	[Tooltip("How far below the player's center to look for the zone (covers his feet, standing or crouching)")]
	public float feetCheckDepth;

	private static readonly List<OutdoorAmbientZone> allZones;

	private static bool mutedByDeath;

	private Collider[] zoneColliders;

	private Coroutine fadeCoroutine;

	private bool playerInside;

	private Vector3 lastPlayerPos;

	private bool hasLastPos;

	private void Awake()
	{
	}

	private void OnEnable()
	{
	}

	private void OnDisable()
	{
	}

	private void Start()
	{
	}

	private void Update()
	{
	}

	private bool IsPlayerInZone()
	{
		return false;
	}

	private bool ContainsPoint(Vector3 point)
	{
		return false;
	}

	public static void OnPlayerDied()
	{
	}

	public static void OnNewDay()
	{
	}

	public void StopAmbientSoundImmediate()
	{
	}

	private void StartFade(float targetVolume)
	{
	}

	[IteratorStateMachine(typeof(_003CFadeAudio_003Ed__23))]
	private IEnumerator FadeAudio(float targetVolume)
	{
		return null;
	}
}

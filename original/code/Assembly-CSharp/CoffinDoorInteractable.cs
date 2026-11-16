using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.CompilerServices;
using UnityEngine;

public class CoffinDoorInteractable : DoorInteractable
{
	[CompilerGenerated]
	private sealed class _003CCheckForDoorOpenRoutine_003Ed__4 : IEnumerator<object>, IEnumerator, IDisposable
	{
		private int _003C_003E1__state;

		private object _003C_003E2__current;

		public CoffinDoorInteractable _003C_003E4__this;

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
		public _003CCheckForDoorOpenRoutine_003Ed__4(int _003C_003E1__state)
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

	[Header("Jumpscare Settings")]
	[Tooltip("Drag your Bat Particle System here")]
	public ParticleSystem batJumpscareSystem;

	[Tooltip("Optional distinct sound effect for the jumpscare itself")]
	public AudioClip jumpscareAudioClip;

	private bool hasTriggeredScare;

	private void Awake()
	{
	}

	[IteratorStateMachine(typeof(_003CCheckForDoorOpenRoutine_003Ed__4))]
	private IEnumerator CheckForDoorOpenRoutine()
	{
		return null;
	}

	private void TriggerBatJumpscare()
	{
	}
}

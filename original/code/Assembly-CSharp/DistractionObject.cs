using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.CompilerServices;
using UnityEngine;

[RequireComponent(typeof(Rigidbody))]
[RequireComponent(typeof(AudioSource))]
public class DistractionObject : MonoBehaviour
{
	[CompilerGenerated]
	private sealed class _003CStartResetTimer_003Ed__16 : IEnumerator<object>, IEnumerator, IDisposable
	{
		private int _003C_003E1__state;

		private object _003C_003E2__current;

		public DistractionObject _003C_003E4__this;

		private Vector3 _003CtargetWorldPosition_003E5__2;

		private Quaternion _003CtargetWorldRotation_003E5__3;

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
		public _003CStartResetTimer_003Ed__16(int _003C_003E1__state)
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

	[Header("Reset Settings")]
	[Tooltip("How many seconds the object stays on the floor before automatically resetting")]
	public float resetDelay;

	[Tooltip("How smoothly the object flies back to its original position")]
	public float returnSpeed;

	[Header("Audio Settings")]
	[Tooltip("The crash/drop sound effect")]
	public AudioClip crashSound;

	[Tooltip("Minimum falling speed required to trigger the sound (prevents tiny nudges from making noise)")]
	public float noiseVelocityThreshold;

	private float soundAlertRadius;

	private Rigidbody rb;

	private AudioSource audioSource;

	private Vector3 originalLocalPosition;

	private Quaternion originalLocalRotation;

	private Transform originalParent;

	private bool hasCrashed;

	private bool isResetting;

	private void Start()
	{
	}

	private void OnCollisionEnter(Collision collision)
	{
	}

	private void PlayCrashNoise()
	{
	}

	private void AlertGrannyAI()
	{
	}

	[IteratorStateMachine(typeof(_003CStartResetTimer_003Ed__16))]
	private IEnumerator StartResetTimer()
	{
		return null;
	}
}

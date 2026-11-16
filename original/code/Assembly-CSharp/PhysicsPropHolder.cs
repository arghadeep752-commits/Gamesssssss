using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.CompilerServices;
using UnityEngine;

[RequireComponent(typeof(Rigidbody))]
public class PhysicsPropHolder : MonoBehaviour
{
	[CompilerGenerated]
	private sealed class _003CAutoResetRoutine_003Ed__17 : IEnumerator<object>, IEnumerator, IDisposable
	{
		private int _003C_003E1__state;

		private object _003C_003E2__current;

		public PhysicsPropHolder _003C_003E4__this;

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
		public _003CAutoResetRoutine_003Ed__17(int _003C_003E1__state)
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

	[Header("Audio Settings")]
	public AudioSource audioSource;

	public AudioClip fallSound;

	[Header("AI Alert Settings")]
	public float alertRange;

	[Tooltip("Distance from player to trigger the painting fall.")]
	[Header("Trap Trigger Settings")]
	public float triggerDistance;

	[Tooltip("Layers that block the trigger vision (e.g., Walls, Environment).")]
	public LayerMask obstacleLayers;

	[Tooltip("Time in seconds before the painting blinks back to the wall after hitting the floor.")]
	[Header("Automatic Reset Settings")]
	public float autoResetDelay;

	private bool hasFallenFromWall;

	private bool hasLandedOnGround;

	private Vector3 initialPosition;

	private Quaternion initialRotation;

	private Rigidbody rb;

	private Coroutine resetCoroutine;

	private void Awake()
	{
	}

	private void FreezeOnWall()
	{
	}

	private void Update()
	{
	}

	public void MakePaintingFall()
	{
	}

	private void OnCollisionEnter(Collision collision)
	{
	}

	[IteratorStateMachine(typeof(_003CAutoResetRoutine_003Ed__17))]
	private IEnumerator AutoResetRoutine()
	{
		return null;
	}

	public void ResetToInitialPosition()
	{
	}

	private void OnDrawGizmosSelected()
	{
	}
}

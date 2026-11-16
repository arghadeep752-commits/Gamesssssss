using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.CompilerServices;
using UnityEngine;
using UnityEngine.AI;

[RequireComponent(typeof(AudioSource))]
public class PlankLockedDoorInteractable : MonoBehaviour, IInteractable
{
	public enum LockType
	{
		None = 0,
		PadlockKey = 1,
		MasterKey = 2,
		GoldKey = 3
	}

	[CompilerGenerated]
	private sealed class _003CShakeDoorRoutine_003Ed__22 : IEnumerator<object>, IEnumerator, IDisposable
	{
		private int _003C_003E1__state;

		private object _003C_003E2__current;

		public PlankLockedDoorInteractable _003C_003E4__this;

		private Quaternion _003CoriginalLocalRotation_003E5__2;

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
		public _003CShakeDoorRoutine_003Ed__22(int _003C_003E1__state)
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

	[Header("Door Movement Settings")]
	public float openAngle;

	public float doorSpeed;

	[Header("Lock Settings")]
	public LockType requiredLock;

	public string lockedNotificationText;

	[Header("Audio & Effects")]
	public AudioClip openSound;

	public AudioClip closeSound;

	public AudioClip lockedSound;

	[Tooltip("Drag the 'doorlockplank' object here. If left blank, it will auto-find it in your child objects!")]
	[Header("Plank Blocker Reference")]
	public DoorPlankComponent blockingPlank;

	[HideInInspector]
	public bool isOpen;

	private bool isMoving;

	private bool isShaking;

	private NavMeshObstacle navMeshObstacle;

	private AudioSource myAudioSource;

	private Collider doorCollider;

	private Quaternion closedRotation;

	private Quaternion openRotation;

	private Quaternion targetRotation;

	private void Start()
	{
	}

	private void Update()
	{
	}

	public void Interact(string heldItemName)
	{
	}

	private void TriggerLockedBehavior()
	{
	}

	[IteratorStateMachine(typeof(_003CShakeDoorRoutine_003Ed__22))]
	private IEnumerator ShakeDoorRoutine()
	{
		return null;
	}
}

using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.CompilerServices;
using UnityEngine;
using UnityEngine.AI;

[RequireComponent(typeof(AudioSource))]
public class DoorInteractable : MonoBehaviour, IInteractable
{
	public enum LockType
	{
		None = 0,
		PadlockKey = 1,
		MasterKey = 2,
		GoldKey = 3,
		CarKey = 4
	}

	[CompilerGenerated]
	private sealed class _003CShakeDoorRoutine_003Ed__24 : IEnumerator<object>, IEnumerator, IDisposable
	{
		private int _003C_003E1__state;

		private object _003C_003E2__current;

		public DoorInteractable _003C_003E4__this;

		private Quaternion _003CoriginalLocalRotation_003E5__2;

		private float _003Cdirection_003E5__3;

		private int _003Cpushes_003E5__4;

		private float _003Celapsed_003E5__5;

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
		public _003CShakeDoorRoutine_003Ed__24(int _003C_003E1__state)
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

	[Header("Locked Door Rattle")]
	[Tooltip("How many degrees the locked door moves when you try it (small = realistic)")]
	public float lockedRattleAngle;

	[Tooltip("How long the rattle lasts in seconds")]
	public float lockedRattleDuration;

	[Tooltip("How many little pushes against the lock")]
	public int lockedRattleCount;

	[Header("Audio & Effects")]
	public AudioClip openSound;

	public AudioClip closeSound;

	public AudioClip lockedSound;

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

	[IteratorStateMachine(typeof(_003CShakeDoorRoutine_003Ed__24))]
	private IEnumerator ShakeDoorRoutine()
	{
		return null;
	}
}

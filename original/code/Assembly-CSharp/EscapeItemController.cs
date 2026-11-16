using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.CompilerServices;
using UnityEngine;

public class EscapeItemController : MonoBehaviour
{
	public enum ItemIdentity
	{
		Hammer = 0,
		ChainCutter = 1,
		PadlockKey = 2,
		PadlockCode = 3,
		MasterKey = 4
	}

	[CompilerGenerated]
	private sealed class _003CSafePhysicsDrop_003Ed__10 : IEnumerator<object>, IEnumerator, IDisposable
	{
		private int _003C_003E1__state;

		private object _003C_003E2__current;

		public GameObject targetCube;

		public EscapeItemController _003C_003E4__this;

		private AudioSource _003CblockAudio_003E5__2;

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
		public _003CSafePhysicsDrop_003Ed__10(int _003C_003E1__state)
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

	[Header("Item Configuration")]
	public ItemIdentity itemType;

	[Tooltip("Drag the visual object ALREADY INSIDE your Player Camera/Hand here.")]
	[Header("Player Hand Links")]
	public GameObject matchingHandVisual;

	[Header("Connected Lock Objects (The Obstacles)")]
	public GameObject associatedLockCube;

	[Header("Audio Settings")]
	public AudioClip pickupSound;

	public AudioClip groundImpactSound;

	[Header("Scene Transition")]
	public string escapeSceneName;

	[Tooltip("Master Key only: escape the moment it's picked up, but ONLY if every lock on the main door is already open. Leave OFF to always have to use the key on the door.")]
	public bool escapeOnPickupIfDoorUnlocked;

	private bool isPickedUp;

	private void OnTriggerEnter(Collider other)
	{
	}

	[IteratorStateMachine(typeof(_003CSafePhysicsDrop_003Ed__10))]
	private IEnumerator SafePhysicsDrop(GameObject targetCube)
	{
		return null;
	}
}

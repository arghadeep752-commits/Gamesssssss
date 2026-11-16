using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.CompilerServices;
using UnityEngine;

public class LeverInteractable : MonoBehaviour
{
	[CompilerGenerated]
	private sealed class _003CRotateLeverDownRoutine_003Ed__12 : IEnumerator<object>, IEnumerator, IDisposable
	{
		private int _003C_003E1__state;

		private object _003C_003E2__current;

		public LeverInteractable _003C_003E4__this;

		private Quaternion _003CtargetRotation_003E5__2;

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
		public _003CRotateLeverDownRoutine_003Ed__12(int _003C_003E1__state)
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

	[Header("Linked Extreme Lock")]
	public ExtremeFenceLock targetFence;

	[Header("Lever States")]
	public bool hasHandlePlaced;

	public bool isPulled;

	[Header("Visual References")]
	public GameObject missingHandleVisual;

	public Transform rotatingHandlePivot;

	[Header("Rotation Settings")]
	public Vector3 pulledRotationAngles;

	public float pullSpeed;

	[Header("Audio Settings")]
	public AudioSource audioSource;

	public AudioClip leverPullSound;

	[Header("Inventory Settings")]
	public string requiredItemName;

	private void Start()
	{
	}

	public void InteractWithLever(GameObject player)
	{
	}

	[IteratorStateMachine(typeof(_003CRotateLeverDownRoutine_003Ed__12))]
	private IEnumerator RotateLeverDownRoutine()
	{
		return null;
	}

	private bool CheckPlayerInventory(GameObject player)
	{
		return false;
	}

	private void RemoveItemFromInventory(GameObject player)
	{
	}
}

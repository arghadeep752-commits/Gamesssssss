using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.CompilerServices;
using UnityEngine;

public class EscapeLockElement : MonoBehaviour
{
	[CompilerGenerated]
	private sealed class _003CLandFallbackRoutine_003Ed__38 : IEnumerator<object>, IEnumerator, IDisposable
	{
		private int _003C_003E1__state;

		private object _003C_003E2__current;

		public EscapeLockElement _003C_003E4__this;

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
		public _003CLandFallbackRoutine_003Ed__38(int _003C_003E1__state)
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
	private sealed class _003CSlideBookshelfRoutine_003Ed__41 : IEnumerator<object>, IEnumerator, IDisposable
	{
		private int _003C_003E1__state;

		private object _003C_003E2__current;

		public EscapeLockElement _003C_003E4__this;

		private Vector3 _003CstartPos_003E5__2;

		private Vector3 _003CtargetPos_003E5__3;

		private float _003CelapsedTime_003E5__4;

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
		public _003CSlideBookshelfRoutine_003Ed__41(int _003C_003E1__state)
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

	[Header("Lock Configuration")]
	public EscapeLockType lockType;

	public string requiredItemName;

	[Tooltip("The message shown on screen if the player doesn't have the correct item")]
	public string missingItemAlertText;

	[HideInInspector]
	public bool isUnlocked;

	[Tooltip("Plank / Padlocks / Chain: ON = this lock must be opened before the Master Key door can be opened. Locks that are switched off in the current mode (e.g. Extra Locks off) are never required. (The Secret Bookshelf is never required.)")]
	public bool requiredForEscape;

	[Header("Audio")]
	public AudioSource audioSource;

	public AudioClip interactionSound;

	[Header("Chain Cut Visual Toggles")]
	public GameObject tightChainsGroup;

	public GameObject looseChainsGroup;

	[Header("Secret Bookshelf Settings")]
	[Tooltip("How far and in which direction the bookshelf slides (e.g., X = 3 means it moves 3 units right)")]
	public Vector3 bookshelfSlideOffset;

	public float bookshelfSlideSpeed;

	[Header("Master Key Win Condition Scene")]
	public string winSceneName;

	[Tooltip("ON: when unlocked, this object drops off the door, falls on the floor and STAYS there. OFF: it vanishes like before. (Untick on a Chain lock if this object is only an invisible trigger.)")]
	[Header("Fall To Floor When Unlocked (Plank / Padlocks / Chain lock)")]
	public bool fallOnUnlock;

	[Tooltip("Small push off the door towards the player, so it doesn't get stuck on the door")]
	public float popOffForce;

	[Tooltip("Granny hears it hit the floor and walks over to check (not in Practice / on silent ground)")]
	public bool alertGrannyOnLand;

	[Tooltip("Optional sound when it hits the floor")]
	public AudioClip landSound;

	[Range(0f, 1f)]
	public float landSoundVolume;

	[Tooltip("How hard it must hit something to count as landing")]
	public float minImpactSpeed;

	[Tooltip("After unlocking, the dropped object is moved to this layer so the player can't interact with it again. Leave empty to keep its layer.")]
	public string fallenLayerName;

	private bool isFalling;

	private bool hasLanded;

	private float fallStartTime;

	private static bool plankCleared;

	private static bool codeCleared;

	private static bool padlockCleared;

	private static bool chainCleared;

	private static bool bookshelfCleared;

	[RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)]
	private static void ResetStaticStates()
	{
	}

	public static bool AreAllDoorLocksCleared()
	{
		return false;
	}

	public static void LogLockedDoorLocks()
	{
	}

	public bool IsEffectivelyUnlocked()
	{
		return false;
	}

	private static string GetPath(Transform t)
	{
		return null;
	}

	public static int CountLockedDoorLocks()
	{
		return 0;
	}

	public static bool SceneHasDoorLocks()
	{
		return false;
	}

	public void InteractWithLock(string itemInHand)
	{
	}

	private void ActivateFallingPhysics()
	{
	}

	private void DropToFloor()
	{
	}

	private void OnCollisionEnter(Collision collision)
	{
	}

	[IteratorStateMachine(typeof(_003CLandFallbackRoutine_003Ed__38))]
	private IEnumerator LandFallbackRoutine()
	{
		return null;
	}

	private void OnLanded(Vector3 point)
	{
	}

	private void SetLayerRecursively(Transform t, int layer)
	{
	}

	[IteratorStateMachine(typeof(_003CSlideBookshelfRoutine_003Ed__41))]
	private IEnumerator SlideBookshelfRoutine()
	{
		return null;
	}

	private void CheckFinalEscapeState(MobilePickUpScript mobilePickup)
	{
	}

	private void PlayLockSound()
	{
	}
}

using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.CompilerServices;
using UnityEngine;

public class SecretBookshelfDoor : MonoBehaviour
{
	[CompilerGenerated]
	private sealed class _003CSlideOpenRoutine_003Ed__10 : IEnumerator<object>, IEnumerator, IDisposable
	{
		private int _003C_003E1__state;

		private object _003C_003E2__current;

		public SecretBookshelfDoor _003C_003E4__this;

		private float _003CelapsedTime_003E5__2;

		private Vector3 _003CstartPos_003E5__3;

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
		public _003CSlideOpenRoutine_003Ed__10(int _003C_003E1__state)
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

	[Header("Linked Lock")]
	[Tooltip("Drag the EscapeLockElement trigger attached to the bookshelf slot here.")]
	public EscapeLockElement lockElement;

	[Header("Movement Settings")]
	[Tooltip("How far and in which direction the bookshelf slides (e.g., X = 3 means 3 units right)")]
	public Vector3 slideOffset;

	public float slideSpeed;

	[Header("Audio")]
	public AudioSource bookshelfAudioSource;

	public AudioClip scrapingSound;

	private Vector3 closedPosition;

	private Vector3 openPosition;

	private bool standardSequenceTriggered;

	private void Start()
	{
	}

	private void Update()
	{
	}

	[IteratorStateMachine(typeof(_003CSlideOpenRoutine_003Ed__10))]
	private IEnumerator SlideOpenRoutine()
	{
		return null;
	}
}

using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.CompilerServices;
using UnityEngine;

public class EscapeSequenceManager : MonoBehaviour
{
	[CompilerGenerated]
	private sealed class _003CEscapeRoutine_003Ed__6 : IEnumerator<object>, IEnumerator, IDisposable
	{
		private int _003C_003E1__state;

		private object _003C_003E2__current;

		public EscapeSequenceManager _003C_003E4__this;

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
		public _003CEscapeRoutine_003Ed__6(int _003C_003E1__state)
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

	public Animator fadeAnimator;

	public GameObject playerObject;

	public Camera mainGameplayCamera;

	public Camera cutsceneCamera;

	public Animator balloonAnimator;

	public void StartEscapeCutscene()
	{
	}

	[IteratorStateMachine(typeof(_003CEscapeRoutine_003Ed__6))]
	private IEnumerator EscapeRoutine()
	{
		return null;
	}
}

using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.CompilerServices;
using UnityEngine;

public class EscapeSceneController : MonoBehaviour
{
	[CompilerGenerated]
	private sealed class _003CWaitAndGoToMenu_003Ed__3 : IEnumerator<object>, IEnumerator, IDisposable
	{
		private int _003C_003E1__state;

		private object _003C_003E2__current;

		public EscapeSceneController _003C_003E4__this;

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
		public _003CWaitAndGoToMenu_003Ed__3(int _003C_003E1__state)
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

	public float escapeDuration;

	public string mainMenuSceneName;

	private void Start()
	{
	}

	[IteratorStateMachine(typeof(_003CWaitAndGoToMenu_003Ed__3))]
	private IEnumerator WaitAndGoToMenu()
	{
		return null;
	}

	public void LoadMainMenu()
	{
	}
}

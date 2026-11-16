using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.CompilerServices;
using UnityEngine;
using UnityEngine.Video;

public class VideoGameOverController : MonoBehaviour
{
	[CompilerGenerated]
	private sealed class _003CEndingDisplaySequence_003Ed__4 : IEnumerator<object>, IEnumerator, IDisposable
	{
		private int _003C_003E1__state;

		private object _003C_003E2__current;

		public VideoGameOverController _003C_003E4__this;

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
		public _003CEndingDisplaySequence_003Ed__4(int _003C_003E1__state)
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

	[Header("Setup References")]
	public VideoPlayer videoPlayer;

	public GameObject gameOverTextUI;

	private void Start()
	{
	}

	private void OnVideoFinished(VideoPlayer vp)
	{
	}

	[IteratorStateMachine(typeof(_003CEndingDisplaySequence_003Ed__4))]
	private IEnumerator EndingDisplaySequence()
	{
		return null;
	}

	private void LoadMainMenu()
	{
	}

	private void OnDestroy()
	{
	}
}

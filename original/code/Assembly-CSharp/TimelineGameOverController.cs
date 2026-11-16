using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.CompilerServices;
using UnityEngine;
using UnityEngine.Playables;

public class TimelineGameOverController : MonoBehaviour
{
	[CompilerGenerated]
	private sealed class _003CEndingDisplaySequence_003Ed__8 : IEnumerator<object>, IEnumerator, IDisposable
	{
		private int _003C_003E1__state;

		private object _003C_003E2__current;

		public TimelineGameOverController _003C_003E4__this;

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
		public _003CEndingDisplaySequence_003Ed__8(int _003C_003E1__state)
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

	[Header("Timeline References")]
	[Tooltip("Drag the PlayableDirector component attached to your Timeline Director here.")]
	public PlayableDirector timelineDirector;

	[Header("UI References")]
	[Tooltip("Drag your Game Over UI canvas / panel here.")]
	public GameObject gameOverTextUI;

	[Header("Timing Settings")]
	[Tooltip("How long the screen stays on the final frame with UI visible before returning to Main Menu.")]
	public float displayDuration;

	[Header("Scene Settings")]
	public string mainMenuSceneName;

	private bool sequenceTriggered;

	private void Start()
	{
	}

	private void Update()
	{
	}

	private void OnTimelineFinished(PlayableDirector director)
	{
	}

	[IteratorStateMachine(typeof(_003CEndingDisplaySequence_003Ed__8))]
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

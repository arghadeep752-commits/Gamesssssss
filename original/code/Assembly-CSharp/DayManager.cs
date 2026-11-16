using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.CompilerServices;
using TMPro;
using UnityEngine;

public class DayManager : MonoBehaviour
{
	[CompilerGenerated]
	private sealed class _003C_003Ec__DisplayClass37_0
	{
		public bool adClosed;

		internal void _003CShowDeathAdOnBlackScreen_003Eb__0()
		{
		}
	}

	[CompilerGenerated]
	private sealed class _003CFadeDeathCanvasIn_003Ed__36 : IEnumerator<object>, IEnumerator, IDisposable
	{
		private int _003C_003E1__state;

		private object _003C_003E2__current;

		public DayManager _003C_003E4__this;

		private CanvasGroup _003Cgroup_003E5__2;

		private float _003Cduration_003E5__3;

		private float _003Celapsed_003E5__4;

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
		public _003CFadeDeathCanvasIn_003Ed__36(int _003C_003E1__state)
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
	private sealed class _003CFadeThenGameOver_003Ed__39 : IEnumerator<object>, IEnumerator, IDisposable
	{
		private int _003C_003E1__state;

		private object _003C_003E2__current;

		public DayManager _003C_003E4__this;

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
		public _003CFadeThenGameOver_003Ed__39(int _003C_003E1__state)
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
	private sealed class _003CGameOverSequence_003Ed__41 : IEnumerator<object>, IEnumerator, IDisposable
	{
		private int _003C_003E1__state;

		private object _003C_003E2__current;

		public DayManager _003C_003E4__this;

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
		public _003CGameOverSequence_003Ed__41(int _003C_003E1__state)
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
	private sealed class _003CInitialStartDaySequence_003Ed__31 : IEnumerator<object>, IEnumerator, IDisposable
	{
		private int _003C_003E1__state;

		private object _003C_003E2__current;

		public DayManager _003C_003E4__this;

		private GameObject _003CmobileCanvas_003E5__2;

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
		public _003CInitialStartDaySequence_003Ed__31(int _003C_003E1__state)
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
	private sealed class _003CLocalNextDaySequence_003Ed__40 : IEnumerator<object>, IEnumerator, IDisposable
	{
		private int _003C_003E1__state;

		private object _003C_003E2__current;

		public DayManager _003C_003E4__this;

		private GameObject _003CmobileCanvas_003E5__2;

		private Vector3 _003CtargetDropPos_003E5__3;

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
		public _003CLocalNextDaySequence_003Ed__40(int _003C_003E1__state)
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
	private sealed class _003CShowDeathAdOnBlackScreen_003Ed__37 : IEnumerator<object>, IEnumerator, IDisposable
	{
		private int _003C_003E1__state;

		private object _003C_003E2__current;

		public DayManager _003C_003E4__this;

		private _003C_003Ec__DisplayClass37_0 _003C_003E8__1;

		private AdsManager _003Cads_003E5__2;

		private float _003Cwaited_003E5__3;

		private float _003CnoAdTimer_003E5__4;

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
		public _003CShowDeathAdOnBlackScreen_003Ed__37(int _003C_003E1__state)
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

	[Header("UI Reference")]
	public GameObject deathCanvas;

	public TMP_Text dayText;

	[Header("Day Text Font (same for every day)")]
	[Tooltip("Optional: the font for ALL day texts. Leave empty to use exactly the font the Day 1 text has.")]
	public TMP_FontAsset dayFont;

	private bool dayStyleSaved;

	private TMP_FontAsset savedFont;

	private Material savedMaterial;

	private float savedFontSize;

	private FontStyles savedFontStyle;

	private Color savedColor;

	private bool savedAutoSize;

	private TextAlignmentOptions savedAlignment;

	private string lastDayMessage;

	[Header("Death Fade & Next Day Sound")]
	[Tooltip("How long the screen takes to fade to black after the player is killed by Granny")]
	public float deathFadeInDuration;

	[Tooltip("How long the black screen with the next day text stays before the game continues")]
	public float dayTextHoldTime;

	[Tooltip("Sound that plays the moment the next day text appears (e.g. a heartbeat / bell / creepy sting)")]
	public AudioClip nextDaySound;

	[Range(0f, 1f)]
	public float nextDaySoundVolume;

	[Header("Death Ad (plays on the black screen, before the next day)")]
	[Tooltip("Play the PlayerDeath ad once the screen is fully black, before the next day starts.")]
	public bool showAdAfterDeath;

	[Tooltip("If the ad is still loading when the screen goes black, wait up to this many seconds for it. If it's still not ready, the ad is skipped (no error) and the next day starts.")]
	public float maxWaitForAdToLoad;

	[Header("Scene Settings")]
	[Tooltip("The exact name of your new Game Over scene in Build Settings.")]
	public string gameOverSceneName;

	[Header("Game Settings")]
	public int maxDays;

	private int currentDay;

	private AudioSource audioSource;

	private float fadeDurationForThisDeath;

	public static DayManager Instance { get; private set; }

	private void Awake()
	{
	}

	private void Start()
	{
	}

	private void SaveDayTextStyle()
	{
	}

	private void SetDayText(string message)
	{
	}

	private void LateUpdate()
	{
	}

	[IteratorStateMachine(typeof(_003CInitialStartDaySequence_003Ed__31))]
	private IEnumerator InitialStartDaySequence()
	{
		return null;
	}

	public void TriggerNextDayScreen()
	{
	}

	public void TriggerNextDayScreen(float fadeDurationOverride)
	{
	}

	private CanvasGroup GetDeathCanvasGroup()
	{
		return null;
	}

	[IteratorStateMachine(typeof(_003CFadeDeathCanvasIn_003Ed__36))]
	private IEnumerator FadeDeathCanvasIn()
	{
		return null;
	}

	[IteratorStateMachine(typeof(_003CShowDeathAdOnBlackScreen_003Ed__37))]
	private IEnumerator ShowDeathAdOnBlackScreen()
	{
		return null;
	}

	private void PlayNextDaySound()
	{
	}

	[IteratorStateMachine(typeof(_003CFadeThenGameOver_003Ed__39))]
	private IEnumerator FadeThenGameOver()
	{
		return null;
	}

	[IteratorStateMachine(typeof(_003CLocalNextDaySequence_003Ed__40))]
	private IEnumerator LocalNextDaySequence()
	{
		return null;
	}

	[IteratorStateMachine(typeof(_003CGameOverSequence_003Ed__41))]
	private IEnumerator GameOverSequence()
	{
		return null;
	}
}

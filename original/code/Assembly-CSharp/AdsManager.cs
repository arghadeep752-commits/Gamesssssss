using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.CompilerServices;
using UnityEngine;
using UnityEngine.Advertisements;

public class AdsManager : MonoBehaviour, IUnityAdsInitializationListener, IUnityAdsLoadListener, IUnityAdsShowListener
{
	public static class Events
	{
		public const string PLAYER_DEATH = "PlayerDeath";

		public const string GAME_END = "GameEnd";

		public const string LEVEL_COMPLETE = "LevelComplete";

		public const string CONTINUE_RUN = "ContinueRun";

		public const string DOUBLE_REWARD = "DoubleReward";
	}

	public enum AdType
	{
		None = 0,
		Interstitial = 1,
		Rewarded = 2
	}

	[Serializable]
	public class AdEventMapping
	{
		[Tooltip("Must match the string you pass into TriggerAd(...) from your game code.")]
		public string eventKey;

		[Tooltip("Which ad (if any) should play for this event.")]
		public AdType adType;
	}

	[CompilerGenerated]
	private sealed class _003CRetryLoadAfterDelay_003Ed__48 : IEnumerator<object>, IEnumerator, IDisposable
	{
		private int _003C_003E1__state;

		private object _003C_003E2__current;

		public AdsManager _003C_003E4__this;

		public string adUnitId;

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
		public _003CRetryLoadAfterDelay_003Ed__48(int _003C_003E1__state)
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

	public static AdsManager Instance;

	[Header("Game IDs")]
	[SerializeField]
	private string androidGameId;

	[SerializeField]
	private string iosGameId;

	[Tooltip("Check this box to enable Test Ads while developing. UNCHECK before publishing.")]
	[SerializeField]
	[Header("Test Mode")]
	private bool testMode;

	[Header("Ad Unit IDs (Android)")]
	[SerializeField]
	private string androidInterstitialId;

	[SerializeField]
	private string androidRewardedId;

	[SerializeField]
	[Header("Ad Unit IDs (iOS)")]
	private string iosInterstitialId;

	[SerializeField]
	private string iosRewardedId;

	[Tooltip("Decide here which ad type fires for each gameplay event. Edit freely without touching code.")]
	[SerializeField]
	[Header("Event -> Ad Mapping")]
	private List<AdEventMapping> eventMappings;

	[Header("Interstitial Frequency (optional)")]
	[SerializeField]
	[Tooltip("Only show an interstitial once every N times that event fires. 1 = every time.")]
	private int interstitialEveryNTimes;

	[Header("Loading / Retry")]
	[Tooltip("If an ad fails to load, try again after this many seconds.")]
	[SerializeField]
	private float loadRetryDelay;

	[Tooltip("How many times in a row a failed ad is retried before waiting for the next request (e.g. next death).")]
	[SerializeField]
	private int maxLoadRetries;

	private string gameId;

	private string interstitialAdUnitId;

	private string rewardedAdUnitId;

	private Dictionary<string, AdType> eventAdTypeMap;

	private Dictionary<string, bool> isAdLoaded;

	private Dictionary<string, int> eventFireCounts;

	private Dictionary<string, bool> isAdLoading;

	private Dictionary<string, int> loadRetryCounts;

	private bool isShowingAd;

	private Action pendingRewardCallback;

	private Action pendingAdClosedCallback;

	private string pendingAdUnitBeingShown;

	public bool IsShowingAd => false;

	public bool IsTestMode => false;

	private void Awake()
	{
	}

	private void BuildEventMap()
	{
	}

	private void InitializeAds()
	{
	}

	public void PreloadAdForEvent(string eventKey)
	{
	}

	public bool IsAdReadyForEvent(string eventKey)
	{
		return false;
	}

	public bool HasAdForEvent(string eventKey)
	{
		return false;
	}

	private AdType GetAdTypeForEvent(string eventKey)
	{
		return AdType.None;
	}

	private bool IsLoaded(string adUnitId)
	{
		return false;
	}

	private bool IsLoading(string adUnitId)
	{
		return false;
	}

	public void TriggerAd(string eventKey, Action onRewardGranted = null, Action onAdClosed = null)
	{
	}

	public void ShowRewardedAd(Action onRewardGranted, Action onAdClosed = null)
	{
	}

	public void ShowInterstitialAd(Action onAdClosed = null)
	{
	}

	private void ShowRewardedInternal(Action onRewardGranted, Action onAdClosed)
	{
	}

	private void ShowInterstitialInternal(Action onAdClosed)
	{
	}

	public void LoadInterstitialAd()
	{
	}

	public void LoadRewardedAd()
	{
	}

	private void SafeLoad(string adUnitId)
	{
	}

	[IteratorStateMachine(typeof(_003CRetryLoadAfterDelay_003Ed__48))]
	private IEnumerator RetryLoadAfterDelay(string adUnitId)
	{
		return null;
	}

	public void OnInitializationComplete()
	{
	}

	public void OnInitializationFailed(UnityAdsInitializationError error, string message)
	{
	}

	public void OnUnityAdsAdLoaded(string placementId)
	{
	}

	public void OnUnityAdsFailedToLoad(string placementId, UnityAdsLoadError error, string message)
	{
	}

	public void OnUnityAdsShowFailure(string placementId, UnityAdsShowError error, string message)
	{
	}

	public void OnUnityAdsShowComplete(string placementId, UnityAdsShowCompletionState showCompletionState)
	{
	}

	private void FireAdClosedAndReload(string placementId)
	{
	}

	public void OnUnityAdsShowStart(string placementId)
	{
	}

	public void OnUnityAdsShowClick(string placementId)
	{
	}
}

using System;
using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// Granny Dimnight has no ads. Same class, events and settings as Granny 4 EndGame's AdsManager (so the scenes and
/// the other scripts keep working), but nothing is shown: a reward someone asked for is granted straight away and
/// "ad closed" callbacks run at once, so the game simply carries on.
/// </summary>
public class AdsManager : MonoBehaviour
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
        public string eventKey;
        public AdType adType;
    }

    public static AdsManager Instance;

    [Header("Game IDs")]
    [SerializeField] private string androidGameId;
    [SerializeField] private string iosGameId;
    [SerializeField] private bool testMode;
    [SerializeField] private string androidInterstitialId;
    [SerializeField] private string androidRewardedId;
    [SerializeField] private string iosInterstitialId;
    [SerializeField] private string iosRewardedId;
    [SerializeField] private List<AdEventMapping> eventMappings;
    [SerializeField] private int interstitialEveryNTimes;
    [SerializeField] private float loadRetryDelay;
    [SerializeField] private int maxLoadRetries;

    public bool IsShowingAd => false;
    public bool IsTestMode => false;

    private void Awake()
    {
        if (Instance != null && Instance != this)
        {
            Destroy(gameObject);
            return;
        }
        Instance = this;
        if (transform.parent == null) DontDestroyOnLoad(gameObject);
    }

    public void PreloadAdForEvent(string eventKey) { }
    public bool IsAdReadyForEvent(string eventKey) { return false; }
    public bool HasAdForEvent(string eventKey) { return false; }

    public void TriggerAd(string eventKey, Action onRewardGranted = null, Action onAdClosed = null)
    {
        onRewardGranted?.Invoke();
        onAdClosed?.Invoke();
    }

    public void ShowRewardedAd(Action onRewardGranted, Action onAdClosed = null)
    {
        onRewardGranted?.Invoke();
        onAdClosed?.Invoke();
    }

    public void ShowInterstitialAd(Action onAdClosed = null)
    {
        onAdClosed?.Invoke();
    }

    public void LoadInterstitialAd() { }
    public void LoadRewardedAd() { }
    public void OnInitializationComplete() { }
    public void OnUnityAdsAdLoaded(string placementId) { }
    public void OnUnityAdsShowStart(string placementId) { }
    public void OnUnityAdsShowClick(string placementId) { }
}

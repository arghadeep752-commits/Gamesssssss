using System.Collections;
using UnityEngine;

/// <summary>
/// The mode chosen in the menu, applied to the house: Practice (no Granny), Extreme / Extra Locks (the fence, the
/// lever and its handle), darker mode, and the house music.
/// </summary>
public class GameplayManager : MonoBehaviour
{
    [Header("Difficulty Tuning")]
    public string currentDifficulty;

    [Header("Atmosphere Modifiers")]
    public GameObject darkerModeFogVolume;
    public Color darkerModeAmbientColor;
    public Color normalAmbientColor;

    [Header("Map Modifiers")]
    public GameObject extraLocksObject;

    [Header("Extreme Mode Exclusive Modifiers")]
    public GameObject extremeFenceObject;
    public GameObject extremeLeverObject;
    public GameObject extremeHandleObject;

    [Header("Audio Settings")]
    public AudioSource houseMusicSource;

    public static GameplayManager Instance { get; private set; }

    private Color sceneAmbientSky, sceneAmbientEquator, sceneAmbientGround;
    private float sceneFogDensity;

    private void Awake()
    {
        Instance = this;
        sceneAmbientSky = RenderSettings.ambientSkyColor;
        sceneAmbientEquator = RenderSettings.ambientEquatorColor;
        sceneAmbientGround = RenderSettings.ambientGroundColor;
        sceneFogDensity = RenderSettings.fogDensity;
    }

    private void Start()
    {
        LoadGameSettings();
        ApplyDifficultySettings();
        ApplyHouseMusic(MusicSettings.IsOn, true);
    }

    public void OnPlayerCaught()
    {
        OnPlayerCaught(0f);
    }

    public void OnPlayerCaught(float fadeDurationOverride)
    {
        if (DayManager.Instance == null) return;
        if (fadeDurationOverride > 0f) DayManager.Instance.TriggerNextDayScreen(fadeDurationOverride);
        else DayManager.Instance.TriggerNextDayScreen();
    }

    public IEnumerator ResetDaySequence()
    {
        if (GameManager.Instance != null) GameManager.Instance.ResetPlayerForNextDay();
        yield return null;
    }

    private void LoadGameSettings()
    {
        currentDifficulty = GameSave.Difficulty;
    }

    private void OnEnable()
    {
        MusicSettings.OnMusicChanged += OnMusicSettingChanged;
    }

    private void OnDisable()
    {
        MusicSettings.OnMusicChanged -= OnMusicSettingChanged;
    }

    private void OnMusicSettingChanged(bool on)
    {
        ApplyHouseMusic(on, false);
    }

    private void ApplyHouseMusic(bool on, bool atStart)
    {
        if (houseMusicSource == null) return;
        if (on) { if (!houseMusicSource.isPlaying) houseMusicSource.Play(); }
        else houseMusicSource.Stop();
    }

    private void ApplyDifficultySettings()
    {
        bool extreme = currentDifficulty == "Extreme";
        bool extra = extreme || GameSave.ExtraLocks;
        if (GameSave.IsPractice) extra = GameSave.ExtraLocks;
        SetActive(extraLocksObject, extra);
        SetActive(extremeFenceObject, extra);
        SetActive(extremeLeverObject, extra);
        SetActive(extremeHandleObject, extra);
        ApplyDarkerMode(extreme || GameSave.DarkerMode);
    }

    private static void SetActive(GameObject go, bool on)
    {
        if (go != null && go.activeSelf != on) go.SetActive(on);
    }

    private void ApplyDarkerMode(bool enabled)
    {
        if (darkerModeFogVolume != null) darkerModeFogVolume.SetActive(enabled);
        if (enabled)
        {
            RenderSettings.ambientSkyColor = sceneAmbientSky * 0.35f;
            RenderSettings.ambientEquatorColor = sceneAmbientEquator * 0.35f;
            RenderSettings.ambientGroundColor = sceneAmbientGround * 0.35f;
            RenderSettings.fogDensity = Mathf.Max(sceneFogDensity * 1.8f, 0.08f);
        }
        else
        {
            RenderSettings.ambientSkyColor = sceneAmbientSky;
            RenderSettings.ambientEquatorColor = sceneAmbientEquator;
            RenderSettings.ambientGroundColor = sceneAmbientGround;
            RenderSettings.fogDensity = sceneFogDensity;
        }
    }
}

using System.Collections;
using TMPro;
using UnityEngine;
using UnityEngine.SceneManagement;

/// <summary>
/// Days, Granny style: "Day 1" on a black screen, then the player wakes up. Caught by Granny: the screen fades to
/// black, "Day 2" appears with a sting, and the next day starts in bed. After the last day: game over.
/// </summary>
public class DayManager : MonoBehaviour
{
    [Header("UI Reference")]
    public GameObject deathCanvas;
    public TMP_Text dayText;

    [Header("Day Text Font (same for every day)")]
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
    public float deathFadeInDuration;
    public float dayTextHoldTime;
    public AudioClip nextDaySound;
    public float nextDaySoundVolume;

    [Header("Death Ad (plays on the black screen, before the next day)")]
    public bool showAdAfterDeath;
    public float maxWaitForAdToLoad;

    [Header("Scene Settings")]
    public string gameOverSceneName;

    [Header("Game Settings")]
    public int maxDays;

    private int currentDay;
    private AudioSource audioSource;
    private float fadeDurationForThisDeath;
    private bool busy;

    public static DayManager Instance { get; private set; }
    public int CurrentDay => currentDay;

    private void Awake()
    {
        Instance = this;
        audioSource = GetComponent<AudioSource>();
        if (audioSource == null) { audioSource = gameObject.AddComponent<AudioSource>(); audioSource.playOnAwake = false; audioSource.spatialBlend = 0f; }
        currentDay = 1;
        if (maxDays <= 0) maxDays = 5;
        if (deathFadeInDuration <= 0f) deathFadeInDuration = 1.5f;
        if (dayTextHoldTime <= 0f) dayTextHoldTime = 3f;
    }

    private void Start()
    {
        Time.timeScale = 1f;
        SaveDayTextStyle();
        if (FindFirstObjectByType<PlayerWakeUp>() != null) StartCoroutine(InitialStartDaySequence());
    }

    private void SaveDayTextStyle()
    {
        if (dayText == null || dayStyleSaved) return;
        dayStyleSaved = true;
        savedFont = dayFont != null ? dayFont : dayText.font;
        savedMaterial = dayText.fontSharedMaterial;
        savedFontSize = dayText.fontSize;
        savedFontStyle = dayText.fontStyle;
        savedColor = dayText.color;
        savedAutoSize = dayText.enableAutoSizing;
        savedAlignment = dayText.alignment;
    }

    private void SetDayText(string message)
    {
        lastDayMessage = message;
        if (dayText == null) return;
        SaveDayTextStyle();
        if (savedFont != null) dayText.font = savedFont;
        dayText.fontSize = savedFontSize;
        dayText.fontStyle = savedFontStyle;
        dayText.enableAutoSizing = savedAutoSize;
        dayText.alignment = savedAlignment;
        Color c = savedColor;
        c.a = 1f;
        dayText.color = c;
        dayText.text = message;
        dayText.gameObject.SetActive(true);
    }

    private void LateUpdate()
    {
        if (dayText != null && !string.IsNullOrEmpty(lastDayMessage) && dayText.text != lastDayMessage && busy) dayText.text = lastDayMessage;
    }

    private GameObject MobileCanvas()
    {
        var jc = JumpscareCoordinator.Instance;
        if (jc != null && jc.mobileControlsCanvas != null) return jc.mobileControlsCanvas;
        return GameObject.Find("MobileControlsCanvas");
    }

    private IEnumerator InitialStartDaySequence()
    {
        busy = true;
        GameObject mobileCanvas = MobileCanvas();
        if (mobileCanvas != null) mobileCanvas.SetActive(false);
        if (GameManager.Instance != null) GameManager.Instance.PlacePlayerAtSpawn();
        CanvasGroup group = GetDeathCanvasGroup();
        if (group != null) { group.alpha = 1f; group.blocksRaycasts = false; }
        SetDayText("Day " + currentDay);
        PlayNextDaySound();
        var wake = FindFirstObjectByType<PlayerWakeUp>();
        if (wake != null) wake.HoldLyingInBed();
        yield return new WaitForSeconds(Mathf.Min(dayTextHoldTime, 2.5f));
        if (wake != null) wake.BeginWakeUp();
        float t = 0f;
        while (t < 1f && group != null)
        {
            t += Time.deltaTime;
            group.alpha = 1f - t;
            yield return null;
        }
        if (group != null) group.alpha = 0f;
        busy = false;
    }

    public void TriggerNextDayScreen()
    {
        TriggerNextDayScreen(deathFadeInDuration);
    }

    public void TriggerNextDayScreen(float fadeDurationOverride)
    {
        if (busy) return;
        busy = true;
        fadeDurationForThisDeath = fadeDurationOverride > 0f ? fadeDurationOverride : deathFadeInDuration;
        OutdoorAmbientZone.OnPlayerDied();
        if (currentDay >= maxDays) StartCoroutine(FadeThenGameOver());
        else StartCoroutine(LocalNextDaySequence());
    }

    private CanvasGroup GetDeathCanvasGroup()
    {
        if (deathCanvas == null) return null;
        if (!deathCanvas.activeSelf) deathCanvas.SetActive(true);
        CanvasGroup g = deathCanvas.GetComponent<CanvasGroup>();
        if (g == null) g = deathCanvas.AddComponent<CanvasGroup>();
        return g;
    }

    private IEnumerator FadeDeathCanvasIn()
    {
        CanvasGroup group = GetDeathCanvasGroup();
        if (dayText != null) dayText.gameObject.SetActive(false);
        float duration = Mathf.Max(0.05f, fadeDurationForThisDeath);
        float elapsed = 0f;
        float start = group != null ? group.alpha : 0f;
        while (elapsed < duration)
        {
            elapsed += Time.deltaTime;
            if (group != null) group.alpha = Mathf.Lerp(start, 1f, elapsed / duration);
            yield return null;
        }
        if (group != null) group.alpha = 1f;
    }

    private IEnumerator ShowDeathAdOnBlackScreen()
    {
        yield break;   // Granny Dimnight has no ads
    }

    private void PlayNextDaySound()
    {
        if (nextDaySound != null && audioSource != null) audioSource.PlayOneShot(nextDaySound, nextDaySoundVolume > 0f ? nextDaySoundVolume : 1f);
    }

    private IEnumerator FadeThenGameOver()
    {
        yield return FadeDeathCanvasIn();
        yield return GameOverSequence();
    }

    private IEnumerator LocalNextDaySequence()
    {
        GameObject mobileCanvas = MobileCanvas();
        yield return FadeDeathCanvasIn();
        if (mobileCanvas != null) mobileCanvas.SetActive(false);
        yield return ShowDeathAdOnBlackScreen();
        currentDay++;
        SetDayText("Day " + currentDay);
        PlayNextDaySound();
        if (GameManager.Instance != null) GameManager.Instance.ResetPlayerForNextDay();
        var wake = FindFirstObjectByType<PlayerWakeUp>();
        if (wake != null) wake.HoldLyingInBed();
        yield return new WaitForSeconds(dayTextHoldTime);
        if (wake != null) wake.BeginWakeUp();
        CanvasGroup group = GetDeathCanvasGroup();
        float t = 0f;
        while (t < 1f && group != null)
        {
            t += Time.deltaTime;
            group.alpha = 1f - t;
            yield return null;
        }
        if (group != null) group.alpha = 0f;
        busy = false;
    }

    private IEnumerator GameOverSequence()
    {
        SetDayText("GAME OVER");
        yield return new WaitForSeconds(1.5f);
        string scene = string.IsNullOrEmpty(gameOverSceneName) ? "GameOverScene" : gameOverSceneName;
        if (Application.CanStreamedLevelBeLoaded(scene)) SceneManager.LoadScene(scene);
        else SceneManager.LoadScene(0);
    }
}

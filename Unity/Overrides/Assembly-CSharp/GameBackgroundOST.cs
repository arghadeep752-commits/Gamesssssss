using System.Collections;
using UnityEngine;

/// <summary>The in-game background soundtrack: fades in, follows the music setting.</summary>
public class GameBackgroundOST : MonoBehaviour
{
    [Header("Audio Setup")]
    public AudioSource ostAudioSource;
    public float targetVolume;
    public float fadeDuration;

    [Header("Music Setting")]
    public bool restartWhenTurnedOn;

    private Coroutine fadeRoutine;
    private bool gameWantsMusic;

    public static GameBackgroundOST Instance { get; private set; }

    private void Awake()
    {
        Instance = this;
        if (ostAudioSource == null) ostAudioSource = GetComponent<AudioSource>();
        if (ostAudioSource != null) { ostAudioSource.playOnAwake = false; ostAudioSource.loop = true; }
    }

    private void Start()
    {
        StartBackgroundMusic();
    }

    private void OnEnable()
    {
        MusicSettings.OnMusicChanged += HandleMusicChanged;
    }

    private void OnDisable()
    {
        MusicSettings.OnMusicChanged -= HandleMusicChanged;
    }

    private void HandleMusicChanged(bool on)
    {
        if (ostAudioSource == null) return;
        if (!on) { if (fadeRoutine != null) StopCoroutine(fadeRoutine); ostAudioSource.Stop(); return; }
        if (gameWantsMusic && (restartWhenTurnedOn || !ostAudioSource.isPlaying)) StartFade(FadeMusicIn());
    }

    public void StartBackgroundMusic()
    {
        gameWantsMusic = true;
        if (ostAudioSource == null || !MusicSettings.IsOn) return;
        StartFade(FadeMusicIn());
    }

    public void StopBackgroundMusic()
    {
        gameWantsMusic = false;
        FadeOutAndStop();
    }

    private void FadeOutAndStop()
    {
        if (ostAudioSource == null || !ostAudioSource.isPlaying) return;
        StartFade(FadeMusicOut());
    }

    private void StartFade(IEnumerator routine)
    {
        if (fadeRoutine != null) StopCoroutine(fadeRoutine);
        if (isActiveAndEnabled) fadeRoutine = StartCoroutine(routine);
    }

    private IEnumerator FadeMusicIn()
    {
        float target = targetVolume > 0f ? targetVolume : 0.8f;
        if (!ostAudioSource.isPlaying) { ostAudioSource.volume = 0f; ostAudioSource.Play(); }
        float elapsed = 0f;
        float start = ostAudioSource.volume;
        float d = Mathf.Max(0.05f, fadeDuration);
        while (elapsed < d)
        {
            elapsed += Time.unscaledDeltaTime;
            ostAudioSource.volume = Mathf.Lerp(start, target, elapsed / d);
            yield return null;
        }
        ostAudioSource.volume = target;
    }

    private IEnumerator FadeMusicOut()
    {
        float startVolume = ostAudioSource.volume;
        float elapsed = 0f;
        float d = Mathf.Max(0.05f, fadeDuration);
        while (elapsed < d)
        {
            elapsed += Time.unscaledDeltaTime;
            ostAudioSource.volume = Mathf.Lerp(startVolume, 0f, elapsed / d);
            yield return null;
        }
        ostAudioSource.Stop();
    }
}

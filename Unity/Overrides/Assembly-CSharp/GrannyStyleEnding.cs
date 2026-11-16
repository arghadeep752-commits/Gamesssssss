using System.Collections;
using UnityEngine;
using UnityEngine.SceneManagement;

/// <summary>
/// "You escaped" ending: a black screen with running footsteps, then the camera glides out of the house while it keeps
/// looking back at Granny; near the end the text and the black screen fade in and it goes back to the menu.
/// </summary>
public class GrannyStyleEnding : MonoBehaviour
{
    [Header("Movement Targets")]
    public Transform cameraEndTarget;
    public Transform grannyTarget;

    [Header("Cinematic Movement")]
    public float cameraTravelDuration;
    public float lookRotationSpeed;

    [Header("Filmy Timing Controls")]
    public float startFadeProgressThreshold;

    [Header("UI Canvas Groups (For Fading)")]
    public CanvasGroup endTextCanvasGroup;
    public CanvasGroup screenFadeCanvasGroup;

    [Header("Audio Configurations")]
    public AudioSource audioSource;
    public AudioClip endSceneSoundtrack;

    [Header("Intro Black Screen")]
    public AudioSource footstepAudioSource;
    public AudioClip footstepSound;
    public float introBlackScreenDuration;

    [Header("Enemy Animations")]
    public Animator enemyOneAnimator;
    public Animator enemyTwoAnimator;
    public string enemyAnimationTrigger;

    [Header("Scene Transition")]
    public string mainMenuSceneName;

    private float _travelProgress;

    private void Start()
    {
        Time.timeScale = 1f;
        if (endTextCanvasGroup != null) endTextCanvasGroup.alpha = 0f;
        if (screenFadeCanvasGroup != null) screenFadeCanvasGroup.alpha = 1f;
        StartCoroutine(IntroThenCinematicRoutine());
    }

    private IEnumerator IntroThenCinematicRoutine()
    {
        AudioSource steps = footstepAudioSource != null ? footstepAudioSource : audioSource;
        if (steps != null && footstepSound != null) steps.PlayOneShot(footstepSound);
        yield return new WaitForSeconds(introBlackScreenDuration > 0f ? introBlackScreenDuration : 3f);
        if (steps != null && steps != audioSource) steps.Stop();
        yield return FadeCanvas(screenFadeCanvasGroup, 1f, 0f, 1f);
        if (!string.IsNullOrEmpty(enemyAnimationTrigger))
        {
            DimnightUtil.Fire(enemyOneAnimator, enemyAnimationTrigger);
            DimnightUtil.Fire(enemyTwoAnimator, enemyAnimationTrigger);
        }
        if (audioSource != null && endSceneSoundtrack != null)
        {
            audioSource.Stop();
            audioSource.clip = endSceneSoundtrack;
            audioSource.loop = false;
            audioSource.volume = 1f;
            audioSource.Play();
        }
        StartCoroutine(TriggerFilmyOverlaysRoutine());
        yield return MoveCameraRoutine();
    }

    private IEnumerator MoveCameraRoutine()
    {
        Vector3 startPosition = transform.position;
        Vector3 endPosition = cameraEndTarget != null ? cameraEndTarget.position : startPosition;
        float elapsed = 0f;
        float duration = cameraTravelDuration > 0f ? cameraTravelDuration : 15f;
        while (elapsed < duration)
        {
            elapsed += Time.deltaTime;
            _travelProgress = Mathf.Clamp01(elapsed / duration);
            transform.position = Vector3.Lerp(startPosition, endPosition, Mathf.SmoothStep(0f, 1f, _travelProgress));
            if (grannyTarget != null)
            {
                Vector3 d = grannyTarget.position - transform.position;
                if (d.sqrMagnitude > 0.001f)
                    transform.rotation = Quaternion.Slerp(transform.rotation, Quaternion.LookRotation(d), Time.deltaTime * Mathf.Max(0.1f, lookRotationSpeed));
            }
            yield return null;
        }
        _travelProgress = 1f;
    }

    private IEnumerator TriggerFilmyOverlaysRoutine()
    {
        float threshold = startFadeProgressThreshold > 0f ? startFadeProgressThreshold : 0.7f;
        while (_travelProgress < threshold) yield return null;
        StartCoroutine(FadeCanvas(endTextCanvasGroup, 0f, 1f, 2f));
        yield return new WaitForSeconds(1.5f);
        yield return FadeCanvas(screenFadeCanvasGroup, 0f, 1f, 3f);
        float startVolume = audioSource != null ? audioSource.volume : 0f;
        float t = 0f;
        while (t < 2f)
        {
            t += Time.deltaTime;
            if (audioSource != null) audioSource.volume = Mathf.Lerp(startVolume, 0f, t / 2f);
            yield return null;
        }
        DimnightUtil.LoadScene(mainMenuSceneName, "MainMenu");
    }

    private IEnumerator FadeCanvas(CanvasGroup cg, float startAlpha, float endAlpha, float duration)
    {
        if (cg == null) yield break;
        float elapsed = 0f;
        while (elapsed < duration)
        {
            elapsed += Time.deltaTime;
            cg.alpha = Mathf.Lerp(startAlpha, endAlpha, elapsed / duration);
            yield return null;
        }
        cg.alpha = endAlpha;
    }
}

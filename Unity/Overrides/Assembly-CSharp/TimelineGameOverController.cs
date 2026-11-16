using System.Collections;
using UnityEngine;
using UnityEngine.Playables;

/// <summary>Game over: the timeline plays out (Granny takes the player away), the text shows, back to the menu.</summary>
public class TimelineGameOverController : MonoBehaviour
{
    [Header("Timeline References")]
    public PlayableDirector timelineDirector;

    [Header("UI References")]
    public GameObject gameOverTextUI;

    [Header("Timing Settings")]
    public float displayDuration;

    [Header("Scene Settings")]
    public string mainMenuSceneName;

    private bool sequenceTriggered;
    private float startTime;

    private void Start()
    {
        Time.timeScale = 1f;
        startTime = Time.time;
        if (gameOverTextUI != null) gameOverTextUI.SetActive(false);
        if (timelineDirector == null) timelineDirector = GetComponent<PlayableDirector>();
        if (timelineDirector != null)
        {
            timelineDirector.stopped += OnTimelineFinished;
            if (timelineDirector.state != PlayState.Playing) timelineDirector.Play();
        }
    }

    private void Update()
    {
        if (sequenceTriggered) return;
        bool done;
        if (timelineDirector == null || timelineDirector.playableAsset == null) done = Time.time - startTime > 8f;
        else done = timelineDirector.time >= timelineDirector.duration - 0.05f || (timelineDirector.state != PlayState.Playing && Time.time - startTime > 1f);
        if (done || Time.time - startTime > 60f) OnTimelineFinished(timelineDirector);
    }

    private void OnTimelineFinished(PlayableDirector director)
    {
        if (sequenceTriggered) return;
        sequenceTriggered = true;
        StartCoroutine(EndingDisplaySequence());
    }

    private IEnumerator EndingDisplaySequence()
    {
        if (gameOverTextUI != null) gameOverTextUI.SetActive(true);
        yield return new WaitForSeconds(Mathf.Max(1f, displayDuration));
        LoadMainMenu();
    }

    private void LoadMainMenu()
    {
        DimnightUtil.LoadScene(mainMenuSceneName, "MainMenu");
    }

    private void OnDestroy()
    {
        if (timelineDirector != null) timelineDirector.stopped -= OnTimelineFinished;
    }
}

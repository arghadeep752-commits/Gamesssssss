using System.Collections;
using UnityEngine;

/// <summary>Balloon fly-away cutscene: fade to black, switch to the cutscene camera, the balloon flies away.</summary>
public class EscapeSequenceManager : MonoBehaviour
{
    public Animator fadeAnimator;
    public GameObject playerObject;
    public Camera mainGameplayCamera;
    public Camera cutsceneCamera;
    public Animator balloonAnimator;

    private bool started;

    public void StartEscapeCutscene()
    {
        if (started) return;
        started = true;
        StartCoroutine(EscapeRoutine());
    }

    private IEnumerator EscapeRoutine()
    {
        DimnightUtil.FadeToBlack(fadeAnimator);
        yield return new WaitForSeconds(1f);
        if (playerObject != null) playerObject.SetActive(false);
        if (mainGameplayCamera != null) mainGameplayCamera.gameObject.SetActive(false);
        if (cutsceneCamera != null) { cutsceneCamera.gameObject.SetActive(true); cutsceneCamera.enabled = true; }
        DimnightUtil.FadeToClear(fadeAnimator);
        DimnightUtil.FireAny(balloonAnimator, "FlyAway", "Fly", "Escape");
    }
}

using UnityEngine;
using UnityEngine.SceneManagement;

/// <summary>Small helpers shared by the rewritten Granny Dimnight scripts.</summary>
public static class DimnightUtil
{
    /// <summary>Fires an animator parameter (trigger or bool) or plays a state with that name. Returns true if anything happened.</summary>
    public static bool Fire(Animator animator, string name)
    {
        if (animator == null || string.IsNullOrEmpty(name) || !animator.isActiveAndEnabled || animator.runtimeAnimatorController == null) return false;
        foreach (AnimatorControllerParameter p in animator.parameters)
        {
            if (p.name != name) continue;
            if (p.type == AnimatorControllerParameterType.Trigger) { animator.SetTrigger(name); return true; }
            if (p.type == AnimatorControllerParameterType.Bool) { animator.SetBool(name, true); return true; }
        }
        int hash = Animator.StringToHash(name);
        for (int layer = 0; layer < animator.layerCount; layer++)
        {
            if (animator.HasState(layer, hash))
            {
                animator.CrossFadeInFixedTime(hash, 0.15f, layer);
                return true;
            }
        }
        return false;
    }

    /// <summary>Fires the first name that exists on the animator.</summary>
    public static bool FireAny(Animator animator, params string[] names)
    {
        foreach (string n in names)
            if (Fire(animator, n)) return true;
        return false;
    }

    /// <summary>Fades a black-screen animator (FadeController: FadeToBlack / FadeToClear).</summary>
    public static void FadeToBlack(Animator fade)
    {
        if (fade == null) return;
        if (!fade.gameObject.activeInHierarchy) fade.gameObject.SetActive(true);
        FireAny(fade, "FadeToBlack", "FadeOut", "Fade", "fade", "StartFade", "Black");
    }

    public static void FadeToClear(Animator fade)
    {
        if (fade == null) return;
        FireAny(fade, "FadeToClear", "FadeIn", "Clear", "Unfade");
    }

    /// <summary>Loads a scene by name; falls back when the name is not in the build (some original references were misspelled).</summary>
    public static void LoadScene(string sceneName, string fallback)
    {
        Time.timeScale = 1f;
        if (!string.IsNullOrEmpty(sceneName) && Application.CanStreamedLevelBeLoaded(sceneName))
        {
            SceneManager.LoadScene(sceneName);
            return;
        }
        if (!string.IsNullOrEmpty(fallback) && Application.CanStreamedLevelBeLoaded(fallback))
        {
            Debug.Log("[DIMNIGHT] Scene '" + sceneName + "' is not in the build, loading '" + fallback + "'.");
            SceneManager.LoadScene(fallback);
            return;
        }
        SceneManager.LoadScene(0);
    }

    public static void Notify(string message)
    {
        if (string.IsNullOrEmpty(message)) return;
        if (MobilePickUpScript.Instance != null) MobilePickUpScript.Instance.ShowLockedNotification(message);
        else Debug.Log("[DIMNIGHT] " + message);
    }

    public static void PlayAt(AudioClip clip, Vector3 position, float volume = 1f)
    {
        if (clip != null) AudioSource.PlayClipAtPoint(clip, position, volume);
    }
}

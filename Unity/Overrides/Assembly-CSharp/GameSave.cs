using UnityEngine;

/// <summary>
/// Granny Dimnight: the choices made in the main menu, shared by every scene (difficulty, darker mode, extra locks,
/// look sensitivity). Not part of Granny 4 EndGame's own code; the rewritten scripts use it instead of hidden keys.
/// </summary>
public static class GameSave
{
    public const string DifficultyKey = "Difficulty";
    public const string DarkerKey = "DarkerMode";
    public const string ExtraLocksKey = "ExtraLocks";
    public const string SensitivityKey = "LookSensitivity";

    public static string Difficulty
    {
        get { return PlayerPrefs.GetString(DifficultyKey, "Normal"); }
        set { PlayerPrefs.SetString(DifficultyKey, string.IsNullOrEmpty(value) ? "Normal" : value); PlayerPrefs.Save(); }
    }

    public static bool IsPractice => string.Equals(Difficulty, "Practice", System.StringComparison.OrdinalIgnoreCase);

    public static bool DarkerMode
    {
        get { return PlayerPrefs.GetInt(DarkerKey, 0) == 1; }
        set { PlayerPrefs.SetInt(DarkerKey, value ? 1 : 0); PlayerPrefs.Save(); }
    }

    public static bool ExtraLocks
    {
        get { return PlayerPrefs.GetInt(ExtraLocksKey, 0) == 1; }
        set { PlayerPrefs.SetInt(ExtraLocksKey, value ? 1 : 0); PlayerPrefs.Save(); }
    }

    public static float Sensitivity(float fallback)
    {
        return PlayerPrefs.GetFloat(SensitivityKey, fallback);
    }

    public static void SetSensitivity(float value)
    {
        PlayerPrefs.SetFloat(SensitivityKey, value);
        PlayerPrefs.Save();
    }

    /// <summary>One action per tap: buttons may be wired both in the scene and in code; the second call in the same frame is ignored.</summary>
    public static bool FirstThisFrame(ref int lastFrame)
    {
        if (lastFrame == Time.frameCount) return false;
        lastFrame = Time.frameCount;
        return true;
    }

    /// <summary>"Padlock Key", "PadlockKey", "padlock_key" all match.</summary>
    public static string Clean(string s)
    {
        if (string.IsNullOrEmpty(s)) return "";
        var b = new System.Text.StringBuilder(s.Length);
        foreach (char c in s)
            if (char.IsLetterOrDigit(c)) b.Append(char.ToLowerInvariant(c));
        return b.ToString();
    }

    public static bool SameItem(string a, string b)
    {
        string ca = Clean(a), cb = Clean(b);
        return ca.Length > 0 && ca == cb;
    }

    public static Transform FindDeep(Transform root, string name)
    {
        if (root == null || string.IsNullOrEmpty(name)) return null;
        if (root.name == name) return root;
        for (int i = 0; i < root.childCount; i++)
        {
            Transform t = FindDeep(root.GetChild(i), name);
            if (t != null) return t;
        }
        return null;
    }

    public static GameObject PlayerObject()
    {
        GameObject p = null;
        try { p = GameObject.FindGameObjectWithTag("Player"); } catch (UnityException) { }
        if (p == null)
        {
            var fps = Object.FindFirstObjectByType<FPSController>();
            if (fps != null) p = fps.gameObject;
        }
        return p;
    }
}

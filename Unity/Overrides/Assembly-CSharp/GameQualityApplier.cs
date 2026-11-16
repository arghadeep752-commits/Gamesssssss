using UnityEngine;

/// <summary>Applies the texture quality chosen in the main menu (Low / Medium / High) every time the game starts.</summary>
public static class GameQualityApplier
{
    public const string QualityIndexKey = "QualityLevel";
    public const string TextureLimitKey = "TextureMipLimit";
    public const string UnityLevelKey = "UnityQualityLevel";

    [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)]
    private static void ApplySavedQualityOnStartup()
    {
        Apply(PlayerPrefs.GetInt(TextureLimitKey, 0), PlayerPrefs.GetInt(UnityLevelKey, -1));
    }

    public static void Apply(int textureLimit, int unityQualityLevel)
    {
        if (unityQualityLevel >= 0 && unityQualityLevel < QualitySettings.names.Length)
            QualitySettings.SetQualityLevel(unityQualityLevel, true);
        QualitySettings.globalTextureMipmapLimit = Mathf.Clamp(textureLimit, 0, 3);
    }
}

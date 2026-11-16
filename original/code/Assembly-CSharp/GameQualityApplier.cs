using UnityEngine;

public static class GameQualityApplier
{
	public const string QualityIndexKey = "QualityLevel";

	public const string TextureLimitKey = "TextureMipLimit";

	public const string UnityLevelKey = "UnityQualityLevel";

	[RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)]
	private static void ApplySavedQualityOnStartup()
	{
	}

	public static void Apply(int textureLimit, int unityQualityLevel)
	{
	}
}

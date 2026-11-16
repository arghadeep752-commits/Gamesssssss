using System;
using System.Runtime.CompilerServices;

public static class MusicSettings
{
	public const string Key = "MusicEnabled";

	[CompilerGenerated]
	private static Action<bool> m_OnMusicChanged;

	public static bool IsOn => false;

	public static event Action<bool> OnMusicChanged
	{
		[CompilerGenerated]
		add
		{
		}
		[CompilerGenerated]
		remove
		{
		}
	}

	public static void SetEnabled(bool on)
	{
	}
}

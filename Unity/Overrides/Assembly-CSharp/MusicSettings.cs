using System;
using UnityEngine;

/// <summary>Music on/off, saved between sessions. Menus, the house music and the soundtrack listen to OnMusicChanged.</summary>
public static class MusicSettings
{
    public const string Key = "MusicEnabled";

    public static event Action<bool> OnMusicChanged;

    public static bool IsOn => PlayerPrefs.GetInt(Key, 1) == 1;

    public static void SetEnabled(bool on)
    {
        PlayerPrefs.SetInt(Key, on ? 1 : 0);
        PlayerPrefs.Save();
        OnMusicChanged?.Invoke(on);
    }
}

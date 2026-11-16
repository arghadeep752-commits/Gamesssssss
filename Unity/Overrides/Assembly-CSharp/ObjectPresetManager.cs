using System;
using System.Collections.Generic;
using UnityEngine;

/// <summary>Every game, one of the item layouts is picked at random: only that layout's copy of each item is there.</summary>
public class ObjectPresetManager : MonoBehaviour
{
    [Serializable]
    public class PresetObjectGroup
    {
        public string presetName;
        public List<GameObject> activeObjects;
    }

    [Header("Preset Configurations")]
    public List<PresetObjectGroup> presetGroups;

    private void Start()
    {
        ApplyRandomPreset();
    }

    public void ApplyRandomPreset()
    {
        if (presetGroups == null || presetGroups.Count == 0) return;
        foreach (PresetObjectGroup g in presetGroups)
            if (g != null && g.activeObjects != null)
                foreach (GameObject go in g.activeObjects)
                    if (go != null) go.SetActive(false);
        PresetObjectGroup chosen = presetGroups[UnityEngine.Random.Range(0, presetGroups.Count)];
        if (chosen == null || chosen.activeObjects == null) return;
        foreach (GameObject go in chosen.activeObjects)
            if (go != null) go.SetActive(true);
    }
}

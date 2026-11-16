using System;
using System.Collections.Generic;
using UnityEngine;

/// <summary>Older item layout system (inactive in the house): spawns each preset item at the matching spawn point.</summary>
public class ItemPresetManager : MonoBehaviour
{
    [Serializable]
    public class ItemPlacement
    {
        public string itemID;
        public GameObject itemPrefab;
    }

    [Serializable]
    public class Preset
    {
        public string presetName;
        public List<ItemPlacement> itemPlacements;
    }

    [Header("Presets Configuration")]
    public List<Preset> availablePresets;

    [Header("Scene References")]
    public List<ItemSpawnPoint> allSpawnPoints;

    private List<GameObject> spawnedItems = new List<GameObject>();

    private void Start()
    {
        SpawnPresetItems();
    }

    public void SpawnPresetItems()
    {
        if (availablePresets == null || availablePresets.Count == 0 || allSpawnPoints == null) return;
        Preset p = availablePresets[UnityEngine.Random.Range(0, availablePresets.Count)];
        if (p == null || p.itemPlacements == null) return;
        foreach (ItemPlacement ip in p.itemPlacements)
        {
            if (ip == null || ip.itemPrefab == null) continue;
            foreach (ItemSpawnPoint sp in allSpawnPoints)
                if (sp != null && sp.itemID == ip.itemID)
                {
                    spawnedItems.Add(Instantiate(ip.itemPrefab, sp.transform.position, sp.transform.rotation));
                    break;
                }
        }
    }
}

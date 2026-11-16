using System;
using System.Collections.Generic;
using UnityEngine;

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

	private List<GameObject> spawnedItems;

	private void Start()
	{
	}

	public void SpawnPresetItems()
	{
	}
}

using System;
using System.Collections.Generic;
using UnityEngine;

public class ObjectPresetManager : MonoBehaviour
{
	[Serializable]
	public class PresetObjectGroup
	{
		[Tooltip("The preset number (e.g., Preset 1 = Index 0, Preset 2 = Index 1)")]
		public string presetName;

		[Tooltip("Objects that should ONLY be active during this preset")]
		public List<GameObject> activeObjects;
	}

	[Header("Preset Configurations")]
	public List<PresetObjectGroup> presetGroups;

	private void Start()
	{
	}

	public void ApplyRandomPreset()
	{
	}
}

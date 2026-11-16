using System.Collections.Generic;
using UnityEngine;

public class SilentGroundZone : MonoBehaviour
{
	private static readonly List<SilentGroundZone> allZones;

	private void OnEnable()
	{
	}

	private void OnDisable()
	{
	}

	public static bool IsSilentAt(Vector3 worldPoint)
	{
		return false;
	}

	public bool Contains(Vector3 worldPoint)
	{
		return false;
	}

	private void OnDrawGizmos()
	{
	}
}

using UnityEngine;

public class GrannyPatrolWaypoint : MonoBehaviour
{
	[Header("Progression Settings")]
	[Tooltip("If checked, Granny won't patrol here until an event unlocks it.")]
	public bool isLockedByDefault;

	[HideInInspector]
	public bool isUnlocked;

	private void Awake()
	{
	}

	public void UnlockWaypoint()
	{
	}
}

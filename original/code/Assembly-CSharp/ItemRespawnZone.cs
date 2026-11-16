using UnityEngine;

[RequireComponent(typeof(Collider))]
public class ItemRespawnZone : MonoBehaviour
{
	[Tooltip("Empty GameObject inside the house where lost items should appear")]
	public Transform respawnPoint;

	[Tooltip("Items are spread a little around the point so several items don't land inside each other")]
	public float scatterRadius;

	[Tooltip("How high above the respawn point the item appears (it then falls onto the floor)")]
	public float spawnHeight;

	private void Reset()
	{
	}

	private void Awake()
	{
	}

	private void OnTriggerEnter(Collider other)
	{
	}

	private void OnDrawGizmos()
	{
	}
}

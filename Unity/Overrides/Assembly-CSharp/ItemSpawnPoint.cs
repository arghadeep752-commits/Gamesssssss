using UnityEngine;

/// <summary>A place where a preset can put an item.</summary>
public class ItemSpawnPoint : MonoBehaviour
{
    public string itemID;

    private void OnDrawGizmos()
    {
        Gizmos.color = Color.cyan;
        Gizmos.DrawWireSphere(transform.position, 0.12f);
    }
}

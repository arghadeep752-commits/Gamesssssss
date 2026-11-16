using UnityEngine;

/// <summary>An item that falls through the floor or out of the map comes back inside the house.</summary>
public class ItemRespawnZone : MonoBehaviour
{
    public Transform respawnPoint;
    public float scatterRadius;
    public float spawnHeight;

    private void Reset()
    {
        scatterRadius = 0.3f;
        spawnHeight = 0.3f;
    }

    private void Awake()
    {
        foreach (Collider c in GetComponents<Collider>()) c.isTrigger = true;
    }

    private void OnTriggerEnter(Collider other)
    {
        InteractableItem item = other.GetComponentInParent<InteractableItem>();
        if (item == null || item.isHeld || respawnPoint == null) return;
        Vector2 r = Random.insideUnitCircle * scatterRadius;
        item.transform.position = respawnPoint.position + new Vector3(r.x, spawnHeight, r.y);
        var rb = item.GetComponent<Rigidbody>();
        if (rb != null && !rb.isKinematic) { rb.linearVelocity = Vector3.zero; rb.angularVelocity = Vector3.zero; }
    }

    private void OnDrawGizmos()
    {
        if (respawnPoint == null) return;
        Gizmos.color = Color.green;
        Gizmos.DrawWireSphere(respawnPoint.position, scatterRadius);
    }
}

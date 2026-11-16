using System.Collections.Generic;
using UnityEngine;

/// <summary>Soft ground (grass outside): things that land here make little or no noise and Granny doesn't hear them.</summary>
public class SilentGroundZone : MonoBehaviour
{
    private static readonly List<SilentGroundZone> allZones = new List<SilentGroundZone>();
    private Collider[] zoneColliders;

    private void OnEnable()
    {
        if (!allZones.Contains(this)) allZones.Add(this);
        zoneColliders = GetComponentsInChildren<Collider>(true);
    }

    private void OnDisable()
    {
        allZones.Remove(this);
    }

    public static bool IsSilentAt(Vector3 worldPoint)
    {
        for (int i = 0; i < allZones.Count; i++)
            if (allZones[i] != null && allZones[i].Contains(worldPoint)) return true;
        return false;
    }

    public bool Contains(Vector3 worldPoint)
    {
        if (zoneColliders == null || zoneColliders.Length == 0) zoneColliders = GetComponentsInChildren<Collider>(true);
        foreach (Collider c in zoneColliders)
        {
            if (c == null || !c.enabled) continue;
            Bounds b = c.bounds;
            b.Expand(new Vector3(0f, 0.6f, 0f));      // things lie on top of the ground volume
            if (!b.Contains(worldPoint)) continue;
            if (c is BoxCollider || c is SphereCollider || c is CapsuleCollider || (c is MeshCollider mc && mc.convex))
            {
                Vector3 p = c.ClosestPoint(worldPoint);
                if ((p - worldPoint).sqrMagnitude < 0.36f) return true;
            }
            else return true;
        }
        return false;
    }

    private void OnDrawGizmos()
    {
        Gizmos.color = new Color(0.2f, 0.8f, 0.2f, 0.25f);
        foreach (Collider c in GetComponentsInChildren<Collider>())
            if (c != null) Gizmos.DrawCube(c.bounds.center, c.bounds.size);
    }
}

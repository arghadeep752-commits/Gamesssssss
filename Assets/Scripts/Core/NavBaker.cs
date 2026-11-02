using System.Collections.Generic;
using UnityEngine;
using UnityEngine.AI;

namespace NightClass
{
    /// <summary>
    /// Builds the teacher's navigation mesh at load time from the level's colliders (doors, pickups,
    /// the player and the teacher are on excluded layers). Dynamic blockers (fire, rubble, hatch,
    /// roller door) carve it with NavMeshObstacles until they are cleared.
    /// </summary>
    public class NavBaker : MonoBehaviour
    {
        public static bool Ready { get; private set; }
        public Bounds bounds = new Bounds(new Vector3(0f, -1f, -2f), new Vector3(110f, 14f, 60f));
        public int layerMask = ~0;
        NavMeshDataInstance instance;

        void Awake() { Ready = false; }

        public void Build()
        {
            float t0 = Time.realtimeSinceStartup;
            NavMeshBuildSettings settings = NavMesh.GetSettingsByID(0);
            settings.agentRadius = 0.3f;
            settings.agentHeight = 1.7f;
            settings.agentClimb = 0.45f;
            settings.agentSlope = 48f;
            settings.minRegionArea = 0.6f;
            settings.overrideVoxelSize = true;
            settings.voxelSize = 0.1f;
            var sources = new List<NavMeshBuildSource>();
            var markups = new List<NavMeshBuildMarkup>();
            NavMeshBuilder.CollectSources(bounds, layerMask, NavMeshCollectGeometry.PhysicsColliders, 0, markups, sources);
            NavMeshData data = NavMeshBuilder.BuildNavMeshData(settings, sources, bounds, Vector3.zero, Quaternion.identity);
            if (data != null)
            {
                instance = NavMesh.AddNavMeshData(data);
                Ready = true;
            }
            NavMeshTriangulation tri = NavMesh.CalculateTriangulation();
            Debug.Log("[RF] navmesh: " + sources.Count + " sources, " + (tri.indices != null ? tri.indices.Length / 3 : 0) + " triangles, " +
                      ((Time.realtimeSinceStartup - t0) * 1000f).ToString("0") + " ms");
        }

        void OnDestroy()
        {
            if (instance.valid) instance.Remove();
            Ready = false;
        }
    }
}

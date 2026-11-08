using UnityEngine;
using UnityEngine.AI;

namespace GridProto
{
    /// <summary>Loads the walkable-area data (baked when the level is built) so the enemy can find paths.</summary>
    [DefaultExecutionOrder(-300)]
    public class NavMeshLoader : MonoBehaviour
    {
        public NavMeshData data;

        NavMeshDataInstance instance;

        void Awake()
        {
            if (data != null) instance = NavMesh.AddNavMeshData(data);
            else Debug.LogWarning("[GridProto] no NavMesh data in the scene");
        }

        void OnDestroy()
        {
            if (instance.valid) instance.Remove();
        }
    }
}

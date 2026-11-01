using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

namespace RealFPS
{
    /// <summary>
    /// Draws the whole forest with GPU instancing instead of ~900 separate tree objects.
    /// Every frame it picks a level of detail for each tree near the view and issues one
    /// instanced draw per tree variant, detail level and material (a few dozen draw calls
    /// in total), which keeps the CPU cost low on phones. Trees just outside the view but
    /// close to the camera are drawn into the shadow map only, so their shadows stay put.
    /// On software GPUs (the emulator) it falls back to one draw per tree.
    /// </summary>
    [DefaultExecutionOrder(1000)]
    public class TreeRenderer : MonoBehaviour
    {
        [System.Serializable]
        public class Variant
        {
            public Mesh lod0;   // submesh 0 bark, 1 needles
            public Mesh lod1;   // submesh 0 bark, 1 needles (cards)
            public Mesh lod2;   // single vertex-coloured silhouette
        }

        [Header("Set by the build script")]
        public Variant[] variants;
        public Material bark;
        public Material needles;
        public Material far;
        public Matrix4x4[] matrices;
        public int[] variantOf;
        public float[] heights;

        [Header("Distances in metres (multiplied by lodScale)")]
        public float lod0Distance = 30f;
        public float lod1Distance = 130f;
        public float cullDistance = 520f;
        public float lodScale = 1f;
        public float shadowDistance = 40f;
        public float chunkSize = 32f;

        public int DrawnLastFrame { get; private set; }
        public int DrawCallsLastFrame { get; private set; }

        // slots per variant: 0 LOD0 + shadows, 1 LOD0, 2 LOD1 + shadows, 3 LOD1, 4 LOD2, 5 shadow only
        const int Slots = 6;
        const int MaxBatch = 511;

        struct Chunk
        {
            public Bounds bounds;
            public int[] trees;
        }

        Matrix4x4[][] buckets;
        int[] counts;
        Vector3[] bMin, bMax;
        Chunk[] chunks;
        Vector3[] positions;
        readonly Plane[] planes = new Plane[6];
        bool instancing;
        int calls;

        void Start()
        {
            if (matrices == null || matrices.Length == 0 || variants == null || variants.Length == 0 ||
                variantOf == null || variantOf.Length != matrices.Length)
            {
                enabled = false;
                return;
            }
            instancing = RenderCompat.UseInstancing;
            foreach (Material m in new[] { bark, needles, far })
                if (m != null) m.enableInstancing = instancing;

            int n = matrices.Length, vc = variants.Length;
            positions = new Vector3[n];
            var perVariant = new int[vc];
            for (int i = 0; i < n; i++)
            {
                positions[i] = matrices[i].GetColumn(3);
                variantOf[i] = Mathf.Clamp(variantOf[i], 0, vc - 1);
                perVariant[variantOf[i]]++;
            }
            buckets = new Matrix4x4[vc * Slots][];
            counts = new int[vc * Slots];
            bMin = new Vector3[vc * Slots];
            bMax = new Vector3[vc * Slots];
            for (int v = 0; v < vc; v++)
                for (int s = 0; s < Slots; s++)
                    buckets[v * Slots + s] = new Matrix4x4[Mathf.Max(1, perVariant[v])];
            BuildChunks();
            Debug.Log("[RF] trees: " + n + " in " + chunks.Length + " chunks, instancing " + (instancing ? "on" : "off"));
        }

        void BuildChunks()
        {
            Vector3 min = positions[0], max = positions[0];
            for (int i = 1; i < positions.Length; i++)
            {
                min = Vector3.Min(min, positions[i]);
                max = Vector3.Max(max, positions[i]);
            }
            int nx = Mathf.Max(1, Mathf.CeilToInt((max.x - min.x + 0.01f) / chunkSize));
            int nz = Mathf.Max(1, Mathf.CeilToInt((max.z - min.z + 0.01f) / chunkSize));
            var lists = new List<int>[nx * nz];
            for (int i = 0; i < positions.Length; i++)
            {
                int cx = Mathf.Clamp((int)((positions[i].x - min.x) / chunkSize), 0, nx - 1);
                int cz = Mathf.Clamp((int)((positions[i].z - min.z) / chunkSize), 0, nz - 1);
                int k = cz * nx + cx;
                if (lists[k] == null) lists[k] = new List<int>();
                lists[k].Add(i);
            }
            var result = new List<Chunk>();
            foreach (List<int> l in lists)
            {
                if (l == null) continue;
                var b = new Bounds(positions[l[0]], Vector3.zero);
                foreach (int i in l)
                {
                    float h = heights != null && i < heights.Length ? heights[i] : 20f;
                    b.Encapsulate(positions[i]);
                    b.Encapsulate(positions[i] + Vector3.up * h);
                }
                b.Expand(new Vector3(10f, 2f, 10f));   // crowns
                result.Add(new Chunk { bounds = b, trees = l.ToArray() });
            }
            chunks = result.ToArray();
        }

        void Add(int bucket, int tree)
        {
            int c = counts[bucket];
            buckets[bucket][c] = matrices[tree];
            Vector3 p = positions[tree];
            float h = heights != null && tree < heights.Length ? heights[tree] : 20f;
            Vector3 lo = new Vector3(p.x - 5f, p.y - 1f, p.z - 5f);
            Vector3 hi = new Vector3(p.x + 5f, p.y + h, p.z + 5f);
            if (c == 0)
            {
                bMin[bucket] = lo;
                bMax[bucket] = hi;
            }
            else
            {
                bMin[bucket] = Vector3.Min(bMin[bucket], lo);
                bMax[bucket] = Vector3.Max(bMax[bucket], hi);
            }
            counts[bucket] = c + 1;
        }

        void LateUpdate()
        {
            Camera cam = Camera.main;
            if (cam == null || chunks == null) return;
            GeometryUtility.CalculateFrustumPlanes(cam, planes);
            Vector3 cp = cam.transform.position;
            float l0 = lod0Distance * lodScale, l1 = lod1Distance * lodScale;
            float lc = Mathf.Min(cullDistance * lodScale, cam.farClipPlane);
            float l0s = l0 * l0, l1s = l1 * l1, lcs = lc * lc;
            float sd = Mathf.Max(0f, shadowDistance), sds = sd * sd;
            System.Array.Clear(counts, 0, counts.Length);

            for (int c = 0; c < chunks.Length; c++)
            {
                Bounds b = chunks[c].bounds;
                float dc = Mathf.Sqrt(b.SqrDistance(cp));
                if (dc > lc) continue;
                bool inView = GeometryUtility.TestPlanesAABB(planes, b);
                if (!inView && dc > sd) continue;
                int[] list = chunks[c].trees;
                for (int k = 0; k < list.Length; k++)
                {
                    int i = list[k];
                    float ds = (positions[i] - cp).sqrMagnitude;
                    int slot;
                    if (!inView)
                    {
                        if (ds > sds) continue;
                        slot = 5;
                    }
                    else if (ds < l0s) slot = ds < sds ? 0 : 1;
                    else if (ds < l1s) slot = ds < sds ? 2 : 3;
                    else if (ds < lcs) slot = 4;
                    else continue;
                    Add(variantOf[i] * Slots + slot, i);
                }
            }
            Draw();
        }

        void Draw()
        {
            int drawn = 0;
            calls = 0;
            for (int v = 0; v < variants.Length; v++)
            {
                Variant va = variants[v];
                for (int s = 0; s < Slots; s++)
                {
                    int idx = v * Slots + s;
                    int n = counts[idx];
                    if (n == 0) continue;
                    if (s != 5) drawn += n;
                    if (s == 4)
                    {
                        Submit(far, va.lod2, 0, idx, n, ShadowCastingMode.Off);
                        continue;
                    }
                    Mesh mesh = s <= 1 ? va.lod0 : va.lod1;
                    ShadowCastingMode shadows = s == 5 ? ShadowCastingMode.ShadowsOnly :
                                                (s == 0 || s == 2) ? ShadowCastingMode.On : ShadowCastingMode.Off;
                    Submit(bark, mesh, 0, idx, n, shadows);
                    if (mesh != null && mesh.subMeshCount > 1) Submit(needles, mesh, 1, idx, n, shadows);
                }
            }
            DrawnLastFrame = drawn;
            DrawCallsLastFrame = calls;
        }

        void Submit(Material mat, Mesh mesh, int submesh, int idx, int n, ShadowCastingMode shadows)
        {
            if (mat == null || mesh == null || submesh >= mesh.subMeshCount) return;
            var rp = new RenderParams(mat)
            {
                shadowCastingMode = shadows,
                receiveShadows = shadows != ShadowCastingMode.ShadowsOnly,
                layer = gameObject.layer,
                worldBounds = new Bounds((bMin[idx] + bMax[idx]) * 0.5f, bMax[idx] - bMin[idx]),
                lightProbeUsage = LightProbeUsage.Off,
                reflectionProbeUsage = ReflectionProbeUsage.Off,
                motionVectorMode = MotionVectorGenerationMode.ForceNoMotion
            };
            Matrix4x4[] arr = buckets[idx];
            if (instancing)
            {
                for (int start = 0; start < n; start += MaxBatch)
                {
                    Graphics.RenderMeshInstanced(rp, mesh, submesh, arr, Mathf.Min(MaxBatch, n - start), start);
                    calls++;
                }
            }
            else
            {
                for (int k = 0; k < n; k++)
                {
                    Graphics.RenderMesh(rp, mesh, submesh, arr[k]);
                    calls++;
                }
            }
        }
    }
}

using System.Collections.Generic;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace NightClass.EditorTools
{
    /// <summary>
    /// Real 3D props (Poly Haven, CC0) downloaded by tools/fetch_assets.py into Assets/Art/Models/&lt;slot&gt;/.
    /// Each placement scales the model to a real-world size, sits it on the floor and adds a box collider.
    /// When a slot has no model the callers fall back to the simple built-in versions.
    /// </summary>
    public static partial class NCWorld
    {
        const string ModelDir = "Assets/Art/Models/";
        static readonly Dictionary<string, GameObject> modelCache = new Dictionary<string, GameObject>();
        static readonly Dictionary<string, int> modelUses = new Dictionary<string, int>();
        static int modelTris, modelTrisSource;
        static readonly Dictionary<string, Mesh> decimated = new Dictionary<string, Mesh>();
        static readonly Dictionary<string, Vector2Int> slotTris = new Dictionary<string, Vector2Int>();

        // triangle budget per placed model (phones like the Galaxy A21s need light props)
        static readonly Dictionary<string, int> ModelBudget = new Dictionary<string, int>
        {
            { "school_desk", 1100 }, { "school_chair", 900 }, { "chair", 1200 }, { "table", 1400 }, { "table2", 1400 },
            { "shelf", 2400 }, { "metal_shelf", 1400 }, { "sofa", 2800 }, { "armchair", 2400 }, { "coffee_table", 1200 },
            { "tv", 1400 }, { "cabinet", 2400 }, { "nightstand", 1200 }, { "barrel", 1100 }, { "wet_sign", 600 },
            { "drill", 900 }, { "wrench", 500 }, { "box", 300 }, { "crate", 500 }, { "bucket", 700 }, { "plant", 2200 },
            { "books", 1400 }, { "desk_lamp", 1100 }, { "extinguisher", 900 }, { "clock", 600 }, { "hammer", 500 },
            { "cash_register", 1400 }, { "trash", 900 }, { "rock", 1000 }, { "toolbox", 900 },
        };

        static int Tris(Mesh m)
        {
            int n = 0;
            for (int i = 0; i < m.subMeshCount; i++) n += (int)(m.GetIndexCount(i) / 3);
            return n;
        }

        /// <summary>
        /// Simple vertex-clustering mesh reduction (own code): vertices that fall into the same small cell
        /// and share nearly the same UV are merged; the cell size is searched until the triangle budget fits.
        /// </summary>
        static Mesh Decimate(Mesh src, int target)
        {
            int srcTris = Tris(src);
            if (srcTris <= target || target < 12) return src;
            string key = src.GetInstanceID() + "_" + target;
            Mesh cached;
            if (decimated.TryGetValue(key, out cached)) return cached;
            Vector3[] v = src.vertices;
            Vector2[] uv = src.uv;
            bool hasUV = uv != null && uv.Length == v.Length;
            int subs = src.subMeshCount;
            var tris = new int[subs][];
            for (int sm = 0; sm < subs; sm++) tris[sm] = src.GetTriangles(sm);
            Bounds b = src.bounds;
            float extent = Mathf.Max(b.size.x, Mathf.Max(b.size.y, b.size.z));
            Mesh best = null;
            // first keep UV seams intact; if that can't reach the budget, merge across seams too
            for (int pass = 0; pass < 2 && best == null; pass++)
            {
                bool keepSeams = hasUV && pass == 0;
                float lo = extent / 4000f, hi = extent / 2f;
                for (int it = 0; it < 16; it++)
                {
                    float cell = Mathf.Sqrt(lo * hi);
                    Mesh m = Cluster(v, uv, hasUV, keepSeams, tris, b.min, cell);
                    if (Tris(m) > target * 1.15f) lo = cell;
                    else { best = m; hi = cell; }
                    if (hi / lo < 1.08f) break;
                }
            }
            if (best == null) best = Cluster(v, uv, hasUV, false, tris, b.min, extent / 2f);
            best.name = src.name + "_lod";
            decimated[key] = best;
            return best;
        }

        static Mesh Cluster(Vector3[] v, Vector2[] uv, bool hasUV, bool keepSeams, int[][] tris, Vector3 origin, float cell)
        {
            var map = new int[v.Length];
            var index = new Dictionary<long, int>();
            var sumP = new List<Vector3>();
            var sumUV = new List<Vector2>();
            var count = new List<int>();
            float inv = 1f / cell;
            for (int i = 0; i < v.Length; i++)
            {
                Vector3 q = (v[i] - origin) * inv;
                long x = (long)Mathf.Floor(q.x), y = (long)Mathf.Floor(q.y), z = (long)Mathf.Floor(q.z);
                long u = 0, w = 0;
                if (keepSeams) { u = (long)Mathf.Floor(uv[i].x * 48f) & 0xFF; w = (long)Mathf.Floor(uv[i].y * 48f) & 0xFF; }
                long k = ((x & 0xFFFF) << 48) | ((y & 0xFFFF) << 32) | ((z & 0xFFFF) << 16) | (u << 8) | w;
                int c;
                if (!index.TryGetValue(k, out c))
                {
                    c = sumP.Count;
                    index[k] = c;
                    sumP.Add(Vector3.zero);
                    sumUV.Add(Vector2.zero);
                    count.Add(0);
                }
                sumP[c] += v[i];
                if (hasUV) sumUV[c] += uv[i];
                count[c]++;
                map[i] = c;
            }
            var pos = new Vector3[sumP.Count];
            var tex = new Vector2[sumP.Count];
            for (int c = 0; c < pos.Length; c++)
            {
                pos[c] = sumP[c] / count[c];
                tex[c] = hasUV ? sumUV[c] / count[c] : Vector2.zero;
            }
            var m = new Mesh();
            if (pos.Length > 65000) m.indexFormat = IndexFormat.UInt32;
            m.vertices = pos;
            if (hasUV) m.uv = tex;
            m.subMeshCount = tris.Length;
            var seen = new HashSet<long>();
            for (int sm = 0; sm < tris.Length; sm++)
            {
                int[] t = tris[sm];
                var o = new List<int>(t.Length / 2);
                for (int i = 0; i + 2 < t.Length; i += 3)
                {
                    int a = map[t[i]], bb = map[t[i + 1]], c = map[t[i + 2]];
                    if (a == bb || bb == c || a == c) continue;
                    o.Add(a); o.Add(bb); o.Add(c);
                }
                m.SetTriangles(o, sm);
            }
            m.RecalculateNormals();
            m.RecalculateBounds();
            if (hasUV) m.RecalculateTangents();
            return m;
        }

        // Yaw correction per model so that the model's "front" points along +Z (fixed after looking at screenshots).
        static readonly Dictionary<string, float> ModelYaw = new Dictionary<string, float>
        {
            { "school_desk", 0f }, { "school_chair", 0f }, { "sofa", 0f }, { "armchair", 0f }, { "tv", 0f },
            { "cabinet", 0f }, { "shelf", 0f }, { "chair", 0f }, { "cash_register", 0f }, { "wet_sign", 0f },
        };

        static GameObject ModelPrefab(string slot)
        {
            GameObject g;
            if (modelCache.TryGetValue(slot, out g)) return g;
            g = null;
            string dir = ModelDir + slot;
            if (AssetDatabase.IsValidFolder(dir))
            {
                foreach (string guid in AssetDatabase.FindAssets("t:Model", new[] { dir }))
                {
                    g = AssetDatabase.LoadAssetAtPath<GameObject>(AssetDatabase.GUIDToAssetPath(guid));
                    if (g != null) break;
                }
            }
            modelCache[slot] = g;
            return g;
        }

        static bool HasModel(string slot) { return ModelPrefab(slot) != null; }

        static Bounds RendBounds(GameObject go)
        {
            Renderer[] rs = go.GetComponentsInChildren<Renderer>();
            if (rs.Length == 0) return new Bounds(go.transform.position, Vector3.one * 0.1f);
            Bounds b = rs[0].bounds;
            for (int i = 1; i < rs.Length; i++) b.Encapsulate(rs[i].bounds);
            return b;
        }

        /// <summary>
        /// Places a real model. size.y > 0 fits the height; otherwise size.x fits the longest horizontal side.
        /// The model's footprint is centred on pos (x/z) and its bottom sits at pos.y.
        /// </summary>
        static GameObject PlaceModel(string slot, Vector3 pos, float yaw, Vector2 size, bool collider = true, Transform parent = null, bool isStatic = true)
        {
            GameObject prefab = ModelPrefab(slot);
            if (prefab == null) return null;
            var go = (GameObject)Object.Instantiate(prefab);
            go.name = slot;
            go.transform.SetParent(parent != null ? parent : objRoot, false);
            go.transform.localScale = Vector3.one;
            go.transform.rotation = Quaternion.identity;
            go.transform.position = Vector3.zero;
            Bounds b = RendBounds(go);
            float s = size.y > 0f ? size.y / Mathf.Max(b.size.y, 1e-3f) : size.x / Mathf.Max(Mathf.Max(b.size.x, b.size.z), 1e-3f);
            go.transform.localScale = go.transform.localScale * s;
            float yo;
            ModelYaw.TryGetValue(slot, out yo);
            go.transform.rotation = Quaternion.Euler(0f, yaw + yo, 0f);
            b = RendBounds(go);
            go.transform.position += new Vector3(pos.x - b.center.x, pos.y - b.min.y, pos.z - b.center.z);
            ReduceModel(go, slot);
            foreach (Renderer r in go.GetComponentsInChildren<Renderer>())
            {
                r.shadowCastingMode = ShadowCastingMode.Off;
                r.receiveShadows = false;
            }
            foreach (Collider c in go.GetComponentsInChildren<Collider>()) Object.DestroyImmediate(c);
            if (isStatic)
                foreach (Transform t in go.GetComponentsInChildren<Transform>())
                    GameObjectUtility.SetStaticEditorFlags(t.gameObject, StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccludeeStatic);
            if (collider)
            {
                b = RendBounds(go);
                Collider(b.center, b.size);
            }
            int n;
            modelUses.TryGetValue(slot, out n);
            modelUses[slot] = n + 1;
            return go;
        }

        /// <summary>Fits every mesh of a placed model into the slot's triangle budget (shared between its meshes).</summary>
        static void ReduceModel(GameObject go, string slot)
        {
            int budget;
            if (!ModelBudget.TryGetValue(slot, out budget)) budget = 1500;
            MeshFilter[] mfs = go.GetComponentsInChildren<MeshFilter>();
            int total = 0;
            foreach (MeshFilter mf in mfs) if (mf.sharedMesh != null) total += Tris(mf.sharedMesh);
            modelTrisSource += total;
            int after = 0;
            foreach (MeshFilter mf in mfs)
            {
                if (mf.sharedMesh == null) continue;
                int t = Tris(mf.sharedMesh);
                if (total > budget)
                {
                    int share = Mathf.Max(60, Mathf.RoundToInt(budget * (float)t / total));
                    try { mf.sharedMesh = Decimate(mf.sharedMesh, share); }
                    catch (System.Exception e) { Log("mesh reduce failed for " + slot + ": " + e.Message); }
                }
                modelTris += Tris(mf.sharedMesh);
                after += Tris(mf.sharedMesh);
            }
            Vector2Int st;
            slotTris.TryGetValue(slot, out st);
            slotTris[slot] = new Vector2Int(st.x + total, st.y + after);
        }

        /// <summary>A loose physics prop made from a real model (boxes, buckets): rigidbody + box collider, makes noise.</summary>
        static GameObject PhysicsModel(string slot, Vector3 pos, float yaw, Vector2 size, float mass)
        {
            GameObject go = PlaceModel(slot, pos, yaw, size, false, null, false);
            if (go == null) return null;
            Bounds b = RendBounds(go);
            var holder = new GameObject(slot + "_prop");
            holder.transform.SetParent(objRoot, false);
            holder.transform.position = b.center;
            go.transform.SetParent(holder.transform, true);
            holder.layer = LayerProp;
            var bc = holder.AddComponent<BoxCollider>();
            bc.size = b.size;
            holder.AddComponent<Rigidbody>().mass = mass;
            holder.AddComponent<NoiseMaker>().loudness = 16f;
            SetLayer(holder, LayerProp);
            return holder;
        }

        /// <summary>Puts a real model under an item / view-model parent, fitted to `length` along its longest side.</summary>
        static bool AttachModel(string slot, Transform parent, float length, Vector3 euler)
        {
            GameObject prefab = ModelPrefab(slot);
            if (prefab == null) return false;
            var go = (GameObject)Object.Instantiate(prefab);
            go.name = slot;
            go.transform.SetParent(parent, false);
            go.transform.localPosition = Vector3.zero;
            go.transform.localRotation = Quaternion.Euler(euler);
            go.transform.localScale = Vector3.one;
            Bounds b = RendBounds(go);
            float s = length / Mathf.Max(Mathf.Max(b.size.x, b.size.y, b.size.z), 1e-3f);
            go.transform.localScale = Vector3.one * s;
            b = RendBounds(go);
            go.transform.position += parent.position - b.center;
            foreach (Collider c in go.GetComponentsInChildren<Collider>()) Object.DestroyImmediate(c);
            ReduceModel(go, slot);
            foreach (Renderer r in go.GetComponentsInChildren<Renderer>()) { r.shadowCastingMode = ShadowCastingMode.Off; r.receiveShadows = false; }
            SetLayer(go, parent.gameObject.layer);
            return true;
        }

        static void ReportModels()
        {
            var parts = new List<string>();
            foreach (var kv in modelUses)
            {
                Vector2Int st;
                slotTris.TryGetValue(kv.Key, out st);
                parts.Add(kv.Key + " x" + kv.Value + " " + (st.x / Mathf.Max(1, kv.Value)) + "->" + (st.y / Mathf.Max(1, kv.Value)));
            }
            Log("real models: " + modelUses.Count + " kinds, " + modelTris + " triangles after reduction (from " + modelTrisSource + "; " + string.Join(", ", parts.ToArray()) + ")");
        }
    }
}

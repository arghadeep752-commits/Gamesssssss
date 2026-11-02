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
        static int modelTris;

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
            foreach (Renderer r in go.GetComponentsInChildren<Renderer>())
            {
                r.shadowCastingMode = ShadowCastingMode.Off;
                r.receiveShadows = false;
                MeshFilter mf = r.GetComponent<MeshFilter>();
                if (mf != null && mf.sharedMesh != null)
                    for (int sm = 0; sm < mf.sharedMesh.subMeshCount; sm++) modelTris += (int)(mf.sharedMesh.GetIndexCount(sm) / 3);
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
            foreach (Renderer r in go.GetComponentsInChildren<Renderer>()) { r.shadowCastingMode = ShadowCastingMode.Off; r.receiveShadows = false; }
            SetLayer(go, parent.gameObject.layer);
            return true;
        }

        static void ReportModels()
        {
            var parts = new List<string>();
            foreach (var kv in modelUses) parts.Add(kv.Key + " x" + kv.Value);
            Log("real models: " + modelUses.Count + " kinds, " + modelTris + " triangles (" + string.Join(", ", parts.ToArray()) + ")");
        }
    }
}

using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace GridProto.EditorTools
{
    /// <summary>
    /// Imports the house modelled and light-baked in Blender (tools/house, run by the cloud build):
    /// Assets/House/House.bytes (meshes with baked light per vertex), house.json (materials, colliders, doors,
    /// rooms, light probes, viewpoints) and Assets/House/Textures. Builds materials, meshes, colliders,
    /// working doors and room reflection probes.
    /// </summary>
    public static class HouseBuilder
    {
        public const string Folder = "Assets/House";
        const string Out = "Assets/Generated/House";

        [Serializable] class MatDef { public string name; public float[] color; public string albedo; public float smoothness; public float metallic; public float tile = 1f; public float[] emission; public float emissionStrength; public float alpha = 1f; public string kind; }
        [Serializable] class ColDef { public float[] c; public float[] s; public float[] q; public int layer; }
        [Serializable] class DoorDef { public string name; public string obj; public float[] hinge; public float[] latch; public float[] outside; public float[] focus; public float width; public float height; public float angle = 95f; }
        [Serializable] class RoomDef { public string name; public int level; public float[] min; public float[] max; public bool patrol; public bool reflection; public bool interior; }
        [Serializable] class ViewDef { public string name; public float[] pos; public float yaw; public float pitch; public float fov; }
        [Serializable] class SpawnDef { public float[] pos; public float yaw; }
        [Serializable] class ProbeDef { public float[] origin; public float[] spacing; public int[] dims; public float[] data; }
        [Serializable] class Manifest { public MatDef[] materials; public ColDef[] colliders; public DoorDef[] doors; public RoomDef[] rooms; public ViewDef[] views; public SpawnDef spawn; public SpawnDef enemySpawn; public float[] sunDir; public float[] plot; public float giveUpDistance; public ProbeDef probes; }

        public class Result
        {
            public Vector3 spawn, enemySpawn, sunDir;
            public float spawnYaw, enemyYaw, giveUp;
            public Bounds navBounds;
            public Vector3[] patrol;
            public Door mainDoor;
            public HouseData data;
            public ReflectionProbe[] probes;
        }

        public static bool Available { get { return File.Exists(Folder + "/House.bytes") && File.Exists(Folder + "/house.json"); } }

        static Vector3 V(float[] a) { return a == null || a.Length < 3 ? Vector3.zero : new Vector3(a[0], a[1], a[2]); }

        public static Result Build()
        {
            if (!AssetDatabase.IsValidFolder("Assets/Generated")) AssetDatabase.CreateFolder("Assets", "Generated");
            if (AssetDatabase.IsValidFolder(Out)) AssetDatabase.DeleteAsset(Out);
            AssetDatabase.CreateFolder("Assets/Generated", "House");
            AssetDatabase.CreateFolder(Out, "Materials");
            AssetDatabase.CreateFolder(Out, "Meshes");

            var man = JsonUtility.FromJson<Manifest>(File.ReadAllText(Folder + "/house.json"));
            Dictionary<string, Material> mats = CreateMaterials(man);
            var root = new GameObject("House");
            var doorMeshes = new Dictionary<string, KeyValuePair<Mesh, Material[]>>();
            int meshes = 0, verts = 0;

            byte[] bytes = File.ReadAllBytes(Folder + "/House.bytes");
            int o = 4;
            int version = BitConverter.ToInt32(bytes, o); o += 4;
            int count = BitConverter.ToInt32(bytes, o); o += 4;
            for (int i = 0; i < count; i++)
            {
                string name = Str(bytes, ref o), group = Str(bytes, ref o);
                int flags = BitConverter.ToInt32(bytes, o); o += 4;
                Vector3 origin = new Vector3(BitConverter.ToSingle(bytes, o), BitConverter.ToSingle(bytes, o + 4), BitConverter.ToSingle(bytes, o + 8)); o += 12;
                int nv = BitConverter.ToInt32(bytes, o); o += 4;
                Vector3[] pos = V3(bytes, ref o, nv), nrm = V3(bytes, ref o, nv);
                Vector2[] uv = V2(bytes, ref o, nv);
                Vector3[] light = V3(bytes, ref o, nv);
                int ns = BitConverter.ToInt32(bytes, o); o += 4;
                var mesh = new Mesh { name = name };
                mesh.indexFormat = nv > 65000 ? IndexFormat.UInt32 : IndexFormat.UInt16;
                mesh.vertices = pos;
                mesh.normals = nrm;
                mesh.uv = uv;
                mesh.SetUVs(1, new List<Vector3>(light));
                mesh.subMeshCount = ns;
                var smats = new Material[ns];
                for (int s = 0; s < ns; s++)
                {
                    string mname = Str(bytes, ref o);
                    int ni = BitConverter.ToInt32(bytes, o); o += 4;
                    var idx = new int[ni];
                    Buffer.BlockCopy(bytes, o, idx, 0, ni * 4); o += ni * 4;
                    mesh.SetTriangles(idx, s, false);
                    Material m;
                    smats[s] = mats.TryGetValue(mname, out m) ? m : mats["__missing"];
                }
                mesh.RecalculateBounds();
                AssetDatabase.CreateAsset(mesh, Out + "/Meshes/" + i.ToString("00") + "_" + Safe(name) + ".asset");
                meshes++;
                verts += nv;
                if ((flags & 2) != 0) { doorMeshes[name] = new KeyValuePair<Mesh, Material[]>(mesh, smats); continue; }
                if ((flags & 4) == 0) continue;
                var go = new GameObject(name);
                go.transform.SetParent(root.transform, false);
                go.transform.position = origin;
                go.AddComponent<MeshFilter>().sharedMesh = mesh;
                var r = go.AddComponent<MeshRenderer>();
                r.sharedMaterials = smats;
                Setup(r);
            }

            // colliders (walls, floors, stair ramp, furniture; layer 1 = glass, which the enemy can see through)
            var cols = new GameObject("House Colliders");
            cols.transform.SetParent(root.transform, false);
            for (int i = 0; i < man.colliders.Length; i++)
            {
                ColDef c = man.colliders[i];
                var go = new GameObject("Collider " + i);
                go.layer = c.layer;
                go.transform.SetParent(cols.transform, false);
                go.transform.position = V(c.c);
                go.transform.rotation = new Quaternion(c.q[0], c.q[1], c.q[2], c.q[3]);
                go.AddComponent<BoxCollider>().size = V(c.s);
            }

            var res = new Result();
            // doors
            foreach (DoorDef d in man.doors)
            {
                KeyValuePair<Mesh, Material[]> dm;
                if (!doorMeshes.TryGetValue(d.obj, out dm)) { Debug.LogWarning("[PROTO] door mesh missing: " + d.obj); continue; }
                Door door = MakeDoor(d, dm.Key, dm.Value, root.transform);
                if (d.name == "Main") res.mainDoor = door;
            }

            // rooms: reflection probes, patrol points, indoor volumes
            var probes = new List<ReflectionProbe>();
            var patrol = new List<Vector3>();
            var interiors = new List<Bounds>();
            var probeRoot = new GameObject("Reflection Probes");
            probeRoot.transform.SetParent(root.transform, false);
            foreach (RoomDef rm in man.rooms)
            {
                Vector3 mn = V(rm.min), mx = V(rm.max);
                var b = new Bounds((mn + mx) * 0.5f, mx - mn);
                if (rm.patrol) patrol.Add(new Vector3(b.center.x, mn.y + 0.05f, b.center.z));
                if (rm.interior) interiors.Add(b);
                if (rm.reflection)
                {
                    var go = new GameObject("Probe " + rm.name);
                    go.transform.SetParent(probeRoot.transform, false);
                    go.transform.position = new Vector3(b.center.x, mn.y + 1.4f, b.center.z);
                    var p = go.AddComponent<ReflectionProbe>();
                    ProbeSettings(p, 128);
                    p.boxProjection = true;
                    p.size = b.size + new Vector3(0.1f, 0.1f, 0.1f);
                    p.center = b.center - go.transform.position;
                    p.importance = 2;
                    p.blendDistance = 0.5f;
                    probes.Add(p);
                }
            }
            {
                var go = new GameObject("Probe Outdoors");
                go.transform.SetParent(probeRoot.transform, false);
                go.transform.position = new Vector3(8f, 2f, 2f);
                var p = go.AddComponent<ReflectionProbe>();
                ProbeSettings(p, 128);
                p.boxProjection = false;
                p.size = new Vector3(300f, 120f, 300f);
                p.importance = 0;
                probes.Insert(0, p);
            }

            // data for runtime lighting and the cloud test
            var data = ScriptableObject.CreateInstance<HouseData>();
            if (man.probes != null && man.probes.dims != null && man.probes.dims.Length == 3)
            {
                data.probeOrigin = V(man.probes.origin);
                data.probeSpacing = V(man.probes.spacing);
                data.nx = man.probes.dims[0]; data.ny = man.probes.dims[1]; data.nz = man.probes.dims[2];
                data.probes = man.probes.data;
            }
            int nvw = man.views != null ? man.views.Length : 0;
            data.viewNames = new string[nvw]; data.viewPositions = new Vector3[nvw]; data.viewYaw = new float[nvw]; data.viewPitch = new float[nvw];
            for (int i = 0; i < nvw; i++)
            {
                data.viewNames[i] = man.views[i].name; data.viewPositions[i] = V(man.views[i].pos);
                data.viewYaw[i] = man.views[i].yaw; data.viewPitch[i] = man.views[i].pitch;
            }
            data.interiors = interiors.ToArray();
            AssetDatabase.CreateAsset(data, Out + "/HouseData.asset");

            res.data = data;
            res.probes = probes.ToArray();
            res.patrol = patrol.ToArray();
            res.spawn = V(man.spawn.pos); res.spawnYaw = man.spawn.yaw;
            res.enemySpawn = V(man.enemySpawn.pos); res.enemyYaw = man.enemySpawn.yaw;
            res.sunDir = man.sunDir != null && man.sunDir.Length == 3 ? V(man.sunDir).normalized : new Vector3(-0.5f, 0.6f, -0.6f).normalized;
            res.giveUp = man.giveUpDistance > 0f ? man.giveUpDistance : 17f;
            float[] pl = man.plot != null && man.plot.Length == 4 ? man.plot : new float[] { -6f, -11f, 22f, 15f };
            // plot is [x0, y0(blender) = unity z0, x1, z1]
            res.navBounds = new Bounds(new Vector3((pl[0] + pl[2]) * 0.5f, 3f, (pl[1] + pl[3]) * 0.5f),
                                       new Vector3(pl[2] - pl[0] + 2f, 10f, pl[3] - pl[1] + 2f));
            Debug.Log("[PROTO] house imported (format " + version + "): " + meshes + " meshes, " + verts + " vertices, " +
                      man.colliders.Length + " colliders, " + man.doors.Length + " doors, " + probes.Count + " reflection probes, " +
                      (data.probes != null ? data.probes.Length / 18 : 0) + " light probes");
            return res;
        }

        static void ProbeSettings(ReflectionProbe p, int resolution)
        {
            p.mode = ReflectionProbeMode.Realtime;
            p.refreshMode = ReflectionProbeRefreshMode.ViaScripting;
            p.timeSlicingMode = ReflectionProbeTimeSlicingMode.AllFacesAtOnce;
            p.resolution = resolution;
            p.hdr = false;
            p.shadowDistance = 0f;
            p.nearClipPlane = 0.05f;
            p.farClipPlane = 300f;
            p.clearFlags = ReflectionProbeClearFlags.Skybox;
            p.intensity = 1f;
        }

        static void Setup(Renderer r)
        {
            r.shadowCastingMode = ShadowCastingMode.Off;
            r.receiveShadows = false;
            r.lightProbeUsage = LightProbeUsage.Off;
            r.reflectionProbeUsage = ReflectionProbeUsage.BlendProbes;
            r.allowOcclusionWhenDynamic = false;
        }

        static Door MakeDoor(DoorDef d, Mesh mesh, Material[] smats, Transform parent)
        {
            Vector3 hingePos = V(d.hinge), latch = V(d.latch).normalized, outside = V(d.outside).normalized;
            var rootGo = new GameObject("Door " + d.name);
            rootGo.transform.SetParent(parent, false);
            rootGo.transform.position = hingePos;
            var hinge = new GameObject("Hinge").transform;
            hinge.SetParent(rootGo.transform, false);
            var body = hinge.gameObject.AddComponent<Rigidbody>();   // moving part: kept out of the NavMesh
            body.isKinematic = true;
            body.useGravity = false;
            var leaf = new GameObject("Leaf");
            leaf.transform.SetParent(hinge, false);
            leaf.AddComponent<MeshFilter>().sharedMesh = mesh;
            var r = leaf.AddComponent<MeshRenderer>();
            r.sharedMaterials = smats;
            Setup(r);
            var box = leaf.AddComponent<BoxCollider>();
            box.center = mesh.bounds.center;
            box.size = mesh.bounds.size + new Vector3(0.0f, -0.02f, 0.0f);

            var focus = new GameObject("Door Focus " + d.name);
            focus.transform.SetParent(rootGo.transform, false);
            focus.transform.position = V(d.focus);
            var src = focus.AddComponent<AudioSource>();
            src.playOnAwake = false;
            src.spatialBlend = 1f;
            src.minDistance = 1.5f;
            src.maxDistance = 22f;
            src.rolloffMode = AudioRolloffMode.Linear;
            var door = focus.AddComponent<Door>();
            door.hinge = hinge;
            door.focusPoint = focus.transform;
            door.range = 1.9f;
            door.openAngle = Mathf.Clamp(d.angle, 60f, 110f) - 3f;
            door.outsideDirection = outside;
            // a positive hinge angle swings the latch edge towards (latch.z, -latch.x)
            Vector3 swing = new Vector3(latch.z, 0f, -latch.x);
            door.outsideSwingSign = Vector3.Dot(swing, outside) >= 0f ? 1f : -1f;
            door.audioSource = src;
            return door;
        }

        static Dictionary<string, Material> CreateMaterials(Manifest man)
        {
            var result = new Dictionary<string, Material>();
            Shader baked = Shader.Find("GridProto/HouseBaked"), glass = Shader.Find("GridProto/HouseGlass");
            var textures = new Dictionary<string, Texture2D>();
            AssetDatabase.StartAssetEditing();
            try
            {
                foreach (MatDef m in man.materials)
                {
                    if (string.IsNullOrEmpty(m.albedo) || textures.ContainsKey(m.albedo)) continue;
                    string path = Folder + "/Textures/" + m.albedo + ".png";
                    var imp = AssetImporter.GetAtPath(path) as TextureImporter;
                    if (imp == null) continue;
                    imp.textureType = TextureImporterType.Default;
                    imp.sRGBTexture = true;
                    imp.mipmapEnabled = true;
                    imp.wrapMode = TextureWrapMode.Repeat;
                    imp.filterMode = FilterMode.Trilinear;
                    imp.anisoLevel = 4;
                    imp.maxTextureSize = 1024;
                    imp.textureCompression = TextureImporterCompression.Compressed;
                    imp.SaveAndReimport();
                    textures[m.albedo] = null;
                }
            }
            finally { AssetDatabase.StopAssetEditing(); }
            foreach (MatDef m in man.materials)
            {
                bool isGlass = m.kind == "glass";
                var mat = new Material(isGlass ? glass : baked) { name = m.name };
                Color c = m.color != null && m.color.Length >= 3 ? new Color(m.color[0], m.color[1], m.color[2]) : Color.white;
                if (isGlass)
                {
                    mat.SetColor("_Color", c);
                    mat.SetFloat("_Alpha", m.alpha);
                }
                else
                {
                    Texture2D tex = null;
                    if (!string.IsNullOrEmpty(m.albedo)) tex = AssetDatabase.LoadAssetAtPath<Texture2D>(Folder + "/Textures/" + m.albedo + ".png");
                    if (tex != null)
                    {
                        mat.SetTexture("_MainTex", tex);
                        float s = 1f / Mathf.Max(m.tile, 0.001f);
                        mat.SetTextureScale("_MainTex", new Vector2(s, s));
                        mat.SetColor("_Color", Color.white);
                    }
                    else mat.SetColor("_Color", c);
                    mat.SetFloat("_Glossiness", m.smoothness);
                    mat.SetFloat("_Metallic", m.metallic);
                    if (m.emissionStrength > 0f && m.emission != null && m.emission.Length >= 3)
                    {
                        Color e = new Color(m.emission[0], m.emission[1], m.emission[2]).linear;
                        float k = m.emissionStrength * 0.25f;
                        mat.SetVector("_EmissionLin", new Vector4(e.r * k, e.g * k, e.b * k, 0f));
                    }
                }
                AssetDatabase.CreateAsset(mat, Out + "/Materials/" + Safe(m.name) + ".mat");
                result[m.name] = mat;
            }
            var missing = new Material(baked) { name = "__missing" };
            missing.SetColor("_Color", Color.magenta);
            AssetDatabase.CreateAsset(missing, Out + "/Materials/__missing.mat");
            result["__missing"] = missing;
            return result;
        }

        static string Str(byte[] b, ref int o)
        {
            int n = BitConverter.ToInt32(b, o);
            string s = Encoding.UTF8.GetString(b, o + 4, n);
            o += 4 + n;
            return s;
        }

        static Vector3[] V3(byte[] b, ref int o, int n)
        {
            var f = new float[n * 3];
            Buffer.BlockCopy(b, o, f, 0, n * 12);
            o += n * 12;
            var v = new Vector3[n];
            for (int i = 0; i < n; i++) v[i] = new Vector3(f[i * 3], f[i * 3 + 1], f[i * 3 + 2]);
            return v;
        }

        static Vector2[] V2(byte[] b, ref int o, int n)
        {
            var f = new float[n * 2];
            Buffer.BlockCopy(b, o, f, 0, n * 8);
            o += n * 8;
            var v = new Vector2[n];
            for (int i = 0; i < n; i++) v[i] = new Vector2(f[i * 2], f[i * 2 + 1]);
            return v;
        }

        static string Safe(string s)
        {
            var sb = new StringBuilder();
            foreach (char ch in s) sb.Append(char.IsLetterOrDigit(ch) ? ch : '_');
            return sb.ToString();
        }
    }
}

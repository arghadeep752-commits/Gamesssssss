using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;
using Object = UnityEngine.Object;

namespace RealFPS.EditorTools
{
    /// <summary>
    /// Builds the whole scene from code: terrain, sky and sun, lake, forest, rocks,
    /// pier, campfire, lanterns, grass, player, camera and the game objects.
    /// </summary>
    public static class RFWorld
    {
        public const string ScenePath = "Assets/Scenes/Valley.unity";
        const string Gen = "Assets/Generated";
        const string Art = "Assets/Art";

        static RFArtInfo art;
        static Terrain terrain;
        static TerrainData tdata;
        static Transform root, propsRoot, treesRoot, rocksRoot, detailRoot;
        static readonly Dictionary<string, Material> mats = new Dictionary<string, Material>();
        static System.Random rng;
        static readonly List<Vector3> occupied = new List<Vector3>(); // xz + radius of placed big objects

        static void Log(string m) { Debug.Log("[RF-BUILD] " + m); }

        public static void Build(RFArtInfo info)
        {
            art = info;
            rng = new System.Random(2026);
            mats.Clear();
            occupied.Clear();
            RFBuild.EnsureFolder(Gen);
            RFBuild.EnsureFolder(Gen + "/Materials");
            RFBuild.EnsureFolder(Gen + "/Meshes");
            RFBuild.EnsureFolder("Assets/Scenes");

            Scene scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            root = new GameObject("World").transform;
            propsRoot = Child(root, "Props");
            treesRoot = Child(root, "Trees");
            rocksRoot = Child(root, "Rocks");
            detailRoot = Child(root, "Detail");

            Light sun = SkyAndSun(out float skyRotation, out SkyLighting skyLighting);
            BuildTerrain();
            Material waterMat = BuildWater(skyRotation);
            Transform pierEnd = BuildPier();
            Vector3 campfire = BuildCampfire();
            BuildRocks();
            BuildTrees();
            BuildDetail();
            BuildFarMountains();
            Lantern[] lanterns = BuildLanterns(pierEnd, campfire);
            BuildGame(sun, skyLighting, lanterns);

            Lightmapping.giWorkflowMode = Lightmapping.GIWorkflowMode.OnDemand;
            if (!EditorSceneManager.SaveScene(scene, ScenePath)) throw new Exception("Could not save the scene");
            EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(ScenePath, true) };
            AssetDatabase.SaveAssets();
            Log("scene saved: " + root.GetComponentsInChildren<Transform>(true).Length + " objects");
        }

        // ------------------------------------------------------------------ helpers
        static Transform Child(Transform parent, string name)
        {
            var t = new GameObject(name).transform;
            t.SetParent(parent, false);
            return t;
        }

        static T Load<T>(string path) where T : Object
        {
            var a = AssetDatabase.LoadAssetAtPath<T>(path);
            if (a == null) Debug.LogWarning("[RF-BUILD] missing asset " + path);
            return a;
        }

        static Texture2D Tex(string rel) { return Load<Texture2D>(Art + "/" + rel); }

        static Texture2D TexAny(string relNoExt)
        {
            foreach (string ext in new[] { ".png", ".jpg" })
            {
                string p = Art + "/" + relNoExt + ext;
                if (File.Exists(p)) return AssetDatabase.LoadAssetAtPath<Texture2D>(p);
            }
            Debug.LogWarning("[RF-BUILD] missing texture " + relNoExt);
            return null;
        }

        static Material SaveMat(Material m)
        {
            string path = Gen + "/Materials/" + m.name + ".mat";
            AssetDatabase.CreateAsset(m, path);
            mats[m.name] = m;
            return m;
        }

        static Material Standard(string name, Texture2D albedo, Texture2D normal, Texture2D mask, float smoothScale = 1f, bool cutout = false, float bump = 1f)
        {
            var m = new Material(Shader.Find("Standard")) { name = name };
            m.SetTexture("_MainTex", albedo);
            m.SetColor("_Color", Color.white);
            if (normal != null)
            {
                m.SetTexture("_BumpMap", normal);
                m.SetFloat("_BumpScale", bump);
                m.EnableKeyword("_NORMALMAP");
            }
            if (mask != null)
            {
                m.SetTexture("_MetallicGlossMap", mask);
                m.EnableKeyword("_METALLICGLOSSMAP");
                m.SetFloat("_GlossMapScale", smoothScale);
                m.SetTexture("_OcclusionMap", mask);
                m.SetFloat("_OcclusionStrength", 1f);
            }
            else
            {
                m.SetFloat("_Glossiness", 0.15f * smoothScale);
                m.SetFloat("_Metallic", 0f);
            }
            m.SetFloat("_SmoothnessTextureChannel", 0f);
            if (cutout)
            {
                m.SetFloat("_Mode", 1f);
                m.SetOverrideTag("RenderType", "TransparentCutout");
                m.EnableKeyword("_ALPHATEST_ON");
                m.SetFloat("_Cutoff", 0.5f);
                m.renderQueue = 2450;
            }
            m.enableInstancing = true;
            return SaveMat(m);
        }

        static Material Foliage(string name, Texture2D albedo, float translucency, float wind, float cutoff = 0.42f)
        {
            var m = new Material(Shader.Find("RealFPS/Foliage")) { name = name };
            m.SetTexture("_MainTex", albedo);
            m.SetFloat("_Translucency", translucency);
            m.SetFloat("_WindStrength", wind);
            m.SetFloat("_Cutoff", cutoff);
            m.enableInstancing = true;
            return SaveMat(m);
        }

        static Material Particles(string name, Texture2D tex, bool additive, Color tint)
        {
            Shader s = Shader.Find(additive ? "Mobile/Particles/Additive" : "Mobile/Particles/Alpha Blended");
            if (s == null) s = Shader.Find(additive ? "Legacy Shaders/Particles/Additive" : "Legacy Shaders/Particles/Alpha Blended");
            var m = new Material(s) { name = name };
            m.SetTexture("_MainTex", tex);
            if (m.HasProperty("_TintColor")) m.SetColor("_TintColor", tint);
            if (m.HasProperty("_Color")) m.SetColor("_Color", tint);
            return SaveMat(m);
        }

        static Mesh SaveMesh(Mesh m)
        {
            string path = Gen + "/Meshes/" + m.name + ".asset";
            if (AssetDatabase.LoadAssetAtPath<Mesh>(path) != null) AssetDatabase.DeleteAsset(path);
            AssetDatabase.CreateAsset(m, path);
            return m;
        }

        static float GroundY(float x, float z)
        {
            return terrain.SampleHeight(new Vector3(x, 0f, z)) + terrain.transform.position.y;
        }

        static float Slope(float x, float z)
        {
            Vector3 lp = new Vector3(x, 0f, z) - terrain.transform.position;
            return tdata.GetSteepness(lp.x / tdata.size.x, lp.z / tdata.size.z);
        }

        static Vector3 GroundNormal(float x, float z)
        {
            Vector3 lp = new Vector3(x, 0f, z) - terrain.transform.position;
            return tdata.GetInterpolatedNormal(lp.x / tdata.size.x, lp.z / tdata.size.z);
        }

        static float R(float a, float b) { return a + (float)rng.NextDouble() * (b - a); }

        static bool Free(float x, float z, float radius)
        {
            foreach (Vector3 o in occupied)
            {
                float dx = o.x - x, dz = o.y - z;
                float rr = o.z + radius;
                if (dx * dx + dz * dz < rr * rr) return false;
            }
            return true;
        }

        static void Occupy(float x, float z, float radius) { occupied.Add(new Vector3(x, z, radius)); }

        static void SetStatic(GameObject go)
        {
            GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccludeeStatic);
        }

        static void SetLayerRecursive(GameObject go, int layer)
        {
            go.layer = layer;
            foreach (Transform t in go.transform) SetLayerRecursive(t.gameObject, layer);
        }

        static Color ToGamma(Color linear)
        {
            return new Color(Mathf.LinearToGammaSpace(linear.r), Mathf.LinearToGammaSpace(linear.g), Mathf.LinearToGammaSpace(linear.b), 1f);
        }

        // ------------------------------------------------------------------ sky, sun and ambient light
        static Light SkyAndSun(out float rotation, out SkyLighting skyLighting)
        {
            // Rotate the HDRI so the sun sits behind the player's left shoulder at the start
            // (south-west), which side-lights the valley and the lake.
            Vector3 src = art.SunDirection;
            float srcAngle = Mathf.Atan2(src.z, src.x) * Mathf.Rad2Deg;
            Vector2 want = new Vector2(-0.62f, -0.78f);
            float dstAngle = Mathf.Atan2(want.y, want.x) * Mathf.Rad2Deg;
            rotation = Mathf.Repeat(dstAngle - srcAngle, 360f);
            float rr = rotation * Mathf.Deg2Rad;
            var sunWorld = new Vector3(Mathf.Cos(rr) * src.x - Mathf.Sin(rr) * src.z, src.y, Mathf.Sin(rr) * src.x + Mathf.Cos(rr) * src.z).normalized;
            Log("sky rotation " + rotation.ToString("0.0") + " sun " + sunWorld.ToString("F3") + " elevation " + (Mathf.Asin(sunWorld.y) * Mathf.Rad2Deg).ToString("0.0"));

            var skyMat = new Material(Shader.Find("Skybox/Panoramic")) { name = "Sky" };
            skyMat.SetTexture("_MainTex", Tex("Sky/sky_pano.png"));
            skyMat.SetFloat("_Rotation", rotation);
            skyMat.SetFloat("_Exposure", art.skyExposure);
            skyMat.SetFloat("_Mapping", 1f);
            skyMat.SetFloat("_ImageType", 0f);
            skyMat.SetColor("_Tint", new Color(0.5f, 0.5f, 0.5f, 0.5f));
            SaveMat(skyMat);
            RenderSettings.skybox = skyMat;

            var cube = Load<Cubemap>(Art + "/Sky/sky_cube.png");
            RenderSettings.defaultReflectionMode = DefaultReflectionMode.Custom;
            RenderSettings.customReflection = cube;
            RenderSettings.reflectionIntensity = 1f;
            RenderSettings.reflectionBounces = 1;

            var sunGo = new GameObject("Sun");
            var sun = sunGo.AddComponent<Light>();
            sun.type = LightType.Directional;
            sun.color = ToGamma(art.SunColorLinear);
            sun.intensity = art.sunIntensity;
            sun.shadows = LightShadows.Soft;
            sun.shadowStrength = 0.92f;
            sun.shadowBias = 0.06f;
            sun.shadowNormalBias = 0.5f;
            sun.lightmapBakeType = LightmapBakeType.Realtime;
            sunGo.transform.rotation = Quaternion.LookRotation(-sunWorld, Vector3.up);
            RenderSettings.sun = sun;

            // ambient light: integrate the sky grid into spherical harmonics
            var sh = new SphericalHarmonicsL2();
            int W = art.shW, H = art.shH;
            if (art.shGrid != null && art.shGrid.Length >= W * H * 3)
            {
                for (int y = 0; y < H; y++)
                {
                    float theta = (y + 0.5f) / H * Mathf.PI;
                    float dOmega = (2f * Mathf.PI / W) * (Mathf.PI / H) * Mathf.Sin(theta);
                    for (int x = 0; x < W; x++)
                    {
                        float phi = (0.5f - (x + 0.5f) / W) * 2f * Mathf.PI;
                        var d = new Vector3(Mathf.Sin(theta) * Mathf.Cos(phi), Mathf.Cos(theta), Mathf.Sin(theta) * Mathf.Sin(phi));
                        var dw = new Vector3(Mathf.Cos(rr) * d.x - Mathf.Sin(rr) * d.z, d.y, Mathf.Sin(rr) * d.x + Mathf.Cos(rr) * d.z);
                        int i = (y * W + x) * 3;
                        var c = new Color(art.shGrid[i], art.shGrid[i + 1], art.shGrid[i + 2]);
                        sh.AddDirectionalLight(dw, c, dOmega / Mathf.PI);
                    }
                }
            }
            else
            {
                sh.AddAmbientLight(new Color(0.45f, 0.5f, 0.6f));
            }
            var coeffs = new float[27];
            for (int c = 0; c < 3; c++) for (int i = 0; i < 9; i++) coeffs[c * 9 + i] = sh[c, i];
            var up = new Vector3[] { Vector3.up, Vector3.down, Vector3.right };
            var outC = new Color[3];
            sh.Evaluate(up, outC);
            Log("ambient up " + outC[0] + " down " + outC[1] + " side " + outC[2]);

            RenderSettings.ambientMode = AmbientMode.Skybox;
            RenderSettings.ambientProbe = sh;
            RenderSettings.fog = true;
            RenderSettings.fogMode = FogMode.Exponential;
            Color fog = ToGamma(art.FogLinear);
            RenderSettings.fogColor = fog;
            RenderSettings.fogDensity = 0.0024f;

            var skyGo = new GameObject("SkyLighting");
            skyLighting = skyGo.AddComponent<SkyLighting>();
            skyLighting.sh = coeffs;
            skyLighting.fogColor = fog;
            skyLighting.fogDensity = 0.0024f;
            return sun;
        }

        // ------------------------------------------------------------------ terrain
        static void BuildTerrain()
        {
            int res = 513;
            float size = RFLayout.TerrainSize;
            Vector3 tp = RFLayout.TerrainPos;
            var heights = new float[res, res];
            for (int j = 0; j < res; j++)
            {
                float z = tp.z + j / (float)(res - 1) * size;
                for (int i = 0; i < res; i++)
                {
                    float x = tp.x + i / (float)(res - 1) * size;
                    heights[j, i] = RFLayout.Height(x, z) / RFLayout.TerrainHeight;
                }
            }

            string[] names = { "grass", "dirt", "rock", "shore" };
            float[] tiles = { 2.4f, 3.2f, 6.0f, 2.5f };
            var layers = new TerrainLayer[4];
            for (int k = 0; k < 4; k++)
            {
                var tl = new TerrainLayer
                {
                    name = "Layer_" + names[k],
                    diffuseTexture = Tex("Terrain/" + names[k] + "_albedo.png"),
                    normalMapTexture = Tex("Terrain/" + names[k] + "_normal.png"),
                    tileSize = new Vector2(tiles[k], tiles[k]),
                    normalScale = k == 2 ? 1.3f : 1f,
                    smoothness = 1f,
                    metallic = 0f
                };
                AssetDatabase.CreateAsset(tl, Gen + "/Layer_" + names[k] + ".terrainlayer");
                layers[k] = tl;
            }

            tdata = new TerrainData();
            tdata.heightmapResolution = res;
            tdata.size = new Vector3(size, RFLayout.TerrainHeight, size);
            tdata.SetHeights(0, 0, heights);
            tdata.alphamapResolution = 512;
            tdata.baseMapResolution = 1024;
            tdata.terrainLayers = layers;

            int ar = tdata.alphamapResolution;
            var alpha = new float[ar, ar, 4];
            for (int j = 0; j < ar; j++)
            {
                float z = tp.z + (j + 0.5f) / ar * size;
                for (int i = 0; i < ar; i++)
                {
                    float x = tp.x + (i + 0.5f) / ar * size;
                    float h = RFLayout.Height(x, z);
                    float hx = RFLayout.Height(x + 1f, z) - RFLayout.Height(x - 1f, z);
                    float hz = RFLayout.Height(x, z + 1f) - RFLayout.Height(x, z - 1f);
                    float slope = Mathf.Atan(Mathf.Sqrt(hx * hx + hz * hz) * 0.5f) * Mathf.Rad2Deg;
                    Vector4 w = RFLayout.Splat(x, z, h, slope);
                    alpha[j, i, 0] = w.x;
                    alpha[j, i, 1] = w.y;
                    alpha[j, i, 2] = w.z;
                    alpha[j, i, 3] = w.w;
                }
            }
            tdata.SetAlphamaps(0, 0, alpha);
            AssetDatabase.CreateAsset(tdata, Gen + "/Terrain.asset");

            GameObject go = Terrain.CreateTerrainGameObject(tdata);
            go.name = "Terrain";
            go.transform.position = tp;
            terrain = go.GetComponent<Terrain>();
            var tm = new Material(Shader.Find("Nature/Terrain/Standard")) { name = "TerrainStandard" };
            tm.EnableKeyword("_NORMALMAP");
            SaveMat(tm);
            terrain.materialTemplate = tm;
            terrain.heightmapPixelError = 8f;
            terrain.basemapDistance = 90f;
            terrain.drawTreesAndFoliage = false;
            terrain.drawInstanced = false;
            terrain.reflectionProbeUsage = ReflectionProbeUsage.Off;
            terrain.allowAutoConnect = false;
            terrain.shadowCastingMode = ShadowCastingMode.Off;
            GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.OccludeeStatic);
            Log("terrain built");
        }

        // ------------------------------------------------------------------ water
        static Material BuildWater(float skyRotation)
        {
            float W = RFLayout.Water;
            Mesh mesh = SaveMesh(RFMeshUtil.WaterMesh(2.5f, W));

            // depth texture over the lake rectangle
            Bounds b = mesh.bounds;
            int tr = 256;
            var tex = new Texture2D(tr, tr, TextureFormat.RGBA32, false, true) { name = "LakeDepth", wrapMode = TextureWrapMode.Clamp, filterMode = FilterMode.Bilinear };
            var px = new Color32[tr * tr];
            for (int j = 0; j < tr; j++)
            {
                for (int i = 0; i < tr; i++)
                {
                    float x = b.min.x + (i + 0.5f) / tr * b.size.x;
                    float z = b.min.z + (j + 0.5f) / tr * b.size.z;
                    float d = Mathf.Clamp01((W - GroundY(x, z)) / RFLayout.LakeDepth);
                    byte v = (byte)Mathf.RoundToInt(d * 255f);
                    px[j * tr + i] = new Color32(v, v, v, 255);
                }
            }
            tex.SetPixels32(px);
            tex.Apply(false, false);
            AssetDatabase.CreateAsset(tex, Gen + "/LakeDepth.asset");

            var m = new Material(Shader.Find("RealFPS/Water")) { name = "Water" };
            m.SetTexture("_NormalMap", Tex("Water/water_normal.png"));
            m.SetTexture("_DepthTex", tex);
            m.SetVector("_DepthRect", new Vector4(b.min.x, b.min.z, 1f / b.size.x, 1f / b.size.z));
            m.SetFloat("_MaxDepth", RFLayout.LakeDepth);
            m.SetTexture("_Sky", Tex("Sky/sky_reflect.png"));
            m.SetFloat("_SkyRotation", skyRotation);
            SaveMat(m);

            var go = new GameObject("Lake");
            go.transform.SetParent(root, false);
            go.AddComponent<MeshFilter>().sharedMesh = mesh;
            var mr = go.AddComponent<MeshRenderer>();
            mr.sharedMaterial = m;
            mr.shadowCastingMode = ShadowCastingMode.Off;
            mr.receiveShadows = false;
            mr.lightProbeUsage = LightProbeUsage.Off;
            mr.reflectionProbeUsage = ReflectionProbeUsage.Off;
            Log("lake: " + mesh.vertexCount + " vertices");
            return m;
        }

        // ------------------------------------------------------------------ models
        static readonly Dictionary<string, List<RFMeshUtil.Part>> partCache = new Dictionary<string, List<RFMeshUtil.Part>>();

        static List<RFMeshUtil.Part> ModelParts(string id, bool makeLod)
        {
            List<RFMeshUtil.Part> parts;
            if (partCache.TryGetValue(id, out parts)) return parts;
            var model = Load<GameObject>(Art + "/Models/" + id + "/" + id + ".fbx");
            parts = model != null ? RFMeshUtil.Parts(model) : new List<RFMeshUtil.Part>();
            foreach (RFMeshUtil.Part p in parts)
            {
                string mats = "";
                foreach (Material sm in p.sourceMaterials) mats += (sm != null ? sm.name : "null") + ";";
                Log("model " + id + " part '" + p.name + "' tris=" + (p.mesh.triangles.Length / 3) + " size=" + p.size.ToString("F2") + " materials=" + mats);
                if (makeLod && p.mesh.triangles.Length / 3 > 3000)
                    p.lod1 = SaveMesh(RFMeshUtil.Cluster(p.mesh, 22, id + "_" + p.name + "_LOD1"));
            }
            partCache[id] = parts;
            return parts;
        }

        static Material ModelMat(string id, string tag = "main", bool cutout = false, float smooth = 1f)
        {
            string key = id + "_" + tag;
            Material m;
            if (mats.TryGetValue(key, out m)) return m;
            Texture2D alb = TexAny("Models/" + id + "/" + tag + "_albedo");
            return Standard(key, alb, Tex("Models/" + id + "/" + tag + "_normal.png"), Tex("Models/" + id + "/" + tag + "_mask.png"), smooth, cutout);
        }

        /// <summary>Places one model part with its bottom at `ground` (minus sink).</summary>
        static GameObject PlacePart(RFMeshUtil.Part p, Material mat, Vector3 ground, float yaw, float scale, float sink, Transform parent,
                                    bool collider, float lodSwitch = 0.12f, float cull = 0.004f, Quaternion? tilt = null)
        {
            Quaternion yawQ = Quaternion.Euler(0f, yaw, 0f);
            Quaternion t = tilt ?? Quaternion.identity;
            var go = new GameObject(p.name);
            go.transform.SetParent(parent, false);
            go.transform.rotation = t * yawQ * p.rotation;
            go.transform.localScale = p.scale * scale;
            Vector3 center = ground + Vector3.up * (p.size.y * scale * 0.5f - sink);
            go.transform.position = center - t * (yawQ * (p.centerOffset * scale));

            var lod0 = new GameObject("LOD0");
            lod0.transform.SetParent(go.transform, false);
            lod0.AddComponent<MeshFilter>().sharedMesh = p.mesh;
            var r0 = lod0.AddComponent<MeshRenderer>();
            var matsArr = new Material[Mathf.Max(1, p.mesh.subMeshCount)];
            for (int i = 0; i < matsArr.Length; i++) matsArr[i] = mat;
            r0.sharedMaterials = matsArr;
            Renderer[] l1 = null;
            if (p.lod1 != null)
            {
                var lod1 = new GameObject("LOD1");
                lod1.transform.SetParent(go.transform, false);
                lod1.AddComponent<MeshFilter>().sharedMesh = p.lod1;
                var r1 = lod1.AddComponent<MeshRenderer>();
                r1.sharedMaterials = matsArr;
                l1 = new Renderer[] { r1 };
            }
            var lg = go.AddComponent<LODGroup>();
            if (l1 != null)
                lg.SetLODs(new[] { new LOD(lodSwitch, new Renderer[] { r0 }), new LOD(cull, l1) });
            else
                lg.SetLODs(new[] { new LOD(cull, new Renderer[] { r0 }) });
            lg.RecalculateBounds();
            if (collider)
            {
                var mc = go.AddComponent<MeshCollider>();
                mc.sharedMesh = p.lod1 != null ? p.lod1 : p.mesh;
                mc.convex = true;
                go.AddComponent<SurfaceTag>().surface = Surface.Rock;
            }
            return go;
        }

        // ------------------------------------------------------------------ pier
        static Transform BuildPier()
        {
            var model = Load<GameObject>(Art + "/Models/modular_wooden_pier/modular_wooden_pier.fbx");
            if (model == null) return null;
            Material planks = ModelMat("modular_wooden_pier", "planks", false, 0.8f);
            Material poles = ModelMat("modular_wooden_pier", "poles", false, 0.8f);

            var pier = (GameObject)Object.Instantiate(model);
            pier.name = "Pier";
            pier.transform.SetParent(propsRoot, false);
            Vector3 measure = new Vector3(0f, -600f, 0f);   // measured well below the terrain
            pier.transform.position = measure;
            pier.transform.rotation = Quaternion.identity;
            foreach (MeshRenderer mr in pier.GetComponentsInChildren<MeshRenderer>())
            {
                Material[] arr = mr.sharedMaterials;
                for (int i = 0; i < arr.Length; i++)
                {
                    string n = (arr[i] != null ? arr[i].name : "").ToLowerInvariant();
                    arr[i] = n.Contains("pole") ? poles : (n.Contains("plank") ? planks : (i == 0 ? planks : poles));
                }
                mr.sharedMaterials = arr;
                mr.gameObject.AddComponent<MeshCollider>().sharedMesh = mr.GetComponent<MeshFilter>().sharedMesh;
                mr.gameObject.AddComponent<SurfaceTag>().surface = Surface.Wood;
                Log("pier part " + mr.name + " mats=" + arr.Length);
            }

            // measure: long axis, deck height (most common surface when looking down) and the taller end
            Bounds b = new Bounds();
            bool first = true;
            foreach (Renderer r in pier.GetComponentsInChildren<Renderer>())
            {
                if (first) { b = r.bounds; first = false; } else b.Encapsulate(r.bounds);
            }
            bool alongZ = b.size.z >= b.size.x;
            Vector3 axis = alongZ ? Vector3.forward : Vector3.right;
            float len = alongZ ? b.size.z : b.size.x;
            Physics.SyncTransforms();
            var hits = new List<float>();
            for (int k = 0; k < 15; k++)
            {
                float t = Mathf.Lerp(0.12f, 0.88f, k / 14f);
                Vector3 o = b.center + axis * ((t - 0.5f) * len);
                o.y = b.max.y + 2f;
                RaycastHit hit;
                if (Physics.Raycast(o, Vector3.down, out hit, b.size.y + 4f)) hits.Add(hit.point.y);
            }
            hits.Sort();
            float deck = hits.Count > 0 ? hits[hits.Count / 2] : b.min.y + b.size.y * 0.4f;
            float endA = MaxHeightNear(pier, b.center - axis * (len * 0.42f), axis, len * 0.1f);
            float endB = MaxHeightNear(pier, b.center + axis * (len * 0.42f), axis, len * 0.1f);
            Vector3 lakeward = endB >= endA ? axis : -axis;   // the taller (posts) end goes out into the lake
            Log("pier bounds " + b.size.ToString("F2") + " deck " + (deck - measure.y).ToString("F2") + " (bottom " + (b.min.y - measure.y).ToString("F2") + ") ends " + endA.ToString("F2") + "/" + endB.ToString("F2") + " hits " + hits.Count);

            Vector2 shore = RFLayout.PierShore(1.03f);
            Vector2 c2 = RFLayout.LakeCenter;
            Vector3 dir = new Vector3(c2.x - shore.x, 0f, c2.y - shore.y).normalized;
            Quaternion rot = Quaternion.FromToRotation(lakeward, dir);
            rot = Quaternion.Euler(0f, rot.eulerAngles.y, 0f);
            float deckTarget = RFLayout.Water + 0.7f;
            Vector3 shoreEndLocal = b.center - lakeward * (len * 0.5f) - measure;
            shoreEndLocal.y = deck - measure.y;
            Vector3 shoreWorld = new Vector3(shore.x, deckTarget, shore.y);
            pier.transform.rotation = rot;
            pier.transform.position = shoreWorld - rot * shoreEndLocal;
            foreach (Transform t in pier.GetComponentsInChildren<Transform>()) SetStatic(t.gameObject);

            // where the far end of the deck is
            var end = new GameObject("PierEnd").transform;
            end.SetParent(propsRoot, false);
            end.position = shoreWorld + dir * (len * 0.86f);
            end.position = new Vector3(end.position.x, deckTarget + 0.02f, end.position.z);
            Occupy(shore.x + dir.x * len * 0.5f, shore.y + dir.z * len * 0.5f, len * 0.6f);
            Log("pier placed at " + shoreWorld + " heading " + dir);
            return end;
        }

        static float MaxHeightNear(GameObject go, Vector3 point, Vector3 axis, float halfWidth)
        {
            float best = float.MinValue;
            foreach (MeshFilter mf in go.GetComponentsInChildren<MeshFilter>())
            {
                Mesh m = mf.sharedMesh;
                if (m == null) continue;
                Matrix4x4 l2w = mf.transform.localToWorldMatrix;
                Vector3[] v = m.vertices;
                for (int i = 0; i < v.Length; i += 3)
                {
                    Vector3 w = l2w.MultiplyPoint3x4(v[i]);
                    if (Mathf.Abs(Vector3.Dot(w - point, axis)) < halfWidth && w.y > best) best = w.y;
                }
            }
            return best;
        }

        // ------------------------------------------------------------------ campfire
        static Vector3 BuildCampfire()
        {
            Vector2 c = RFLayout.Campfire;
            Vector3 p = new Vector3(c.x, GroundY(c.x, c.y), c.y);
            Occupy(c.x, c.y, 6f);
            var fire = new GameObject("Campfire");
            fire.transform.SetParent(propsRoot, false);
            fire.transform.position = p;

            List<RFMeshUtil.Part> pit = ModelParts("stone_fire_pit", true);
            if (pit.Count > 0)
            {
                Material m = ModelMat("stone_fire_pit");
                foreach (RFMeshUtil.Part part in pit)
                {
                    GameObject g = PlacePart(part, m, p, 0f, 1f, 0.05f, fire.transform, false);
                    SetStatic(g);
                }
            }
            List<RFMeshUtil.Part> logs = ModelParts("dry_branches_medium_01", true);
            if (logs.Count > 0)
            {
                Material m = ModelMat("dry_branches_medium_01");
                for (int i = 0; i < 2; i++)
                    PlacePart(logs[i % logs.Count], m, p + new Vector3(R(-0.2f, 0.2f), 0.05f, R(-0.2f, 0.2f)), i * 75f + 20f, 0.55f, 0f, fire.transform, false);
            }
            // a stump to sit on
            List<RFMeshUtil.Part> stump = ModelParts("tree_stump_01", true);
            if (stump.Count > 0)
            {
                Vector3 sp = p + new Vector3(2.4f, 0f, 1.1f);
                sp.y = GroundY(sp.x, sp.z);
                GameObject s = PlacePart(stump[0], ModelMat("tree_stump_01"), sp, 40f, 0.7f, 0.1f, fire.transform, true);
                s.name = "CampStump";
            }

            // flames, embers and smoke
            Material flameMat = Particles("Flame", Tex("UI/flame.png"), true, new Color(1f, 0.62f, 0.3f, 0.7f));
            Material smokeMat = Particles("Smoke", Tex("UI/smoke.png"), false, new Color(0.55f, 0.55f, 0.55f, 0.35f));
            Particles(fire.transform, "Flames", flameMat, p + Vector3.up * 0.15f, 28f, 0.9f, 0.55f, new Vector2(0.35f, 0.7f), 0.25f, new Color(1f, 0.8f, 0.5f, 1f), 0f);
            Particles(fire.transform, "Smoke", smokeMat, p + Vector3.up * 0.8f, 4f, 6f, 0.5f, new Vector2(0.8f, 1.6f), 0.4f, new Color(0.6f, 0.6f, 0.6f, 0.45f), 0.05f);
            var glowMat = Particles("FireGlow", Tex("UI/glow.png"), true, new Color(1f, 0.55f, 0.25f, 0.35f));
            GameObject glow = Glow(fire.transform, glowMat, p + Vector3.up * 0.5f, 2.6f);
            glow.name = "FireGlow";

            var audio = new GameObject("FireAudio").AddComponent<AudioSource>();
            audio.transform.SetParent(fire.transform, false);
            audio.transform.position = p + Vector3.up * 0.3f;
            audio.clip = Load<AudioClip>(Art + "/Audio/fire.wav");
            audio.loop = true;
            audio.playOnAwake = true;
            audio.spatialBlend = 1f;
            audio.rolloffMode = AudioRolloffMode.Linear;
            audio.minDistance = 1.5f;
            audio.maxDistance = 22f;
            audio.volume = 0.7f;
            audio.dopplerLevel = 0f;
            return p;
        }

        static void Particles(Transform parent, string name, Material mat, Vector3 pos, float rate, float life, float speed, Vector2 size, float radius, Color color, float gravity)
        {
            var go = new GameObject(name);
            go.transform.SetParent(parent, false);
            go.transform.position = pos;
            go.transform.rotation = Quaternion.Euler(-90f, 0f, 0f);
            var ps = go.AddComponent<ParticleSystem>();
            ParticleSystem.MainModule main = ps.main;
            main.startLifetime = new ParticleSystem.MinMaxCurve(life * 0.7f, life);
            main.startSpeed = new ParticleSystem.MinMaxCurve(speed * 0.6f, speed);
            main.startSize = new ParticleSystem.MinMaxCurve(size.x, size.y);
            main.startColor = color;
            main.startRotation = new ParticleSystem.MinMaxCurve(0f, Mathf.PI * 2f);
            main.gravityModifier = -gravity;
            main.maxParticles = 80;
            main.simulationSpace = ParticleSystemSimulationSpace.World;
            main.loop = true;
            main.playOnAwake = true;
            ParticleSystem.EmissionModule em = ps.emission;
            em.rateOverTime = rate;
            ParticleSystem.ShapeModule shape = ps.shape;
            shape.shapeType = ParticleSystemShapeType.Cone;
            shape.angle = 8f;
            shape.radius = radius;
            ParticleSystem.ColorOverLifetimeModule col = ps.colorOverLifetime;
            col.enabled = true;
            var grad = new Gradient();
            grad.SetKeys(new[] { new GradientColorKey(Color.white, 0f), new GradientColorKey(Color.white, 1f) },
                         new[] { new GradientAlphaKey(0f, 0f), new GradientAlphaKey(1f, 0.15f), new GradientAlphaKey(0.6f, 0.6f), new GradientAlphaKey(0f, 1f) });
            col.color = new ParticleSystem.MinMaxGradient(grad);
            ParticleSystem.SizeOverLifetimeModule sz = ps.sizeOverLifetime;
            sz.enabled = true;
            sz.size = new ParticleSystem.MinMaxCurve(1f, gravity > 0f ? AnimationCurve.Linear(0f, 0.6f, 1f, 1.6f) : AnimationCurve.Linear(0f, 1f, 1f, 0.3f));
            var r = go.GetComponent<ParticleSystemRenderer>();
            r.sharedMaterial = mat;
            r.renderMode = ParticleSystemRenderMode.Billboard;
            r.shadowCastingMode = ShadowCastingMode.Off;
            r.receiveShadows = false;
        }

        static Mesh glowQuad;

        static GameObject Glow(Transform parent, Material mat, Vector3 pos, float size)
        {
            if (glowQuad == null) glowQuad = SaveMesh(RFMeshUtil.Quad("GlowQuad", 1f, 1f, 0.5f));
            var go = new GameObject("Glow");
            go.transform.SetParent(parent, false);
            go.transform.position = pos;
            go.transform.localScale = Vector3.one * size;
            go.AddComponent<MeshFilter>().sharedMesh = glowQuad;
            var mr = go.AddComponent<MeshRenderer>();
            mr.sharedMaterial = mat;
            mr.shadowCastingMode = ShadowCastingMode.Off;
            mr.receiveShadows = false;
            mr.lightProbeUsage = LightProbeUsage.Off;
            go.AddComponent<Billboard>();
            return go;
        }

        // ------------------------------------------------------------------ rocks
        static void BuildRocks()
        {
            List<RFMeshUtil.Part> faces1 = ModelParts("rock_face_01", true);
            List<RFMeshUtil.Part> faces2 = ModelParts("rock_face_02", true);
            List<RFMeshUtil.Part> set1 = ModelParts("rock_moss_set_01", true);
            List<RFMeshUtil.Part> set2 = ModelParts("rock_moss_set_02", true);
            int placed = 0;

            // big rock faces where the valley floor meets the mountains, and two by the north shore
            var faces = new List<KeyValuePair<RFMeshUtil.Part, Material>>();
            foreach (var p in faces1) faces.Add(new KeyValuePair<RFMeshUtil.Part, Material>(p, ModelMat("rock_face_01")));
            foreach (var p in faces2) faces.Add(new KeyValuePair<RFMeshUtil.Part, Material>(p, ModelMat("rock_face_02")));
            if (faces.Count > 0)
            {
                var spots = new List<Vector2>();
                for (int k = 0; k < 16; k++)
                {
                    float a = k / 16f * Mathf.PI * 2f + R(-0.15f, 0.15f);
                    float rr = R(118f, 134f);
                    spots.Add(RFLayout.ValleyCenter + new Vector2(Mathf.Cos(a) * rr, Mathf.Sin(a) * rr * 1.1f));
                }
                spots.Add(RFLayout.LakePoint(95f * Mathf.Deg2Rad, 1.12f));
                spots.Add(RFLayout.LakePoint(30f * Mathf.Deg2Rad, 1.15f));
                spots.Add(RFLayout.Lookout + new Vector2(10f, -12f));
                foreach (Vector2 s in spots)
                {
                    if (RFLayout.TrailDistance(s.x, s.y) < 7f) continue;
                    var f = faces[rng.Next(faces.Count)];
                    float scale = R(0.8f, 1.35f);
                    Vector3 g = new Vector3(s.x, GroundY(s.x, s.y), s.y);
                    // face the rock towards the valley centre
                    Vector2 toC = RFLayout.LakeCenter - s;
                    float yaw = Mathf.Atan2(toC.x, toC.y) * Mathf.Rad2Deg + R(-40f, 40f);
                    GameObject go = PlacePart(f.Key, f.Value, g, yaw, scale, f.Key.size.y * scale * 0.3f, rocksRoot, true, 0.15f, 0.003f);
                    go.name = "RockFace";
                    SetStatic(go);
                    Occupy(s.x, s.y, Mathf.Max(f.Key.size.x, f.Key.size.z) * scale * 0.5f);
                    placed++;
                }
            }

            // boulders and stones
            var stones = new List<KeyValuePair<RFMeshUtil.Part, Material>>();
            foreach (var p in set1) stones.Add(new KeyValuePair<RFMeshUtil.Part, Material>(p, ModelMat("rock_moss_set_01")));
            foreach (var p in set2) stones.Add(new KeyValuePair<RFMeshUtil.Part, Material>(p, ModelMat("rock_moss_set_02")));
            if (stones.Count > 0)
            {
                int tries = 0, count = 0;
                while (count < 85 && tries < 4000)
                {
                    tries++;
                    float x = R(-150f, 150f), z = R(-110f, 185f);
                    float dx = x - RFLayout.PlayCenter.x, dz = z - RFLayout.PlayCenter.y;
                    if (dx * dx + dz * dz > 165f * 165f) continue;
                    float e = RFLayout.LakeE(x, z);
                    float h = GroundY(x, z);
                    float slope = Slope(x, z);
                    float trail = RFLayout.TrailDistance(x, z);
                    if (trail < 2.2f) continue;
                    float want = 0.08f;
                    if (e > 0.96f && e < 1.18f) want = 0.7f;                  // the shore
                    if (trail < 5f) want = Mathf.Max(want, 0.35f);             // along the trail
                    if (RFLayout.Forest(x, z, h, slope) > 0.4f) want = Mathf.Max(want, 0.3f);
                    if (Vector2.Distance(new Vector2(x, z), RFLayout.Lookout) < 22f) want = 0.6f;
                    if (e < 0.93f) continue;
                    if ((float)rng.NextDouble() > want) continue;
                    var s = stones[rng.Next(stones.Count)];
                    float scale = R(0.7f, 1.9f);
                    if (e < 1.05f) scale *= 1.3f;
                    float radius = Mathf.Max(s.Key.size.x, s.Key.size.z) * scale * 0.5f;
                    if (!Free(x, z, radius + 0.5f)) continue;
                    Vector3 n = GroundNormal(x, z);
                    Quaternion tilt = Quaternion.FromToRotation(Vector3.up, Vector3.Slerp(Vector3.up, n, 0.6f));
                    bool big = s.Key.size.y * scale > 0.55f;
                    GameObject go = PlacePart(s.Key, s.Value, new Vector3(x, h, z), R(0f, 360f), scale, s.Key.size.y * scale * R(0.15f, 0.35f),
                                              rocksRoot, big, 0.08f, big ? 0.004f : 0.012f, tilt);
                    go.name = "Rock";
                    SetStatic(go);
                    if (!big) SetLayerRecursive(go, QualityManager.DetailLayer);
                    else if (s.Key.size.y * scale < 1.4f) SetLayerRecursive(go, QualityManager.PropLayer);
                    Occupy(x, z, radius);
                    count++;
                }
                placed += count;
            }
            Log("rocks placed: " + placed);
        }

        // ------------------------------------------------------------------ trees
        static void BuildTrees()
        {
            Material bark = Standard("Bark", Tex("Trees/bark_albedo.jpg"), Tex("Trees/bark_normal.png"), Tex("Trees/bark_mask.png"), 1f, false, 1.2f);
            Material twig = Foliage("Needles", Tex("Trees/twig_atlas.png"), 0.65f, 1f);
            twig.SetColor("_TransColor", new Color(0.55f, 0.7f, 0.22f, 1f));
            twig.SetFloat("_Smoothness", 0.22f);

            // variants
            int variants = 6;
            var templates = new GameObject[variants];
            var heights = new float[variants];
            var templRoot = Child(root, "TreeTemplates");
            for (int v = 0; v < variants; v++)
            {
                float h = Mathf.Lerp(13f, 20f, v / (float)(variants - 1)) + R(-1f, 1f);
                RFTrees.TreeMesh tm = RFTrees.Build(100 + v * 13, h, art.twigRects);
                tm.lod0 = SaveMesh(tm.lod0);
                tm.lod1 = SaveMesh(tm.lod1);
                heights[v] = h;
                var go = new GameObject("Fir" + v);
                go.transform.SetParent(templRoot, false);
                var l0 = new GameObject("LOD0");
                l0.transform.SetParent(go.transform, false);
                l0.AddComponent<MeshFilter>().sharedMesh = tm.lod0;
                var r0 = l0.AddComponent<MeshRenderer>();
                r0.sharedMaterials = new[] { bark, twig };
                var l1 = new GameObject("LOD1");
                l1.transform.SetParent(go.transform, false);
                l1.AddComponent<MeshFilter>().sharedMesh = tm.lod1;
                var r1 = l1.AddComponent<MeshRenderer>();
                r1.sharedMaterials = new[] { bark, twig };
                var lg = go.AddComponent<LODGroup>();
                lg.SetLODs(new[] { new LOD(0.3f, new Renderer[] { r0 }), new LOD(0.006f, new Renderer[] { r1 }) });
                lg.RecalculateBounds();
                var cap = go.AddComponent<CapsuleCollider>();
                cap.radius = tm.trunkRadius * 1.1f;
                cap.height = 5f;
                cap.center = new Vector3(0f, 2.5f, 0f);
                templates[v] = go;
                Log("tree variant " + v + " h=" + h.ToString("0.0") + " lod0 tris=" + (tm.lod0.triangles.Length / 3) + " lod1 tris=" + (tm.lod1.triangles.Length / 3));
            }

            int count = 0;
            float step = 5.4f;
            Vector3 tp = RFLayout.TerrainPos;
            for (float x = tp.x + 6f; x < tp.x + RFLayout.TerrainSize - 6f; x += step)
            {
                for (float z = tp.z + 6f; z < tp.z + RFLayout.TerrainSize - 6f; z += step)
                {
                    float px = x + R(-0.45f, 0.45f) * step, pz = z + R(-0.45f, 0.45f) * step;
                    float h = GroundY(px, pz);
                    if (h < RFLayout.Water + 1.1f) continue;
                    float slope = Slope(px, pz);
                    float f = RFLayout.Forest(px, pz, h, slope);
                    // thin out far up the mountains (keeps the tree count sane)
                    float vr = RFLayout.ValleyR(px, pz);
                    if (vr > 175f) f *= 0.55f;
                    if ((float)rng.NextDouble() > f * 0.92f) continue;
                    if (!Free(px, pz, 1.2f)) continue;
                    int v = rng.Next(variants);
                    float s = R(0.82f, 1.22f);
                    if (vr > 150f) s *= 0.85f;
                    var t = (GameObject)Object.Instantiate(templates[v], treesRoot);
                    t.name = "Fir";
                    t.transform.position = new Vector3(px, h - 0.15f, pz);
                    t.transform.rotation = Quaternion.Euler(R(-2.5f, 2.5f), R(0f, 360f), R(-2.5f, 2.5f));
                    t.transform.localScale = Vector3.one * s;
                    count++;
                }
            }
            Object.DestroyImmediate(templRoot.gameObject);
            Log("trees placed: " + count);
        }

        // ------------------------------------------------------------------ small detail: ferns, branches, stumps
        static void BuildDetail()
        {
            List<RFMeshUtil.Part> ferns = ModelParts("fern_02", false);
            Material fernMat = null;
            if (ferns.Count > 0)
            {
                fernMat = Foliage("Fern", TexAny("Models/fern_02/main_albedo"), 0.8f, 0.7f, 0.45f);
                fernMat.SetColor("_TransColor", new Color(0.6f, 0.8f, 0.25f, 1f));
            }
            List<RFMeshUtil.Part> branches = ModelParts("dry_branches_medium_01", true);
            List<RFMeshUtil.Part> stumps = ModelParts("tree_stump_01", true);
            int nf = 0, nb = 0, ns = 0, tries = 0;
            while (tries < 9000 && (nf < 240 || nb < 26 || ns < 8))
            {
                tries++;
                float x = R(-160f, 160f), z = R(-120f, 195f);
                float dx = x - RFLayout.PlayCenter.x, dz = z - RFLayout.PlayCenter.y;
                if (dx * dx + dz * dz > 170f * 170f) continue;
                float h = GroundY(x, z);
                if (h < RFLayout.Water + 0.6f) continue;
                float slope = Slope(x, z);
                if (slope > 30f) continue;
                if (RFLayout.TrailDistance(x, z) < 2f) continue;
                float forest = RFLayout.Forest(x, z, h, slope);
                double roll = rng.NextDouble();
                if (nf < 240 && ferns.Count > 0 && roll < forest * 0.9f + 0.03f)
                {
                    var p = ferns[rng.Next(ferns.Count)];
                    Vector3 n = GroundNormal(x, z);
                    GameObject g = PlacePart(p, fernMat, new Vector3(x, h, z), R(0f, 360f), R(0.8f, 1.35f), 0.05f, detailRoot, false, 0.5f, 0.02f,
                                             Quaternion.FromToRotation(Vector3.up, n));
                    g.name = "Fern";
                    SetLayerRecursive(g, QualityManager.DetailLayer);
                    foreach (Renderer r in g.GetComponentsInChildren<Renderer>()) r.shadowCastingMode = ShadowCastingMode.Off;
                    nf++;
                }
                else if (nb < 26 && branches.Count > 0 && roll < forest * 0.15f)
                {
                    var p = branches[rng.Next(branches.Count)];
                    GameObject g = PlacePart(p, ModelMat("dry_branches_medium_01"), new Vector3(x, h, z), R(0f, 360f), R(0.7f, 1.2f), 0.03f, detailRoot, false, 0.2f, 0.015f,
                                             Quaternion.FromToRotation(Vector3.up, GroundNormal(x, z)));
                    g.name = "Branches";
                    SetLayerRecursive(g, QualityManager.DetailLayer);
                    nb++;
                }
                else if (ns < 8 && stumps.Count > 0 && roll < forest * 0.02f && Free(x, z, 1.5f))
                {
                    var p = stumps[rng.Next(stumps.Count)];
                    GameObject g = PlacePart(p, ModelMat("tree_stump_01"), new Vector3(x, h, z), R(0f, 360f), R(0.6f, 0.9f), 0.12f, propsRoot, true, 0.15f, 0.01f);
                    g.name = "Stump";
                    SetLayerRecursive(g, QualityManager.PropLayer);
                    Occupy(x, z, 1f);
                    ns++;
                }
            }
            Log("detail: ferns " + nf + " branches " + nb + " stumps " + ns);
        }

        // ------------------------------------------------------------------ distant mountains
        static void BuildFarMountains()
        {
            Mesh m = SaveMesh(RFMeshUtil.FarMountains(RFLayout.ValleyCenter, 430f, 1500f, 160, 10, RFLayout.Water));
            var mat = new Material(Shader.Find("RealFPS/Distant")) { name = "FarMountains" };
            mat.SetTexture("_Detail", Tex("Terrain/rock_albedo.png"));
            mat.SetFloat("_DetailScale", 0.012f);
            SaveMat(mat);
            var go = new GameObject("FarMountains");
            go.transform.SetParent(root, false);
            go.AddComponent<MeshFilter>().sharedMesh = m;
            var mr = go.AddComponent<MeshRenderer>();
            mr.sharedMaterial = mat;
            mr.shadowCastingMode = ShadowCastingMode.Off;
            mr.receiveShadows = false;
            SetStatic(go);
        }

        // ------------------------------------------------------------------ lanterns
        static Lantern[] BuildLanterns(Transform pierEnd, Vector3 campfire)
        {
            List<RFMeshUtil.Part> parts = ModelParts("Lantern_01", false);
            var model = Load<GameObject>(Art + "/Models/Lantern_01/Lantern_01.fbx");
            Material painted = ModelMat("Lantern_01", "painted", true, 0.9f);
            Material brass = ModelMat("Lantern_01", "brass", true, 0.9f);
            Material glowMat = Particles("LanternGlow", Tex("UI/glow.png"), true, new Color(1f, 0.72f, 0.38f, 0.55f));
            Material flameMat = Particles("LanternFlame", Tex("UI/flame.png"), true, new Color(1f, 0.75f, 0.45f, 0.9f));

            var spots = new List<Vector3>();
            if (pierEnd != null) spots.Add(pierEnd.position);
            spots.Add(campfire + new Vector3(2.4f, 0f, 1.1f));             // on the stump by the fire
            spots.Add(new Vector3(RFLayout.Lookout.x, 0f, RFLayout.Lookout.y));
            Vector2 north = RFLayout.LakePoint(95f * Mathf.Deg2Rad, 1.2f);
            spots.Add(new Vector3(north.x, 0f, north.y));
            Vector2 east = RFLayout.LakePoint(-20f * Mathf.Deg2Rad, 1.55f);
            spots.Add(new Vector3(east.x, 0f, east.y));

            var list = new List<Lantern>();
            Physics.SyncTransforms();
            for (int i = 0; i < spots.Count; i++)
            {
                Vector3 s = spots[i];
                float y;
                RaycastHit hit;
                if (Physics.Raycast(new Vector3(s.x, 200f, s.z), Vector3.down, out hit, 400f)) y = hit.point.y;
                else y = GroundY(s.x, s.z);
                if (i == 0 && pierEnd != null) y = Mathf.Max(y, pierEnd.position.y);
                var go = new GameObject("Lantern" + (i + 1));
                go.transform.SetParent(propsRoot, false);
                go.transform.position = new Vector3(s.x, y, s.z);
                go.transform.rotation = Quaternion.Euler(0f, R(0f, 360f), 0f);
                float scale = 1.7f;
                float top = 0.5f;
                if (model != null)
                {
                    var inst = (GameObject)Object.Instantiate(model, go.transform);
                    inst.name = "Model";
                    inst.transform.localPosition = Vector3.zero;
                    inst.transform.localRotation = Quaternion.identity;
                    inst.transform.localScale = Vector3.one * scale;
                    Bounds b = new Bounds();
                    bool first = true;
                    foreach (MeshRenderer mr in inst.GetComponentsInChildren<MeshRenderer>())
                    {
                        Material[] arr = mr.sharedMaterials;
                        for (int k = 0; k < arr.Length; k++)
                        {
                            string n = arr[k] != null ? arr[k].name.ToLowerInvariant() : "";
                            arr[k] = n.Contains("brass") ? brass : painted;
                        }
                        mr.sharedMaterials = arr;
                        if (first) { b = mr.bounds; first = false; } else b.Encapsulate(mr.bounds);
                    }
                    // stand it on the surface
                    inst.transform.position += Vector3.up * (go.transform.position.y - b.min.y);
                    top = b.size.y;
                }
                Vector3 flamePos = go.transform.position + Vector3.up * (top * 0.42f);
                GameObject glow = Glow(go.transform, glowMat, flamePos, 1.3f);
                GameObject flame = Glow(go.transform, flameMat, flamePos - Vector3.up * 0.03f, 0.12f);
                flame.name = "Flame";
                flame.GetComponent<Billboard>().upright = true;
                var l = go.AddComponent<Lantern>();
                l.glow = glow.transform;
                l.flame = flame.transform;
                l.baseGlowSize = 1.3f;
                list.Add(l);
                Log("lantern " + (i + 1) + " at " + go.transform.position);
            }
            return list.ToArray();
        }

        // ------------------------------------------------------------------ player, camera, game
        static void BuildGame(Light sun, SkyLighting skyLighting, Lantern[] lanterns)
        {
            // camera
            var camGo = new GameObject("Main Camera");
            camGo.tag = "MainCamera";
            var cam = camGo.AddComponent<Camera>();
            cam.nearClipPlane = 0.06f;
            cam.farClipPlane = 2200f;
            cam.fieldOfView = 58f;
            cam.allowHDR = true;
            cam.allowMSAA = true;
            cam.clearFlags = CameraClearFlags.Skybox;
            camGo.AddComponent<AudioListener>();
            var post = camGo.AddComponent<PostFX>();
            post.shader = Shader.Find("Hidden/RealFPS/Post");

            // player
            Vector2 sp = RFLayout.Spawn;
            Vector3 spawnPos = new Vector3(sp.x, GroundY(sp.x, sp.y) + 0.1f, sp.y);
            Vector2 look = RFLayout.LakeCenter - sp;
            float spawnYaw = Mathf.Atan2(look.x, look.y) * Mathf.Rad2Deg - 6f;
            var playerGo = new GameObject("Player");
            playerGo.transform.position = spawnPos;
            var cc = playerGo.AddComponent<CharacterController>();
            cc.height = 1.8f;
            cc.radius = 0.32f;
            cc.center = new Vector3(0f, 0.9f, 0f);
            cc.slopeLimit = 46f;
            cc.stepOffset = 0.42f;
            cc.skinWidth = 0.04f;
            cc.minMoveDistance = 0f;
            var head = new GameObject("Head").transform;
            head.SetParent(playerGo.transform, false);
            head.localPosition = new Vector3(0f, 1.68f, 0f);
            var fp = playerGo.AddComponent<FPController>();
            fp.head = head;
            fp.terrain = terrain;
            fp.waterLevel = RFLayout.Water;
            fp.worldCenter = new Vector3(RFLayout.PlayCenter.x, 0f, RFLayout.PlayCenter.y);
            fp.worldRadius = RFLayout.PlayRadius;

            var spawn = new GameObject("SpawnPoint").transform;
            spawn.position = spawnPos;
            spawn.rotation = Quaternion.Euler(0f, spawnYaw, 0f);

            // game root
            var gameGo = new GameObject("Game");
            var assets = gameGo.AddComponent<GameAssets>();
            FillAssets(assets);
            var game = gameGo.AddComponent<Game>();
            game.player = fp;
            game.mainCamera = cam;
            game.spawnPoint = spawn;
            game.lanterns = lanterns;
            var q = gameGo.AddComponent<QualityManager>();
            q.cam = cam;
            q.sun = sun;
            q.terrain = terrain;
            q.post = post;
            game.quality = q;

            var grass = gameGo.AddComponent<GrassRenderer>();
            var gm = new Material(Shader.Find("RealFPS/Grass")) { name = "Grass" };
            gm.SetTexture("_MainTex", Tex("Grass/grass_atlas.png"));
            gm.enableInstancing = true;
            SaveMat(gm);
            assets.grassMaterial = gm;
            grass.terrain = terrain;
            grass.material = gm;
            grass.rects = art.grassRects;
            grass.kinds = art.grassKinds;
            grass.waterLevel = RFLayout.Water;
            grass.worldCenter = new Vector3(RFLayout.PlayCenter.x, 0f, RFLayout.PlayCenter.y);
            grass.worldRadius = RFLayout.PlayRadius;
            q.grass = grass;

            var amb = gameGo.AddComponent<AmbientAudio>();
            amb.lakeCenter = RFLayout.LakeCenter;
            amb.lakeRadii = RFLayout.LakeRadii;
            amb.lakeAngle = RFLayout.LakeAngle;
            amb.waterLevel = RFLayout.Water;
            game.ambientAudio = amb;

            // menu camera flight over the lake
            var cine = gameGo.AddComponent<CinematicCamera>();
            float W = RFLayout.Water;
            Vector2[] path =
            {
                RFLayout.LakePoint(-130f * Mathf.Deg2Rad, 0.7f), RFLayout.LakePoint(-85f * Mathf.Deg2Rad, 0.85f),
                RFLayout.LakePoint(-20f * Mathf.Deg2Rad, 0.75f), RFLayout.LakePoint(40f * Mathf.Deg2Rad, 0.8f),
                RFLayout.LakePoint(110f * Mathf.Deg2Rad, 0.75f), RFLayout.LakePoint(175f * Mathf.Deg2Rad, 0.8f)
            };
            float[] alts = { 10f, 5.5f, 9f, 13f, 8f, 11f };
            Vector2[] lookAt =
            {
                RFLayout.LakePoint(60f * Mathf.Deg2Rad, 1.9f), RFLayout.LakePoint(100f * Mathf.Deg2Rad, 2.3f),
                RFLayout.LakePoint(160f * Mathf.Deg2Rad, 1.6f), RFLayout.LakePoint(-140f * Mathf.Deg2Rad, 1.8f),
                RFLayout.LakePoint(-60f * Mathf.Deg2Rad, 2.0f), RFLayout.LakePoint(-10f * Mathf.Deg2Rad, 1.8f)
            };
            cine.points = new Vector3[path.Length];
            cine.targets = new Vector3[path.Length];
            for (int i = 0; i < path.Length; i++)
            {
                float y = Mathf.Max(W + alts[i], GroundY(path[i].x, path[i].y) + 6f);
                cine.points[i] = new Vector3(path[i].x, y, path[i].y);
                cine.targets[i] = new Vector3(lookAt[i].x, W + 14f, lookAt[i].y);
            }
            game.menuCamera = cine;

            // viewpoints for the automated screenshot tour
            var tour = new List<Transform>();
            System.Action<string, Vector2, Vector2, float> addView = (name, at, lookTo, pitch) =>
            {
                var t = new GameObject("Tour_" + name).transform;
                t.SetParent(gameGo.transform, false);
                t.position = new Vector3(at.x, GroundY(at.x, at.y) + 0.1f, at.y);
                Vector2 d = lookTo - at;
                t.rotation = Quaternion.Euler(pitch, Mathf.Atan2(d.x, d.y) * Mathf.Rad2Deg, 0f);
                tour.Add(t);
            };
            Vector2 pierShore = RFLayout.PierShore(1.25f);
            addView("shore", pierShore, RFLayout.LakeCenter + new Vector2(10f, 30f), -2f);
            addView("campfire", RFLayout.Campfire + new Vector2(-6f, -5f), RFLayout.Campfire, 12f);
            addView("westshore", RFLayout.LakePoint(175f * Mathf.Deg2Rad, 1.25f), RFLayout.LakeCenter + new Vector2(40f, 0f), -1f);
            addView("north", RFLayout.LakePoint(80f * Mathf.Deg2Rad, 1.3f), RFLayout.LakePoint(80f * Mathf.Deg2Rad, 3f), -4f);
            addView("forest", RFLayout.ValleyCenter + new Vector2(-95f, -60f), RFLayout.ValleyCenter + new Vector2(-120f, -90f), -2f);
            addView("lookout", RFLayout.Lookout + new Vector2(3f, 3f), RFLayout.LakeCenter, 4f);
            addView("grass", RFLayout.Spawn + new Vector2(4f, 12f), RFLayout.Spawn + new Vector2(10f, 30f), 22f);
            addView("water", RFLayout.LakePoint(-60f * Mathf.Deg2Rad, 1.04f), RFLayout.LakeCenter, 28f);
            addView("back", RFLayout.Spawn + new Vector2(0f, 6f), RFLayout.Spawn + new Vector2(-20f, -60f), -3f);
            game.tourPoints = tour.ToArray();

            Log("spawn " + spawnPos + " yaw " + spawnYaw.ToString("0"));
        }

        static void FillAssets(GameAssets a)
        {
            a.uiFont = Load<Font>(Art + "/Fonts/Barlow-Medium.ttf");
            a.uiFontBold = Load<Font>(Art + "/Fonts/Barlow-SemiBold.ttf");
            a.titleFont = Load<Font>(Art + "/Fonts/Cinzel.ttf");
            if (a.titleFont == null) a.titleFont = Load<Font>(Art + "/Fonts/Marcellus-Regular.ttf");
            Func<string, Sprite> S = n => Load<Sprite>(Art + "/UI/" + n + ".png");
            a.circle = S("circle"); a.ring = S("ring"); a.rounded = S("rounded"); a.glow = S("glow"); a.dot = S("dot");
            a.fadeH = S("fade_h"); a.fadeV = S("fade_v");
            a.iconJump = S("icon_jump"); a.iconCrouch = S("icon_crouch"); a.iconRun = S("icon_run"); a.iconPause = S("icon_pause");
            a.iconHand = S("icon_hand"); a.iconLantern = S("icon_lantern"); a.iconGear = S("icon_gear");
            Func<string, AudioClip> A = n => Load<AudioClip>(Art + "/Audio/" + n + ".wav");
            a.wind = A("wind"); a.lake = A("lake"); a.fire = A("fire");
            a.jump = A("jump"); a.land = A("land"); a.uiClick = A("ui_click"); a.pickup = A("pickup"); a.complete = A("complete");
            a.birds = new AudioClip[6];
            for (int i = 0; i < 6; i++) a.birds[i] = A("bird" + (i + 1));
            Func<string, int, AudioClip[]> Steps = (k, n) =>
            {
                var arr = new AudioClip[n];
                for (int i = 0; i < n; i++) arr[i] = A("step_" + k + (i + 1));
                return arr;
            };
            a.stepGrass = Steps("grass", 4); a.stepDirt = Steps("dirt", 4); a.stepRock = Steps("rock", 3);
            a.stepWood = Steps("wood", 3); a.stepWater = Steps("water", 3);
            a.postShader = Shader.Find("Hidden/RealFPS/Post");
        }
    }
}

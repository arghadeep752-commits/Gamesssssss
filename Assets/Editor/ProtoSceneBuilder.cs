using System.Collections.Generic;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.AI;

namespace GridProto.EditorTools
{
    /// <summary>
    /// Builds the prototype level: a white grid landscape with blocks, stairs, physics cubes and a small
    /// test room with a working door. Everything (textures, materials, meshes, scene) is generated here.
    /// </summary>
    public static class ProtoSceneBuilder
    {
        public const string ScenePath = "Assets/Scenes/Prototype.unity";
        const string Gen = "Assets/Generated";
        const int InteriorLayer = 8;          // only the room's ceiling light touches this layer
        const float Tile = ProtoTextures.TileMeters;

        public static readonly Color AmbientSky = new Color(0.66f, 0.73f, 0.82f);
        public static readonly Color AmbientEquator = new Color(0.56f, 0.58f, 0.61f);
        public static readonly Color AmbientGround = new Color(0.38f, 0.37f, 0.35f);

        static Material matGround, matWhite, matLight, matGray, matDark, matOrange, matBlue, matDoor, matTrim, matMetal, matLamp, matShadow, matSky;
        static MeshBuilder contactShadows;
        static int meshCount;

        public static string Build()
        {
            EnsureFolder("Assets", "Generated");
            EnsureFolder(Gen, "Textures");
            EnsureFolder(Gen, "Materials");
            EnsureFolder(Gen, "Meshes");
            EnsureFolder("Assets", "Scenes");
            ClearFolder(Gen + "/Meshes");
            meshCount = 0;

            CreateMaterials();

            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            contactShadows = new MeshBuilder();

            if (HouseBuilder.Available)
            {
                BuildHouseScene();
                EditorSceneManager.SaveScene(scene, ScenePath);
                AssetDatabase.SaveAssets();
                return ScenePath;
            }

            Light sun = CreateLighting();
            BuildGround();
            Door door = BuildRoom();
            BuildCourse();
            BuildFarBlocks();
            BuildPhysicsCubes();
            FinishContactShadows();
            ReflectionProbe probe = CreateReflectionProbe();
            Camera cam;
            Light faceLight;
            PlayerController player = CreatePlayer(new Vector3(0f, 0.05f, -6f), 0f, out cam, out faceLight);
            NavMeshData navMesh = BuildNavMesh(new Bounds(new Vector3(0f, 2f, 6f), new Vector3(130f, 14f, 130f)));
            // the enemy starts behind the test room, facing away, and patrols until it notices the player
            EnemyAI enemy = EnemyBuilder.Create(Gen, new Vector3(8f, 0f, 26f), 20f);
            CreateGameRoot(player, cam, sun, probe, door, enemy, navMesh, faceLight);

            EditorSceneManager.SaveScene(scene, ScenePath);
            AssetDatabase.SaveAssets();
            Debug.Log("[PROTO] scene built: " + meshCount + " meshes, " + contactShadows.VertexCount + " contact shadow vertices");
            return ScenePath;
        }

        // ------------------------------------------------------------------ materials

        static void CreateMaterials()
        {
            string tex = Gen + "/Textures/";
            ProtoTextures.WriteGridAlbedo(tex + "grid_albedo.png", 1024);
            ProtoTextures.WriteGridNormal(tex + "grid_normal.png", 1024);
            ProtoTextures.WriteContactShadowMask(tex + "contact_shadow.png", 64);
            Texture2D albedo = ProtoTextures.Import(tex + "grid_albedo.png", true, false, true, 9);
            Texture2D normal = ProtoTextures.Import(tex + "grid_normal.png", false, true, true, 9);
            Texture2D mask = ProtoTextures.Import(tex + "contact_shadow.png", false, false, false, 1);

            matGround = Save(Standard(new Color(1f, 1f, 1f), albedo, normal, 0.9f, 0.16f, 0f), "Ground");
            matWhite = Save(Standard(new Color(0.98f, 0.98f, 0.98f), albedo, normal, 0.6f, 0.2f, 0f), "White");
            matLight = Save(Standard(new Color(0.8f, 0.81f, 0.83f), albedo, normal, 0.6f, 0.2f, 0f), "LightGray");
            matGray = Save(Standard(new Color(0.56f, 0.58f, 0.61f), albedo, normal, 0.6f, 0.22f, 0f), "Gray");
            matDark = Save(Standard(new Color(0.3f, 0.31f, 0.33f), albedo, normal, 0.6f, 0.25f, 0f), "Dark");
            matOrange = Save(Standard(new Color(0.96f, 0.55f, 0.24f), albedo, normal, 0.6f, 0.25f, 0f), "Orange");
            matBlue = Save(Standard(new Color(0.47f, 0.64f, 0.86f), albedo, normal, 0.6f, 0.25f, 0f), "Blue");
            matDoor = Save(Standard(new Color(0.93f, 0.52f, 0.22f), null, null, 0f, 0.35f, 0f), "Door");
            matTrim = Save(Standard(new Color(0.22f, 0.23f, 0.25f), null, null, 0f, 0.3f, 0f), "Trim");
            matMetal = Save(Standard(new Color(0.78f, 0.79f, 0.8f), null, null, 0f, 0.72f, 1f), "Metal");

            Material lamp = Standard(new Color(1f, 0.95f, 0.85f), null, null, 0f, 0.5f, 0f);
            lamp.EnableKeyword("_EMISSION");
            lamp.SetColor("_EmissionColor", new Color(1f, 0.85f, 0.62f) * 2.2f);
            lamp.globalIlluminationFlags = MaterialGlobalIlluminationFlags.None;
            matLamp = Save(lamp, "Lamp");

            var shadow = new Material(Shader.Find("GridProto/ContactShadow"));
            shadow.SetTexture("_MainTex", mask);
            matShadow = Save(shadow, "ContactShadow");

            var sky = new Material(Shader.Find("Skybox/Procedural"));
            sky.SetFloat("_SunDisk", 2f);
            sky.DisableKeyword("_SUNDISK_NONE");
            sky.DisableKeyword("_SUNDISK_SIMPLE");
            sky.EnableKeyword("_SUNDISK_HIGH_QUALITY");
            sky.SetFloat("_SunSize", 0.035f);
            sky.SetFloat("_SunSizeConvergence", 6f);
            sky.SetFloat("_AtmosphereThickness", 0.85f);
            sky.SetColor("_SkyTint", new Color(0.5f, 0.52f, 0.56f));
            sky.SetColor("_GroundColor", new Color(0.42f, 0.42f, 0.43f));
            sky.SetFloat("_Exposure", 1.2f);
            matSky = Save(sky, "Sky");
        }

        static Material Standard(Color color, Texture2D albedo, Texture2D normal, float bump, float smoothness, float metallic)
        {
            var m = new Material(Shader.Find("Standard"));
            m.SetColor("_Color", color);
            if (albedo != null) m.SetTexture("_MainTex", albedo);
            if (normal != null)
            {
                m.SetTexture("_BumpMap", normal);
                m.SetFloat("_BumpScale", bump);
                m.EnableKeyword("_NORMALMAP");
            }
            m.SetFloat("_Glossiness", smoothness);
            m.SetFloat("_Metallic", metallic);
            m.enableInstancing = true;
            return m;
        }

        static Material Save(Material m, string name)
        {
            string path = Gen + "/Materials/" + name + ".mat";
            AssetDatabase.DeleteAsset(path);
            m.name = name;
            AssetDatabase.CreateAsset(m, path);
            return m;
        }

        // ------------------------------------------------------------------ lighting

        static Light CreateLighting()
        {
            var sunGo = new GameObject("Sun");
            sunGo.transform.rotation = Quaternion.Euler(50f, 38f, 0f);   // behind the player's left shoulder at spawn
            var sun = sunGo.AddComponent<Light>();
            sun.type = LightType.Directional;
            sun.color = new Color(1f, 0.955f, 0.885f);
            sun.intensity = 1f;
            sun.shadows = LightShadows.Soft;
            sun.shadowStrength = 0.92f;
            sun.shadowBias = 0.045f;
            sun.shadowNormalBias = 0.35f;
            sun.shadowResolution = UnityEngine.Rendering.LightShadowResolution.High;
            sun.lightmapBakeType = LightmapBakeType.Realtime;

            // no baked lighting at all: everything is real-time, so nothing can go missing in the build
            var lighting = new LightingSettings();
            lighting.name = "Lighting";
            lighting.bakedGI = false;
            lighting.realtimeGI = false;
            string lightingPath = Gen + "/Lighting.lighting";
            AssetDatabase.DeleteAsset(lightingPath);
            AssetDatabase.CreateAsset(lighting, lightingPath);
            Lightmapping.lightingSettings = lighting;

            RenderSettings.skybox = matSky;
            RenderSettings.sun = sun;
            RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Trilight;
            RenderSettings.ambientSkyColor = AmbientSky;
            RenderSettings.ambientEquatorColor = AmbientEquator;
            RenderSettings.ambientGroundColor = AmbientGround;
            RenderSettings.fog = true;
            RenderSettings.fogMode = FogMode.Exponential;
            RenderSettings.fogDensity = 0.0055f;
            RenderSettings.fogColor = new Color(0.74f, 0.79f, 0.86f);
            RenderSettings.defaultReflectionMode = UnityEngine.Rendering.DefaultReflectionMode.Skybox;
            RenderSettings.reflectionIntensity = 0.8f;
            return sun;
        }

        static ReflectionProbe CreateReflectionProbe()
        {
            var go = new GameObject("Reflection Probe");
            go.transform.position = new Vector3(0f, 2f, 0f);
            var probe = go.AddComponent<ReflectionProbe>();
            probe.mode = UnityEngine.Rendering.ReflectionProbeMode.Realtime;
            probe.refreshMode = UnityEngine.Rendering.ReflectionProbeRefreshMode.ViaScripting;
            probe.timeSlicingMode = UnityEngine.Rendering.ReflectionProbeTimeSlicingMode.NoTimeSlicing;
            probe.resolution = 128;
            probe.size = new Vector3(1000f, 400f, 1000f);
            probe.boxProjection = false;
            probe.hdr = false;
            probe.shadowDistance = 30f;
            probe.farClipPlane = 600f;
            probe.clearFlags = UnityEngine.Rendering.ReflectionProbeClearFlags.Skybox;
            probe.importance = 1;
            probe.intensity = 1f;
            return probe;
        }

        // ------------------------------------------------------------------ level

        static void BuildGround()
        {
            Mesh mesh = SaveMesh(MeshGen.Ground("ground", 1000f, 40, Tile));
            GameObject go = MakeRenderer("Ground", mesh, matGround, Vector3.zero, 0f, null);
            go.GetComponent<MeshRenderer>().shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            var col = go.AddComponent<BoxCollider>();
            col.center = new Vector3(0f, -0.5f, 0f);
            col.size = new Vector3(1000f, 1f, 1000f);
            MarkStatic(go);
        }

        static Door BuildRoom()
        {
            Transform room = new GameObject("Test Room").transform;
            const float x0 = -4f, x1 = 4f, z0 = 8.5f, z1 = 15.5f, H = 3.2f, T = 0.25f;
            const float doorHalf = 0.55f, doorHeight = 2.2f;
            const int L = InteriorLayer;
            float zf = z0 + T * 0.5f;          // centre line of the front wall
            float midZ = (z0 + z1) * 0.5f;

            Block("Wall Back", new Vector3(0f, H * 0.5f, z1 - T * 0.5f), new Vector3(x1 - x0, H, T), matWhite, 0f, room, false, L);
            Block("Wall Left", new Vector3(x0 + T * 0.5f, H * 0.5f, midZ), new Vector3(T, H, z1 - z0 - 2f * T), matWhite, 0f, room, false, L);
            Block("Wall Right", new Vector3(x1 - T * 0.5f, H * 0.5f, midZ), new Vector3(T, H, z1 - z0 - 2f * T), matWhite, 0f, room, false, L);
            float segment = (x1 - x0) * 0.5f - doorHalf;
            Block("Wall Front Left", new Vector3(x0 + segment * 0.5f, H * 0.5f, zf), new Vector3(segment, H, T), matWhite, 0f, room, false, L);
            Block("Wall Front Right", new Vector3(x1 - segment * 0.5f, H * 0.5f, zf), new Vector3(segment, H, T), matWhite, 0f, room, false, L);
            Block("Lintel", new Vector3(0f, (doorHeight + H) * 0.5f, zf), new Vector3(doorHalf * 2f, H - doorHeight, T), matWhite, 0f, room, false, L);
            Block("Roof", new Vector3(0f, H + 0.12f, midZ), new Vector3(x1 - x0 + 0.4f, 0.24f, z1 - z0 + 0.4f), matLight, 0f, room, false, L);
            Block("Floor", new Vector3(0f, 0.02f, midZ), new Vector3(x1 - x0 - 2f * T, 0.04f, z1 - z0 - 2f * T), matLight, 0f, room, false, L);
            Block("Threshold", new Vector3(0f, 0.02f, zf), new Vector3(doorHalf * 2f, 0.04f, T), matTrim, 0f, room, false, L);

            // contact shadows: outside around the building, inside along the walls (on top of the floor slab)
            MeshGen.AddContactShadow(contactShadows, new Vector3(0f, 0.006f, midZ), (x1 - x0) * 0.5f, (z1 - z0) * 0.5f, 0f, 0.75f, 0.5f);
            float xi0 = x0 + T, xi1 = x1 - T, zi0 = z0 + T, zi1 = z1 - T, yi = 0.046f;
            MeshGen.AddContactStrip(contactShadows, new Vector3(xi0, yi, zi1), new Vector3(xi1, yi, zi1), Vector3.back, 0.55f, 0.38f);
            MeshGen.AddContactStrip(contactShadows, new Vector3(xi0, yi, zi0), new Vector3(xi0, yi, zi1), Vector3.right, 0.55f, 0.38f);
            MeshGen.AddContactStrip(contactShadows, new Vector3(xi1, yi, zi0), new Vector3(xi1, yi, zi1), Vector3.left, 0.55f, 0.38f);
            MeshGen.AddContactStrip(contactShadows, new Vector3(xi0, yi, zi0), new Vector3(-doorHalf, yi, zi0), Vector3.forward, 0.55f, 0.38f);
            MeshGen.AddContactStrip(contactShadows, new Vector3(doorHalf, yi, zi0), new Vector3(xi1, yi, zi0), Vector3.forward, 0.55f, 0.38f);

            // door frame: casings on both faces and jamb liners inside the opening (visual only)
            float[] faces = { z0 - 0.01f, z0 + T + 0.01f };
            for (int f = 0; f < faces.Length; f++)
            {
                float zc = faces[f];
                Trim("Casing Left", new Vector3(-doorHalf - 0.04f, (doorHeight + 0.08f) * 0.5f, zc), new Vector3(0.08f, doorHeight + 0.08f, 0.02f), room);
                Trim("Casing Right", new Vector3(doorHalf + 0.04f, (doorHeight + 0.08f) * 0.5f, zc), new Vector3(0.08f, doorHeight + 0.08f, 0.02f), room);
                Trim("Casing Top", new Vector3(0f, doorHeight + 0.04f, zc), new Vector3(doorHalf * 2f + 0.16f, 0.08f, 0.02f), room);
            }
            Trim("Jamb Left", new Vector3(-doorHalf + 0.01f, doorHeight * 0.5f, zf), new Vector3(0.02f, doorHeight, T), room);
            Trim("Jamb Right", new Vector3(doorHalf - 0.01f, doorHeight * 0.5f, zf), new Vector3(0.02f, doorHeight, T), room);
            Trim("Jamb Top", new Vector3(0f, doorHeight - 0.01f, zf), new Vector3(doorHalf * 2f, 0.02f, T), room);

            // the door: a panel on a hinge at the left edge of the opening (seen from outside)
            Transform hinge = new GameObject("Door Hinge").transform;
            hinge.SetParent(room, false);
            hinge.position = new Vector3(-doorHalf + 0.02f, 0.05f, zf);   // just above the threshold and the floor slab
            hinge.gameObject.layer = L;
            var hingeBody = hinge.gameObject.AddComponent<Rigidbody>();
            hingeBody.isKinematic = true;
            hingeBody.useGravity = false;

            const float panelW = 1.06f, panelH = 2.12f, panelT = 0.045f;
            Mesh panelMesh = SaveMesh(MeshGen.Box("door_panel", new Vector3(panelW, panelH, panelT), Vector3.zero, 1f));
            GameObject panel = MakeRenderer("Door", panelMesh, matDoor, Vector3.zero, 0f, hinge);
            panel.transform.localPosition = new Vector3(panelW * 0.5f, panelH * 0.5f, 0f);
            panel.layer = L;
            var panelCollider = panel.AddComponent<BoxCollider>();
            panelCollider.size = new Vector3(panelW, panelH, panelT);

            for (int s = -1; s <= 1; s += 2)
            {
                Part("Handle Rose", panel.transform, new Vector3(0.42f, -0.1f, s * (panelT * 0.5f + 0.008f)), new Vector3(0.055f, 0.055f, 0.016f), matMetal);
                Part("Handle Neck", panel.transform, new Vector3(0.42f, -0.1f, s * (panelT * 0.5f + 0.035f)), new Vector3(0.02f, 0.02f, 0.05f), matMetal);
                Part("Handle Lever", panel.transform, new Vector3(0.36f, -0.1f, s * (panelT * 0.5f + 0.058f)), new Vector3(0.14f, 0.024f, 0.022f), matMetal);
            }

            Transform focus = new GameObject("Door Focus").transform;
            focus.SetParent(room, false);
            focus.position = new Vector3(0f, 1.1f, zf);
            var audio = focus.gameObject.AddComponent<AudioSource>();
            audio.playOnAwake = false;
            audio.spatialBlend = 1f;
            audio.minDistance = 1.5f;
            audio.maxDistance = 30f;
            audio.rolloffMode = AudioRolloffMode.Logarithmic;
            var door = focus.gameObject.AddComponent<Door>();
            door.hinge = hinge;
            door.focusPoint = focus;
            door.range = 2.4f;
            door.openAngle = 92f;
            door.outsideSwingSign = 1f;       // +angle moves the free edge towards -Z, which is outside
            door.outsideDirection = Vector3.back;
            door.audioSource = audio;

            // inside: a few props and a warm ceiling light
            InteriorBlock("Crate", new Vector3(-2.6f, 0.54f, 14.2f), Vector3.one, matOrange, 0f, room);
            InteriorBlock("Small Crate", new Vector3(-1.45f, 0.44f, 14.45f), new Vector3(0.8f, 0.8f, 0.8f), matGray, 20f, room);
            InteriorBlock("Table", new Vector3(2.3f, 0.415f, 12.6f), new Vector3(1.6f, 0.75f, 0.9f), matDark, 0f, room);
            InteriorBlock("Shelf", new Vector3(3.45f, 1.04f, 10.6f), new Vector3(0.5f, 2f, 2.2f), matLight, 0f, room);

            var lampGo = new GameObject("Ceiling Light");
            lampGo.transform.SetParent(room, false);
            lampGo.transform.position = new Vector3(0f, H - 0.35f, midZ);
            var lamp = lampGo.AddComponent<Light>();
            lamp.type = LightType.Point;
            lamp.range = 8.5f;
            lamp.intensity = 1.5f;
            lamp.color = new Color(1f, 0.86f, 0.66f);
            lamp.shadows = LightShadows.None;
            lamp.cullingMask = 1 << L;
            lamp.renderMode = LightRenderMode.ForcePixel;
            lamp.lightmapBakeType = LightmapBakeType.Realtime;
            Part("Lamp Fixture", room, new Vector3(0f, H - 0.03f, midZ), new Vector3(0.6f, 0.06f, 0.6f), matLamp);

            return door;
        }

        static void BuildCourse()
        {
            Transform t = new GameObject("Course").transform;

            // left side
            Block("Cube 4m", new Vector3(-9f, 2f, 3f), new Vector3(4f, 4f, 4f), matWhite, 0f, t);
            Block("Cube 2m", new Vector3(-5.5f, 1f, -1.5f), new Vector3(2f, 2f, 2f), matOrange, 0f, t);
            Block("Cube 1m", new Vector3(-4.2f, 0.5f, -3.4f), Vector3.one, matLight, 0f, t);
            Block("Stack Base", new Vector3(-10f, 1f, -6f), new Vector3(2f, 2f, 2f), matGray, 0f, t);
            Block("Stack Top", new Vector3(-10.2f, 2.5f, -6.1f), Vector3.one, matOrange, 15f, t, false);
            Block("Pillar", new Vector3(-5f, 3f, 6.5f), new Vector3(1f, 6f, 1f), matDark, 0f, t);

            // platform with a staircase (10 steps of 20 cm)
            Block("Platform", new Vector3(-14f, 1f, 9f), new Vector3(4f, 2f, 4f), matLight, 0f, t);
            const float stairsStart = 3.6f, stairsEnd = 7f;
            for (int i = 1; i <= 10; i++)
            {
                float top = 0.2f * i;
                float front = stairsStart + (i - 1) * 0.3f;
                Block("Step " + i, new Vector3(-14f, top * 0.5f, (front + stairsEnd) * 0.5f), new Vector3(4f, top, stairsEnd - front), matWhite, 0f, t, false);
            }
            MeshGen.AddContactShadow(contactShadows, new Vector3(-14f, 0.006f, (stairsStart + stairsEnd) * 0.5f), 2f, (stairsEnd - stairsStart) * 0.5f, 0f, 0.45f, 0.45f);

            // right side
            Block("Cube 3m", new Vector3(8.5f, 1.5f, 1f), new Vector3(3f, 3f, 3f), matBlue, 0f, t);
            Block("Cube 1m A", new Vector3(5f, 0.5f, -4f), Vector3.one, matWhite, 0f, t);
            Block("Cube 1m B", new Vector3(6.3f, 0.5f, -3.5f), Vector3.one, matLight, 25f, t);
            Block("Cube 1m C", new Vector3(5.6f, 1.5f, -3.8f), Vector3.one, matOrange, -10f, t, false);
            Block("Wall Segment", new Vector3(11f, 1.25f, 9f), new Vector3(6f, 2.5f, 0.5f), matWhite, 0f, t);
            Block("Low Wall", new Vector3(6f, 0.5f, 5f), new Vector3(3f, 1f, 0.5f), matGray, 0f, t);
            Block("Long Block", new Vector3(14f, 0.75f, -3f), new Vector3(1.5f, 1.5f, 8f), matLight, 0f, t);
            Block("Cube 2m Turned", new Vector3(12.5f, 1f, 4f), new Vector3(2f, 2f, 2f), matDark, 30f, t);
        }

        static void BuildFarBlocks()
        {
            Transform t = new GameObject("Far Blocks").transform;
            Block("Far A", new Vector3(-32f, 5f, 42f), new Vector3(6f, 10f, 6f), matLight, 0f, t);
            Block("Far B", new Vector3(36f, 2f, 30f), new Vector3(10f, 4f, 10f), matWhite, 0f, t);
            Block("Far C", new Vector3(26f, 8f, 64f), new Vector3(4f, 16f, 4f), matGray, 0f, t);
            Block("Far D", new Vector3(-44f, 1.5f, -18f), new Vector3(8f, 3f, 8f), matWhite, 20f, t);
            Block("Far E", new Vector3(8f, 3f, 48f), new Vector3(14f, 6f, 3f), matLight, 0f, t);
            Block("Far F", new Vector3(-18f, 2.5f, 26f), new Vector3(5f, 5f, 5f), matOrange, 0f, t);
            Block("Far G", new Vector3(52f, 6f, -6f), new Vector3(6f, 12f, 6f), matLight, 0f, t);
            Block("Far H", new Vector3(-22f, 1f, -34f), new Vector3(4f, 2f, 12f), matGray, 0f, t);
            Block("Far I", new Vector3(20f, 1.5f, -30f), new Vector3(3f, 3f, 3f), matBlue, 45f, t);
        }

        static void BuildPhysicsCubes()
        {
            Transform t = new GameObject("Physics Cubes").transform;
            Vector3[] spots =
            {
                new Vector3(2.9f, 0.36f, -3.2f),
                new Vector3(3.9f, 0.36f, -2.2f),
                new Vector3(3.3f, 0.36f, -0.8f),
                new Vector3(-3.3f, 0.36f, 1.2f),
            };
            Vector3 size = new Vector3(0.7f, 0.7f, 0.7f);
            Mesh mesh = SaveMesh(MeshGen.Box("physics_cube", size, Vector3.zero, Tile));
            for (int i = 0; i < spots.Length; i++)
            {
                GameObject go = MakeRenderer("Physics Cube " + (i + 1), mesh, i % 2 == 0 ? matOrange : matBlue, spots[i], i * 23f, t);
                var box = go.AddComponent<BoxCollider>();
                box.size = size;
                var body = go.AddComponent<Rigidbody>();
                body.mass = 12f;
                body.interpolation = RigidbodyInterpolation.Interpolate;
                var obstacle = go.AddComponent<NavMeshObstacle>();   // the enemy steers around them
                obstacle.shape = NavMeshObstacleShape.Box;
                obstacle.size = size;
                obstacle.carving = false;
            }
        }

        static void FinishContactShadows()
        {
            Mesh mesh = SaveMesh(contactShadows.ToMesh("contact_shadows", false));
            GameObject go = MakeRenderer("Contact Shadows", mesh, matShadow, Vector3.zero, 0f, null);
            var r = go.GetComponent<MeshRenderer>();
            r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            r.receiveShadows = false;
            r.lightProbeUsage = UnityEngine.Rendering.LightProbeUsage.Off;
            r.reflectionProbeUsage = UnityEngine.Rendering.ReflectionProbeUsage.Off;
            MarkStatic(go);
        }

        // ------------------------------------------------------------------ player and game

        /// <summary>Walkable-area map for the enemy: the floor, block tops and stairs, through the doorway.</summary>
        static NavMeshData BuildNavMesh(Bounds bounds)
        {
            var sources = new List<NavMeshBuildSource>();
            var markups = new List<NavMeshBuildMarkup>();
            int mask = ~((1 << 2) | (1 << EnemyBuilder.EnemyLayer) | (1 << EnemyBuilder.EnemyVisualLayer));
            UnityEngine.AI.NavMeshBuilder.CollectSources(bounds, mask, NavMeshCollectGeometry.PhysicsColliders, 0, markups, sources);
            // things that move are not floor or walls: the physics cubes and the door (its hinge has a Rigidbody)
            sources.RemoveAll(s => s.component != null && s.component.GetComponentInParent<Rigidbody>() != null);
            NavMeshBuildSettings settings = NavMesh.GetSettingsByID(0);
            settings.agentRadius = 0.3f;
            settings.agentHeight = 1.9f;
            settings.agentClimb = 0.45f;
            settings.agentSlope = 46f;
            settings.overrideVoxelSize = true;
            settings.voxelSize = 0.1f;
            NavMeshData data = UnityEngine.AI.NavMeshBuilder.BuildNavMeshData(settings, sources, bounds, Vector3.zero, Quaternion.identity);
            if (data == null) throw new System.Exception("NavMesh build failed");
            data.name = "NavMesh";
            string path = Gen + "/NavMesh.asset";
            AssetDatabase.DeleteAsset(path);
            AssetDatabase.CreateAsset(data, path);
            Debug.Log("[PROTO] navmesh built from " + sources.Count + " sources");
            return data;
        }

        static PlayerController CreatePlayer(Vector3 position, float yaw, out Camera cam, out Light faceLight)
        {
            var go = new GameObject("Player");
            go.layer = 2;   // "Ignore Raycast": keeps the player out of its own physics checks
            go.transform.position = position;
            go.transform.rotation = Quaternion.Euler(0f, yaw, 0f);
            var controller = go.AddComponent<CharacterController>();
            controller.height = 1.8f;
            controller.radius = 0.35f;
            controller.center = new Vector3(0f, 0.9f, 0f);
            controller.stepOffset = 0.4f;
            controller.slopeLimit = 50f;
            controller.skinWidth = 0.03f;
            controller.minMoveDistance = 0f;

            Transform head = new GameObject("Head").transform;
            head.SetParent(go.transform, false);
            head.localPosition = new Vector3(0f, 1.67f, 0f);

            var camGo = new GameObject("Main Camera");
            camGo.tag = "MainCamera";
            camGo.transform.SetParent(head, false);
            cam = camGo.AddComponent<Camera>();
            cam.clearFlags = CameraClearFlags.Skybox;
            cam.fieldOfView = 62f;
            cam.nearClipPlane = 0.05f;
            cam.farClipPlane = 700f;
            cam.allowHDR = false;
            cam.allowMSAA = true;
            cam.useOcclusionCulling = false;
            camGo.AddComponent<AudioListener>();

            // only lights the enemy's face during the jumpscare
            var lightGo = new GameObject("Jumpscare Light");
            lightGo.transform.SetParent(camGo.transform, false);
            lightGo.transform.localPosition = new Vector3(0f, 0.3f, 0.05f);
            faceLight = lightGo.AddComponent<Light>();
            faceLight.type = LightType.Point;
            faceLight.range = 3f;
            faceLight.intensity = 1.6f;
            faceLight.color = new Color(1f, 0.9f, 0.82f);
            faceLight.cullingMask = 1 << EnemyBuilder.EnemyVisualLayer;
            faceLight.shadows = LightShadows.None;
            faceLight.renderMode = LightRenderMode.ForcePixel;
            faceLight.lightmapBakeType = LightmapBakeType.Realtime;
            faceLight.enabled = false;

            var feet = go.AddComponent<AudioSource>();
            feet.playOnAwake = false;
            feet.spatialBlend = 0f;

            var player = go.AddComponent<PlayerController>();
            player.cameraPivot = head;
            player.playerCamera = cam;
            player.footstepSource = feet;

            var interactor = go.AddComponent<PlayerInteractor>();
            interactor.player = player;
            interactor.view = camGo.transform;
            return player;
        }

        static void CreateGameRoot(PlayerController player, Camera cam, Light sun, ReflectionProbe probe, Door door,
                                   EnemyAI enemy, NavMeshData navMesh, Light faceLight)
        {
            var go = new GameObject("Game");
            var ambience = go.AddComponent<AudioSource>();
            ambience.playOnAwake = false;
            ambience.spatialBlend = 0f;
            ambience.volume = 0.2f;
            ambience.loop = true;

            var root = go.AddComponent<GameRoot>();
            root.player = player;
            root.playerCamera = cam;
            root.sun = sun;
            root.reflectionProbe = probe;
            root.ambience = ambience;
            root.door = door;
            root.ambientSky = AmbientSky;
            root.ambientEquator = AmbientEquator;
            root.ambientGround = AmbientGround;

            var hud = go.AddComponent<Hud>();
            hud.player = player;
            hud.interactor = player.GetComponent<PlayerInteractor>();
            hud.root = root;
            root.hud = hud;

            var loader = go.AddComponent<NavMeshLoader>();
            loader.data = navMesh;

            var sfx = go.AddComponent<AudioSource>();
            sfx.playOnAwake = false;
            sfx.spatialBlend = 0f;
            sfx.ignoreListenerPause = true;
            var jumpscare = go.AddComponent<Jumpscare>();
            jumpscare.player = player;
            jumpscare.hud = hud;
            jumpscare.faceLight = faceLight;
            jumpscare.sfx = sfx;

            enemy.player = player;
            enemy.jumpscare = jumpscare;
            enemy.door = door;
            root.enemy = enemy;
            root.jumpscare = jumpscare;
        }

        // ------------------------------------------------------------------ the Blender house map

        /// <summary>The level made in Blender: a furnished two-storey house with a modular kitchen on a garden plot.</summary>
        static void BuildHouseScene()
        {
            HouseBuilder.Result house = HouseBuilder.Build();
            Light sun = CreateLighting();
            sun.transform.rotation = Quaternion.LookRotation(-house.sunDir);
            sun.shadows = LightShadows.None;           // all house lighting is baked; the sun only drives the sky
            sun.cullingMask = 1 << 31;
            RenderSettings.fogDensity = 0.0042f;
            RenderSettings.fogColor = new Color(0.76f, 0.82f, 0.9f);
            RenderSettings.defaultReflectionMode = UnityEngine.Rendering.DefaultReflectionMode.Skybox;

            Camera cam;
            Light faceLight;
            PlayerController player = CreatePlayer(house.spawn, house.spawnYaw, out cam, out faceLight);
            cam.farClipPlane = 400f;
            NavMeshData navMesh = BuildNavMesh(house.navBounds);
            EnemyAI enemy = EnemyBuilder.Create(Gen, house.enemySpawn, house.enemyYaw);
            enemy.patrolPoints = house.patrol;
            enemy.patrolCenter = house.enemySpawn;
            enemy.giveUpDistance = house.giveUp;
            var skins = enemy.GetComponentsInChildren<SkinnedMeshRenderer>();
            foreach (var sk in skins) { sk.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; sk.receiveShadows = false; }
            AddBlobShadow(enemy.transform);
            CreateGameRoot(player, cam, sun, null, house.mainDoor, enemy, navMesh, faceLight);

            var game = Object.FindFirstObjectByType<GameRoot>();
            var lighting = game.gameObject.AddComponent<HouseLighting>();
            lighting.data = house.data;
            lighting.viewer = cam.transform;
            lighting.dynamicRenderers = skins;
            lighting.probes = house.probes;
            Debug.Log("[PROTO] house scene built");
        }

        static void AddBlobShadow(Transform enemy)
        {
            string tex = Gen + "/Textures/blob_shadow.png";
            var img = new Texture2D(64, 64, TextureFormat.RGBA32, false);
            for (int y = 0; y < 64; y++)
                for (int x = 0; x < 64; x++)
                {
                    float dx = (x + 0.5f) / 32f - 1f, dy = (y + 0.5f) / 32f - 1f;
                    float d = Mathf.Sqrt(dx * dx + dy * dy);
                    float v = Mathf.Clamp01(1f - d);
                    v = v * v * (3f - 2f * v);
                    img.SetPixel(x, y, new Color(v, v, v, 1f));
                }
            System.IO.File.WriteAllBytes(tex, img.EncodeToPNG());
            Texture2D mask = ProtoTextures.Import(tex, false, false, false, 1);
            var mat = new Material(Shader.Find("GridProto/ContactShadow"));
            mat.SetTexture("_MainTex", mask);
            Save(mat, "BlobShadow");
            var mesh = new Mesh { name = "blob" };
            mesh.vertices = new[] { new Vector3(-0.5f, 0f, -0.5f), new Vector3(-0.5f, 0f, 0.5f), new Vector3(0.5f, 0f, 0.5f), new Vector3(0.5f, 0f, -0.5f) };
            mesh.uv = new[] { new Vector2(0, 0), new Vector2(0, 1), new Vector2(1, 1), new Vector2(1, 0) };
            mesh.colors = new[] { new Color(1, 1, 1, 0.62f), new Color(1, 1, 1, 0.62f), new Color(1, 1, 1, 0.62f), new Color(1, 1, 1, 0.62f) };
            mesh.triangles = new[] { 0, 1, 2, 0, 2, 3 };
            mesh.RecalculateNormals();
            mesh.RecalculateBounds();
            SaveMesh(mesh);
            var blob = new GameObject("Enemy Blob Shadow");
            blob.AddComponent<MeshFilter>().sharedMesh = mesh;
            var r = blob.AddComponent<MeshRenderer>();
            r.sharedMaterial = mat;
            r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            r.receiveShadows = false;
            r.lightProbeUsage = UnityEngine.Rendering.LightProbeUsage.Off;
            r.reflectionProbeUsage = UnityEngine.Rendering.ReflectionProbeUsage.Off;
            var follow = enemy.gameObject.AddComponent<BlobShadow>();
            follow.target = enemy;
            follow.blob = blob.transform;
        }

        // ------------------------------------------------------------------ helpers

        /// <summary>Solid block with a collider; grid lines line up with the floor unless rotated.</summary>
        static GameObject Block(string name, Vector3 center, Vector3 size, Material mat, float rotY, Transform parent,
                                bool contactShadow = true, int layer = 0)
        {
            bool aligned = Mathf.Approximately(rotY, 0f);
            Mesh mesh = SaveMesh(MeshGen.Box(name, size, aligned ? center : Vector3.zero, Tile));
            GameObject go = MakeRenderer(name, mesh, mat, center, rotY, parent);
            var box = go.AddComponent<BoxCollider>();
            box.size = size;
            go.layer = layer;
            MarkStatic(go);
            if (contactShadow && center.y - size.y * 0.5f < 0.05f)
            {
                float margin = Mathf.Clamp(0.22f + size.y * 0.14f, 0.28f, 1.1f);
                MeshGen.AddContactShadow(contactShadows, new Vector3(center.x, 0.006f, center.z), size.x * 0.5f, size.z * 0.5f, rotY, margin, 0.5f);
            }
            return go;
        }

        /// <summary>Block standing on the room's floor slab (contact shadow drawn on the slab).</summary>
        static void InteriorBlock(string name, Vector3 center, Vector3 size, Material mat, float rotY, Transform parent)
        {
            Block(name, center, size, mat, rotY, parent, false, InteriorLayer);
            MeshGen.AddContactShadow(contactShadows, new Vector3(center.x, 0.046f, center.z), size.x * 0.5f, size.z * 0.5f, rotY, 0.35f, 0.45f);
        }

        /// <summary>Thin decorative piece without a collider.</summary>
        static void Trim(string name, Vector3 center, Vector3 size, Transform parent)
        {
            Mesh mesh = SaveMesh(MeshGen.Box(name, size, Vector3.zero, 1f));
            GameObject go = MakeRenderer(name, mesh, matTrim, center, 0f, parent);
            go.layer = InteriorLayer;
            MarkStatic(go);
        }

        /// <summary>Small moving or decorative part (no collider, not static).</summary>
        static void Part(string name, Transform parent, Vector3 localPosition, Vector3 size, Material mat)
        {
            Mesh mesh = SaveMesh(MeshGen.Box(name, size, Vector3.zero, 1f));
            GameObject go = MakeRenderer(name, mesh, mat, Vector3.zero, 0f, parent);
            go.transform.localPosition = localPosition;
            go.layer = InteriorLayer;
        }

        static GameObject MakeRenderer(string name, Mesh mesh, Material mat, Vector3 position, float rotY, Transform parent)
        {
            var go = new GameObject(name);
            if (parent != null) go.transform.SetParent(parent, false);
            go.transform.position = position;
            go.transform.rotation = Quaternion.Euler(0f, rotY, 0f);
            go.AddComponent<MeshFilter>().sharedMesh = mesh;
            var r = go.AddComponent<MeshRenderer>();
            r.sharedMaterial = mat;
            r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.On;
            r.receiveShadows = true;
            return go;
        }

        static Mesh SaveMesh(Mesh mesh)
        {
            meshCount++;
            string safeName = mesh.name.Replace("/", "_").Replace("\\", "_");
            string path = Gen + "/Meshes/" + meshCount.ToString("000") + "_" + safeName + ".asset";
            AssetDatabase.CreateAsset(mesh, path);
            return mesh;
        }

        static void MarkStatic(GameObject go)
        {
            GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.BatchingStatic);
        }

        static void EnsureFolder(string parent, string name)
        {
            if (!AssetDatabase.IsValidFolder(parent + "/" + name)) AssetDatabase.CreateFolder(parent, name);
        }

        static void ClearFolder(string folder)
        {
            string[] guids = AssetDatabase.FindAssets("", new[] { folder });
            var paths = new List<string>();
            foreach (string guid in guids) paths.Add(AssetDatabase.GUIDToAssetPath(guid));
            foreach (string path in paths) AssetDatabase.DeleteAsset(path);
        }
    }
}

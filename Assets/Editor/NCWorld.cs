using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using UnityEngine.SceneManagement;

namespace NightClass.EditorTools
{
    /// <summary>
    /// Builds the Night Class scene from code: the school (NCWorldLevel), furniture and puzzles
    /// (NCWorldProps), the teacher (NCWorldTeacher) and the game systems (this file).
    /// Static geometry is merged per room and material to keep draw calls low on phones.
    /// </summary>
    public static partial class NCWorld
    {
        public const string ScenePath = "Assets/Scenes/NightClass.unity";
        const int LayerDoor = 9, LayerProp = 10, LayerPlayer = 11, LayerTeacher = 12, LayerTrigger = 13;

        static Dictionary<string, MeshBuilder> builders;
        static Dictionary<string, Material> builderMats;
        static Transform root, geoRoot, colRoot, objRoot, lightRoot, logicRoot, templRoot;
        static int lightCount, colliderCount;

        static void Log(string m) { Debug.Log("[RF-BUILD] " + m); }

        public static void Build()
        {
            NCMats.Reset();
            NCBuild.EnsureFolder("Assets/Scenes");
            builders = new Dictionary<string, MeshBuilder>();
            builderMats = new Dictionary<string, Material>();
            lightCount = colliderCount = 0;
            Scene scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            root = new GameObject("School").transform;
            geoRoot = Child(root, "Geometry");
            colRoot = Child(root, "Colliders");
            objRoot = Child(root, "Objects");
            lightRoot = Child(root, "Lights");
            logicRoot = Child(root, "Logic");
            templRoot = Child(root, "Templates");

            CreateMaterials();
            BuildLevel();
            BuildProps();
            BuildTeacher();
            BuildSystems();
            FlushGeometry();
            SetupLighting();
            NCMats.Report();
            ReportModels();

            EditorSceneManager.SaveScene(scene, ScenePath);
            EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(ScenePath, true) };
            AssetDatabase.SaveAssets();
            Log("scene saved: " + builders.Count + " merged meshes, " + colliderCount + " colliders, " + lightCount + " lights");
        }

        // ------------------------------------------------------------------ helpers
        static Transform Child(Transform parent, string name)
        {
            var go = new GameObject(name);
            go.transform.SetParent(parent, false);
            return go.transform;
        }

        static MeshBuilder G(string group, Material mat)
        {
            string key = group + "|" + mat.name;
            MeshBuilder b;
            if (!builders.TryGetValue(key, out b))
            {
                b = new MeshBuilder { uvScale = NCMats.UVScale(mat) };
                builders[key] = b;
                builderMats[key] = mat;
            }
            return b;
        }

        /// <summary>Static box merged into the room mesh, with an optional collider.</summary>
        static void Box(string group, Material mat, Vector3 center, Vector3 size, bool collider = true, Surface? surface = null, float yaw = 0f)
        {
            MeshBuilder b = G(group, mat);
            b.m = Matrix4x4.TRS(center, Quaternion.Euler(0f, yaw, 0f), Vector3.one);
            b.Box(Vector3.zero, size);
            b.m = Matrix4x4.identity;
            if (collider) Collider(center, size, yaw, surface);
        }

        static void Draw(string group, Material mat, Matrix4x4 m, Action<MeshBuilder> draw)
        {
            MeshBuilder b = G(group, mat);
            b.m = m;
            draw(b);
            b.m = Matrix4x4.identity;
        }

        static BoxCollider Collider(Vector3 center, Vector3 size, float yaw = 0f, Surface? surface = null, int layer = 0)
        {
            var go = new GameObject("c");
            go.transform.SetParent(colRoot, false);
            go.transform.position = center;
            go.transform.rotation = Quaternion.Euler(0f, yaw, 0f);
            go.layer = layer;
            go.isStatic = layer == 0;
            var bc = go.AddComponent<BoxCollider>();
            bc.size = size;
            if (surface.HasValue) go.AddComponent<SurfaceTag>().surface = surface.Value;
            colliderCount++;
            return bc;
        }

        static void FlushGeometry()
        {
            int verts = 0;
            foreach (KeyValuePair<string, MeshBuilder> kv in builders)
            {
                if (!kv.Value.HasGeometry) continue;
                string name = kv.Key.Replace('|', '_');
                Mesh mesh = kv.Value.ToMesh(name);
                verts += mesh.vertexCount;
                var go = new GameObject(name);
                go.transform.SetParent(geoRoot, false);
                go.AddComponent<MeshFilter>().sharedMesh = mesh;
                var mr = go.AddComponent<MeshRenderer>();
                mr.sharedMaterial = builderMats[kv.Key];
                mr.shadowCastingMode = ShadowCastingMode.Off;
                mr.receiveShadows = false;
                GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccluderStatic | StaticEditorFlags.OccludeeStatic);
            }
            Log("geometry: " + builders.Count + " meshes, " + verts + " vertices");
        }

        /// <summary>A separate (movable) object made of mesh parts, one child per material.</summary>
        static GameObject Obj(string name, Transform parent, Vector3 pos, Quaternion rot)
        {
            var go = new GameObject(name);
            go.transform.SetParent(parent != null ? parent : objRoot, false);
            go.transform.position = pos;
            go.transform.rotation = rot;
            return go;
        }

        static MeshRenderer Part(Transform parent, string name, Material mat, Action<MeshBuilder> draw, bool castShadows = false)
        {
            var b = new MeshBuilder { uvScale = NCMats.UVScale(mat) };
            draw(b);
            var go = new GameObject(name);
            go.transform.SetParent(parent, false);
            go.layer = parent.gameObject.layer;
            go.AddComponent<MeshFilter>().sharedMesh = b.ToMesh(name);
            var mr = go.AddComponent<MeshRenderer>();
            mr.sharedMaterial = mat;
            mr.shadowCastingMode = castShadows ? ShadowCastingMode.On : ShadowCastingMode.Off;
            mr.receiveShadows = false;
            return mr;
        }

        static Light PointLight(Transform parent, Vector3 pos, Color color, float intensity, float range, string name = "Light")
        {
            var go = new GameObject(name);
            go.transform.SetParent(parent != null ? parent : lightRoot, false);
            go.transform.position = pos;
            var l = go.AddComponent<Light>();
            l.type = LightType.Point;
            l.color = color;
            l.intensity = intensity;
            l.range = range;
            l.shadows = LightShadows.None;
            l.renderMode = LightRenderMode.Auto;
            lightCount++;
            return l;
        }

        static Light SpotLight(Transform parent, Vector3 pos, Quaternion rot, Color color, float intensity, float range, float angle)
        {
            var go = new GameObject("Spot");
            go.transform.SetParent(parent != null ? parent : lightRoot, false);
            go.transform.position = pos;
            go.transform.rotation = rot;
            var l = go.AddComponent<Light>();
            l.type = LightType.Spot;
            l.color = color;
            l.intensity = intensity;
            l.range = range;
            l.spotAngle = angle;
            l.innerSpotAngle = angle * 0.4f;
            l.shadows = LightShadows.None;
            lightCount++;
            return l;
        }

        static GameObject Trigger(string name, Vector3 center, Vector3 size, Transform parent = null)
        {
            var go = new GameObject(name);
            go.transform.SetParent(parent != null ? parent : logicRoot, false);
            go.transform.position = center;
            go.layer = LayerTrigger;
            var bc = go.AddComponent<BoxCollider>();
            bc.isTrigger = true;
            bc.size = size;
            return go;
        }

        static Transform Point(string name, Vector3 pos, float yaw = 0f, float pitch = 0f, Transform parent = null)
        {
            var go = new GameObject(name);
            go.transform.SetParent(parent != null ? parent : logicRoot, false);
            go.transform.position = pos;
            go.transform.rotation = Quaternion.Euler(pitch, yaw, 0f);
            return go.transform;
        }

        static void SetLayer(GameObject go, int layer)
        {
            go.layer = layer;
            foreach (Transform c in go.transform) SetLayer(c.gameObject, layer);
        }

        // ------------------------------------------------------------------ particles
        static ParticleSystem Particles(Transform parent, string name, Vector3 localPos, Material mat, bool playOnAwake,
                                        float rate, float lifetime, float speed, float size, Color c0, Color c1,
                                        float coneAngle, float radius, float gravity = 0f, int max = 120, bool world = true)
        {
            var go = new GameObject(name);
            go.transform.SetParent(parent, false);
            go.transform.localPosition = localPos;
            go.transform.localRotation = Quaternion.Euler(-90f, 0f, 0f);
            var ps = go.AddComponent<ParticleSystem>();
            ps.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            var main = ps.main;
            main.playOnAwake = playOnAwake;
            main.loop = true;
            main.duration = 2f;
            main.startLifetime = new ParticleSystem.MinMaxCurve(lifetime * 0.6f, lifetime);
            main.startSpeed = new ParticleSystem.MinMaxCurve(speed * 0.6f, speed);
            main.startSize = new ParticleSystem.MinMaxCurve(size * 0.6f, size);
            main.startRotation = new ParticleSystem.MinMaxCurve(0f, Mathf.PI * 2f);
            main.startColor = c0;
            main.gravityModifier = gravity;
            main.maxParticles = max;
            main.simulationSpace = world ? ParticleSystemSimulationSpace.World : ParticleSystemSimulationSpace.Local;
            var em = ps.emission;
            em.rateOverTime = rate;
            var sh = ps.shape;
            sh.shapeType = ParticleSystemShapeType.Cone;
            sh.angle = coneAngle;
            sh.radius = radius;
            var col = ps.colorOverLifetime;
            col.enabled = true;
            var g = new Gradient();
            g.SetKeys(new[] { new GradientColorKey(c0, 0f), new GradientColorKey(c1, 1f) },
                      new[] { new GradientAlphaKey(0f, 0f), new GradientAlphaKey(c0.a, 0.15f), new GradientAlphaKey(c1.a, 0.6f), new GradientAlphaKey(0f, 1f) });
            col.color = g;
            var sz = ps.sizeOverLifetime;
            sz.enabled = true;
            sz.size = new ParticleSystem.MinMaxCurve(1f, AnimationCurve.Linear(0f, 1f, 1f, 0.5f));
            var rot = ps.rotationOverLifetime;
            rot.enabled = true;
            rot.z = new ParticleSystem.MinMaxCurve(-1f, 1f);
            var r = go.GetComponent<ParticleSystemRenderer>();
            r.sharedMaterial = mat;
            r.renderMode = ParticleSystemRenderMode.Billboard;
            r.shadowCastingMode = ShadowCastingMode.Off;
            r.receiveShadows = false;
            r.maxParticleSize = 1.5f;
            return ps;
        }

        static ParticleSystem Fire(Transform parent, Vector3 localPos, float scale, bool play = true)
        {
            ParticleSystem f = Particles(parent, "Fire", localPos, mFire, play, 28f * scale, 0.9f, 0.9f * Mathf.Sqrt(scale), 0.5f * scale,
                new Color(1f, 0.62f, 0.25f, 0.9f), new Color(0.8f, 0.15f, 0.04f, 0.4f), 8f, 0.12f * scale, -0.05f, 150);
            return f;
        }

        static ParticleSystem Smoke(Transform parent, Vector3 localPos, float scale, bool play = true)
        {
            return Particles(parent, "Smoke", localPos, mSmoke, play, 6f * scale, 3.2f, 0.6f, 0.9f * scale,
                new Color(0.2f, 0.2f, 0.2f, 0.35f), new Color(0.1f, 0.1f, 0.1f, 0f), 12f, 0.2f * scale, -0.02f, 80);
        }

        static ParticleSystem BurstOnce(ParticleSystem ps, int count)
        {
            var main = ps.main;
            main.loop = false;
            main.duration = 0.4f;
            var em = ps.emission;
            em.rateOverTime = 0f;
            em.SetBursts(new[] { new ParticleSystem.Burst(0f, (short)count) });
            return ps;
        }

        // ------------------------------------------------------------------ assets
        static T A<T>(string path) where T : UnityEngine.Object { return AssetDatabase.LoadAssetAtPath<T>(path); }
        static AudioClip Clip(string name) { return A<AudioClip>("Assets/Art/Audio/" + name + ".wav"); }
        static AudioClip[] Clips(string prefix, int n)
        {
            var list = new List<AudioClip>();
            for (int i = 0; i < n; i++)
            {
                AudioClip c = Clip(prefix + i);
                if (c != null) list.Add(c);
            }
            return list.ToArray();
        }
        static Sprite Spr(string name) { return A<Sprite>("Assets/Art/UI/" + name + ".png"); }

        static void FillAssets(GameAssets ga)
        {
            ga.uiFont = A<Font>("Assets/Art/Fonts/Barlow-Medium.ttf");
            ga.uiFontBold = A<Font>("Assets/Art/Fonts/Barlow-SemiBold.ttf");
            ga.titleFont = A<Font>("Assets/Art/Fonts/Creepster-Regular.ttf");
            ga.chalkFont = A<Font>("Assets/Art/Fonts/CabinSketch-Bold.ttf");
            ga.circle = Spr("circle"); ga.ring = Spr("ring"); ga.rounded = Spr("rounded"); ga.glow = Spr("glow");
            ga.vignette = Spr("vignette"); ga.dot = Spr("dot");
            ga.iconHand = Spr("icon_hand"); ga.iconDrop = Spr("icon_drop"); ga.iconCrouch = Spr("icon_crouch"); ga.iconStand = Spr("icon_stand");
            ga.iconHide = Spr("icon_hide"); ga.iconUnhide = Spr("icon_unhide"); ga.iconFire = Spr("icon_fire"); ga.iconJump = Spr("icon_jump");
            ga.iconPause = Spr("icon_pause");
            ga.itemMainKey = Spr("item_mainkey"); ga.itemHammer = Spr("item_hammer"); ga.itemTorch = Spr("item_torch"); ga.itemNote = Spr("item_note");
            ga.itemSafeKey = Spr("item_safekey"); ga.itemSpring = Spr("item_spring"); ga.itemDynamite = Spr("item_dynamite");
            ga.uiClick = Clip("ui_click"); ga.pickup = Clip("pickup"); ga.drop = Clip("drop"); ga.doorOpen = Clip("door_open");
            ga.doorClose = Clip("door_close"); ga.doorLocked = Clip("door_locked"); ga.plankBreak = Clip("plank_break");
            ga.fireWhoosh = Clip("fire_whoosh"); ga.fireLoop = Clip("fire_loop"); ga.water = Clip("water"); ga.steam = Clip("steam");
            ga.keypadBeep = Clip("keypad_beep"); ga.keypadOk = Clip("keypad_ok"); ga.keypadNo = Clip("keypad_no"); ga.safeOpen = Clip("safe_open");
            ga.explosion = Clip("explosion"); ga.fuse = Clip("fuse"); ga.eat = Clip("eat"); ga.bell = Clip("bell"); ga.motor = Clip("motor");
            ga.trapdoor = Clip("trapdoor"); ga.burnScream = Clip("burn_scream"); ga.scream = Clip("scream"); ga.heartbeat = Clip("heartbeat");
            ga.chaseLoop = Clip("chase_loop"); ga.ambientLoop = Clip("ambient_loop"); ga.teacherHum = Clip("teacher_hum");
            ga.jump = Clip("jump"); ga.land = Clip("land"); ga.rulerHit = Clip("ruler_hit"); ga.lightPop = Clip("light_pop");
            ga.musicBox = Clip("music_box"); ga.slam = Clip("slam");
            ga.stepConcrete = Clips("step_concrete_", 4); ga.stepWood = Clips("step_wood_", 4); ga.stepTile = Clips("step_tile_", 4);
            ga.stepMetal = Clips("step_metal_", 3); ga.teacherSteps = Clips("teacher_step_", 3); ga.ambientOneShots = Clips("ambient_", 6);
            ga.fireMat = mFire; ga.smokeMat = mSmoke; ga.waterMat = mWater; ga.sparkMat = mSpark; ga.dustMat = mDust;
            ga.fogColor = new Color(0.03f, 0.038f, 0.05f);
            ga.fogDensity = 0.014f;
            ga.fogDensityHard = 0.05f;
            ga.ambientColor = new Color(0.2f, 0.21f, 0.2f);
            int missingClips = 0;
            foreach (var f in typeof(GameAssets).GetFields())
                if (f.FieldType == typeof(AudioClip) && f.GetValue(ga) == null) missingClips++;
            Log("assets: fonts " + (ga.uiFont != null) + "/" + (ga.titleFont != null) + "/" + (ga.chalkFont != null) +
                ", hand icon " + (ga.iconHand != null) + ", missing clips " + missingClips + ", steps " + ga.stepConcrete.Length);
        }

        // ------------------------------------------------------------------ systems
        static void BuildSystems()
        {
            var sys = new GameObject("Game");
            GameAssets ga = sys.AddComponent<GameAssets>();
            FillAssets(ga);
            QualityManager qm = sys.AddComponent<QualityManager>();
            NavBaker nav = sys.AddComponent<NavBaker>();
            nav.layerMask = ~((1 << LayerDoor) | (1 << LayerProp) | (1 << LayerPlayer) | (1 << LayerTeacher) | (1 << LayerTrigger));
            nav.bounds = new Bounds(new Vector3(0f, -1.5f, -2f), new Vector3(80f, 9f, 40f));
            TouchControls tc = sys.AddComponent<TouchControls>();
            sys.AddComponent<AmbientSounds>();
            NCGame game = sys.AddComponent<NCGame>();
            UIRoot ui = sys.AddComponent<UIRoot>();

            // post-processing
            var volGo = new GameObject("PostProcessing");
            var vol = volGo.AddComponent<Volume>();
            vol.isGlobal = true;
            vol.priority = 1f;
            vol.sharedProfile = NCRenderSetup.CreateVolumeProfile();
            qm.volume = vol;

            // camera
            var camGo = new GameObject("Main Camera");
            camGo.tag = "MainCamera";
            Camera cam = camGo.AddComponent<Camera>();
            cam.nearClipPlane = 0.05f;
            cam.farClipPlane = 70f;
            cam.fieldOfView = 64f;
            cam.clearFlags = CameraClearFlags.SolidColor;
            cam.backgroundColor = new Color(0.008f, 0.012f, 0.022f);
            cam.allowMSAA = true;
            cam.allowHDR = true;
            camGo.AddComponent<AudioListener>();
            var cd = camGo.AddComponent<UniversalAdditionalCameraData>();
            cd.renderPostProcessing = true;
            cd.antialiasing = AntialiasingMode.None;
            cd.dithering = true;
            cd.renderShadows = false;
            camGo.transform.position = new Vector3(-7f, 1.6f, 7f);

            // player
            var pGo = new GameObject("Player");
            pGo.layer = LayerPlayer;
            pGo.transform.position = playerSpawn.position;
            var cc = pGo.AddComponent<CharacterController>();
            cc.radius = 0.3f;
            cc.height = 1.75f;
            cc.center = new Vector3(0f, 0.875f, 0f);
            cc.slopeLimit = 50f;
            cc.stepOffset = 0.38f;
            cc.skinWidth = 0.03f;
            cc.minMoveDistance = 0f;
            FPController fp = pGo.AddComponent<FPController>();
            Transform head = Child(pGo.transform, "Head");
            head.localPosition = new Vector3(0f, 1.63f, 0f);
            fp.head = head;
            Inventory inv = pGo.AddComponent<Inventory>();
            pGo.AddComponent<Interactor>();
            BuildViewModels(camGo.transform, inv);
            BuildTemplates(inv);

            game.player = fp;
            game.inventory = inv;
            game.teacher = teacherAI;
            game.ui = ui;
            game.mainCam = cam;
            game.playerSpawn = playerSpawn;
            game.introCam = introCam;
            game.menuCamPoints = menuCam.ToArray();
            game.endingCamPoints = endingCam.ToArray();
            game.navBaker = nav;
        }

        static void SetupLighting()
        {
            Color amb = new Color(0.2f, 0.21f, 0.2f);
            RenderSettings.ambientMode = AmbientMode.Flat;
            RenderSettings.ambientLight = amb;
            RenderSettings.ambientIntensity = 1f;
            var sh = new SphericalHarmonicsL2();
            sh.AddAmbientLight(amb);
            RenderSettings.ambientProbe = sh;   // no lighting bake in batch mode: set the probe directly
            RenderSettings.fog = true;
            RenderSettings.fogMode = FogMode.ExponentialSquared;
            RenderSettings.fogColor = new Color(0.03f, 0.038f, 0.05f);
            RenderSettings.fogDensity = 0.014f;
            RenderSettings.skybox = null;
            RenderSettings.sun = null;
            RenderSettings.defaultReflectionMode = DefaultReflectionMode.Custom;
            RenderSettings.reflectionIntensity = 0f;
        }
    }
}

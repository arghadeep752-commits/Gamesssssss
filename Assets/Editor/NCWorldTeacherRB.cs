using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEditor.Animations;
using UnityEngine;
using UnityEngine.AI;
using UnityEngine.Rendering;

namespace NightClass.EditorTools
{
    /// <summary>
    /// The realistic teacher: Microsoft Rocketbox "Business_Female_02" (MIT licence) — a rigged older
    /// woman with glasses and 49 facial blendshapes — driven by Rocketbox motion-capture clips through a
    /// Humanoid animator (walk / run / angry idle / look around / angry gesture / nervous).
    /// TeacherRig adds the head tracking, the stern face, the scream (jaw open) and the lunge on top.
    /// </summary>
    public static partial class NCWorld
    {
        const string RBDir = "Assets/Art/Teacher/Rocketbox/";

        static AnimationClip RBClip(string name, bool loop)
        {
            string path = RBDir + "Anims/" + name + ".fbx";
            var mi = AssetImporter.GetAtPath(path) as ModelImporter;
            if (mi == null) return null;
            ModelImporterClipAnimation[] clips = mi.defaultClipAnimations;
            if (clips == null || clips.Length == 0) return null;
            foreach (var c in clips)
            {
                c.loopTime = loop;
                c.loopPose = loop;
                c.lockRootRotation = true;
                c.lockRootHeightY = true;
                c.lockRootPositionXZ = true;
                c.keepOriginalOrientation = true;
                c.keepOriginalPositionY = true;
                c.keepOriginalPositionXZ = true;
                c.name = "rb_" + name;
            }
            mi.clipAnimations = new[] { clips[0] };
            mi.SaveAndReimport();
            return AssetDatabase.LoadAllAssetsAtPath(path).OfType<AnimationClip>().FirstOrDefault(a => !a.name.StartsWith("__preview__"));
        }

        static void AddT(AnimatorState from, AnimatorState to, string p, bool on, float dur)
        {
            AnimatorStateTransition t = from.AddTransition(to);
            t.hasExitTime = false;
            t.duration = dur;
            t.AddCondition(on ? AnimatorConditionMode.If : AnimatorConditionMode.IfNot, 0f, p);
        }

        static void AddAnyT(AnimatorStateMachine sm, AnimatorState to, string p, float dur)
        {
            AnimatorStateTransition t = sm.AddAnyStateTransition(to);
            t.hasExitTime = false;
            t.duration = dur;
            t.canTransitionToSelf = false;
            t.AddCondition(AnimatorConditionMode.If, 0f, p);
        }

        static AnimatorController TeacherController(AnimationClip idle, AnimationClip walk, AnimationClip run, AnimationClip look, AnimationClip attack, AnimationClip burn)
        {
            string path = "Assets/Generated/TeacherAnimator.controller";
            AssetDatabase.DeleteAsset(path);
            AnimatorController c = AnimatorController.CreateAnimatorControllerAtPath(path);
            c.AddParameter("Speed", AnimatorControllerParameterType.Float);
            c.AddParameter("Search", AnimatorControllerParameterType.Bool);
            c.AddParameter("Attack", AnimatorControllerParameterType.Bool);
            c.AddParameter("Burn", AnimatorControllerParameterType.Bool);
            AnimatorStateMachine sm = c.layers[0].stateMachine;
            BlendTree tree;
            AnimatorState loco = c.CreateBlendTreeInController("Locomotion", out tree, 0);
            tree.blendType = BlendTreeType.Simple1D;
            tree.blendParameter = "Speed";
            tree.useAutomaticThresholds = false;
            tree.AddChild(idle, 0f);
            tree.AddChild(walk, 1.35f);
            tree.AddChild(run, 3.4f);
            sm.defaultState = loco;
            AnimatorState search = sm.AddState("Search");
            search.motion = look != null ? look : idle;
            AnimatorState atk = sm.AddState("Attack");
            atk.motion = attack != null ? attack : idle;
            AnimatorState brn = sm.AddState("Burn");
            brn.motion = burn != null ? burn : idle;
            AddT(loco, search, "Search", true, 0.35f);
            AddT(search, loco, "Search", false, 0.3f);
            AddAnyT(sm, atk, "Attack", 0.12f);
            AddT(atk, loco, "Attack", false, 0.3f);
            AddAnyT(sm, brn, "Burn", 0.2f);
            AddT(brn, loco, "Burn", false, 0.4f);
            EditorUtility.SetDirty(c);
            return c;
        }

        static Material RBMat(string key, string color, string normal, float smooth, bool cutout, bool twoSided)
        {
            Texture2D albedo = NCMats.Tex(RBDir + "Textures/" + color);
            Material m = NCMats.Lit(key, null, Color.white, smooth, 0f, 1f, null, 1f, albedo);
            if (normal != null)
            {
                Texture2D n = NCMats.Tex(RBDir + "Textures/" + normal);
                if (n != null)
                {
                    m.SetTexture("_BumpMap", n);
                    m.SetFloat("_BumpScale", 1f);
                    m.EnableKeyword("_NORMALMAP");
                }
            }
            if (cutout)
            {
                m.SetFloat("_AlphaClip", 1f);
                m.SetFloat("_Cutoff", 0.42f);
                m.EnableKeyword("_ALPHATEST_ON");
                m.SetOverrideTag("RenderType", "TransparentCutout");
                m.renderQueue = (int)RenderQueue.AlphaTest;
            }
            if (twoSided) m.SetFloat("_Cull", 0f);
            EditorUtility.SetDirty(m);
            return m;
        }

        static Transform FindBone(Transform root, string name)
        {
            foreach (Transform t in root.GetComponentsInChildren<Transform>(true))
                if (t.name == name) return t;
            return null;
        }

        static bool BuildRocketboxTeacher()
        {
            string fbxPath = RBDir + "Business_Female_02_facial.fbx";
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(fbxPath);
            Avatar avatar = AssetDatabase.LoadAllAssetsAtPath(fbxPath).OfType<Avatar>().FirstOrDefault();
            if (model == null || avatar == null || !avatar.isValid || !avatar.isHuman)
            {
                Log("teacher: Rocketbox model not usable (model " + (model != null) + ", avatar " + (avatar != null && avatar.isValid && avatar.isHuman) + "), using the procedural teacher");
                return false;
            }
            AnimationClip walk = RBClip("walk", true), run = RBClip("run", true), idle = RBClip("idle", true);
            AnimationClip look = RBClip("look", true), attack = RBClip("attack", true), burn = RBClip("burn", true);
            if (walk == null || run == null || idle == null)
            {
                Log("teacher: Rocketbox animations missing, using the procedural teacher");
                return false;
            }
            AnimatorController ctrl = TeacherController(idle, walk, run, look, attack, burn);

            Vector3 spawnPos = teacherSpawn != null ? teacherSpawn.position : new Vector3(0.5f, 0f, 8.5f);
            var go = new GameObject("Teacher");
            go.transform.position = spawnPos;
            go.transform.rotation = Quaternion.identity;
            go.layer = LayerTeacher;
            var body = (GameObject)Object.Instantiate(model);
            body.name = "Body";
            body.transform.SetParent(go.transform, false);
            body.transform.localPosition = Vector3.zero;
            body.transform.localRotation = Quaternion.identity;

            // real textures, graded older and paler by tools/process_assets.py
            Material mBody = RBMat("teacher_rb_body", "f015_body_color", "f015_body_normal", 0.25f, false, false);
            Material mHead = RBMat("teacher_rb_head", "f015_head_color", "f015_head_normal", 0.36f, false, false);
            Material mHair = RBMat("teacher_rb_hair", "f015_opacity_color", null, 0.3f, true, true);
            Material mGlass = RBMat("teacher_rb_glasses", "f015_glasses_opacity_color", null, 0.8f, true, true);
            var rends = new List<Renderer>();
            SkinnedMeshRenderer face = null;
            foreach (SkinnedMeshRenderer smr in body.GetComponentsInChildren<SkinnedMeshRenderer>(true))
            {
                string n = smr.name.ToLowerInvariant();
                if (n.Contains("lowpoly") || n.Contains("midpoly")) { smr.gameObject.SetActive(false); continue; }
                Material[] mats = smr.sharedMaterials;
                for (int i = 0; i < mats.Length; i++)
                {
                    string mn = (mats[i] != null ? mats[i].name : n).ToLowerInvariant();
                    if (mn.Contains("glasses")) mats[i] = mGlass;
                    else if (mn.Contains("opacity")) mats[i] = mHair;
                    else if (mn.Contains("head")) mats[i] = mHead;
                    else mats[i] = mBody;
                }
                smr.sharedMaterials = mats;
                smr.shadowCastingMode = ShadowCastingMode.Off;
                smr.receiveShadows = false;
                smr.updateWhenOffscreen = false;
                rends.Add(smr);
                if (smr.sharedMesh != null && smr.sharedMesh.blendShapeCount > 0 && (face == null || smr.sharedMesh.blendShapeCount > face.sharedMesh.blendShapeCount)) face = smr;
            }
            foreach (MeshRenderer mr in body.GetComponentsInChildren<MeshRenderer>(true)) { mr.shadowCastingMode = ShadowCastingMode.Off; rends.Add(mr); }

            Animator anim = body.GetComponent<Animator>();
            if (anim == null) anim = body.AddComponent<Animator>();
            anim.avatar = avatar;
            anim.runtimeAnimatorController = ctrl;
            anim.applyRootMotion = false;
            anim.cullingMode = AnimatorCullingMode.CullUpdateTransforms;

            Transform head = FindBone(body.transform, "Bip01 Head");
            Transform spine = FindBone(body.transform, "Bip01 Spine1") ?? FindBone(body.transform, "Bip01 Spine");
            Transform armL = FindBone(body.transform, "Bip01 L UpperArm");
            Transform armR = FindBone(body.transform, "Bip01 R UpperArm");
            Transform handR = FindBone(body.transform, "Bip01 R Hand");
            if (head == null) head = body.transform;
            if (spine == null) spine = body.transform;
            Bounds bb = RendBounds(body);
            Log("teacher: Rocketbox height " + bb.size.y.ToString("0.00") + " m, face blendshapes " + (face != null ? face.sharedMesh.blendShapeCount : 0));
            // she is a tall, imposing woman: about 1.78 m
            if (bb.size.y > 0.5f) body.transform.localScale = Vector3.one * (1.78f / bb.size.y);

            // the wooden ruler in her right hand (real wood texture)
            if (handR != null)
            {
                var ruler = new GameObject("Ruler");
                ruler.transform.SetParent(handR, false);
                ruler.transform.position = handR.position + go.transform.forward * 0.24f + Vector3.down * 0.03f;
                ruler.transform.rotation = Quaternion.LookRotation(go.transform.forward, Vector3.up);
                ruler.layer = LayerTeacher;
                Vector3 ls = ruler.transform.lossyScale;
                ruler.transform.localScale = new Vector3(1f / Mathf.Max(ls.x, 1e-4f), 1f / Mathf.Max(ls.y, 1e-4f), 1f / Mathf.Max(ls.z, 1e-4f));
                rends.Add(Part(ruler.transform, "Wood", mRuler, b => b.Box(Vector3.zero, new Vector3(0.036f, 0.006f, 0.6f))));
            }

            Vector3 fwd = go.transform.forward, up = Vector3.up;
            Vector3 faceCenter = head.position + up * 0.085f + fwd * 0.07f;

            TeacherRig rig = go.AddComponent<TeacherRig>();
            rig.animator = anim;
            rig.face = face;
            rig.headBone = head;
            rig.spineBone = spine;
            rig.armL = armL;
            rig.armR = armR;
            rig.tintable = rends.ToArray();
            var glowGo = new GameObject("EyeGlow");
            glowGo.transform.SetParent(head, true);
            glowGo.transform.position = faceCenter + fwd * 0.12f;
            Light glow = glowGo.AddComponent<Light>();
            glow.type = LightType.Point; glow.color = new Color(1f, 0.16f, 0.08f); glow.range = 0.9f; glow.intensity = 0.15f; glow.shadows = LightShadows.None;
            rig.eyeGlow = glow;

            NavMeshAgent agent = go.AddComponent<NavMeshAgent>();
            agent.radius = 0.3f;
            agent.height = 1.75f;
            agent.speed = 1.45f;
            agent.angularSpeed = 420f;
            agent.acceleration = 9f;
            agent.stoppingDistance = 0.25f;
            agent.obstacleAvoidanceType = ObstacleAvoidanceType.LowQualityObstacleAvoidance;
            agent.enabled = false;
            var cap = go.AddComponent<CapsuleCollider>();
            cap.isTrigger = true;
            cap.radius = 0.35f;
            cap.height = 1.75f;
            cap.center = new Vector3(0f, 0.875f, 0f);
            var rb = go.AddComponent<Rigidbody>();
            rb.isKinematic = true;
            rb.useGravity = false;

            TeacherAI ai = go.AddComponent<TeacherAI>();
            ai.rig = rig;
            ai.spawn = teacherSpawn;
            ai.patrolPoints = patrol.ToArray();
            var eye = new GameObject("Eye");
            eye.transform.SetParent(head, true);
            eye.transform.position = faceCenter + fwd * 0.03f;
            ai.eye = eye.transform;
            // jumpscare: a camera right in front of her face, looking at it (follows the head)
            var js = new GameObject("JumpscareCam");
            js.transform.SetParent(head, true);
            js.transform.position = faceCenter + fwd * 0.36f + up * 0.01f;
            js.transform.rotation = Quaternion.LookRotation(-fwd, up) * Quaternion.Euler(3f, 0f, 0f);
            ai.jumpscareCam = js.transform;
            var flGo = new GameObject("FaceLight");
            flGo.transform.SetParent(js.transform, true);
            flGo.transform.position = js.transform.position + Vector3.down * 0.16f + go.transform.right * 0.05f;
            Light fl = flGo.AddComponent<Light>();
            fl.type = LightType.Point; fl.color = new Color(0.8f, 0.9f, 1f); fl.range = 1.2f; fl.intensity = 1.8f; fl.shadows = LightShadows.None;
            fl.enabled = false;
            ai.faceLight = fl;
            ai.burnFire = Fire(spine, Vector3.zero, 0.9f, false);
            ai.burnSmoke = Smoke(head, new Vector3(0f, 0.1f, 0f), 0.8f, false);
            go.transform.rotation = Quaternion.Euler(0f, 180f, 0f);

            SetLayer(go, LayerTeacher);
            teacherAI = ai;
            Log("teacher built: Rocketbox (" + rends.Count + " renderers)");
            return true;
        }
    }
}

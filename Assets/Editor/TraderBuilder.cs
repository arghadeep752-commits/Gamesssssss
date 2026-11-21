using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace TradersMadness.EditorTools
{
    /// <summary>
    /// Builds Resources/Trader.prefab from the converted Rodin character (tools/unity/convert_assets.py):
    /// skinned mesh, skeleton and his moves (idle, walk, run, attack, taunt, look ...), already trimmed and walked in
    /// place. The moves become legacy animation clips.
    /// </summary>
    public static class TraderBuilder
    {
        public const string Folder = "Assets/Game/Trader";
        const string Out = "Assets/Generated/Trader";
        public const string PrefabPath = "Assets/Resources/Trader.prefab";

        public static bool Available { get { return File.Exists(Folder + "/trader.bytes"); } }

        static string Str(BinaryReader r)
        {
            int n = r.ReadInt32();
            return System.Text.Encoding.UTF8.GetString(r.ReadBytes(n));
        }

        static Texture2D Tex(string file)
        {
            string path = Folder + "/" + file;
            AssetRules.Ensure(path);
            return AssetDatabase.LoadAssetAtPath<Texture2D>(path);
        }

        static string FileFor(string key)
        {
            foreach (string ext in new[] { ".png", ".jpg" })
                if (File.Exists(Folder + "/trader_" + key + ext)) return "trader_" + key + ext;
            return null;
        }

        public static void Build()
        {
            if (!Available) throw new Exception("converted trader missing in " + Folder);
            if (!AssetDatabase.IsValidFolder("Assets/Generated")) AssetDatabase.CreateFolder("Assets", "Generated");
            if (AssetDatabase.IsValidFolder(Out)) AssetDatabase.DeleteAsset(Out);
            AssetDatabase.CreateFolder("Assets/Generated", "Trader");
            if (!AssetDatabase.IsValidFolder("Assets/Resources")) AssetDatabase.CreateFolder("Assets", "Resources");

            string fa = FileFor("albedo"), fn = FileFor("normal"), fm = FileFor("mr");
            Texture2D albedo = fa != null ? Tex(fa) : null;
            Texture2D normal = fn != null ? Tex(fn) : null;
            Texture2D mr = fm != null ? Tex(fm) : null;

            Shader sh = Shader.Find("TradersMadness/Character");
            if (sh == null) throw new Exception("TradersMadness/Character shader missing");
            var mat = new Material(sh) { name = "Trader" };
            if (albedo != null) mat.SetTexture("_MainTex", albedo);
            if (normal != null) mat.SetTexture("_BumpMap", normal);
            if (mr != null) mat.SetTexture("_MR", mr);
            AssetDatabase.CreateAsset(mat, Out + "/Trader.mat");

            var root = new GameObject("Trader");
            var model = new GameObject("Model");
            model.transform.SetParent(root.transform, false);
            var armature = new GameObject("Armature");
            armature.transform.SetParent(model.transform, false);
            var bodyGo = new GameObject("Body");
            bodyGo.transform.SetParent(model.transform, false);

            Mesh mesh;
            Transform[] bones;
            string[] paths;
            float scale, yOff;
            var clips = new List<AnimationClip>();
            var nat = new Dictionary<string, float>();
            using (var r = new BinaryReader(File.OpenRead(Folder + "/trader.bytes")))
            {
                if (r.ReadInt32() != 0x52445254 || r.ReadInt32() != 1) throw new Exception("unexpected trader.bytes format");
                int nv = r.ReadInt32();
                var pos = new Vector3[nv];
                var nrm = new Vector3[nv];
                var uv = new Vector2[nv];
                for (int i = 0; i < nv; i++) pos[i] = new Vector3(r.ReadSingle(), r.ReadSingle(), r.ReadSingle());
                for (int i = 0; i < nv; i++) nrm[i] = new Vector3(r.ReadSingle(), r.ReadSingle(), r.ReadSingle());
                for (int i = 0; i < nv; i++) uv[i] = new Vector2(r.ReadSingle(), r.ReadSingle());
                var bi = new int[nv * 4];
                for (int i = 0; i < nv * 4; i++) bi[i] = r.ReadInt32();
                var bw = new float[nv * 4];
                for (int i = 0; i < nv * 4; i++) bw[i] = r.ReadSingle();
                int ni = r.ReadInt32();
                var idx = new int[ni];
                for (int i = 0; i < ni; i++) idx[i] = r.ReadInt32();
                int nb = r.ReadInt32();
                bones = new Transform[nb];
                paths = new string[nb];
                var binds = new Matrix4x4[nb];
                for (int b = 0; b < nb; b++)
                {
                    string name = Str(r);
                    int parent = r.ReadInt32();
                    var t = new Vector3(r.ReadSingle(), r.ReadSingle(), r.ReadSingle());
                    var q = new Quaternion(r.ReadSingle(), r.ReadSingle(), r.ReadSingle(), r.ReadSingle());
                    var s = new Vector3(r.ReadSingle(), r.ReadSingle(), r.ReadSingle());
                    var m = new Matrix4x4();
                    for (int row = 0; row < 4; row++)
                        for (int col = 0; col < 4; col++)
                            m[row, col] = r.ReadSingle();
                    binds[b] = m;
                    var go = new GameObject(name);
                    Transform pt = parent >= 0 ? bones[parent] : armature.transform;
                    go.transform.SetParent(pt, false);
                    go.transform.localPosition = t;
                    go.transform.localRotation = q.normalized;
                    go.transform.localScale = s;
                    bones[b] = go.transform;
                    paths[b] = (parent >= 0 ? paths[parent] : "Armature") + "/" + name;
                }
                scale = r.ReadSingle();
                yOff = r.ReadSingle();

                var weights = new BoneWeight[nv];
                for (int i = 0; i < nv; i++)
                {
                    weights[i] = new BoneWeight
                    {
                        boneIndex0 = bi[i * 4], weight0 = bw[i * 4],
                        boneIndex1 = bi[i * 4 + 1], weight1 = bw[i * 4 + 1],
                        boneIndex2 = bi[i * 4 + 2], weight2 = bw[i * 4 + 2],
                        boneIndex3 = bi[i * 4 + 3], weight3 = bw[i * 4 + 3],
                    };
                }
                mesh = new Mesh { name = "Trader" };
                mesh.indexFormat = IndexFormat.UInt32;
                mesh.vertices = pos;
                mesh.normals = nrm;
                mesh.uv = uv;
                mesh.triangles = idx;
                mesh.boneWeights = weights;
                mesh.bindposes = binds;
                mesh.RecalculateTangents();
                mesh.RecalculateBounds();

                int nc = r.ReadInt32();
                for (int c = 0; c < nc; c++)
                {
                    string move = Str(r);
                    float length = r.ReadSingle();
                    bool loop = r.ReadInt32() != 0;
                    float natural = r.ReadSingle();
                    int frames = r.ReadInt32();
                    float fps = r.ReadSingle();
                    var P = new float[nb * frames * 3];
                    for (int i = 0; i < P.Length; i++) P[i] = r.ReadSingle();
                    var R = new float[nb * frames * 4];
                    for (int i = 0; i < R.Length; i++) R[i] = r.ReadSingle();
                    var clip = new AnimationClip { name = move, legacy = true, frameRate = fps };
                    clip.wrapMode = loop ? WrapMode.Loop : WrapMode.ClampForever;
                    for (int b = 0; b < nb; b++)
                    {
                        string[] pn = { "localPosition.x", "localPosition.y", "localPosition.z" };
                        for (int k = 0; k < 3; k++)
                        {
                            var keys = new Keyframe[frames];
                            for (int f = 0; f < frames; f++) keys[f] = new Keyframe(Mathf.Min(f / fps, length), P[(b * frames + f) * 3 + k]);
                            clip.SetCurve(paths[b], typeof(Transform), pn[k], Linear(keys));
                        }
                        string[] rn = { "localRotation.x", "localRotation.y", "localRotation.z", "localRotation.w" };
                        for (int k = 0; k < 4; k++)
                        {
                            var keys = new Keyframe[frames];
                            for (int f = 0; f < frames; f++) keys[f] = new Keyframe(Mathf.Min(f / fps, length), R[(b * frames + f) * 4 + k]);
                            clip.SetCurve(paths[b], typeof(Transform), rn[k], Linear(keys));
                        }
                    }
                    clip.EnsureQuaternionContinuity();
                    AssetDatabase.CreateAsset(clip, Out + "/" + move + ".anim");
                    clips.Add(clip);
                    nat[move] = natural;
                }
            }
            AssetDatabase.CreateAsset(mesh, Out + "/Trader.asset");

            model.transform.localRotation = Quaternion.Euler(0f, 180f, 0f);   // Rodin characters face +Z in glTF
            model.transform.localScale = Vector3.one * scale;
            model.transform.localPosition = new Vector3(0f, yOff, 0f);

            var skin = bodyGo.AddComponent<SkinnedMeshRenderer>();
            skin.sharedMesh = mesh;
            skin.bones = bones;
            skin.rootBone = bones.Length > 0 ? FindBone(bones, "Hips") ?? bones[0] : null;
            skin.sharedMaterial = mat;
            skin.quality = SkinQuality.Bone4;
            skin.updateWhenOffscreen = false;
            skin.shadowCastingMode = ShadowCastingMode.Off;
            skin.receiveShadows = false;
            skin.lightProbeUsage = LightProbeUsage.Off;
            skin.reflectionProbeUsage = ReflectionProbeUsage.Off;
            skin.localBounds = new Bounds(Vector3.zero, new Vector3(3f, 3f, 3f));

            var anim = model.AddComponent<Animation>();
            anim.playAutomatically = false;
            anim.cullingType = AnimationCullingType.AlwaysAnimate;
            // AddClip only changes the live state in the editor; SetAnimationClips is what gets saved in the prefab
            AnimationUtility.SetAnimationClips(anim, clips.ToArray());
            if (clips.Count > 0) anim.clip = clips[0];

            var rig = root.AddComponent<TraderRig>();
            rig.anim = anim;
            rig.body = skin;
            float v;
            if (nat.TryGetValue("walk", out v) && v > 0.1f) rig.walkNat = v;
            if (nat.TryGetValue("run", out v) && v > 0.1f) rig.runNat = v;

            AssetDatabase.DeleteAsset(PrefabPath);
            PrefabUtility.SaveAsPrefabAsset(root, PrefabPath);
            UnityEngine.Object.DestroyImmediate(root);
            AssetDatabase.SaveAssets();
            Debug.Log("[TM] trader built: " + mesh.vertexCount + " vertices, " + bones.Length + " bones, " + clips.Count
                      + " moves, scale " + scale.ToString("0.000") + ", walk " + rig.walkNat.ToString("0.00") + " m/s, run " + rig.runNat.ToString("0.00") + " m/s");
        }

        static Transform FindBone(Transform[] bones, string name)
        {
            foreach (Transform b in bones) if (b.name == name) return b;
            return null;
        }

        static AnimationCurve Linear(Keyframe[] keys)
        {
            var c = new AnimationCurve(keys);
            for (int i = 0; i < c.length; i++)
            {
                AnimationUtility.SetKeyLeftTangentMode(c, i, AnimationUtility.TangentMode.Linear);
                AnimationUtility.SetKeyRightTangentMode(c, i, AnimationUtility.TangentMode.Linear);
            }
            return c;
        }
    }
}

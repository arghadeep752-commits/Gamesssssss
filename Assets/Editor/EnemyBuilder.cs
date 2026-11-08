using System.IO;
using UnityEditor;
using UnityEngine;
using UnityEngine.AI;

namespace GridProto.EditorTools
{
    /// <summary>
    /// Builds the enemy ("Red Hooded Hollow") from the rigged mesh exported by the rigging step:
    /// Assets/Models/Enemy/RedHoodedHollow.bytes (vertices, normals, UVs, triangles, 4 bone weights per
    /// vertex and a 19-bone T-pose skeleton) plus its base colour texture.
    /// </summary>
    public static class EnemyBuilder
    {
        public const int EnemyLayer = 9;         // body collider
        public const int EnemyVisualLayer = 10;  // skinned mesh (the jumpscare light only lights this layer)
        const string MeshFile = "Assets/Models/Enemy/RedHoodedHollow.bytes";
        const string TextureFile = "Assets/Models/Enemy/RedHoodedHollow_BaseColor.jpg";

        public static EnemyAI Create(string generatedFolder, Vector3 position, float yaw)
        {
            // ---- texture and material
            AssetDatabase.ImportAsset(TextureFile, ImportAssetOptions.ForceUpdate);
            var importer = (TextureImporter)AssetImporter.GetAtPath(TextureFile);
            importer.textureType = TextureImporterType.Default;
            importer.sRGBTexture = true;
            importer.mipmapEnabled = true;
            importer.maxTextureSize = 2048;
            importer.anisoLevel = 4;
            importer.filterMode = FilterMode.Trilinear;
            importer.textureCompression = TextureImporterCompression.CompressedHQ;
            importer.SaveAndReimport();
            Texture2D texture = AssetDatabase.LoadAssetAtPath<Texture2D>(TextureFile);

            var material = new Material(Shader.Find("Standard"));
            material.name = "Enemy";
            material.SetTexture("_MainTex", texture);
            material.SetColor("_Color", Color.white);
            material.SetFloat("_Glossiness", 0.14f);
            material.SetFloat("_Metallic", 0f);
            string materialPath = generatedFolder + "/Materials/Enemy.mat";
            AssetDatabase.DeleteAsset(materialPath);
            AssetDatabase.CreateAsset(material, materialPath);

            // ---- mesh and skeleton
            string[] boneNames;
            int[] boneParents;
            Vector3[] bonePositions;
            Mesh mesh = ReadMesh(out boneNames, out boneParents, out bonePositions);
            string meshPath = generatedFolder + "/Meshes/Enemy.asset";
            AssetDatabase.DeleteAsset(meshPath);
            AssetDatabase.CreateAsset(mesh, meshPath);

            var root = new GameObject("Enemy (Red Hooded Hollow)");
            root.layer = EnemyLayer;
            var model = new GameObject("Model");
            model.layer = EnemyVisualLayer;
            model.transform.SetParent(root.transform, false);
            var armature = new GameObject("Armature");
            armature.layer = EnemyVisualLayer;
            armature.transform.SetParent(root.transform, false);

            var bones = new Transform[boneNames.Length];
            for (int i = 0; i < boneNames.Length; i++)
            {
                var bone = new GameObject(boneNames[i]);
                bone.layer = EnemyVisualLayer;
                Transform parent = boneParents[i] >= 0 ? bones[boneParents[i]] : armature.transform;
                bone.transform.SetParent(parent, false);
                Vector3 parentPosition = boneParents[i] >= 0 ? bonePositions[boneParents[i]] : Vector3.zero;
                bone.transform.localPosition = bonePositions[i] - parentPosition;
                bone.transform.localRotation = Quaternion.identity;
                bones[i] = bone.transform;
            }

            var skin = model.AddComponent<SkinnedMeshRenderer>();
            skin.sharedMesh = mesh;
            skin.bones = bones;
            skin.rootBone = bones[0];
            skin.sharedMaterial = material;
            skin.quality = SkinQuality.Bone4;
            skin.updateWhenOffscreen = false;
            skin.localBounds = new Bounds(new Vector3(0f, 0.05f, 0.1f), new Vector3(2.2f, 2.4f, 2.2f));
            skin.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.On;
            skin.receiveShadows = true;

            // ---- body: collider (pushes the physics cubes, blocks the player) and path following
            var capsule = root.AddComponent<CapsuleCollider>();
            capsule.center = new Vector3(0f, 0.95f, 0f);
            capsule.height = 1.9f;
            capsule.radius = 0.3f;
            var body = root.AddComponent<Rigidbody>();
            body.isKinematic = true;
            body.useGravity = false;

            var agent = root.AddComponent<NavMeshAgent>();
            agent.radius = 0.32f;
            agent.height = 1.9f;
            agent.baseOffset = 0f;
            agent.speed = 1.45f;
            agent.acceleration = 14f;
            agent.angularSpeed = 600f;
            agent.stoppingDistance = 0.25f;
            agent.autoBraking = true;
            agent.obstacleAvoidanceType = ObstacleAvoidanceType.LowQualityObstacleAvoidance;
            agent.enabled = false;   // switched on by EnemyAI once the NavMesh is loaded

            // ---- sounds
            AudioSource voice = Audio3D(root, 2f, 45f);
            AudioSource feet = Audio3D(root, 1.5f, 35f);
            AudioSource breath = Audio3D(root, 1f, 14f);
            AudioSource heartbeat = root.AddComponent<AudioSource>();
            heartbeat.playOnAwake = false;
            heartbeat.spatialBlend = 0f;
            AudioSource drone = root.AddComponent<AudioSource>();
            drone.playOnAwake = false;
            drone.spatialBlend = 0f;

            // ---- brains
            var anim = root.AddComponent<EnemyAnimator>();
            anim.hips = Find(bones, boneNames, "Hips");
            anim.spine = Find(bones, boneNames, "Spine");
            anim.chest = Find(bones, boneNames, "Chest");
            anim.neck = Find(bones, boneNames, "Neck");
            anim.head = Find(bones, boneNames, "Head");
            anim.upperArmL = Find(bones, boneNames, "UpperArm.L");
            anim.lowerArmL = Find(bones, boneNames, "LowerArm.L");
            anim.handL = Find(bones, boneNames, "Hand.L");
            anim.fingersL = Find(bones, boneNames, "Fingers.L");
            anim.upperArmR = Find(bones, boneNames, "UpperArm.R");
            anim.lowerArmR = Find(bones, boneNames, "LowerArm.R");
            anim.handR = Find(bones, boneNames, "Hand.R");
            anim.fingersR = Find(bones, boneNames, "Fingers.R");
            anim.upperLegL = Find(bones, boneNames, "UpperLeg.L");
            anim.lowerLegL = Find(bones, boneNames, "LowerLeg.L");
            anim.footL = Find(bones, boneNames, "Foot.L");
            anim.upperLegR = Find(bones, boneNames, "UpperLeg.R");
            anim.lowerLegR = Find(bones, boneNames, "LowerLeg.R");
            anim.footR = Find(bones, boneNames, "Foot.R");
            anim.feet = feet;

            var ai = root.AddComponent<EnemyAI>();
            ai.anim = anim;
            ai.body = skin;
            ai.voice = voice;
            ai.breath = breath;
            ai.heartbeat = heartbeat;
            ai.drone = drone;

            root.transform.position = position;
            root.transform.rotation = Quaternion.Euler(0f, yaw, 0f);
            Debug.Log("[PROTO] enemy built: " + mesh.vertexCount + " vertices, " + bones.Length + " bones");
            return ai;
        }

        static AudioSource Audio3D(GameObject go, float minDistance, float maxDistance)
        {
            var source = go.AddComponent<AudioSource>();
            source.playOnAwake = false;
            source.spatialBlend = 1f;
            source.minDistance = minDistance;
            source.maxDistance = maxDistance;
            source.rolloffMode = AudioRolloffMode.Logarithmic;
            source.dopplerLevel = 0f;
            return source;
        }

        static Transform Find(Transform[] bones, string[] names, string name)
        {
            for (int i = 0; i < names.Length; i++)
                if (names[i] == name) return bones[i];
            Debug.LogError("[PROTO-ERR] enemy bone missing: " + name);
            return null;
        }

        static Mesh ReadMesh(out string[] boneNames, out int[] boneParents, out Vector3[] bonePositions)
        {
            byte[] data = File.ReadAllBytes(MeshFile);
            using (var reader = new BinaryReader(new MemoryStream(data)))
            {
                int magic = reader.ReadInt32();
                int version = reader.ReadInt32();
                if (magic != 0x4E455047 || version != 1) throw new System.Exception("unexpected enemy mesh file format");
                int vertexCount = reader.ReadInt32();
                int indexCount = reader.ReadInt32();
                int boneCount = reader.ReadInt32();

                var positions = new Vector3[vertexCount];
                for (int i = 0; i < vertexCount; i++) positions[i] = new Vector3(reader.ReadSingle(), reader.ReadSingle(), reader.ReadSingle());
                var normals = new Vector3[vertexCount];
                for (int i = 0; i < vertexCount; i++) normals[i] = new Vector3(reader.ReadSingle(), reader.ReadSingle(), reader.ReadSingle());
                var uvs = new Vector2[vertexCount];
                for (int i = 0; i < vertexCount; i++) uvs[i] = new Vector2(reader.ReadSingle(), reader.ReadSingle());
                var indices = new int[indexCount];
                for (int i = 0; i < indexCount; i++) indices[i] = reader.ReadInt32();
                byte[] boneIndex = reader.ReadBytes(vertexCount * 4);
                var weights = new BoneWeight[vertexCount];
                for (int i = 0; i < vertexCount; i++)
                {
                    float w0 = reader.ReadSingle(), w1 = reader.ReadSingle(), w2 = reader.ReadSingle(), w3 = reader.ReadSingle();
                    weights[i] = new BoneWeight
                    {
                        boneIndex0 = boneIndex[i * 4], weight0 = w0,
                        boneIndex1 = boneIndex[i * 4 + 1], weight1 = w1,
                        boneIndex2 = boneIndex[i * 4 + 2], weight2 = w2,
                        boneIndex3 = boneIndex[i * 4 + 3], weight3 = w3,
                    };
                }
                boneNames = new string[boneCount];
                boneParents = new int[boneCount];
                bonePositions = new Vector3[boneCount];
                var bindposes = new Matrix4x4[boneCount];
                for (int b = 0; b < boneCount; b++)
                {
                    int length = reader.ReadInt32();
                    boneNames[b] = System.Text.Encoding.UTF8.GetString(reader.ReadBytes(length));
                    boneParents[b] = reader.ReadInt32();
                    bonePositions[b] = new Vector3(reader.ReadSingle(), reader.ReadSingle(), reader.ReadSingle());
                    bindposes[b] = Matrix4x4.Translate(-bonePositions[b]);   // T-pose, bones axis-aligned
                }

                var mesh = new Mesh();
                mesh.name = "RedHoodedHollow";
                mesh.indexFormat = UnityEngine.Rendering.IndexFormat.UInt32;
                mesh.vertices = positions;
                mesh.normals = normals;
                mesh.uv = uvs;
                mesh.triangles = indices;
                mesh.boneWeights = weights;
                mesh.bindposes = bindposes;
                mesh.RecalculateBounds();
                return mesh;
            }
        }
    }
}

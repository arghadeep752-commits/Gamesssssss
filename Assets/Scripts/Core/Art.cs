using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

namespace ZombieStrike
{
    /// <summary>Shared materials, meshes, textures, sprites and the UI font.</summary>
    public static class Art
    {
        static bool ready;
        static Material litBase, unlitBase, transparentBase, additiveBase, alphaBase;
        static readonly Dictionary<string, Material> materials = new Dictionary<string, Material>();
        static readonly Dictionary<string, Texture2D> textures = new Dictionary<string, Texture2D>();
        static readonly Dictionary<string, Sprite> sprites = new Dictionary<string, Sprite>();
        static readonly Dictionary<string, Mesh> quads = new Dictionary<string, Mesh>();

        public static Mesh Cube { get; private set; }
        public static Mesh BarrelMesh { get; private set; }
        public static Font Font { get; private set; }
        public static Sprite White { get; private set; }

        public static void Init()
        {
            if (ready) return;
            ready = true;
            litBase = LoadBase("Lit", "Legacy Shaders/Diffuse");
            unlitBase = LoadBase("Unlit", "Unlit/Color");
            transparentBase = LoadBase("UnlitTransparent", "Unlit/Transparent");
            additiveBase = LoadBase("Additive", "Mobile/Particles/Additive");
            alphaBase = LoadBase("AlphaBlend", "Mobile/Particles/Alpha Blended");
            Cube = MeshUtil.UnitCube();
            BarrelMesh = MeshUtil.Cylinder(0.5f, 1f, 12);
            Font = LoadFont();
            Texture2D w = Texture2D.whiteTexture;
            White = Sprite.Create(w, new Rect(0, 0, w.width, w.height), new Vector2(0.5f, 0.5f), 100f);
        }

        static Material LoadBase(string name, string shaderName)
        {
            var m = Resources.Load<Material>("Materials/" + name);
            if (m != null) return m;
            Debug.LogWarning("[ZS] base material " + name + " missing; using shader " + shaderName);
            Shader s = Shader.Find(shaderName);
            if (s == null) s = Shader.Find("Unlit/Color");
            if (s == null) s = Shader.Find("Sprites/Default");
            return new Material(s);
        }

        static Font LoadFont()
        {
#if UNITY_2022_2_OR_NEWER
            return Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
#else
            return Resources.GetBuiltinResource<Font>("Arial.ttf");
#endif
        }

        public static Texture2D Tex(string name)
        {
            Texture2D t;
            if (textures.TryGetValue(name, out t)) return t;
            t = Resources.Load<Texture2D>("Textures/" + name);
            if (t == null) t = Resources.Load<Texture2D>("UI/" + name);
            if (t == null) Debug.LogWarning("[ZS] texture missing: " + name);
            textures[name] = t;
            return t;
        }

        /// <summary>Sprite from Resources/UI (border &gt; 0 makes it 9-sliced).</summary>
        public static Sprite UISprite(string name, float border = 0f)
        {
            string key = name + "|" + border;
            Sprite s;
            if (sprites.TryGetValue(key, out s)) return s;
            Texture2D t = Tex(name);
            if (t == null) return White;
            s = Sprite.Create(t, new Rect(0, 0, t.width, t.height), new Vector2(0.5f, 0.5f), 100f, 0,
                SpriteMeshType.FullRect, new Vector4(border, border, border, border));
            sprites[key] = s;
            return s;
        }

        static string Key(Color c)
        {
            Color32 k = c;
            return k.r + "," + k.g + "," + k.b + "," + k.a;
        }

        /// <summary>Lambert-lit material (fog, flashlight and lamps light it).</summary>
        public static Material Lit(Color color, string texture = null, float tile = 1f)
        {
            string key = "lit|" + Key(color) + "|" + texture + "|" + tile;
            Material m;
            if (materials.TryGetValue(key, out m)) return m;
            m = new Material(litBase) { name = "Lit " + (texture ?? "plain") };
            m.color = color;
            if (texture != null)
            {
                m.mainTexture = Tex(texture);
                m.mainTextureScale = new Vector2(tile, tile);
            }
            materials[key] = m;
            return m;
        }

        /// <summary>Self-lit flat colour (eyes, lamps, windows).</summary>
        public static Material Unlit(Color color)
        {
            string key = "unlit|" + Key(color);
            Material m;
            if (materials.TryGetValue(key, out m)) return m;
            m = new Material(unlitBase) { name = "Unlit" };
            m.color = color;
            materials[key] = m;
            return m;
        }

        public static Material Transparent(string texture)
        {
            string key = "transparent|" + texture;
            Material m;
            if (materials.TryGetValue(key, out m)) return m;
            m = new Material(transparentBase) { name = "Transparent " + texture };
            m.mainTexture = Tex(texture);
            materials[key] = m;
            return m;
        }

        /// <summary>Additive blend; colour comes from vertex / particle colour.</summary>
        public static Material Additive(string texture)
        {
            string key = "add|" + texture;
            Material m;
            if (materials.TryGetValue(key, out m)) return m;
            m = new Material(additiveBase) { name = "Additive " + texture };
            m.mainTexture = Tex(texture);
            materials[key] = m;
            return m;
        }

        /// <summary>Alpha blend; colour comes from vertex / particle colour.</summary>
        public static Material AlphaBlend(string texture)
        {
            string key = "alpha|" + texture;
            Material m;
            if (materials.TryGetValue(key, out m)) return m;
            m = new Material(alphaBase) { name = "AlphaBlend " + texture };
            m.mainTexture = Tex(texture);
            materials[key] = m;
            return m;
        }

        /// <summary>Quad mesh whose vertex colour is the given tint (for additive glows).</summary>
        public static Mesh Quad(Color tint)
        {
            string key = Key(tint);
            Mesh m;
            if (quads.TryGetValue(key, out m)) return m;
            m = MeshUtil.UnitQuad(tint);
            quads[key] = m;
            return m;
        }

        public static void Plain(Renderer r)
        {
            r.shadowCastingMode = ShadowCastingMode.Off;
            r.receiveShadows = false;
            r.lightProbeUsage = LightProbeUsage.Off;
            r.reflectionProbeUsage = ReflectionProbeUsage.Off;
        }

        /// <summary>Child object using the shared unit cube, scaled to size.</summary>
        public static GameObject Box(Transform parent, Vector3 localPos, Vector3 size, Material mat, Vector3 euler, int layer)
        {
            var go = new GameObject("Box");
            go.layer = layer;
            Transform t = go.transform;
            t.SetParent(parent, false);
            t.localPosition = localPos;
            t.localRotation = Quaternion.Euler(euler);
            t.localScale = size;
            go.AddComponent<MeshFilter>().sharedMesh = Cube;
            var r = go.AddComponent<MeshRenderer>();
            r.sharedMaterial = mat;
            Plain(r);
            return go;
        }

        public static GameObject Box(Transform parent, Vector3 localPos, Vector3 size, Material mat)
        {
            return Box(parent, localPos, size, mat, Vector3.zero, parent != null ? parent.gameObject.layer : 0);
        }

        public static GameObject MeshObject(Transform parent, Mesh mesh, Material mat, Vector3 localPos, Vector3 euler, Vector3 scale, int layer)
        {
            var go = new GameObject(mesh.name);
            go.layer = layer;
            Transform t = go.transform;
            t.SetParent(parent, false);
            t.localPosition = localPos;
            t.localRotation = Quaternion.Euler(euler);
            t.localScale = scale;
            go.AddComponent<MeshFilter>().sharedMesh = mesh;
            var r = go.AddComponent<MeshRenderer>();
            r.sharedMaterial = mat;
            Plain(r);
            return go;
        }
    }
}

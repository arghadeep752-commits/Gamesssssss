using UnityEditor;
using UnityEngine;

namespace Danga.EditorTools
{
    /// <summary>
    /// Import settings for everything the cloud build generates, applied the first time Unity imports a file (so
    /// nothing is compressed twice) and checked again by DGBuild.
    /// </summary>
    public static class AssetRules
    {
        public struct Rule
        {
            public TextureImporterType type;
            public bool srgb, mips, alpha, sprite;
            public TextureWrapMode wrap;
            public TextureImporterCompression comp;
            public int max, flipbook;
            public Vector4 border;
            public TextureImporterFormat android;
        }

        public static bool For(string path, out Rule r)
        {
            r = new Rule { type = TextureImporterType.Default, srgb = true, mips = true, wrap = TextureWrapMode.Repeat, comp = TextureImporterCompression.Compressed,
                           max = 1024, android = TextureImporterFormat.Automatic };
            if (!path.EndsWith(".png")) return false;
            string f = System.IO.Path.GetFileNameWithoutExtension(path);
            if (path.StartsWith("Assets/Resources/Gen/City/"))
            {
                if (f == "layers") { r.flipbook = 6; r.max = 8192; r.alpha = true; r.android = TextureImporterFormat.ETC2_RGBA8; return true; }
                if (f == "layers_n") { r.flipbook = 6; r.max = 4096; r.srgb = false; r.android = TextureImporterFormat.ETC2_RGB4; return true; }
                r.wrap = TextureWrapMode.Clamp;
                r.max = 2048;
                if (f == "lightmap") { r.srgb = false; r.android = TextureImporterFormat.ASTC_4x4; }
                return true;
            }
            if (path.StartsWith("Assets/Resources/Gen/Sky/")) { r.mips = false; r.max = 2048; r.android = TextureImporterFormat.ASTC_6x6; return true; }
            if (path.StartsWith("Assets/Resources/Gen/"))
            {
                // the Hyper3D Rodin models' own textures
                if (f.EndsWith("_normal")) { r.type = TextureImporterType.NormalMap; r.srgb = false; }
                else if (f.EndsWith("_mr")) r.srgb = false;
                r.android = TextureImporterFormat.ASTC_6x6;
                return true;
            }
            if (path.StartsWith("Assets/Branding/"))
            {
                r.mips = false; r.alpha = true; r.wrap = TextureWrapMode.Clamp; r.comp = TextureImporterCompression.Uncompressed;
                return true;
            }
            if (path.StartsWith("Assets/Resources/UI/"))
            {
                r.sprite = true; r.type = TextureImporterType.Sprite; r.mips = false; r.alpha = true; r.wrap = TextureWrapMode.Clamp;
                r.comp = TextureImporterCompression.Uncompressed; r.max = 1024;
                if (f == "panel") r.border = new Vector4(36, 36, 36, 36);
                if (f == "pill") r.border = new Vector4(60, 60, 60, 60);
                if (f == "glow" || f == "blob") { r.sprite = false; r.type = TextureImporterType.Default; r.mips = true; }
                return true;
            }
            return false;
        }

        public static bool Matches(TextureImporter imp, Rule r)
        {
            var s = new TextureImporterSettings();
            imp.ReadTextureSettings(s);
            int fb = r.flipbook > 0 ? r.flipbook : 0;
            bool shapeOk = fb > 0 ? (s.textureShape == TextureImporterShape.Texture2DArray && s.flipbookRows == fb && s.flipbookColumns == fb)
                                  : s.textureShape == TextureImporterShape.Texture2D;
            return shapeOk && imp.textureType == r.type && imp.sRGBTexture == r.srgb && imp.mipmapEnabled == r.mips && imp.wrapMode == r.wrap
                   && imp.textureCompression == r.comp && imp.maxTextureSize == r.max && imp.alphaIsTransparency == r.alpha
                   && (!r.sprite || imp.spriteBorder == r.border);
        }

        public static void Apply(TextureImporter imp, Rule r)
        {
            imp.textureType = r.type;
            var s = new TextureImporterSettings();
            imp.ReadTextureSettings(s);
            if (r.flipbook > 0)
            {
                s.textureShape = TextureImporterShape.Texture2DArray;
                s.flipbookRows = r.flipbook;
                s.flipbookColumns = r.flipbook;
            }
            else s.textureShape = TextureImporterShape.Texture2D;
            if (r.sprite)
            {
                s.spriteMode = (int)SpriteImportMode.Single;
                s.spriteMeshType = SpriteMeshType.FullRect;
                s.spriteBorder = r.border;
                s.spritePixelsPerUnit = 100;
            }
            imp.SetTextureSettings(s);
            imp.sRGBTexture = r.srgb;
            imp.mipmapEnabled = r.mips;
            imp.wrapMode = r.wrap;
            imp.filterMode = r.mips ? FilterMode.Trilinear : FilterMode.Bilinear;
            imp.anisoLevel = r.mips ? 4 : 1;
            imp.textureCompression = r.comp;
            imp.maxTextureSize = r.max;
            imp.alphaIsTransparency = r.alpha;
            imp.npotScale = TextureImporterNPOTScale.None;
            if (r.sprite) imp.spriteBorder = r.border;
            if (r.android != TextureImporterFormat.Automatic)
            {
                var ps = imp.GetPlatformTextureSettings("Android");
                ps.overridden = true;
                ps.maxTextureSize = r.max;
                ps.format = r.android;
                ps.compressionQuality = 50;
                imp.SetPlatformTextureSettings(ps);
            }
        }

        public static void Ensure(string path)
        {
            Rule r;
            var imp = AssetImporter.GetAtPath(path) as TextureImporter;
            if (imp == null || !For(path, out r) || Matches(imp, r)) return;
            Apply(imp, r);
            imp.SaveAndReimport();
        }

        /// <summary>
        /// The emulator's graphics cannot read compressed texture arrays (they come out black), so its test build gets
        /// the city's surface layers uncompressed. The phone APK keeps the compressed ones.
        /// </summary>
        public static void EmulatorTextures()
        {
            foreach (string path in new[] { "Assets/Resources/Gen/City/layers.png", "Assets/Resources/Gen/City/layers_n.png" })
            {
                var imp = AssetImporter.GetAtPath(path) as TextureImporter;
                if (imp == null) continue;
                var ps = imp.GetPlatformTextureSettings("Android");
                ps.overridden = true;
                ps.format = TextureImporterFormat.RGBA32;
                imp.SetPlatformTextureSettings(ps);
                imp.SaveAndReimport();
            }
            var arr = AssetDatabase.LoadAssetAtPath<Texture2DArray>("Assets/Resources/Gen/City/layers.png");
            Debug.Log("[DG] emulator city texture array: " + (arr != null ? arr.format.ToString() : "MISSING"));
        }

        public static bool LongSound(string path)
        {
            string n = System.IO.Path.GetFileNameWithoutExtension(path);
            return path.Contains("/Music/") || n.StartsWith("amb_") || n.StartsWith("engine_");
        }
    }

    public class AssetRulesImporter : AssetPostprocessor
    {
        void OnPreprocessTexture()
        {
            AssetRules.Rule r;
            if (AssetRules.For(assetPath, out r)) AssetRules.Apply((TextureImporter)assetImporter, r);
        }

        void OnPreprocessAudio()
        {
            if (!assetPath.StartsWith("Assets/Resources/")) return;
            var imp = (AudioImporter)assetImporter;
            AudioImporterSampleSettings s = imp.defaultSampleSettings;
            bool music = assetPath.Contains("/Music/");
            s.loadType = music ? AudioClipLoadType.Streaming : AssetRules.LongSound(assetPath) ? AudioClipLoadType.CompressedInMemory : AudioClipLoadType.DecompressOnLoad;
            s.compressionFormat = AudioCompressionFormat.Vorbis;
            s.quality = music ? 0.6f : 0.7f;
            s.sampleRateSetting = AudioSampleRateSetting.OptimizeSampleRate;
            imp.defaultSampleSettings = s;
            imp.forceToMono = !music;
        }
    }
}

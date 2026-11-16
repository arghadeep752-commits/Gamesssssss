using UnityEditor;
using UnityEngine;

namespace Moulika.EditorTools
{
    /// <summary>
    /// Import settings for the converted game files, applied the first time Unity imports them (so nothing has to be
    /// compressed twice) and checked again by the builders.
    /// </summary>
    public static class AssetRules
    {
        public struct Rule
        {
            public TextureImporterType type;
            public bool srgb, mips, alpha;
            public TextureWrapMode wrap;
            public TextureImporterCompression comp;
            public int max;
        }

        public static bool For(string path, out Rule r)
        {
            r = new Rule { type = TextureImporterType.Default, srgb = true, mips = true, wrap = TextureWrapMode.Repeat, comp = TextureImporterCompression.Compressed, max = 1024 };
            if (path.StartsWith("Assets/Game/School/Photos/") || path.StartsWith("Assets/Game/School/Textures/")) return true;
            if (path.StartsWith("Assets/Game/School/Lightmaps/"))
            {
                r.mips = false;
                r.wrap = TextureWrapMode.Clamp;
                r.comp = TextureImporterCompression.Uncompressed;
                return true;
            }
            if (path.StartsWith("Assets/Game/Moulika/"))
            {
                r.max = 2048;
                r.comp = TextureImporterCompression.CompressedHQ;
                if (path.Contains("_normal")) { r.type = TextureImporterType.NormalMap; r.srgb = false; }
                else if (path.Contains("_mr")) r.srgb = false;
                return true;
            }
            if (path.StartsWith("Assets/Game/Sky/")) return true;
            if (path.StartsWith("Assets/Branding/"))
            {
                // app icons: kept exactly as drawn (Unity scales them for every screen density itself)
                r.mips = false;
                r.alpha = true;
                r.wrap = TextureWrapMode.Clamp;
                r.comp = TextureImporterCompression.Uncompressed;
                return true;
            }
            if (path.StartsWith("Assets/Resources/UI/"))
            {
                r.alpha = true;
                r.wrap = TextureWrapMode.Clamp;
                r.comp = TextureImporterCompression.Uncompressed;
                r.max = 512;
                return true;
            }
            return false;
        }

        public static bool Matches(TextureImporter imp, Rule r)
        {
            return imp.textureType == r.type && imp.sRGBTexture == r.srgb && imp.mipmapEnabled == r.mips && imp.wrapMode == r.wrap
                   && imp.textureCompression == r.comp && imp.maxTextureSize == r.max && imp.alphaIsTransparency == r.alpha
                   && imp.npotScale == TextureImporterNPOTScale.None;
        }

        public static void Apply(TextureImporter imp, Rule r)
        {
            imp.textureType = r.type;
            imp.sRGBTexture = r.srgb;
            imp.mipmapEnabled = r.mips;
            imp.wrapMode = r.wrap;
            imp.filterMode = r.mips ? FilterMode.Trilinear : FilterMode.Bilinear;
            imp.anisoLevel = r.mips ? 4 : 1;
            imp.textureCompression = r.comp;
            imp.maxTextureSize = r.max;
            imp.alphaIsTransparency = r.alpha;
            imp.npotScale = TextureImporterNPOTScale.None;   // keep odd-sized images (the hand icon) their real shape
        }

        /// <summary>Re-imports a texture only if its settings are not the right ones yet.</summary>
        public static void Ensure(string path)
        {
            Rule r;
            var imp = AssetImporter.GetAtPath(path) as TextureImporter;
            if (imp == null || !For(path, out r) || Matches(imp, r)) return;
            Apply(imp, r);
            imp.SaveAndReimport();
        }

        public static bool LongSound(string name)
        {
            return name.Contains("music") || name.Contains("raga") || name == "night" || name == "wind" || name == "drone" || name == "heartbeat";
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
            if (!assetPath.StartsWith("Assets/Resources/Sounds/")) return;
            var imp = (AudioImporter)assetImporter;
            AudioImporterSampleSettings s = imp.defaultSampleSettings;
            s.loadType = AssetRules.LongSound(System.IO.Path.GetFileNameWithoutExtension(assetPath)) ? AudioClipLoadType.Streaming : AudioClipLoadType.DecompressOnLoad;
            s.compressionFormat = AudioCompressionFormat.Vorbis;
            s.quality = 0.8f;
            imp.defaultSampleSettings = s;
        }
    }
}

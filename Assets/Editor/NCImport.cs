using System.IO;
using UnityEditor;
using UnityEngine;

namespace NightClass.EditorTools
{
    /// <summary>Import rules for the generated art (Assets/Art/...).</summary>
    public class NCImport : AssetPostprocessor
    {
        void OnPreprocessTexture()
        {
            string p = assetPath.Replace('\\', '/').ToLowerInvariant();
            if (!p.StartsWith("assets/art/")) return;
            Configure((TextureImporter)assetImporter, p, Path.GetFileNameWithoutExtension(p));
        }

        public static void Configure(TextureImporter ti, string p, string file)
        {
            ti.textureCompression = TextureImporterCompression.Compressed;
            ti.mipmapEnabled = true;
            ti.streamingMipmaps = false;
            ti.mipmapFilter = TextureImporterMipFilter.KaiserFilter;
            ti.anisoLevel = 4;
            ti.maxTextureSize = 1024;
            ti.wrapMode = TextureWrapMode.Repeat;
            ti.isReadable = false;
            ti.textureType = TextureImporterType.Default;
            ti.sRGBTexture = true;
            TextureImporterFormat android = TextureImporterFormat.ASTC_6x6;
            int androidMax = 1024;

            if (p.Contains("/ui/") || p.Contains("/icons/"))
            {
                ti.textureType = TextureImporterType.Sprite;
                ti.spriteImportMode = SpriteImportMode.Single;
                ti.mipmapEnabled = false;
                ti.alphaIsTransparency = true;
                ti.wrapMode = TextureWrapMode.Clamp;
                ti.textureCompression = TextureImporterCompression.Uncompressed;
                ti.maxTextureSize = 1024;
                if (file == "rounded") ti.spriteBorder = new Vector4(24, 24, 24, 24);
                if (p.Contains("/icons/")) ti.isReadable = true;
                ti.ClearPlatformTextureSettings("Android");
                return;
            }
            if (file.EndsWith("_normal"))
            {
                ti.textureType = TextureImporterType.NormalMap;
                ti.mipmapFilter = TextureImporterMipFilter.BoxFilter;
                android = TextureImporterFormat.ASTC_5x5;
            }
            else if (file.EndsWith("_mask") || file.StartsWith("noise") || file.StartsWith("grime"))
            {
                ti.sRGBTexture = false;
                android = TextureImporterFormat.ASTC_8x8;
                ti.maxTextureSize = 512;
                androidMax = 512;
            }
            if (p.Contains("/fx/"))
            {
                ti.alphaSource = TextureImporterAlphaSource.FromInput;
                ti.alphaIsTransparency = true;
                ti.wrapMode = TextureWrapMode.Clamp;
                ti.maxTextureSize = 256;
                androidMax = 256;
                android = TextureImporterFormat.ASTC_5x5;
            }
            if (p.Contains("/decals/"))
            {
                ti.alphaSource = TextureImporterAlphaSource.FromInput;
                ti.alphaIsTransparency = true;
                ti.wrapMode = TextureWrapMode.Clamp;
                android = TextureImporterFormat.ASTC_5x5;
            }
            if (p.Contains("/teacher/"))
            {
                ti.wrapMode = TextureWrapMode.Clamp;
                android = TextureImporterFormat.ASTC_5x5;
            }
            var ps = new TextureImporterPlatformSettings
            {
                name = "Android",
                overridden = true,
                maxTextureSize = androidMax,
                format = android,
                compressionQuality = 50
            };
            ti.SetPlatformTextureSettings(ps);
        }
    }
}

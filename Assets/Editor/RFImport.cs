using System.IO;
using UnityEditor;
using UnityEngine;

namespace RealFPS.EditorTools
{
    /// <summary>
    /// Import settings for everything under Assets/Art (chosen by folder and file
    /// name), tuned for mobile: ASTC compression, foliage alpha coverage, sprites,
    /// the 4K sky panorama and the reflection cubemap.
    /// </summary>
    public class RFImport : AssetPostprocessor
    {
        void OnPreprocessTexture()
        {
            if (!assetPath.StartsWith("Assets/Art/")) return;
            var ti = (TextureImporter)assetImporter;
            string p = assetPath.Replace('\\', '/').ToLowerInvariant();
            string file = Path.GetFileNameWithoutExtension(p);
            Configure(ti, p, file);
        }

        public static void Configure(TextureImporter ti, string p, string file)
        {
            ti.textureCompression = TextureImporterCompression.Compressed;
            ti.mipmapEnabled = true;
            ti.streamingMipmaps = false;
            ti.anisoLevel = 2;
            ti.maxTextureSize = 2048;
            ti.wrapMode = TextureWrapMode.Repeat;
            ti.isReadable = false;
            TextureImporterFormat android = TextureImporterFormat.ASTC_6x6;
            int androidMax = 2048;

            if (p.Contains("/ui/") || p.Contains("/icons/"))
            {
                ti.textureType = p.Contains("/icons/") ? TextureImporterType.Default : TextureImporterType.Sprite;
                ti.spriteImportMode = SpriteImportMode.Single;
                ti.mipmapEnabled = false;
                ti.alphaIsTransparency = true;
                ti.wrapMode = TextureWrapMode.Clamp;
                ti.textureCompression = TextureImporterCompression.Uncompressed;
                if (file == "rounded") ti.spriteBorder = new Vector4(16, 16, 16, 16);
                if (p.Contains("/icons/")) { ti.maxTextureSize = 1024; ti.isReadable = true; }
                ti.ClearPlatformTextureSettings("Android");
                return;
            }
            if (file.EndsWith("_normal") || p.Contains("water_normal"))
            {
                ti.textureType = TextureImporterType.NormalMap;
                android = TextureImporterFormat.ASTC_5x5;
            }
            else if (file.EndsWith("_mask"))
            {
                ti.textureType = TextureImporterType.Default;
                ti.sRGBTexture = false;
                android = TextureImporterFormat.ASTC_6x6;
            }
            else
            {
                ti.textureType = TextureImporterType.Default;
                ti.sRGBTexture = true;
            }

            if (p.Contains("twig_atlas") || p.Contains("grass_atlas") || (p.Contains("/models/fern") && file.Contains("albedo")) ||
                (p.Contains("/models/lantern") && file.Contains("albedo")))
            {
                ti.alphaSource = TextureImporterAlphaSource.FromInput;
                ti.alphaIsTransparency = false;
                ti.mipMapsPreserveCoverage = true;
                ti.alphaTestReferenceValue = 0.42f;
                ti.wrapMode = TextureWrapMode.Clamp;
                android = TextureImporterFormat.ASTC_5x5;
            }
            if (p.Contains("/terrain/") && file.EndsWith("_albedo"))
            {
                ti.alphaSource = TextureImporterAlphaSource.FromInput; // smoothness in alpha
                android = TextureImporterFormat.ASTC_6x6;
            }
            if (p.Contains("/sky/sky_pano"))
            {
                ti.mipmapEnabled = false;
                ti.maxTextureSize = 4096;
                androidMax = 4096;
                ti.wrapModeU = TextureWrapMode.Repeat;
                ti.wrapModeV = TextureWrapMode.Clamp;
                ti.anisoLevel = 0;
                android = TextureImporterFormat.ASTC_5x5;
            }
            if (p.Contains("/sky/sky_reflect"))
            {
                ti.wrapModeU = TextureWrapMode.Repeat;
                ti.wrapModeV = TextureWrapMode.Clamp;
                ti.maxTextureSize = 1024;
                androidMax = 1024;
                android = TextureImporterFormat.ASTC_5x5;
            }
            if (p.Contains("/sky/sky_cube"))
            {
                ti.textureShape = TextureImporterShape.TextureCube;
                var s = new TextureImporterSettings();
                ti.ReadTextureSettings(s);
                s.textureShape = TextureImporterShape.TextureCube;
                s.generateCubemap = TextureImporterGenerateCubemap.Cylindrical;
                s.cubemapConvolution = TextureImporterCubemapConvolution.Specular;
                s.seamlessCubemap = true;
                s.mipmapEnabled = true;
                ti.SetTextureSettings(s);
                ti.maxTextureSize = 256;
                androidMax = 256;
                android = TextureImporterFormat.RGBA32;
            }
            if (p.Contains("/water/")) android = TextureImporterFormat.ASTC_5x5;

            var ps = new TextureImporterPlatformSettings
            {
                name = "Android",
                overridden = true,
                maxTextureSize = androidMax,
                format = android,
                compressionQuality = 60,
                textureCompression = TextureImporterCompression.Compressed
            };
            ti.SetPlatformTextureSettings(ps);
        }

        void OnPreprocessModel()
        {
            if (!assetPath.StartsWith("Assets/Art/Models/")) return;
            var mi = (ModelImporter)assetImporter;
            mi.importAnimation = false;
            mi.animationType = ModelImporterAnimationType.None;
            mi.importCameras = false;
            mi.importLights = false;
            mi.importBlendShapes = false;
            mi.importVisibility = false;
            mi.materialImportMode = ModelImporterMaterialImportMode.ImportStandard;
            mi.materialLocation = ModelImporterMaterialLocation.InPrefab;
            mi.isReadable = true;
            mi.meshCompression = ModelImporterMeshCompression.Off;
            mi.importNormals = ModelImporterNormals.Import;
            mi.importTangents = ModelImporterTangents.CalculateMikk;
            mi.optimizeMeshPolygons = true;
            mi.optimizeMeshVertices = true;
            mi.useFileScale = true;
            mi.globalScale = 1f;
            mi.addCollider = false;
            mi.weldVertices = true;
        }

        void OnPreprocessAudio()
        {
            if (!assetPath.StartsWith("Assets/Art/")) return;
            var ai = (AudioImporter)assetImporter;
            string file = Path.GetFileNameWithoutExtension(assetPath).ToLowerInvariant();
            bool loop = file == "wind" || file == "lake" || file == "fire";
            AudioImporterSampleSettings s = ai.defaultSampleSettings;
            s.loadType = loop ? AudioClipLoadType.CompressedInMemory : AudioClipLoadType.DecompressOnLoad;
            s.compressionFormat = AudioCompressionFormat.Vorbis;
            s.quality = loop ? 0.55f : 0.7f;
            s.sampleRateSetting = AudioSampleRateSetting.PreserveSampleRate;
            ai.defaultSampleSettings = s;
            ai.forceToMono = file != "wind";
            ai.loadInBackground = loop;
        }
    }
}

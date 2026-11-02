using System.IO;
using UnityEditor;
using UnityEngine;

namespace NightClass.EditorTools
{
    /// <summary>Import rules for the generated art (Assets/Art/...).</summary>
    public class NCImport : AssetPostprocessor
    {
        public override int GetPostprocessOrder() { return 100; }   // after URP's FBX material preprocessor

        void OnPreprocessTexture()
        {
            string p = assetPath.Replace('\\', '/').ToLowerInvariant();
            if (!p.StartsWith("assets/art/")) return;
            string file = Path.GetFileNameWithoutExtension(p);
            if (p.Contains("/models/"))
            {
                // Poly Haven model textures: <id>_diff_1k, <id>_nor_gl_1k, <id>_arm_1k, <id>_rough_1k ...
                if (file.Contains("_nor")) file = "x_normal";
                else if (file.Contains("_arm") || file.Contains("_rough") || file.Contains("_ao") || file.Contains("_metal") || file.Contains("_disp") || file.Contains("_spec")) file = "x_mask";
            }
            Configure((TextureImporter)assetImporter, p, file);
        }

        void OnPreprocessModel()
        {
            string p = assetPath.Replace('\\', '/').ToLowerInvariant();
            if (!p.StartsWith("assets/art/")) return;
            var mi = (ModelImporter)assetImporter;
            mi.importCameras = false;
            mi.importLights = false;
            mi.isReadable = false;
            mi.meshCompression = ModelImporterMeshCompression.Medium;
            mi.importVisibility = false;
            mi.materialLocation = ModelImporterMaterialLocation.InPrefab;
            if (p.Contains("/teacher/rocketbox/"))
            {
                bool anim = p.Contains("/anims/");
                mi.animationType = ModelImporterAnimationType.Human;
                mi.avatarSetup = ModelImporterAvatarSetup.CreateFromThisModel;
                mi.importAnimation = anim;
                mi.importBlendShapes = !anim;
                mi.optimizeGameObjects = false;
                mi.materialImportMode = anim ? ModelImporterMaterialImportMode.None : ModelImporterMaterialImportMode.ImportViaMaterialDescription;
                mi.meshCompression = ModelImporterMeshCompression.Off;
                return;
            }
            mi.animationType = ModelImporterAnimationType.None;
            mi.importAnimation = false;
            mi.importBlendShapes = false;
            mi.materialImportMode = ModelImporterMaterialImportMode.ImportViaMaterialDescription;
        }

        void OnPostprocessMaterial(Material m)
        {
            string p = assetPath.Replace('\\', '/').ToLowerInvariant();
            if (!p.StartsWith("assets/art/models/")) return;
            // no reflection probe in this game: keep imported props matte and free of sky reflections
            if (m.HasProperty("_EnvironmentReflections")) m.SetFloat("_EnvironmentReflections", 0f);
            m.EnableKeyword("_ENVIRONMENTREFLECTIONS_OFF");
            if (m.HasProperty("_Smoothness")) m.SetFloat("_Smoothness", Mathf.Min(m.GetFloat("_Smoothness"), 0.42f));
            if (m.HasProperty("_Metallic")) m.SetFloat("_Metallic", Mathf.Min(m.GetFloat("_Metallic"), 0.6f));
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

using System.IO;
using UnityEditor;
using UnityEngine;

namespace GridProto.EditorTools
{
    /// <summary>Generates the prototype grid textures (seamless, 4 m per tile, 1 m lines) at build time.</summary>
    public static class ProtoTextures
    {
        public const float TileMeters = 4f;

        /// <summary>Off-white concrete-like base with faint 0.5 m, medium 1 m and strong 4 m lines.</summary>
        public static void WriteGridAlbedo(string path, int size)
        {
            var px = new Color32[size * size];
            float metersPerPixel = TileMeters / size;
            for (int j = 0; j < size; j++)
            {
                for (int i = 0; i < size; i++)
                {
                    float u = (i + 0.5f) / size, v = (j + 0.5f) / size;
                    float mx = u * TileMeters, my = v * TileMeters;
                    float major = Line(mx, my, TileMeters, 0.011f, metersPerPixel);
                    float minor = Line(mx, my, 1f, 0.0055f, metersPerPixel);
                    float half = Line(mx, my, 0.5f, 0.0025f, metersPerPixel);
                    float n = (Noise(u, v, 4, 1) - 0.5f) * 0.035f
                            + (Noise(u, v, 16, 2) - 0.5f) * 0.02f
                            + (Noise(u, v, 64, 3) - 0.5f) * 0.014f
                            + (Hash(i, j, 9) - 0.5f) * 0.012f;
                    float shade = 0.80f + n;
                    shade *= 1f - 0.07f * half;
                    shade *= 1f - 0.17f * minor;
                    shade *= 1f - 0.30f * major;
                    int b = Mathf.Clamp(Mathf.RoundToInt(shade * 255f), 0, 255);
                    px[j * size + i] = new Color32((byte)Mathf.Clamp(b - 1, 0, 255), (byte)b, (byte)Mathf.Clamp(b + 2, 0, 255), 255);
                }
            }
            Save(path, size, px);
        }

        /// <summary>Tangent-space normal map: shallow grooves on the 1 m and 4 m lines plus a little surface wobble.</summary>
        public static void WriteGridNormal(string path, int size)
        {
            var height = new float[size * size];
            for (int j = 0; j < size; j++)
            {
                for (int i = 0; i < size; i++)
                {
                    float u = (i + 0.5f) / size, v = (j + 0.5f) / size;
                    float mx = u * TileMeters, my = v * TileMeters;
                    float major = Groove(mx, my, TileMeters, 0.016f);
                    float minor = Groove(mx, my, 1f, 0.008f);
                    float rough = (Noise(u, v, 32, 5) - 0.5f) * 0.25f + (Noise(u, v, 128, 6) - 0.5f) * 0.12f;
                    height[j * size + i] = -major - minor * 0.45f + rough * 0.06f;
                }
            }
            var px = new Color32[size * size];
            const float strength = 2.6f;
            for (int j = 0; j < size; j++)
            {
                for (int i = 0; i < size; i++)
                {
                    float l = height[j * size + Wrap(i - 1, size)], r = height[j * size + Wrap(i + 1, size)];
                    float d = height[Wrap(j - 1, size) * size + i], up = height[Wrap(j + 1, size) * size + i];
                    float dx = (r - l) * 0.5f * strength, dy = (up - d) * 0.5f * strength;
                    Vector3 n = new Vector3(-dx, -dy, 1f).normalized;
                    px[j * size + i] = new Color32(ToByte(n.x), ToByte(n.y), ToByte(n.z), 255);
                }
            }
            Save(path, size, px);
        }

        /// <summary>Radial fall-off used by the contact shadows (white = darkest).</summary>
        public static void WriteContactShadowMask(string path, int size)
        {
            var px = new Color32[size * size];
            for (int j = 0; j < size; j++)
            {
                for (int i = 0; i < size; i++)
                {
                    float x = Mathf.Abs((i + 0.5f) / size - 0.5f) * 2f;
                    float y = Mathf.Abs((j + 0.5f) / size - 0.5f) * 2f;
                    float r = Mathf.Clamp01(Mathf.Sqrt(x * x + y * y));
                    float a = Mathf.Pow(1f - r, 1.8f);
                    byte b = (byte)Mathf.RoundToInt(a * 255f);
                    px[j * size + i] = new Color32(b, b, b, 255);
                }
            }
            Save(path, size, px);
        }

        public static Texture2D Import(string path, bool sRGB, bool normalMap, bool repeat, int aniso)
        {
            AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceUpdate);
            var importer = (TextureImporter)AssetImporter.GetAtPath(path);
            importer.textureType = normalMap ? TextureImporterType.NormalMap : TextureImporterType.Default;
            importer.sRGBTexture = sRGB && !normalMap;
            importer.alphaSource = TextureImporterAlphaSource.None;
            importer.mipmapEnabled = true;
            importer.mipmapFilter = TextureImporterMipFilter.KaiserFilter;   // keeps thin lines visible far away
            importer.wrapMode = repeat ? TextureWrapMode.Repeat : TextureWrapMode.Clamp;
            importer.filterMode = FilterMode.Trilinear;
            importer.anisoLevel = aniso;
            importer.maxTextureSize = 2048;
            importer.textureCompression = TextureImporterCompression.CompressedHQ;
            importer.SaveAndReimport();
            return AssetDatabase.LoadAssetAtPath<Texture2D>(path);
        }

        static byte ToByte(float v)
        {
            return (byte)Mathf.Clamp(Mathf.RoundToInt((v * 0.5f + 0.5f) * 255f), 0, 255);
        }

        // anti-aliased coverage of grid lines with the given period and half width (metres)
        static float Line(float x, float y, float period, float halfWidth, float pixel)
        {
            float dx = Mathf.Abs(x - Mathf.Round(x / period) * period);
            float dy = Mathf.Abs(y - Mathf.Round(y / period) * period);
            float d = Mathf.Min(dx, dy);
            return 1f - Mathf.Clamp01((d - halfWidth) / pixel + 0.5f);
        }

        static float Groove(float x, float y, float period, float halfWidth)
        {
            float dx = Mathf.Abs(x - Mathf.Round(x / period) * period);
            float dy = Mathf.Abs(y - Mathf.Round(y / period) * period);
            float t = Mathf.Clamp01(1f - Mathf.Min(dx, dy) / halfWidth);
            return t * t * (3f - 2f * t);
        }

        static int Wrap(int a, int m)
        {
            int r = a % m;
            return r < 0 ? r + m : r;
        }

        static float Hash(int x, int y, int seed)
        {
            unchecked
            {
                int h = x * 374761393 + y * 668265263 + seed * 1013904223;
                h = (h ^ (h >> 13)) * 1274126177;
                h ^= h >> 16;
                return (h & 0x7fffffff) / (float)0x7fffffff;
            }
        }

        // value noise that repeats every `cells` cells, so the texture tiles seamlessly
        static float Noise(float u, float v, int cells, int seed)
        {
            float x = u * cells, y = v * cells;
            int x0 = Mathf.FloorToInt(x), y0 = Mathf.FloorToInt(y);
            float fx = x - x0, fy = y - y0;
            fx = fx * fx * (3f - 2f * fx);
            fy = fy * fy * (3f - 2f * fy);
            int xa = Wrap(x0, cells), xb = Wrap(x0 + 1, cells), ya = Wrap(y0, cells), yb = Wrap(y0 + 1, cells);
            float a = Hash(xa, ya, seed), b = Hash(xb, ya, seed), c = Hash(xa, yb, seed), d = Hash(xb, yb, seed);
            return Mathf.Lerp(Mathf.Lerp(a, b, fx), Mathf.Lerp(c, d, fx), fy);
        }

        static void Save(string path, int size, Color32[] px)
        {
            var tex = new Texture2D(size, size, TextureFormat.RGBA32, false, true);
            tex.SetPixels32(px);
            tex.Apply(false);
            File.WriteAllBytes(path, tex.EncodeToPNG());
            Object.DestroyImmediate(tex);
        }
    }
}

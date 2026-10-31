using System;
using System.IO;
using UnityEngine;

namespace RealFPS.EditorTools
{
    /// <summary>Data written by tools/process_assets.py (Assets/Art/art.json).</summary>
    [Serializable]
    public class RFArtInfo
    {
        public float[] sunDir = { 0.55f, 0.74f, -0.38f };
        public float[] sunColor = { 1f, 1f, 0.92f };
        public float sunIntensity = 1.6f;
        public float skyExposure = 1.6667f;
        public float[] fogColorLinear = { 0.52f, 0.56f, 0.69f };
        public float[] ambientUp = new float[0];
        public float[] ambientDown = new float[0];
        public int shW = 32;
        public int shH = 16;
        public float[] shGrid = new float[0];
        public float[] twigRects = new float[0];
        public float[] grassRects = new float[0];
        public int[] grassKinds = new int[0];

        public const string Path = "Assets/Art/art.json";

        public static RFArtInfo Load()
        {
            if (!File.Exists(Path)) throw new Exception("Missing " + Path + " - run tools/process_assets.py first");
            var info = JsonUtility.FromJson<RFArtInfo>(File.ReadAllText(Path));
            if (info.twigRects == null || info.twigRects.Length < 16) throw new Exception("art.json has no twig atlas layout");
            return info;
        }

        public Vector3 SunDirection { get { return new Vector3(sunDir[0], sunDir[1], sunDir[2]).normalized; } }
        public Color SunColorLinear { get { return new Color(sunColor[0], sunColor[1], sunColor[2]); } }
        public Color FogLinear { get { return new Color(fogColorLinear[0], fogColorLinear[1], fogColorLinear[2]); } }
    }
}

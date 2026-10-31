using UnityEditor;
using UnityEngine;

namespace RealFPS.EditorTools
{
    /// <summary>
    /// Runs right after the scripts compile (before the textures are imported on a
    /// fresh checkout), so the textures are imported once, already in linear colour
    /// space with ASTC compression.
    /// </summary>
    [InitializeOnLoad]
    static class RFProjectSetup
    {
        static RFProjectSetup()
        {
            if (PlayerSettings.colorSpace != ColorSpace.Linear)
            {
                PlayerSettings.colorSpace = ColorSpace.Linear;
                Debug.Log("[RF-BUILD] colour space set to linear");
            }
            if (EditorUserBuildSettings.androidBuildSubtarget != MobileTextureSubtarget.ASTC)
                EditorUserBuildSettings.androidBuildSubtarget = MobileTextureSubtarget.ASTC;
        }
    }
}

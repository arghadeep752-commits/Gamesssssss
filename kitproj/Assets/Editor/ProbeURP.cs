// Probe run in the "Unity 6 compile kit" workflow: creates URP assets the same way the
// game's build script will, and writes a report of serialized field names, quality
// settings layout and the URP shaders available in this editor.
using System;
using System.IO;
using System.Text;
using UnityEditor;
using UnityEditor.Rendering;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

public static class ProbeURP
{
    static readonly StringBuilder sb = new StringBuilder();

    static void L(string s)
    {
        sb.AppendLine(s);
        Debug.Log("[PROBE] " + s);
    }

    public static void Run()
    {
        try { Inner(); }
        catch (Exception e) { L("EXCEPTION " + e); }
        try { CheckShaders(); }
        catch (Exception e) { L("SHADER CHECK EXCEPTION " + e); }
        try { File.WriteAllText(Path.GetFullPath("../probe-urp.txt"), sb.ToString()); }
        catch (Exception e) { Debug.Log("[PROBE] could not write report: " + e.Message); }
        EditorApplication.Exit(0);
    }

    static string Val(SerializedProperty p)
    {
        switch (p.propertyType)
        {
            case SerializedPropertyType.Integer: return p.intValue.ToString();
            case SerializedPropertyType.Boolean: return p.boolValue.ToString();
            case SerializedPropertyType.Float: return p.floatValue.ToString("0.###");
            case SerializedPropertyType.String: return p.stringValue;
            case SerializedPropertyType.Enum: return p.enumValueIndex + " (" + (p.enumValueIndex >= 0 && p.enumValueIndex < p.enumDisplayNames.Length ? p.enumDisplayNames[p.enumValueIndex] : "?") + ")";
            case SerializedPropertyType.ObjectReference: return p.objectReferenceValue != null ? p.objectReferenceValue.name + " [" + p.objectReferenceValue.GetType().Name + "]" : "null";
            case SerializedPropertyType.ArraySize: return p.intValue.ToString();
            default: return "";
        }
    }

    static void Dump(UnityEngine.Object o, int maxDepth)
    {
        if (o == null) { L("  (null)"); return; }
        var so = new SerializedObject(o);
        var it = so.GetIterator();
        bool enter = true;
        int n = 0;
        while (it.Next(enter) && n < 1500)
        {
            enter = it.depth < maxDepth;
            L("  " + new string(' ', it.depth * 2) + it.propertyPath + " : " + it.propertyType + " = " + Val(it));
            n++;
        }
    }

    static void CheckShaders()
    {
        string[][] keywordSets =
        {
            new string[0],
            new[] { "_MAIN_LIGHT_SHADOWS" },
            new[] { "_MAIN_LIGHT_SHADOWS_CASCADE", "_SHADOWS_SOFT" },
            new[] { "_MAIN_LIGHT_SHADOWS", "_SHADOWS_SOFT_LOW" },
            new[] { "FOG_EXP" },
            new[] { "INSTANCING_ON" },
            new[] { "_MAIN_LIGHT_SHADOWS", "FOG_EXP", "INSTANCING_ON" },
        };
        foreach (string g in AssetDatabase.FindAssets("t:Shader", new[] { "Assets/Shaders" }))
        {
            var shader = AssetDatabase.LoadAssetAtPath<Shader>(AssetDatabase.GUIDToAssetPath(g));
            if (shader == null) continue;
            L("== shader " + shader.name + " hasError=" + ShaderUtil.ShaderHasError(shader) + " supported=" + shader.isSupported);
            foreach (ShaderMessage m in ShaderUtil.GetShaderMessages(shader))
                L("   import " + m.severity + ": " + m.message + " line " + m.line + " " + m.platform);
            ShaderData data = ShaderUtil.GetShaderData(shader);
            for (int si = 0; si < data.SubshaderCount; si++)
            {
                ShaderData.Subshader sub = data.GetSubshader(si);
                for (int p = 0; p < sub.PassCount; p++)
                {
                    ShaderData.Pass pass = sub.GetPass(p);
                    int ok = 0, bad = 0;
                    foreach (ShaderCompilerPlatform platform in new[] { ShaderCompilerPlatform.GLES3x, ShaderCompilerPlatform.Vulkan })
                    foreach (string[] kw in keywordSets)
                    foreach (ShaderType st in new[] { ShaderType.Vertex, ShaderType.Fragment })
                    {
                        ShaderData.VariantCompileInfo info = pass.CompileVariant(st, kw, platform, BuildTarget.Android);
                        if (info.Success) ok++; else bad++;
                        if (!info.Success || (info.Messages != null && info.Messages.Length > 0))
                        {
                            L("   pass '" + pass.Name + "' " + platform + " " + st + " [" + string.Join(",", kw) + "] success=" + info.Success);
                            if (info.Messages != null)
                                foreach (ShaderMessage m in info.Messages)
                                    L("      " + m.severity + ": " + m.message + " (line " + m.line + ") " + m.messageDetails);
                        }
                    }
                    L("   pass '" + pass.Name + "': " + ok + " variants compiled, " + bad + " failed");
                }
            }
        }
    }

    static void Inner()
    {
        L("Unity " + Application.unityVersion + " platform " + EditorUserBuildSettings.activeBuildTarget);
        Directory.CreateDirectory("Assets/Settings");

        var rd = ScriptableObject.CreateInstance<UniversalRendererData>();
        AssetDatabase.CreateAsset(rd, "Assets/Settings/Probe_Renderer.asset");
        var ppd = AssetDatabase.LoadAssetAtPath<PostProcessData>("Packages/com.unity.render-pipelines.universal/Runtime/Data/PostProcessData.asset");
        L("default PostProcessData found: " + (ppd != null));
        if (rd.postProcessData == null && ppd != null) rd.postProcessData = ppd;
        EditorUtility.SetDirty(rd);

        var asset = UniversalRenderPipelineAsset.Create(rd);
        AssetDatabase.CreateAsset(asset, "Assets/Settings/Probe_URP.asset");
        GraphicsSettings.defaultRenderPipeline = asset;
        QualitySettings.renderPipeline = asset;
        AssetDatabase.SaveAssets();

        L("== URP asset fields");
        Dump(asset, 0);
        L("== Renderer data fields");
        Dump(rd, 1);

        var gs = GraphicsSettings.GetSettingsForRenderPipeline<UniversalRenderPipeline>();
        L("== global settings: " + (gs != null ? gs.name + " at " + AssetDatabase.GetAssetPath(gs) : "null"));

        var qsAll = AssetDatabase.LoadAllAssetsAtPath("ProjectSettings/QualitySettings.asset");
        L("== QualitySettings objects: " + qsAll.Length + " names " + string.Join(",", QualitySettings.names));
        if (qsAll.Length > 0) Dump(qsAll[0], 4);

        var gfx = AssetDatabase.LoadAllAssetsAtPath("ProjectSettings/GraphicsSettings.asset");
        L("== GraphicsSettings");
        if (gfx.Length > 0) Dump(gfx[0], 1);

        var volume = ScriptableObject.CreateInstance<VolumeProfile>();
        AssetDatabase.CreateAsset(volume, "Assets/Settings/Probe_Volume.asset");
        var tm = volume.Add<Tonemapping>(true);
        AssetDatabase.AddObjectToAsset(tm, volume);
        tm.mode.Override(TonemappingMode.ACES);
        AssetDatabase.SaveAssets();
        L("volume components: " + volume.components.Count);

        string[] names =
        {
            "Universal Render Pipeline/Lit", "Universal Render Pipeline/Simple Lit", "Universal Render Pipeline/Unlit",
            "Universal Render Pipeline/Terrain/Lit", "Universal Render Pipeline/Particles/Unlit", "Universal Render Pipeline/Particles/Simple Lit",
            "Universal Render Pipeline/Nature/SpeedTree8", "Universal Render Pipeline/Baked Lit",
            "Hidden/TerrainEngine/Details/UniversalPipeline/WavingDoublePass", "Hidden/TerrainEngine/Details/UniversalPipeline/BillboardWavingDoublePass",
            "Hidden/TerrainEngine/Details/UniversalPipeline/Vertexlit", "Skybox/Panoramic", "Skybox/Procedural"
        };
        L("== shaders");
        foreach (string n in names)
        {
            Shader s = Shader.Find(n);
            if (s == null) { L("MISSING " + n); continue; }
            var props = new StringBuilder();
            for (int i = 0; i < s.GetPropertyCount(); i++) props.Append(s.GetPropertyName(i)).Append(' ');
            L("found " + n + " supported=" + s.isSupported + " props: " + props);
        }
        foreach (ShaderInfo info in ShaderUtil.GetAllShaderInfo())
            if (info.name.Contains("Universal") || info.name.Contains("TerrainEngine"))
                L("  shaderinfo " + info.name + " supported=" + info.supported + " errors=" + info.hasErrors);

        L("== terrain defaults");
        var td = new TerrainData();
        L("default detail scatter mode: " + td.detailScatterMode);
        L("done");
    }
}

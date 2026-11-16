#if DIMNIGHT_AUTOTEST
using System.Collections;
using UnityEngine;
using UnityEngine.AI;
using UnityEngine.SceneManagement;

/// <summary>
/// Only in the emulator build (DIMNIGHT_AUTOTEST): plays the game like a player would and saves screenshots of real
/// gameplay for the release page - the menu, "Day 1", waking up in bed with the touch controls, a walk through every
/// room Granny patrols, and Granny herself. ci/smoke_test.sh grabs the screen whenever a "[DIMNIGHT-TEST] SNAP name"
/// line appears.
/// </summary>
public class DimnightAutoTest : MonoBehaviour
{
    static readonly string[] Rooms =
    {
        "PlayerBedRoom Point", "KitchenRoom Point", "LibraryRoom Point", "BedRoomLeft Point", "BedRoomRight Point",
        "SecretBookRoom Point", "InnerNosferaRoom Point", "Garage Point", "BackYard Point", "EscapeDoor Point",
    };

    int shot = 1;

    [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
    static void Boot()
    {
        var go = new GameObject("DimnightAutoTest");
        DontDestroyOnLoad(go);
        go.AddComponent<DimnightAutoTest>();
    }

    static void Say(string s) { Debug.Log("[DIMNIGHT-TEST] " + s); }

    IEnumerator Snap(string name)
    {
        yield return new WaitForEndOfFrame();
        string file = shot.ToString("00") + "-" + name;
        shot++;
        // on Android Unity puts a relative file name in persistentDataPath by itself
        ScreenCapture.CaptureScreenshot("shot_" + file + ".png");
        Say("SNAP " + file);
        yield return new WaitForSecondsRealtime(3f);
    }

    static void HideBlackOverlays()
    {
        foreach (CanvasGroup g in FindObjectsByType<CanvasGroup>(FindObjectsSortMode.None))
        {
            string n = g.name.ToLowerInvariant();
            if (g.alpha > 0.5f && (n.Contains("fade") || n.Contains("black") || n.Contains("death")))
            {
                Say("overlay still showing, hidden for the tour: " + g.name);
                g.alpha = 0f;
            }
        }
        foreach (UnityEngine.UI.Image img in FindObjectsByType<UnityEngine.UI.Image>(FindObjectsSortMode.None))
        {
            string n = img.name.ToLowerInvariant();
            if (img.color.a > 0.5f && img.color.maxColorComponent < 0.05f && (n.Contains("fade") || n.Contains("black")))
            {
                Say("black panel still showing, hidden for the tour: " + img.name);
                img.enabled = false;
            }
        }
    }

    static void Teleport(Transform player, Vector3 floorPoint)
    {
        CharacterController cc = player.GetComponent<CharacterController>();
        float lift = cc != null ? cc.height * 0.5f - cc.center.y + 0.08f : 1f;
        if (cc != null) cc.enabled = false;
        player.position = floorPoint + Vector3.up * lift;
        if (cc != null) cc.enabled = true;
        FPSController fps = player.GetComponent<FPSController>();
        if (fps != null) fps.ResetGravityVelocity();
    }

    static Vector3 Floor(Vector3 at)
    {
        if (Physics.Raycast(at + Vector3.up * 0.8f, Vector3.down, out RaycastHit hit, 5f, Physics.DefaultRaycastLayers, QueryTriggerInteraction.Ignore))
            return hit.point;
        return at;
    }

    static float OpenestHeading(Vector3 eye)
    {
        float best = 0f, bestDist = -1f;
        for (int a = 0; a < 360; a += 45)
        {
            Vector3 d = Quaternion.Euler(0f, a, 0f) * Vector3.forward;
            float dist = Physics.Raycast(eye, d, out RaycastHit hit, 12f, Physics.DefaultRaycastLayers, QueryTriggerInteraction.Ignore) ? hit.distance : 12f;
            if (dist > bestDist) { bestDist = dist; best = a; }
        }
        return best;
    }

    static object GetProp(Component c, string name)
    {
        if (c == null) return null;
        var p = c.GetType().GetProperty(name);
        return p != null ? p.GetValue(c) : null;
    }

    static void SetProp(Component c, string name, object value)
    {
        if (c == null) return;
        var p = c.GetType().GetProperty(name);
        if (p != null && p.CanWrite) p.SetValue(c, value);
    }

    /// <summary>Finds out why the 3D view might not show: cameras, overlays, post-processing, lighting.</summary>
    IEnumerator Diagnose(Transform player)
    {
        foreach (Camera c in FindObjectsByType<Camera>(FindObjectsInactive.Include, FindObjectsSortMode.None))
        {
            Component data = c.GetComponent("UniversalAdditionalCameraData");
            Say("camera " + c.name + " active=" + c.gameObject.activeInHierarchy + " enabled=" + c.enabled + " depth=" + c.depth
                + " clear=" + c.clearFlags + " mask=0x" + c.cullingMask.ToString("X") + " near=" + c.nearClipPlane + " far=" + c.farClipPlane
                + " pos=" + c.transform.position + " rot=" + c.transform.eulerAngles + " type=" + GetProp(data, "renderType")
                + " post=" + GetProp(data, "renderPostProcessing") + " target=" + (c.targetTexture != null ? c.targetTexture.name : "screen"));
        }
        int visible = 0, total = 0;
        foreach (Renderer r in FindObjectsByType<Renderer>(FindObjectsSortMode.None)) { total++; if (r.isVisible) visible++; }
        Say("renderers visible " + visible + " of " + total + ", fog " + RenderSettings.fog + " " + RenderSettings.fogMode + " " + RenderSettings.fogDensity
            + ", ambient " + RenderSettings.ambientMode + " " + RenderSettings.ambientLight + " x" + RenderSettings.ambientIntensity);
        foreach (UnityEngine.UI.Graphic g in FindObjectsByType<UnityEngine.UI.Graphic>(FindObjectsSortMode.None))
        {
            Canvas cv = g.canvas;
            if (g.color.a > 0.3f && g.rectTransform.rect.width * g.rectTransform.lossyScale.x > Screen.width * 0.8f)
                Say("big UI graphic " + g.name + " on canvas " + (cv != null ? cv.name + " order " + cv.sortingOrder : "?") + " color " + g.color + " enabled " + g.enabled);
        }

        Camera main = Camera.main;
        var canvases = FindObjectsByType<Canvas>(FindObjectsSortMode.None);
        foreach (Canvas cv in canvases) cv.enabled = false;
        yield return Snap("diag-3d-only");

        Component mainData = main != null ? main.GetComponent("UniversalAdditionalCameraData") : null;
        object post = GetProp(mainData, "renderPostProcessing");
        SetProp(mainData, "renderPostProcessing", false);
        yield return Snap("diag-no-post");
        if (post is bool b) SetProp(mainData, "renderPostProcessing", b);

        var others = new System.Collections.Generic.List<Camera>();
        foreach (Camera c in FindObjectsByType<Camera>(FindObjectsSortMode.None))
            if (c != main && c.enabled) { c.enabled = false; others.Add(c); }
        Say("other cameras switched off: " + others.Count);
        yield return Snap("diag-main-camera-only");

        bool fog = RenderSettings.fog;
        var ambientMode = RenderSettings.ambientMode;
        Color ambient = RenderSettings.ambientLight;
        RenderSettings.fog = false;
        RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Flat;
        RenderSettings.ambientLight = Color.white;
        GameObject cube = GameObject.CreatePrimitive(PrimitiveType.Cube);
        Shader unlit = Shader.Find("Universal Render Pipeline/Unlit");
        if (unlit != null)
        {
            var m = new Material(unlit);
            m.SetColor("_BaseColor", Color.magenta);
            cube.GetComponent<Renderer>().sharedMaterial = m;
        }
        if (main != null) cube.transform.position = main.transform.position + main.transform.forward * 1.2f;
        cube.transform.localScale = Vector3.one * 0.4f;
        yield return Snap("diag-bright-cube");
        Destroy(cube);
        RenderSettings.fog = fog;
        RenderSettings.ambientMode = ambientMode;
        RenderSettings.ambientLight = ambient;
        foreach (Camera c in others) c.enabled = true;
        foreach (Canvas cv in canvases) if (cv != null) cv.enabled = true;
    }

    IEnumerator Heartbeat()
    {
        // a line every 10 s: frame rate and memory, so a slow or stuck run shows where it is
        int lastFrame = Time.frameCount;
        float last = Time.realtimeSinceStartup;
        while (true)
        {
            yield return new WaitForSecondsRealtime(10f);
            float now = Time.realtimeSinceStartup;
            float fps = (Time.frameCount - lastFrame) / Mathf.Max(0.01f, now - last);
            lastFrame = Time.frameCount;
            last = now;
            Say("alive: " + fps.ToString("0.0") + " fps, memory " +
                (UnityEngine.Profiling.Profiler.GetTotalAllocatedMemoryLong() / 1048576) + " MB used / " +
                (UnityEngine.Profiling.Profiler.GetTotalReservedMemoryLong() / 1048576) + " MB reserved, scene " +
                SceneManager.GetActiveScene().name);
        }
    }

    IEnumerator Start()
    {
        // the emulator's software GPU: smaller textures (top mip levels skipped) and no shadow maps keep it responsive
        QualitySettings.globalTextureMipmapLimit = 1;
        QualitySettings.shadows = ShadowQuality.Disable;
        StartCoroutine(Heartbeat());
        PlayerPrefs.SetString(GameSave.DifficultyKey, "Normal");
        PlayerPrefs.Save();
        Say("files go to " + Application.persistentDataPath);
        Say("started in scene " + SceneManager.GetActiveScene().name + ", screen " + Screen.width + "x" + Screen.height);
        yield return new WaitForSecondsRealtime(10f);
        yield return Snap("menu");

        SceneManager.LoadScene("Main");
        yield return new WaitForSecondsRealtime(3f);
        Say("house loaded: " + SceneManager.GetActiveScene().name);
        // the emulator's software GPU can't show URP's HDR / MSAA / post-processing image: draw straight to the screen
        foreach (Camera c in FindObjectsByType<Camera>(FindObjectsInactive.Include, FindObjectsSortMode.None))
        {
            c.allowHDR = false;
            c.allowMSAA = false;
        }
        yield return Snap("day-1");
        yield return new WaitForSecondsRealtime(4f);
        yield return Snap("waking-up");

        PlayerWakeUp wake = FindFirstObjectByType<PlayerWakeUp>();
        float waitStart = Time.realtimeSinceStartup;
        int framesStart = Time.frameCount;
        while (wake != null && wake.IsWakingUp && Time.realtimeSinceStartup - waitStart < 150f)
            yield return new WaitForSecondsRealtime(1f);
        float waited = Time.realtimeSinceStartup - waitStart;
        Say("wake-up finished after " + waited.ToString("0") + " s, " + ((Time.frameCount - framesStart) / Mathf.Max(0.1f, waited)).ToString("0.0") + " fps");
        yield return new WaitForSecondsRealtime(1.5f);

        GameObject playerObject = GameSave.PlayerObject();
        if (playerObject == null) { Say("no player found"); Say("DONE"); yield break; }
        Transform player = playerObject.transform;
        FPSController fps = player.GetComponent<FPSController>();
        Say("player at " + player.position + ", controls " + (fps != null && fps.enabled ? "on" : "off"));
        // the game's colour grading and vignette stay on for the shots, unless the emulator draws them black
        yield return new WaitForEndOfFrame();
        Texture2D grab = ScreenCapture.CaptureScreenshotAsTexture();
        float sum = 0f;
        int n = 0;
        for (int y = grab.height / 8; y < grab.height * 7 / 8; y += 16)
            for (int x = grab.width / 4; x < grab.width * 3 / 4; x += 16) { sum += grab.GetPixel(x, y).grayscale; n++; }
        Destroy(grab);
        float avg = n > 0 ? sum / n : 0f;
        Say("screen brightness with post-processing: " + avg.ToString("0.000"));
        if (avg < 0.02f)
        {
            Say("too dark on the emulator: post-processing off for the shots");
            foreach (Camera c in FindObjectsByType<Camera>(FindObjectsInactive.Include, FindObjectsSortMode.None))
                SetProp(c.GetComponent("UniversalAdditionalCameraData"), "renderPostProcessing", false);
        }
        yield return Snap("gameplay-bed");
        yield return Diagnose(player);

        // Granny stays where she is for the tour, so she can't catch the camera mid-way
        GrannyAI granny = GrannyAI.Instance != null ? GrannyAI.Instance : FindFirstObjectByType<GrannyAI>();
        if (granny != null)
        {
            Say("granny at " + granny.transform.position);
            granny.enabled = false;
            NavMeshAgent agent = granny.GetComponent<NavMeshAgent>();
            if (agent != null) Say("granny on navmesh: " + agent.isOnNavMesh);
            if (agent != null && agent.isOnNavMesh) { agent.isStopped = true; agent.velocity = Vector3.zero; }
        }
        HideBlackOverlays();

        float yaw = player.eulerAngles.y;
        for (int i = 1; i < 4; i++)
        {
            if (fps != null) fps.SetLook(yaw + i * 90f, 6f);
            yield return Snap("gameplay-bed-turn" + i);
        }

        foreach (string room in Rooms)
        {
            GameObject p = GameObject.Find(room);
            if (p == null) { Say("no " + room); continue; }
            Vector3 at = Floor(p.transform.position);
            Teleport(player, at);
            yield return null;
            float heading = OpenestHeading(at + Vector3.up * 1.5f);
            string label = room.Replace(" Point", "").Replace(" ", "");
            if (fps != null) fps.SetLook(heading + 180f, 8f);
            yield return Snap(label + "-a");
            if (fps != null) fps.SetLook(heading, 8f);
            yield return Snap(label + "-b");
        }

        if (granny != null)
        {
            Vector3 front = granny.transform.forward;
            front.y = 0f;
            if (front.sqrMagnitude < 0.01f) front = Vector3.forward;
            Vector3 spot = Floor(granny.transform.position + front.normalized * 2.6f);
            Teleport(player, spot);
            yield return null;
            Vector3 look = granny.GetHeadLookPoint() - (player.position + Vector3.up * 0.6f);
            float y = Mathf.Atan2(look.x, look.z) * Mathf.Rad2Deg;
            float pitch = -Mathf.Atan2(look.y, new Vector2(look.x, look.z).magnitude) * Mathf.Rad2Deg;
            if (fps != null) fps.SetLook(y, pitch);
            yield return Snap("granny");
        }
        Say("DONE");
    }
}
#endif

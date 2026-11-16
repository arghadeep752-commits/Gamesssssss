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

    IEnumerator Start()
    {
        PlayerPrefs.SetString(GameSave.DifficultyKey, "Normal");
        PlayerPrefs.Save();
        Say("files go to " + Application.persistentDataPath);
        Say("started in scene " + SceneManager.GetActiveScene().name + ", screen " + Screen.width + "x" + Screen.height);
        yield return new WaitForSecondsRealtime(10f);
        yield return Snap("menu");

        SceneManager.LoadScene("Main");
        yield return new WaitForSecondsRealtime(3f);
        Say("house loaded: " + SceneManager.GetActiveScene().name);
        yield return Snap("day-1");
        yield return new WaitForSecondsRealtime(4f);
        yield return Snap("waking-up");
        yield return new WaitForSecondsRealtime(6f);

        GameObject playerObject = GameSave.PlayerObject();
        if (playerObject == null) { Say("no player found"); Say("DONE"); yield break; }
        Transform player = playerObject.transform;
        FPSController fps = player.GetComponent<FPSController>();
        Say("player at " + player.position + ", controls " + (fps != null && fps.enabled ? "on" : "off"));
        yield return Snap("gameplay-bed");

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

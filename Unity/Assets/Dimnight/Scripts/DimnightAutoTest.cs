#if DIMNIGHT_AUTOTEST
using System.Collections;
using System.IO;
using UnityEngine;
using UnityEngine.SceneManagement;

/// <summary>
/// Only in the emulator build (DIMNIGHT_AUTOTEST): shows the menu, then walks a camera through the house - the player's
/// start and every room Granny patrols - and saves a screenshot of each stop for the release page.
/// ci/smoke_test.sh grabs the screen whenever a "[DIMNIGHT-TEST] SNAP name" line appears.
/// </summary>
public class DimnightAutoTest : MonoBehaviour
{
    static readonly string[] Rooms =
    {
        "KitchenRoom Point", "LibraryRoom Point", "BedRoomLeft Point", "BedRoomRight Point", "PlayerBedRoom Point",
        "SecretBookRoom Point", "InnerNosferaRoom Point", "Garage Point", "BackYard Point", "EscapeDoor Point",
    };

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
        string path = Path.Combine(Application.persistentDataPath, "shot_" + name + ".png");
        ScreenCapture.CaptureScreenshot(path);
        Say("SNAP " + name);
        yield return new WaitForSecondsRealtime(3f);
    }

    Camera FreeCamera()
    {
        Camera cam = Camera.main;
        if (cam == null || !cam.isActiveAndEnabled)
            foreach (Camera c in FindObjectsByType<Camera>(FindObjectsSortMode.None))
                if (c.isActiveAndEnabled && c.targetTexture == null) { cam = c; break; }
        if (cam == null) cam = new GameObject("TestCamera").AddComponent<Camera>();
        cam.transform.SetParent(null, true);
        cam.nearClipPlane = 0.05f;
        return cam;
    }

    IEnumerator Start()
    {
        Say("files go to " + Application.persistentDataPath);
        Say("started in scene " + SceneManager.GetActiveScene().name + ", screen " + Screen.width + "x" + Screen.height);
        yield return new WaitForSecondsRealtime(9f);
        yield return Snap("01-menu");

        SceneManager.LoadScene("Main");
        yield return new WaitForSecondsRealtime(8f);
        Say("house loaded: " + SceneManager.GetActiveScene().name);
        Camera cam = FreeCamera();
        Vector3 start = cam.transform.position;
        string[] dirs = { "north", "east", "south", "west" };
        for (int i = 0; i < 4; i++)
        {
            cam.transform.rotation = Quaternion.Euler(8f, i * 90f, 0f);
            yield return Snap("02-start-" + dirs[i]);
        }
        int n = 3;
        foreach (string room in Rooms)
        {
            GameObject p = GameObject.Find(room);
            if (p == null) { Say("no " + room); continue; }
            Vector3 at = p.transform.position;
            if (Physics.Raycast(at + Vector3.up * 0.5f, Vector3.down, out RaycastHit hit, 4f)) at = hit.point;
            cam.transform.position = at + Vector3.up * 1.6f;
            string label = room.Replace(" Point", "").Replace(" ", "");
            cam.transform.rotation = Quaternion.Euler(10f, 0f, 0f);
            yield return Snap(n.ToString("00") + "-" + label + "-a");
            cam.transform.rotation = Quaternion.Euler(10f, 180f, 0f);
            yield return Snap(n.ToString("00") + "-" + label + "-b");
            n++;
        }
        cam.transform.position = start;
        Say("DONE");
    }
}
#endif

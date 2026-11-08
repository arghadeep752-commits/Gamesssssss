#if PROTO_AUTOTEST
using System.Collections;
using UnityEngine;
using UnityEngine.AI;

namespace GridProto
{
    /// <summary>
    /// Only compiled into the emulator test build (never into the phone APK). Plays through the enemy
    /// encounter: spotted -> chased -> player far away (enemy confused) -> caught (grab, punches, caught
    /// screen), freezing the game at each moment so the cloud test can take a screenshot.
    /// </summary>
    public class AutoTest : MonoBehaviour
    {
        IEnumerator Start()
        {
            GameRoot root = GetComponent<GameRoot>();
            Debug.Log("[PROTO-TEST] start " + Screen.width + "x" + Screen.height
                      + " gpu=" + SystemInfo.graphicsDeviceName + " api=" + SystemInfo.graphicsDeviceType
                      + " msaa=" + QualitySettings.antiAliasing);
            PlayerController p = root.player;
            EnemyAI e = root.enemy;
            Jumpscare js = root.jumpscare;
            if (p == null || e == null || js == null)
            {
                Debug.Log("[PROTO-TEST] missing references, player=" + (p != null) + " enemy=" + (e != null) + " jumpscare=" + (js != null));
                Debug.Log("[PROTO-TEST] DONE");
                yield break;
            }

            HouseLighting house = root.GetComponent<HouseLighting>();
            if (house != null)
            {
                yield return HouseTour(p, e, js, house);
                yield break;
            }
            yield return new WaitForSeconds(3f);
            Debug.Log("[PROTO-TEST] enemy on navmesh: " + e.GetComponent<NavMeshAgent>().isOnNavMesh + ", state " + e.Current);
            yield return Snap("01-start");

            // meet the enemy in the open, 9 m apart, facing each other
            e.DebugWarp(new Vector3(0f, 0f, -20f), 0f);
            p.Teleport(new Vector3(0f, 0.05f, -11f), 180f, 2f);
            yield return new WaitForSeconds(0.4f);
            yield return Snap("02-enemy");
            float t = 0f;
            while (e.Current != EnemyAI.State.Chase && t < 6f) { t += Time.deltaTime; yield return null; }
            Debug.Log("[PROTO-TEST] enemy state after seeing the player: " + e.Current);
            yield return new WaitForSeconds(0.7f);
            yield return Snap("03-chase");

            // the player gets very far away: the enemy stops, confused
            p.Teleport(new Vector3(0f, 0.05f, 45f), 180f, 0f);
            t = 0f;
            while (e.Current != EnemyAI.State.Confused && t < 4f) { t += Time.deltaTime; yield return null; }
            Debug.Log("[PROTO-TEST] enemy state when the player is far away: " + e.Current);
            e.perceptionEnabled = false;   // watch it without being noticed
            if (e.Current != EnemyAI.State.Confused) e.DebugConfuse();
            Vector3 front = e.transform.position + e.transform.forward * 5f;
            NavMeshHit hit;
            if (NavMesh.SamplePosition(front, out hit, 3f, NavMesh.AllAreas)) front = hit.position;
            p.Teleport(front + Vector3.up * 0.05f, YawTowards(front, e.transform.position), 4f);
            yield return new WaitForSeconds(1.4f);
            yield return Snap("04-confused");

            // caught
            e.perceptionEnabled = true;
            Vector3 close = e.transform.position + e.transform.forward * 1f;
            p.Teleport(close + Vector3.up * 0.05f, YawTowards(close, e.transform.position), 0f);
            t = 0f;
            while (!js.Active && t < 5f) { t += Time.deltaTime; yield return null; }
            Debug.Log("[PROTO-TEST] jumpscare started: " + js.Active);
            t = 0f;
            while (js.GrabProgress < 0.95f && t < 3f) { t += Time.deltaTime; yield return null; }
            yield return new WaitForSeconds(0.15f);
            yield return Snap("05-grab");
            t = 0f;
            while (js.Impacts < 1 && t < 5f) { t += Time.deltaTime; yield return null; }
            yield return Snap("06-punch");
            t = 0f;
            while (!js.Finished && t < 8f) { t += Time.deltaTime; yield return null; }
            yield return new WaitForSeconds(0.3f);
            yield return Snap("07-caught");
            Debug.Log("[PROTO-TEST] punches landed: " + js.Impacts + ", caught screen: " + js.Finished);
            Debug.Log("[PROTO-TEST] DONE");
        }

        /// <summary>House map: a photo tour of the rooms, then the full enemy encounter inside the house.</summary>
        IEnumerator HouseTour(PlayerController p, EnemyAI e, Jumpscare js, HouseLighting house)
        {
            e.perceptionEnabled = false;
            float t = 0f;
            while (!house.ProbesDone && t < 20f) { t += Time.unscaledDeltaTime; yield return null; }
            yield return new WaitForSeconds(1f);
            e.DebugWarp(new Vector3(-3f, 0f, 13f), 0f);
            Debug.Log("[PROTO-TEST] probes ready after " + t.ToString("0.0") + " s, enemy on navmesh: " + e.GetComponent<NavMeshAgent>().isOnNavMesh);
            HouseData d = house.data;
            int shot = 1;
            for (int i = 0; i < d.viewNames.Length; i++)
            {
                if (d.viewNames[i] == "aerial") continue;
                p.Teleport(d.viewPositions[i] - Vector3.up * 1.59f, d.viewYaw[i], d.viewPitch[i]);
                yield return new WaitForSeconds(2.2f);
                Debug.Log("[PROTO-TEST] view " + d.viewNames[i] + " exposure " + house.Exposure.ToString("0.00") + " at " + p.transform.position);
                yield return Snap(shot.ToString("00") + "-" + d.viewNames[i]);
                shot++;
            }

            // the hooded man in the living room: spotted, chased
            e.perceptionEnabled = true;
            e.DebugWarp(new Vector3(5.4f, 0.3f, 5.0f), 180f);
            p.Teleport(new Vector3(5.4f, 0.33f, 1.3f), 0f, 3f);
            yield return new WaitForSeconds(0.5f);
            yield return Snap(shot.ToString("00") + "-enemy"); shot++;
            t = 0f;
            while (e.Current != EnemyAI.State.Chase && t < 6f) { t += Time.deltaTime; yield return null; }
            Debug.Log("[PROTO-TEST] enemy state after seeing the player: " + e.Current);
            yield return new WaitForSeconds(0.6f);
            yield return Snap(shot.ToString("00") + "-chase"); shot++;

            // the player escapes to the far corner of the garden: the enemy gets confused
            p.Teleport(new Vector3(20.6f, 0.05f, -9.9f), 180f, 0f);
            t = 0f;
            while (e.Current != EnemyAI.State.Confused && t < 5f) { t += Time.deltaTime; yield return null; }
            Debug.Log("[PROTO-TEST] enemy state when the player is far away: " + e.Current);
            e.perceptionEnabled = false;
            if (e.Current != EnemyAI.State.Confused) e.DebugConfuse();
            Vector3 front = e.transform.position + e.transform.forward * 3.5f;
            NavMeshHit hit;
            if (NavMesh.SamplePosition(front, out hit, 3f, NavMesh.AllAreas)) front = hit.position;
            p.Teleport(front + Vector3.up * 0.05f, YawTowards(front, e.transform.position), 4f);
            yield return new WaitForSeconds(1.2f);
            yield return Snap(shot.ToString("00") + "-confused"); shot++;

            // caught
            e.perceptionEnabled = true;
            Vector3 close = e.transform.position + e.transform.forward * 1f;
            p.Teleport(close + Vector3.up * 0.05f, YawTowards(close, e.transform.position), 0f);
            t = 0f;
            while (!js.Active && t < 5f) { t += Time.deltaTime; yield return null; }
            Debug.Log("[PROTO-TEST] jumpscare started: " + js.Active);
            t = 0f;
            while (js.GrabProgress < 0.95f && t < 3f) { t += Time.deltaTime; yield return null; }
            yield return new WaitForSeconds(0.15f);
            yield return Snap(shot.ToString("00") + "-grab"); shot++;
            t = 0f;
            while (js.Impacts < 1 && t < 5f) { t += Time.deltaTime; yield return null; }
            yield return Snap(shot.ToString("00") + "-punch"); shot++;
            t = 0f;
            while (!js.Finished && t < 8f) { t += Time.deltaTime; yield return null; }
            yield return new WaitForSeconds(0.3f);
            yield return Snap(shot.ToString("00") + "-caught");
            Debug.Log("[PROTO-TEST] punches landed: " + js.Impacts + ", caught screen: " + js.Finished);
            Debug.Log("[PROTO-TEST] DONE");
        }

        static float YawTowards(Vector3 from, Vector3 to)
        {
            Vector3 d = to - from;
            d.y = 0f;
            return Mathf.Atan2(d.x, d.z) * Mathf.Rad2Deg;
        }

        // freezes the game for a moment so the test script can screenshot exactly this frame
        IEnumerator Snap(string name)
        {
            float scale = Time.timeScale;
            Time.timeScale = 0f;
            yield return null;
            Debug.Log("[PROTO-TEST] SNAP " + name);
            yield return new WaitForSecondsRealtime(3f);
            Time.timeScale = scale;
        }
    }
}
#endif

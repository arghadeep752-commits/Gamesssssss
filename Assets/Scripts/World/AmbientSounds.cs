using UnityEngine;

namespace NightClass
{
    /// <summary>Random creaks, knocks and whispers around the player every half minute (not on Hard).</summary>
    public class AmbientSounds : MonoBehaviour
    {
        float timer = 12f;

        void Update()
        {
            NCGame g = NCGame.I;
            if (g == null || g.State != GameState.Playing || g.Diff == Difficulty.Hard || FPController.I == null) return;
            timer -= Time.deltaTime;
            if (timer > 0f) return;
            timer = Random.Range(24f, 38f);
            Vector2 r = Random.insideUnitCircle.normalized * Random.Range(5f, 12f);
            Vector3 p = FPController.I.transform.position + new Vector3(r.x, 1.5f, r.y);
            Sfx.Play3D(Sfx.Pick(GameAssets.I.ambientOneShots), p, Random.Range(0.5f, 0.9f), Random.Range(0.9f, 1.05f), 30f);
        }
    }
}

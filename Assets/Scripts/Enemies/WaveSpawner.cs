using System.Collections.Generic;
using UnityEngine;
using UnityEngine.AI;

namespace ZombieStrike
{
    /// <summary>Endless waves: each wave has more (and nastier) zombies, with short breaks in between.</summary>
    public class WaveSpawner : MonoBehaviour
    {
        public int Wave { get; private set; }
        public bool Between { get { return intermission >= 0f; } }
        public int Remaining { get { return queue.Count + Zombie.All.Count; } }

        readonly List<ZombieKind> queue = new List<ZombieKind>();
        List<Vector3> spawns;
        bool useNavMesh;
        bool running;
        float intermission = -1f;
        float spawnTimer;
        float interval;
        int maxAlive;

        public void Init(List<Vector3> spawnPoints, bool navMesh)
        {
            spawns = spawnPoints;
            useNavMesh = navMesh;
        }

        public void Begin()
        {
            running = true;
            Wave = 0;
            intermission = 2.5f;
        }

        void Update()
        {
            if (!running || GameManager.I == null || GameManager.I.State != GameState.Playing) return;
            float dt = Time.deltaTime;

            if (intermission >= 0f)
            {
                intermission -= dt;
                if (intermission < 0f) StartWave(Wave + 1);
                return;
            }

            if (queue.Count > 0)
            {
                spawnTimer -= dt;
                if (spawnTimer <= 0f && Zombie.All.Count < maxAlive)
                {
                    ZombieKind kind = queue[queue.Count - 1];
                    queue.RemoveAt(queue.Count - 1);
                    Zombie.Spawn(kind, PickSpawn(), Wave);
                    if (kind == ZombieKind.Brute && Sfx.I != null) Sfx.I.Play2D("brute_roar", 0.45f, 0.8f);
                    spawnTimer = interval;
                }
            }
            else if (Zombie.All.Count == 0)
            {
                GameManager.I.OnWaveCleared(Wave);
                intermission = 7f;
            }
        }

        void StartWave(int n)
        {
            Wave = n;
            int total = Mathf.Min(6 + (n - 1) * 4, 70);
            int brutes = n >= 3 ? 1 + (n - 3) / 2 : 0;
            int runners = n >= 2 ? Mathf.RoundToInt(total * Mathf.Min(0.15f + 0.05f * (n - 2), 0.4f)) : 0;
            int walkers = Mathf.Max(0, total - brutes - runners);

            queue.Clear();
            // the queue is consumed from the end: brutes arrive in the second half of the wave
            var early = new List<ZombieKind>();
            for (int i = 0; i < walkers; i++) early.Add(ZombieKind.Walker);
            for (int i = 0; i < runners; i++) early.Add(ZombieKind.Runner);
            Shuffle(early);
            int split = early.Count / 2;
            for (int i = 0; i < brutes; i++) queue.Add(ZombieKind.Brute);
            for (int i = split; i < early.Count; i++) queue.Add(early[i]);
            var late = new List<ZombieKind>();
            for (int i = 0; i < split; i++) late.Add(early[i]);
            Shuffle(queue);
            queue.AddRange(late);

            maxAlive = Mathf.Min(5 + n, 14);
            interval = Mathf.Max(1.5f - n * 0.08f, 0.55f);
            spawnTimer = 0.5f;
            GameManager.I.OnWaveStarted(n);
        }

        static void Shuffle(List<ZombieKind> list)
        {
            for (int i = list.Count - 1; i > 0; i--)
            {
                int j = Random.Range(0, i + 1);
                ZombieKind tmp = list[i];
                list[i] = list[j];
                list[j] = tmp;
            }
        }

        Vector3 PickSpawn()
        {
            PlayerController p = PlayerController.I;
            Vector3 pp = p != null ? p.transform.position : Vector3.zero;
            Vector3 fwd = p != null ? p.transform.forward : Vector3.forward;
            Vector3 best = spawns.Count > 0 ? spawns[0] : new Vector3(0f, 0f, 40f);
            float bestScore = float.MinValue;
            foreach (Vector3 s in spawns)
            {
                Vector3 d = s - pp;
                d.y = 0f;
                float dist = d.magnitude;
                if (dist < 16f) continue;
                // mostly in front of / beside the player, so zombies are seen coming out of the fog
                float facing = Vector3.Dot(fwd, d / Mathf.Max(dist, 0.01f));
                float score = facing * 6f - Mathf.Abs(dist - 24f) * 0.35f + Random.Range(0f, 8f);
                if (score > bestScore)
                {
                    bestScore = score;
                    best = s;
                }
            }
            Vector3 jitter = new Vector3(Random.Range(-1.5f, 1.5f), 0f, Random.Range(-1.5f, 1.5f));
            Vector3 pos = best + jitter;
            if (useNavMesh)
            {
                NavMeshHit hit;
                if (NavMesh.SamplePosition(pos, out hit, 2f, NavMesh.AllAreas)) return hit.position;
                return best;
            }
            return pos;
        }
    }
}

using System;
using System.Collections.Generic;
using UnityEngine;

namespace Moulika
{
    /// <summary>
    /// Moulika ma'am, the school's ghost (a Hyper3D Rodin character, rigged and animated by Rodin).
    /// She patrols the school, follows noises, and chases you when she sees you. Port of game/scripts/ragini.gd.
    /// </summary>
    public class Enemy : MonoBehaviour
    {
        public enum State { Patrol, Investigate, Chase, Search, Attack, Frozen }

        public const float Height = 1.68f;
        public event Action Caught;
        public event Action Spotted;

        public Level level;
        public Player player;
        public GameAudio sound;
        public State state = State.Patrol;
        public Animation anim;

        List<Vector3> path = new List<Vector3>();
        int pathI;
        float repathT, waitT, seeT, stepT, laughT = 20f;
        Vector3 lastSeen;
        float walkSpeed = 1.9f, chaseSpeed = 3.3f, hearing = 1f, sight = 13f;
        float walkNat = 1.25f, runNat = 3.3f;
        string curAnim = "";
        float eyeH = Height - 0.12f;
        Material mat;
        readonly Vector4[] lpos = new Vector4[5];
        readonly Vector4[] lcol = new Vector4[5];
        float[] lampD;
        static readonly Color EyeLight = new Color(0.72f, 0.8f, 1f).linear * 0.35f;

        public float Yaw
        {
            get { return transform.eulerAngles.y; }
            set { transform.rotation = Quaternion.Euler(0f, value, 0f); }
        }

        public void Setup(int mode)
        {
            walkSpeed = new[] { 1.5f, 1.9f, 2.4f }[mode];
            chaseSpeed = new[] { 2.7f, 3.3f, 3.9f }[mode];
            hearing = new[] { 0.6f, 1f, 1.5f }[mode];
            sight = new[] { 10f, 13f, 17f }[mode];
        }

        public bool Build()
        {
            var prefab = Resources.Load<GameObject>("Moulika");
            if (prefab == null) return false;
            GameObject m = Instantiate(prefab, transform);
            m.name = "Moulika model";
            var rig = m.GetComponent<MoulikaRig>();
            if (rig != null)
            {
                anim = rig.anim;
                walkNat = rig.walkNat;
                runNat = rig.runNat;
                if (rig.body != null) mat = rig.body.material;
            }
            Play("idle");
            return true;
        }

        public void Play(string a, float blend = 0.25f, float speed = 1f)
        {
            if (anim == null) return;
            AnimationState st = anim[a];
            if (st == null) return;
            if (curAnim == a && anim.IsPlaying(a))
            {
                st.speed = speed;
                return;
            }
            curAnim = a;
            st.speed = speed;
            st.time = 0f;
            if (blend <= 0f) anim.Play(a);
            else anim.CrossFade(a, blend);
        }

        public Vector3 Eyes { get { return transform.position + new Vector3(0f, eyeH, 0f); } }
        public Vector3 FaceDir { get { return transform.forward; } }

        void MoveAnim(float speed)
        {
            // walk, or run once walking would look rushed
            if (speed / walkNat <= 1.45f) Play("walk", 0.3f, speed / walkNat);
            else Play("run", 0.3f, speed / runNat);
        }

        public bool CanSeePlayer()
        {
            if (player == null || player.hidden) return false;
            Vector3 to = player.Head - Eyes;
            float d = to.magnitude;
            float rng = sight * (player.crouched ? 0.5f : 1f);
            if (d > rng) return false;
            Vector3 flat = new Vector3(to.x, 0f, to.z).normalized;
            if (d > 1.8f && Vector3.Dot(FaceDir, flat) < 0.25f) return false;
            return !Physics.Linecast(Eyes, player.Head - new Vector3(0f, 0.15f, 0f), Level.WallMask, QueryTriggerInteraction.Ignore);
        }

        public void Hear(Vector3 pos, float radius)
        {
            if (state == State.Chase || state == State.Attack || state == State.Frozen) return;
            if (Vector3.Distance(transform.position, pos) > radius * hearing * 2.2f) return;
            state = State.Investigate;
            Go(pos);
            waitT = 0f;
        }

        void Go(Vector3 pos)
        {
            path = level.FindPath(transform.position, pos);
            pathI = 0;
            repathT = 0.6f;
            // skip the cells she is already standing on, so a new path never costs her a step
            Vector3 me = transform.position;
            while (pathI < path.Count - 1 && new Vector2(path[pathI].x - me.x, path[pathI].z - me.z).magnitude < 0.25f) pathI++;
        }

        public void PickPatrol()
        {
            List<object> pts = Json.A(level.meta, "patrol");
            Vector3 best = Vector3.zero;
            float bestD = 1e9f;
            // prefer points nearer the player a little, so the school never feels empty
            for (int k = 0; k < 3; k++)
            {
                Vector3 v = Json.GV(pts[UnityEngine.Random.Range(0, pts.Count)]);
                v.y = 0f;
                float d = player != null ? Vector3.Distance(v, player.transform.position) : 0f;
                if (d < bestD && Vector3.Distance(v, transform.position) > 5f)
                {
                    bestD = d;
                    best = v;
                }
            }
            if (best == Vector3.zero)
            {
                best = Json.GV(pts[UnityEngine.Random.Range(0, pts.Count)]);
                best.y = 0f;
            }
            Go(best);
        }

        /// <summary>Moves along the path; true when the end is reached.</summary>
        bool Follow(float dt, float speed)
        {
            if (pathI >= path.Count) return true;
            Vector3 to = path[pathI] - transform.position;
            to.y = 0f;
            float d = to.magnitude;
            if (d < 0.25f)
            {
                pathI++;
                return pathI >= path.Count;
            }
            Vector3 dir = to / d;
            Vector3 p = transform.position + dir * Mathf.Min(speed * dt, d);
            p.y = 0f;
            transform.position = p;
            float want = Mathf.Atan2(dir.x, dir.z) * Mathf.Rad2Deg;
            Yaw = Mathf.LerpAngle(Yaw, want, Mathf.Clamp01(dt * 7f));
            OpenDoors();
            stepT += dt * speed;
            if (stepT > 1.5f)
            {
                stepT = 0f;
                if (sound != null)
                {
                    sound.Play3D("payal", transform.position + new Vector3(0f, 0.2f, 0f), -2f, UnityEngine.Random.Range(0.95f, 1.05f));
                    sound.Play3D("footstep_" + UnityEngine.Random.Range(1, 7), transform.position, -6f, UnityEngine.Random.Range(0.78f, 0.86f));
                }
            }
            return false;
        }

        void OpenDoors()
        {
            foreach (Level.Door d in level.doors.Values)
            {
                if (d.open || d.lockId == "main") continue;
                if (new Vector2(d.pos.x - transform.position.x, d.pos.z - transform.position.z).magnitude < 1.4f)
                    level.ToggleDoor(d, true);
            }
        }

        public void Freeze(bool on)
        {
            state = on ? State.Frozen : State.Patrol;
            if (!on)
            {
                path = new List<Vector3>();
                pathI = 0;
            }
        }

        void Update()
        {
            UpdateLights();
            float dt = Time.deltaTime;
            if (level == null || player == null || state == State.Frozen || dt <= 0f) return;
            bool sees = CanSeePlayer();
            if (sees)
            {
                seeT = 0f;
                lastSeen = player.transform.position;
            }
            else seeT += dt;
            float dist = Vector3.Distance(transform.position, player.transform.position);
            switch (state)
            {
                case State.Patrol:
                    MoveAnim(walkSpeed);
                    if (sees) StartChase();
                    else if (Follow(dt, walkSpeed))
                    {
                        waitT += dt;
                        Play("idle");
                        if (waitT > 2.5f)
                        {
                            waitT = 0f;
                            PickPatrol();
                        }
                    }
                    laughT -= dt;
                    if (laughT < 0f)
                    {
                        laughT = UnityEngine.Random.Range(25f, 50f);
                        if (sound != null && dist < 22f)
                            sound.Play3D(UnityEngine.Random.Range(0, 2) == 0 ? "laugh" : "whisper", transform.position + new Vector3(0f, 1.5f, 0f), -4f);
                    }
                    break;
                case State.Investigate:
                    MoveAnim(walkSpeed * 1.25f);
                    if (sees) StartChase();
                    else if (Follow(dt, walkSpeed * 1.25f))
                    {
                        Play("idle");
                        waitT += dt;
                        Yaw -= dt * 1.2f * Mathf.Rad2Deg;
                        if (waitT > 3.5f)
                        {
                            waitT = 0f;
                            state = State.Patrol;
                            PickPatrol();
                        }
                    }
                    break;
                case State.Chase:
                    Play("run", 0.2f, chaseSpeed / runNat);
                    repathT -= dt;
                    if (repathT <= 0f)
                    {
                        Go(sees || seeT < 1.5f ? player.transform.position : lastSeen);
                        repathT = 0.35f;
                    }
                    bool hiddenSeen = player.hidden && seeT < 2f;
                    if (dist < 1.35f && (sees || hiddenSeen || seeT < 0.6f))
                    {
                        Attack();
                        return;
                    }
                    bool done = Follow(dt, chaseSpeed);
                    if (seeT > 5f || (done && seeT > 1.5f))
                    {
                        state = State.Search;
                        waitT = 0f;
                        if (sound != null) sound.SetVol("heartbeat", -60f);
                    }
                    break;
                case State.Search:
                    Play("idle");
                    Yaw -= dt * 1.6f * Mathf.Rad2Deg;
                    waitT += dt;
                    if (sees) StartChase();
                    else if (waitT > 4f)
                    {
                        state = State.Patrol;
                        PickPatrol();
                    }
                    break;
            }
        }

        void StartChase()
        {
            if (state != State.Chase)
            {
                if (Spotted != null) Spotted();
                if (sound != null) sound.Play3D("spotted", Eyes, 2f);
            }
            state = State.Chase;
            repathT = 0f;
        }

        void Attack()
        {
            state = State.Attack;
            Vector3 to = player.transform.position - transform.position;
            Yaw = Mathf.Atan2(to.x, to.z) * Mathf.Rad2Deg;
            Play("attack", 0.1f, 1.3f);
            if (Caught != null) Caught();
        }

        /// <summary>The nearest lamps and the cold glow in front of her face light her (Godot OmniLight3D).</summary>
        void UpdateLights()
        {
            if (mat == null) return;
            lpos[0] = transform.TransformPoint(new Vector3(0f, 1.35f, 0.55f));
            lpos[0].w = 2.2f;
            lcol[0] = EyeLight;
            int n = 1;
            if (level != null)
            {
                // the four nearest lamps within reach (no allocations: this runs every frame)
                Vector3 me = transform.position + Vector3.up;
                int count = level.lamps.Count;
                if (lampD == null || lampD.Length != count) lampD = new float[count];
                for (int i = 0; i < count; i++) lampD[i] = (level.lamps[i].pos - me).sqrMagnitude;
                for (; n < 5; n++)
                {
                    int best = -1;
                    float bd = 7.5f * 7.5f;
                    for (int i = 0; i < count; i++)
                        if (lampD[i] < bd) { bd = lampD[i]; best = i; }
                    if (best < 0) break;
                    lampD[best] = float.MaxValue;
                    Level.Lamp l = level.lamps[best];
                    lpos[n] = new Vector4(l.pos.x, l.pos.y, l.pos.z, 7.5f);
                    lcol[n] = l.color;
                }
            }
            for (; n < 5; n++)
            {
                lpos[n] = Vector4.zero;
                lcol[n] = Vector4.zero;
            }
            mat.SetVectorArray("_LPos", lpos);
            mat.SetVectorArray("_LCol", lcol);
        }
    }
}

using System;
using System.Collections.Generic;
using UnityEngine;

namespace TradersMadness
{
    /// <summary>
    /// The binary trader (a Hyper3D Rodin character, rigged and animated by Rodin). He walks between his rooms on both
    /// floors, takes the stairs, follows noises, chases you when he sees you, and punches when he catches you.
    /// </summary>
    public class Enemy : MonoBehaviour
    {
        public enum State { Patrol, Investigate, Chase, Search, Attack, Frozen }

        public const float Height = 1.8f;
        public event Action Caught;
        public event Action Spotted;

        public Level level;
        public Player player;
        public GameAudio sound;
        public State state = State.Patrol;
        public Animation anim;

        List<Vector3> path = new List<Vector3>();
        int pathI;
        Vector3 segFrom;
        float repathT, waitT, seeT, stepT, mutterT = 18f;
        Vector3 lastSeen;
        float walkSpeed = 1.7f, chaseSpeed = 3.0f, hearing = 1f, sight = 13f;
        float walkNat = 1.3f, runNat = 3.2f;
        string curAnim = "", idleAnim = "idle";
        Material mat;
        readonly Vector4[] lpos = new Vector4[5];
        readonly Vector4[] lcol = new Vector4[5];
        float[] lampD;
        static readonly Color FaceLight = new Color(0.72f, 0.8f, 1f).linear * 0.3f;

        public float Yaw
        {
            get { return transform.eulerAngles.y; }
            set { transform.rotation = Quaternion.Euler(0f, value, 0f); }
        }

        public void Setup(int mode)
        {
            walkSpeed = new[] { 1.4f, 1.7f, 2.05f }[mode];
            chaseSpeed = new[] { 2.6f, 3.0f, 3.5f }[mode];
            hearing = new[] { 0.6f, 1f, 1.45f }[mode];
            sight = new[] { 10f, 13f, 16f }[mode];
        }

        public bool Build()
        {
            var prefab = Resources.Load<GameObject>("Trader");
            if (prefab == null) return false;
            GameObject m = Instantiate(prefab, transform);
            m.name = "Trader model";
            var rig = m.GetComponent<TraderRig>();
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

        public bool Has(string a) { return anim != null && anim[a] != null; }

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

        public Vector3 Eyes { get { return transform.position + new Vector3(0f, Height - 0.12f, 0f); } }
        public Vector3 FaceDir { get { return transform.forward; } }
        public Vector3 HeadPos { get { return transform.position + new Vector3(0f, Height - 0.15f, 0f); } }

        void MoveAnim(float speed)
        {
            if (speed / walkNat <= 1.45f) Play("walk", 0.3f, speed / walkNat);
            else Play("run", 0.3f, speed / runNat);
        }

        public bool CanSeePlayer()
        {
            if (player == null || player.hidden) return false;
            Vector3 to = player.Head - Eyes;
            float d = to.magnitude;
            float rng = sight * (player.crouched ? 0.55f : 1f);
            if (d > rng) return false;
            if (Mathf.Abs(to.y) > 2.6f) return false;
            Vector3 flat = new Vector3(to.x, 0f, to.z).normalized;
            if (d > 1.8f && Vector3.Dot(FaceDir, flat) < 0.25f) return false;
            return !Physics.Linecast(Eyes, player.Head - new Vector3(0f, 0.15f, 0f), Level.WallMask, QueryTriggerInteraction.Ignore);
        }

        public void Hear(Vector3 pos, float radius)
        {
            if (state == State.Chase || state == State.Attack || state == State.Frozen) return;
            float d = Vector3.Distance(transform.position, pos);
            if (Mathf.Abs(pos.y - transform.position.y) > 2f) d += 5f;      // through the floor
            if (d > radius * hearing * 2.2f) return;
            state = State.Investigate;
            Go(pos);
            waitT = 0f;
        }

        void Go(Vector3 pos)
        {
            path = level.FindPath(transform.position, pos);
            pathI = 0;
            segFrom = transform.position;
            repathT = 0.6f;
            Vector3 me = transform.position;
            while (pathI < path.Count - 1 && new Vector2(path[pathI].x - me.x, path[pathI].z - me.z).magnitude < 0.25f
                   && Mathf.Abs(path[pathI].y - me.y) < 0.3f) pathI++;
        }

        bool PointOk(Vector3 v)
        {
            Level.Door g;
            if (level.doors.TryGetValue("door_garage", out g) && g.Locked && Level.RoomAt(level.meta, v) == "garage") return false;
            return true;
        }

        public void PickPatrol()
        {
            List<object> pts = Json.A(level.meta, "patrol");
            Vector3 best = Vector3.zero;
            float bestD = 1e9f;
            bool any = false;
            // prefer points nearer the player a little, so the house never feels empty
            for (int k = 0; k < 4; k++)
            {
                Vector3 v = Json.V3(pts[UnityEngine.Random.Range(0, pts.Count)]);
                if (!PointOk(v) || Vector3.Distance(v, transform.position) < 4f) continue;
                float d = player != null ? Vector3.Distance(v, player.transform.position) + Mathf.Abs(v.y - player.transform.position.y) * 2f : 0f;
                if (d < bestD)
                {
                    bestD = d;
                    best = v;
                    any = true;
                }
            }
            if (!any)
            {
                best = Json.V3(pts[UnityEngine.Random.Range(0, pts.Count)]);
                if (!PointOk(best)) best = Json.V3(pts[0]);
            }
            Go(best);
        }

        /// <summary>Moves along the path (up and down the stair too); true when the end is reached.</summary>
        bool Follow(float dt, float speed)
        {
            if (pathI >= path.Count) return true;
            Vector3 target = path[pathI];
            Vector3 to = target - transform.position;
            to.y = 0f;
            float d = to.magnitude;
            if (d < 0.22f)
            {
                segFrom = target;
                transform.position = new Vector3(transform.position.x, target.y, transform.position.z);
                pathI++;
                return pathI >= path.Count;
            }
            Vector3 dir = to / d;
            Vector3 p = transform.position + dir * Mathf.Min(speed * dt, d);
            // height: along the segment from the last point to this one (the stair rises cell by cell)
            Vector3 seg = target - segFrom;
            seg.y = 0f;
            float segLen = seg.magnitude;
            float done = segLen > 0.01f ? Mathf.Clamp01(1f - new Vector2(target.x - p.x, target.z - p.z).magnitude / segLen) : 1f;
            p.y = Mathf.Lerp(segFrom.y, target.y, done);
            transform.position = p;
            float want = Mathf.Atan2(dir.x, dir.z) * Mathf.Rad2Deg;
            Yaw = Mathf.LerpAngle(Yaw, want, Mathf.Clamp01(dt * 7f));
            OpenDoors();
            stepT += dt * speed;
            if (stepT > 1.45f)
            {
                stepT = 0f;
                if (sound != null)
                    sound.Play3D("footstep_" + UnityEngine.Random.Range(1, 7), transform.position, -3f, UnityEngine.Random.Range(0.78f, 0.86f));
            }
            return false;
        }

        void OpenDoors()
        {
            foreach (Level.Door d in level.doors.Values)
            {
                if (d.open || d.Locked) continue;
                if (Mathf.Abs(d.pos.y - 1.1f - transform.position.y) > 1.5f) continue;
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
                segFrom = transform.position;
            }
        }

        void Update()
        {
            UpdateLights();
            float dt = Time.deltaTime;
            if (level == null || player == null || state == State.Frozen || state == State.Attack || dt <= 0f) return;
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
                    if (sees) { StartChase(); break; }
                    if (!Follow(dt, walkSpeed))
                    {
                        MoveAnim(walkSpeed);
                        waitT = 0f;
                    }
                    else
                    {
                        if (waitT == 0f)
                            idleAnim = Has("taunt") && UnityEngine.Random.value < 0.3f ? "taunt" : (Has("look") && UnityEngine.Random.value < 0.5f ? "look" : "idle");
                        Play(idleAnim, 0.3f);
                        waitT += dt;
                        if (waitT > 3f)
                        {
                            waitT = 0f;
                            PickPatrol();
                        }
                    }
                    mutterT -= dt;
                    if (mutterT < 0f)
                    {
                        mutterT = UnityEngine.Random.Range(22f, 45f);
                        if (sound != null && dist < 20f)
                            sound.Play3D(UnityEngine.Random.Range(0, 2) == 0 ? "laugh" : "grunt", HeadPos, -8f, UnityEngine.Random.Range(0.9f, 1.0f));
                    }
                    break;
                case State.Investigate:
                    if (sees) { StartChase(); break; }
                    if (!Follow(dt, walkSpeed * 1.3f)) MoveAnim(walkSpeed * 1.3f);
                    else
                    {
                        Play(Has("look") ? "look" : "idle", 0.3f);
                        waitT += dt;
                        Yaw -= dt * 60f;
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
                    if (dist < 1.35f && Mathf.Abs(player.transform.position.y - transform.position.y) < 1.2f && (sees || hiddenSeen || seeT < 0.6f))
                    {
                        Attack();
                        return;
                    }
                    bool done = Follow(dt, chaseSpeed);
                    if (seeT > 5f || (done && seeT > 1.5f))
                    {
                        state = State.Search;
                        waitT = 0f;
                    }
                    break;
                case State.Search:
                    Play(Has("look") ? "look" : "idle", 0.3f);
                    Yaw -= dt * 90f;
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
                if (sound != null)
                {
                    sound.Play3D("spotted", Eyes, 0f);
                    sound.Play3D("grunt", HeadPos, -1f);
                }
            }
            state = State.Chase;
            repathT = 0f;
        }

        void Attack()
        {
            state = State.Attack;
            Vector3 to = player.transform.position - transform.position;
            Yaw = Mathf.Atan2(to.x, to.z) * Mathf.Rad2Deg;
            Play("attack", 0.1f, 1.2f);
            if (Caught != null) Caught();
        }

        /// <summary>The nearest lamps and a faint glow in front of his face light him.</summary>
        void UpdateLights()
        {
            if (mat == null) return;
            lpos[0] = transform.TransformPoint(new Vector3(0f, 1.45f, 0.6f));
            lpos[0].w = 2.2f;
            lcol[0] = FaceLight;
            int n = 1;
            if (level != null)
            {
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

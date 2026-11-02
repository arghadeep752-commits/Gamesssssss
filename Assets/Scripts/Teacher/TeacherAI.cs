using UnityEngine;
using UnityEngine.AI;

namespace NightClass
{
    /// <summary>
    /// The teacher. Patrols random rooms (waits a few seconds at each), sees in a cone, hears dropped
    /// things and loud noises, chases on sight, gives up 5 s after losing you, opens doors, drags you
    /// out of a hiding place if she saw you get in, and flees for 30 s when burned by the torch.
    /// Ghost difficulty: she wanders but can't see or catch you.
    /// </summary>
    [RequireComponent(typeof(NavMeshAgent))]
    public class TeacherAI : MonoBehaviour
    {
        public static TeacherAI I { get; private set; }

        public enum Mode { Patrol, Wait, Investigate, Search, Chase, GoToHide, Burned, Frozen }

        public Transform[] patrolPoints;
        public Transform spawn;
        public Transform eye;
        public Transform jumpscareCam;
        public TeacherRig rig;
        public ParticleSystem burnFire;
        public ParticleSystem burnSmoke;
        public Light faceLight;

        public float patrolSpeed = 1.45f;
        public float investigateSpeed = 2.2f;
        public float chaseSpeed = 3.25f;
        public float viewDistance = 15f;
        public float viewHalfAngle = 62f;
        public float giveUpTime = 5f;

        NavMeshAgent agent;
        Mode mode = Mode.Patrol;
        Difficulty diff = Difficulty.Normal;
        bool started, menuMode, seeing, canHunt = true;
        float timer, lastSeen = -99f, nextVision, nextDoor, nextRepath, stepDist, burnT;
        Vector3 lastKnown;
        HidingSpot targetSpot;
        int lastPoint = -1;
        NavMeshPath patrolPath;
        AudioSource voice;
        Camera jumpCam;
        Transform jumpCamPrevParent;

        const int SightMask = (1 << 0) | (1 << 9);

        public Mode CurrentMode { get { return mode; } }
        public bool IsChasing { get { return mode == Mode.Chase || mode == Mode.GoToHide; } }
        public bool IsActiveHunter { get { return started && canHunt && !menuMode && mode != Mode.Burned && mode != Mode.Frozen; } }
        public bool Seeing { get { return seeing; } }

        void Awake()
        {
            I = this;
            agent = GetComponent<NavMeshAgent>();
            agent.enabled = false;
        }

        void Start()
        {
            voice = Sfx.Loop(gameObject, GameAssets.I.teacherHum, 0.0f, 14f);
        }

        public void Configure(Difficulty d)
        {
            diff = d;
            canHunt = d != Difficulty.Ghost;
            switch (d)
            {
                case Difficulty.Ghost:
                    patrolSpeed = 1.4f; chaseSpeed = 3f; viewDistance = 0f; break;
                case Difficulty.Normal:
                    patrolSpeed = 1.45f; investigateSpeed = 2.2f; chaseSpeed = 3.2f; viewDistance = 15f; break;
                case Difficulty.Hard:
                    patrolSpeed = 1.75f; investigateSpeed = 2.6f; chaseSpeed = 3.65f; viewDistance = 19f; giveUpTime = 7f; break;
            }
            if (started) agent.speed = patrolSpeed;
        }

        public void SetMenuMode(bool on)
        {
            menuMode = on;
            if (on && started && mode != Mode.Patrol && mode != Mode.Wait) GoPatrol();
        }

        void Init()
        {
            agent.enabled = true;
            agent.Warp(spawn != null ? spawn.position : transform.position);
            agent.speed = patrolSpeed;
            agent.angularSpeed = 420f;
            agent.acceleration = 9f;
            agent.stoppingDistance = 0.25f;
            agent.autoBraking = true;
            started = true;
            GoPatrol();
        }

        // ------------------------------------------------------------------ public events
        public static void HearNoise(Vector3 pos, float radius)
        {
            if (I != null) I.Hear(pos, radius);
        }

        public void Hear(Vector3 pos, float radius)
        {
            if (!started || menuMode || mode == Mode.Burned || mode == Mode.Frozen || mode == Mode.Chase || mode == Mode.GoToHide) return;
            if (Vector3.Distance(pos, transform.position) > radius) return;
            mode = Mode.Investigate;
            lastKnown = pos;
            agent.isStopped = false;
            agent.speed = investigateSpeed;
            SetDest(pos);
            if (rig != null) rig.Alert();
        }

        public void OnPlayerHid(HidingSpot s)
        {
            if (!IsActiveHunter) return;
            if (IsChasing && Time.time - lastSeen < 1.8f)
            {
                mode = Mode.GoToHide;
                targetSpot = s;
                agent.speed = chaseSpeed;
                SetDest(s.exitPoint.position);
            }
            else if (IsChasing)
            {
                mode = Mode.Search;
                SetDest(lastKnown);
            }
        }

        public void Burn()
        {
            if (!started || mode == Mode.Burned || mode == Mode.Frozen) return;
            mode = Mode.Burned;
            burnT = 30f;
            agent.isStopped = true;
            agent.velocity = Vector3.zero;
            if (rig != null) rig.SetBurned(true);
            if (burnFire != null) burnFire.Play(true);
            if (burnSmoke != null) burnSmoke.Play(true);
            Sfx.Play3D(GameAssets.I.burnScream, transform.position + Vector3.up * 1.5f, 1f, 1f, 40f);
            if (NCGame.I != null) NCGame.I.Message("She's burning! You have 30 seconds.", 3f);
        }

        public void BeginJumpscare(Camera cam)
        {
            mode = Mode.Frozen;
            if (agent.enabled) { agent.isStopped = true; agent.velocity = Vector3.zero; }
            FPController p = FPController.I;
            if (p != null)
            {
                Vector3 d = p.transform.position - transform.position;
                d.y = 0f;
                if (d.sqrMagnitude > 0.01f) transform.rotation = Quaternion.LookRotation(d);
            }
            jumpCam = cam;
            jumpCamPrevParent = cam.transform.parent;
            cam.transform.SetParent(jumpscareCam, false);
            cam.transform.localPosition = Vector3.zero;
            cam.transform.localRotation = Quaternion.identity;
            cam.fieldOfView = 52f;
            if (faceLight != null) faceLight.enabled = true;
            if (rig != null) rig.SetAttack(true);
            if (voice != null) voice.volume = 0f;
            Sfx.Play2D(GameAssets.I.scream, 1f);
            Sfx.Play2D(GameAssets.I.rulerHit, 0.8f, 0.9f);
        }

        public void EndJumpscare()
        {
            if (rig != null) rig.SetAttack(false);
            if (faceLight != null) faceLight.enabled = false;
            if (jumpCam != null && jumpCam.transform.parent == jumpscareCam) jumpCam.transform.SetParent(jumpCamPrevParent, true);
            jumpCam = null;
        }

        public void ResetToSpawn()
        {
            lastSeen = -99f;
            seeing = false;
            if (rig != null) { rig.SetBurned(false); rig.SetAttack(false); }
            if (burnFire != null) burnFire.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            if (started)
            {
                agent.Warp(spawn != null ? spawn.position : transform.position);
                agent.isStopped = false;
            }
            GoPatrol();
        }

        public void Freeze()
        {
            mode = Mode.Frozen;
            if (agent.enabled) { agent.isStopped = true; agent.velocity = Vector3.zero; }
        }

        // ------------------------------------------------------------------ update
        void Update()
        {
            if (!started)
            {
                if (!NavBaker.Ready) return;
                Init();
            }
            float dt = Time.deltaTime;
            NCGame g = NCGame.I;
            bool playing = g != null && g.State == GameState.Playing;
            if (!playing && !menuMode)
            {
                // frozen while paused / during cinematics
                if (agent.enabled && !agent.isStopped && (g == null || g.State != GameState.Caught)) agent.isStopped = true;
                AnimateRig(dt);
                return;
            }
            if (mode != Mode.Burned && mode != Mode.Frozen && agent.isStopped) agent.isStopped = false;

            // vision
            if (Time.time >= nextVision)
            {
                nextVision = Time.time + 0.12f;
                seeing = playing && canHunt && !menuMode && mode != Mode.Burned && mode != Mode.Frozen && See();
                if (seeing)
                {
                    lastSeen = Time.time;
                    lastKnown = FPController.I.transform.position;
                    if (mode != Mode.Chase && mode != Mode.GoToHide) StartChase();
                }
            }

            switch (mode)
            {
                case Mode.Patrol:
                    agent.speed = patrolSpeed;
                    if (Arrived()) { mode = Mode.Wait; timer = Random.Range(4f, 6f); }
                    break;
                case Mode.Wait:
                    timer -= dt;
                    if (timer <= 0f) GoPatrol();
                    break;
                case Mode.Investigate:
                    if (Arrived()) { mode = Mode.Search; timer = 4f; }
                    break;
                case Mode.Search:
                    if (Arrived())
                    {
                        timer -= dt;
                        if (timer <= 0f) GoPatrol();
                    }
                    break;
                case Mode.Chase:
                    agent.speed = chaseSpeed;
                    if (Time.time >= nextRepath)
                    {
                        nextRepath = Time.time + 0.2f;
                        SetDest(seeing ? FPController.I.transform.position : lastKnown);
                    }
                    if (!seeing && Time.time - lastSeen > giveUpTime)
                    {
                        mode = Mode.Search;
                        timer = 4f;
                        SetDest(lastKnown);
                    }
                    TryCatch();
                    break;
                case Mode.GoToHide:
                    if (targetSpot == null || FPController.I == null || !FPController.I.Hidden) { mode = Mode.Search; timer = 3f; break; }
                    if (Vector3.Distance(transform.position, targetSpot.exitPoint.position) < 1.1f)
                    {
                        targetSpot.TeacherOpen();
                        Catch();
                    }
                    break;
                case Mode.Burned:
                    burnT -= dt;
                    if (burnT < 27f && burnFire != null && burnFire.isPlaying) burnFire.Stop(true, ParticleSystemStopBehavior.StopEmitting);
                    if (burnT <= 0f)
                    {
                        if (rig != null) rig.SetBurned(false);
                        if (burnSmoke != null) burnSmoke.Stop(true, ParticleSystemStopBehavior.StopEmitting);
                        agent.isStopped = false;
                        GoPatrol();
                    }
                    break;
            }

            // doors in the way
            if (Time.time >= nextDoor && mode != Mode.Burned && mode != Mode.Frozen)
            {
                nextDoor = Time.time + 0.2f;
                Vector3 c = transform.position + transform.forward * 0.6f + Vector3.up * 1f;
                Collider[] hits = Physics.OverlapSphere(c, 1.1f, 1 << 9, QueryTriggerInteraction.Collide);
                foreach (Collider h in hits)
                {
                    Door d = h.GetComponentInParent<Door>();
                    if (d != null) d.TeacherOpen(transform.position);
                }
            }

            UpdateAudio(dt);
            AnimateRig(dt);
        }

        bool Arrived()
        {
            return agent.enabled && !agent.pathPending && agent.remainingDistance <= agent.stoppingDistance + 0.2f;
        }

        void SetDest(Vector3 p)
        {
            if (!agent.enabled) return;
            NavMeshHit hit;
            if (NavMesh.SamplePosition(p, out hit, 2.5f, NavMesh.AllAreas)) agent.SetDestination(hit.position);
        }

        void GoPatrol()
        {
            if (mode == Mode.Frozen && NCGame.I != null && NCGame.I.State == GameState.Caught) { }
            mode = Mode.Patrol;
            targetSpot = null;
            if (!started || patrolPoints == null || patrolPoints.Length == 0) return;
            agent.speed = patrolSpeed;
            // prefer points she can actually reach (the fire, rubble and roller door cut parts of the school off)
            if (patrolPath == null) patrolPath = new NavMeshPath();
            int i = 0;
            for (int tries = 0; tries < 6; tries++)
            {
                i = Random.Range(0, patrolPoints.Length);
                if (i == lastPoint) i = (i + 1) % patrolPoints.Length;
                if (patrolPoints[i] == null) continue;
                NavMeshHit hit;
                if (NavMesh.SamplePosition(patrolPoints[i].position, out hit, 2.5f, NavMesh.AllAreas) &&
                    agent.CalculatePath(hit.position, patrolPath) && patrolPath.status == NavMeshPathStatus.PathComplete) break;
            }
            lastPoint = i;
            if (patrolPoints[i] != null) SetDest(patrolPoints[i].position);
        }

        void StartChase()
        {
            mode = Mode.Chase;
            agent.speed = chaseSpeed;
            nextRepath = 0f;
            if (rig != null) rig.Alert();
            Sfx.Play3D(GameAssets.I.rulerHit, transform.position + Vector3.up * 1.4f, 0.8f, 1f, 30f);
        }

        bool See()
        {
            FPController p = FPController.I;
            if (p == null || p.Hidden || viewDistance <= 0f) return false;
            Vector3 e = eye != null ? eye.position : transform.position + Vector3.up * 1.6f;
            Vector3 target = p.HeadPosition - Vector3.up * 0.2f;
            Vector3 d = target - e;
            float dist = d.magnitude;
            float range = viewDistance * (p.Crouching ? 0.6f : 1f);
            if (dist > range) return false;
            if (dist > 1.6f && Vector3.Angle(transform.forward, d) > viewHalfAngle) return false;
            if (Physics.Raycast(e, d / dist, dist - 0.2f, SightMask, QueryTriggerInteraction.Ignore)) return false;
            return true;
        }

        void TryCatch()
        {
            FPController p = FPController.I;
            if (p == null || p.Hidden) return;
            float d = Vector3.Distance(transform.position, p.transform.position);
            if (d < 1.25f && (seeing || Time.time - lastSeen < 0.6f)) Catch();
        }

        void Catch()
        {
            if (!canHunt || menuMode || NCGame.I == null || NCGame.I.State != GameState.Playing) return;
            Freeze();
            NCGame.I.OnCaught();
        }

        void UpdateAudio(float dt)
        {
            float sp = agent.enabled ? agent.velocity.magnitude : 0f;
            stepDist += sp * dt;
            float stride = sp > 2.5f ? 0.85f : 0.62f;
            if (stepDist > stride)
            {
                stepDist = 0f;
                Sfx.Play3D(Sfx.Pick(GameAssets.I.teacherSteps), transform.position, sp > 2.5f ? 0.95f : 0.65f, Random.Range(0.92f, 1.06f), 26f);
            }
            if (voice != null)
            {
                float target = (mode == Mode.Patrol || mode == Mode.Wait || mode == Mode.Search) && !menuMode ? 0.5f : 0f;
                voice.volume = Mathf.MoveTowards(voice.volume, target, dt * 0.5f);
            }
        }

        void AnimateRig(float dt)
        {
            if (rig == null) return;
            rig.speed = agent.enabled ? agent.velocity.magnitude : 0f;
            rig.chasing = IsChasing;
            rig.lookTarget = seeing && FPController.I != null ? (Vector3?)FPController.I.HeadPosition : null;
            rig.searching = mode == Mode.Wait || mode == Mode.Search;
        }
    }
}

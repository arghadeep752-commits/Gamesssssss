using UnityEngine;
using UnityEngine.AI;

namespace GridProto
{
    /// <summary>
    /// The hunter. Patrols the area; notices the player by sight (view cone + line of sight; slower to
    /// notice a crouching player) or by noise (running, landing, the door); chases at a sprint, aiming at
    /// where the player is heading and pathing around every obstacle; opens the door if the player hides
    /// behind it; gets confused when the player gets very far away, then searches the last known spot;
    /// and starts the jumpscare when it catches the player.
    /// </summary>
    [RequireComponent(typeof(NavMeshAgent))]
    public class EnemyAI : MonoBehaviour
    {
        public enum State { Patrol, Investigate, Chase, Search, Confused, Attack }

        public EnemyAnimator anim;
        public PlayerController player;
        public Jumpscare jumpscare;
        public Door door;
        public Renderer body;
        public AudioSource voice;       // roar when it spots the player (3D)
        public AudioSource breath;      // heavy breathing / growl loop (3D)
        public AudioSource heartbeat;   // the player's heartbeat while hunted (2D)
        public AudioSource drone;       // tension drone during a chase (2D)

        public Vector3 patrolCenter = new Vector3(0f, 0f, 4f);
        public Vector3[] patrolPoints;            // rooms to walk through (both floors); empty = random points
        public float patrolRadius = 26f;
        public float walkSpeed = 1.45f;
        public float alertSpeed = 2.7f;
        public float runSpeed = 5.1f;
        public float viewDistance = 30f;
        public float viewAngle = 130f;
        public float catchDistance = 1.25f;
        public float giveUpDistance = 32f;

        [System.NonSerialized] public bool perceptionEnabled = true;

        public State Current { get; private set; }
        /// <summary>0..1, how much danger the player is in (drives the red screen edge and the heartbeat).</summary>
        public float Threat { get; private set; }

        NavMeshAgent agent;
        bool started, seesPlayer, lookingAround;
        int sightMask;
        float awareness, stateTime, repathTimer, waitTimer, lostSight, doorPause, prevYaw, goTime;
        Vector3 lastKnown, lastKnownVelocity, investigatePoint, searchCenter;
        int searchLeft;

        void OnEnable() { NoiseSystem.OnNoise += Hear; }
        void OnDisable() { NoiseSystem.OnNoise -= Hear; }

        void Start()
        {
            agent = GetComponent<NavMeshAgent>();
            sightMask = ~((1 << 1) | (1 << 2) | (1 << gameObject.layer) | (1 << 10));   // sees through glass
            NavMeshHit hit;
            if (NavMesh.SamplePosition(transform.position, out hit, 6f, NavMesh.AllAreas)) transform.position = hit.position;
            agent.enabled = true;
            agent.Warp(transform.position);
            agent.speed = walkSpeed;
            if (!agent.isOnNavMesh) Debug.LogWarning("[GridProto] enemy is not on the NavMesh");
            prevYaw = transform.eulerAngles.y;
            StartLoop(breath, ProtoAudio.Growl, 0.35f);
            StartLoop(heartbeat, ProtoAudio.Heartbeat, 0f);
            StartLoop(drone, ProtoAudio.Drone, 0f);
            started = true;
            SetState(State.Patrol);
        }

        static void StartLoop(AudioSource source, AudioClip clip, float volume)
        {
            if (source == null) return;
            source.clip = clip;
            source.loop = true;
            source.volume = volume;
            source.Play();
        }

        void Update()
        {
            if (!started || Current == State.Attack || player == null) return;
            float dt = Time.deltaTime;
            if (dt <= 0f) return;
            stateTime += dt;

            Vector3 toPlayer = player.transform.position - transform.position;
            toPlayer.y = 0f;
            float distance = toPlayer.magnitude;
            seesPlayer = perceptionEnabled && player.ControlEnabled && CanSeePlayer(distance);

            // awareness builds up while the player is in sight (fast up close, slower far away or crouched)
            if (seesPlayer)
            {
                float rate = distance < 4f ? 7f : Mathf.Lerp(2.4f, 0.6f, Mathf.InverseLerp(4f, viewDistance, distance));
                if (player.IsRunning) rate *= 1.5f;
                if (player.IsCrouching) rate *= 0.6f;
                awareness = Mathf.Min(1.5f, awareness + rate * dt);
            }
            else
            {
                awareness = Mathf.Max(0f, awareness - dt * (Current == State.Chase ? 0.1f : 0.3f));
            }
            if (seesPlayer && Current != State.Chase && awareness >= 1f) StartChase();

            switch (Current)
            {
                case State.Patrol: UpdatePatrol(dt); break;
                case State.Investigate: UpdateInvestigate(); break;
                case State.Chase: UpdateChase(dt, distance); break;
                case State.Search: UpdateSearch(dt); break;
                case State.Confused: UpdateConfused(); break;
            }
            if (Current == State.Attack) return;

            UpdateDoor(dt);
            UpdateAnimation(dt);
            UpdateAudio(dt, distance);
        }

        // ------------------------------------------------------------------ senses

        bool CanSeePlayer(float distance)
        {
            float range = viewDistance * (player.IsCrouching ? 0.6f : 1f);
            if (distance > range) return false;
            Vector3 eye = anim != null && anim.head != null ? anim.head.position + Vector3.up * 0.12f : transform.position + Vector3.up * 1.75f;
            Vector3 headTarget = player.HeadPosition;
            Vector3 flat = headTarget - eye;
            flat.y = 0f;
            if (distance > 2.5f && Vector3.Angle(transform.forward, flat) > viewAngle * 0.5f) return false;
            if (!Physics.Linecast(eye, headTarget, sightMask, QueryTriggerInteraction.Ignore)) return true;
            Vector3 chestTarget = player.transform.position + Vector3.up * 1f;
            return !Physics.Linecast(eye, chestTarget, sightMask, QueryTriggerInteraction.Ignore);
        }

        void Hear(Vector3 position, float radius)
        {
            if (!started || !perceptionEnabled || Current == State.Attack) return;
            if ((position - transform.position).sqrMagnitude > radius * radius) return;
            if (Current == State.Chase)
            {
                lastKnown = position;
                lostSight = Mathf.Min(lostSight, 1f);
                return;
            }
            investigatePoint = position;
            awareness = Mathf.Max(awareness, 0.4f);
            if (Current != State.Investigate) SetState(State.Investigate);
            Go(position);
        }

        // ------------------------------------------------------------------ states

        void SetState(State next)
        {
            Current = next;
            stateTime = 0f;
            waitTimer = 0f;
            lookingAround = false;
            if (next == State.Confused) Stop();
        }

        void StartChase()
        {
            SetState(State.Chase);
            lastKnown = player.transform.position;
            lastKnownVelocity = player.Velocity;
            lostSight = 0f;
            repathTimer = 0f;
            if (voice != null)
            {
                voice.pitch = Random.Range(0.9f, 1.05f);
                voice.PlayOneShot(ProtoAudio.Roar, 1f);
            }
        }

        void UpdatePatrol(float dt)
        {
            agent.speed = walkSpeed;
            if (awareness > 0.35f && seesPlayer)
            {
                // noticed something: stop and stare before deciding
                Stop();
                FaceTowards(player.transform.position, dt);
                return;
            }
            if (waitTimer > 0f)
            {
                waitTimer -= dt;
                if (waitTimer <= 0f)
                {
                    lookingAround = false;
                    Go(NextPatrolPoint());
                }
                return;
            }
            if (Arrived())
            {
                Stop();
                waitTimer = Random.Range(1.5f, 3.5f);
                lookingAround = Random.value < 0.35f;
            }
        }

        void UpdateInvestigate()
        {
            agent.speed = alertSpeed;
            if (Arrived()) BeginSearch(investigatePoint, 1);
            else if (stateTime > 20f) SetState(State.Patrol);
        }

        void UpdateChase(float dt, float distance)
        {
            if (seesPlayer)
            {
                lastKnown = player.transform.position;
                lastKnownVelocity = player.Velocity;
                lostSight = 0f;
            }
            else
            {
                lostSight += dt;
            }

            if (distance > giveUpDistance)
            {
                // the player got very far away: it stops, confused, then searches
                lastKnown = player.transform.position;
                SetState(State.Confused);
                return;
            }
            if (lostSight > 4.5f)
            {
                BeginSearch(lastKnown + Vector3.ClampMagnitude(lastKnownVelocity, 6f) * 1.2f, 2);
                return;
            }

            float dy = Mathf.Abs(player.transform.position.y - transform.position.y);
            if (distance < catchDistance && dy < 1.3f && seesPlayer && jumpscare != null && !jumpscare.Active)
            {
                SetState(State.Attack);
                jumpscare.Begin(this);
                return;
            }

            agent.speed = runSpeed;
            repathTimer -= dt;
            if (repathTimer <= 0f)
            {
                repathTimer = 0.15f;
                Vector3 goal;
                if (seesPlayer)
                {
                    // aim where the player is going to be, not where they are
                    float lead = Mathf.Clamp(distance / runSpeed, 0f, 0.6f);
                    goal = player.transform.position + Vector3.ClampMagnitude(player.Velocity, 6f) * lead;
                }
                else
                {
                    goal = lastKnown + Vector3.ClampMagnitude(lastKnownVelocity, 6f) * Mathf.Min(lostSight, 1.5f);
                }
                Go(goal);
            }
        }

        void UpdateConfused()
        {
            Stop();
            lookingAround = true;
            if (stateTime > 4.6f) BeginSearch(lastKnown, 2);
        }

        void BeginSearch(Vector3 center, int points)
        {
            SetState(State.Search);
            searchCenter = center;
            searchLeft = points;
            Go(center);
        }

        void UpdateSearch(float dt)
        {
            agent.speed = alertSpeed;
            if (waitTimer > 0f)
            {
                waitTimer -= dt;
                lookingAround = true;
                if (waitTimer <= 0f)
                {
                    lookingAround = false;
                    if (searchLeft-- > 0) Go(RandomPoint(searchCenter, 7f));
                    else SetState(State.Patrol);
                }
                return;
            }
            if (Arrived())
            {
                Stop();
                waitTimer = 2.6f;
            }
            if (stateTime > 30f) SetState(State.Patrol);
        }

        // ------------------------------------------------------------------ doors

        void UpdateDoor(float dt)
        {
            if (doorPause > 0f)
            {
                doorPause -= dt;
                anim.reachWeight = Mathf.Clamp01(1f - Mathf.Abs(doorPause - 0.25f) / 0.25f);
                if (doorPause <= 0f && agent.isOnNavMesh) agent.isStopped = false;
                return;
            }
            anim.reachWeight = Mathf.MoveTowards(anim.reachWeight, 0f, dt * 4f);
            if (!agent.isOnNavMesh || !agent.hasPath) return;
            Vector3 heading = agent.desiredVelocity;
            heading.y = 0f;
            Door best = null;
            float bestDist = 1.7f;
            foreach (Interactable it in Interactable.All)
            {
                Door d = it as Door;
                if (d == null || d.IsOpen) continue;
                Vector3 toDoor = d.FocusPosition - transform.position;
                if (Mathf.Abs(toDoor.y) > 1.6f) continue;
                toDoor.y = 0f;
                float dist = toDoor.magnitude;
                if (dist > bestDist || Vector3.Dot(toDoor, heading) <= 0f) continue;
                best = d;
                bestDist = dist;
            }
            if (best == null) return;
            // the path leads through a closed door: grab the handle and push it open
            best.OpenAwayFrom(transform.position);
            doorPause = 0.5f;
            agent.isStopped = true;
            Vector3 side = transform.position - best.FocusPosition;
            side.y = 0f;
            anim.reachTarget = best.FocusPosition + Vector3.down * 0.1f + (side.sqrMagnitude > 0.0001f ? side.normalized * 0.15f : Vector3.zero);
        }

        Vector3 NextPatrolPoint()
        {
            if (patrolPoints == null || patrolPoints.Length == 0) return RandomPoint(patrolCenter, patrolRadius);
            Vector3 p = patrolPoints[Random.Range(0, patrolPoints.Length)];
            Vector3 q = RandomPoint(p, 2.5f);
            return q;
        }

        // ------------------------------------------------------------------ animation and sound

        void UpdateAnimation(float dt)
        {
            Vector3 v = agent.velocity;
            v.y = 0f;
            anim.speed = v.magnitude;
            anim.run = Current == State.Chase ? 1f : (Current == State.Investigate || Current == State.Search ? 0.3f : 0f);
            float yaw = transform.eulerAngles.y;
            anim.turnRate = Mathf.DeltaAngle(prevYaw, yaw) / dt;
            prevYaw = yaw;
            float stance = Current == State.Chase ? 1f : (Current == State.Search || Current == State.Investigate ? 0.5f : 0f);
            anim.aggression = Mathf.MoveTowards(anim.aggression, stance, dt * 1.2f);
            anim.confused = (Current == State.Confused || lookingAround) ? 1f : 0f;
            anim.hasLookTarget = seesPlayer || (Current == State.Patrol && awareness > 0.35f);
            anim.lookTarget = player.HeadPosition;
        }

        void UpdateAudio(float dt, float distance)
        {
            bool chasing = Current == State.Chase;
            float closeness = Mathf.Clamp01(1f - distance / 25f);
            float target = chasing ? Mathf.Lerp(0.45f, 1f, closeness) : (awareness > 0.3f ? 0.2f : 0f);
            Threat = Mathf.MoveTowards(Threat, target, dt * 1.5f);
            if (breath != null) breath.volume = Mathf.MoveTowards(breath.volume, chasing ? 0.9f : 0.35f, dt);
            if (heartbeat != null)
            {
                heartbeat.volume = Threat * 0.9f;
                heartbeat.pitch = Mathf.Lerp(0.9f, 1.35f, Threat);
            }
            if (drone != null) drone.volume = Mathf.MoveTowards(drone.volume, chasing ? 0.55f : 0f, dt * 0.6f);
        }

        // ------------------------------------------------------------------ helpers

        void Go(Vector3 point)
        {
            if (agent == null || !agent.isOnNavMesh) return;
            NavMeshHit hit;
            if (NavMesh.SamplePosition(point, out hit, 3f, NavMesh.AllAreas)) point = hit.position;
            agent.isStopped = false;
            agent.SetDestination(point);
            goTime = Time.time;
        }

        void Stop()
        {
            if (agent != null && agent.isOnNavMesh) agent.ResetPath();
        }

        bool Arrived()
        {
            if (agent == null || !agent.isOnNavMesh) return true;
            if (Time.time - goTime < 0.3f || agent.pathPending) return false;
            return !agent.hasPath || agent.remainingDistance <= agent.stoppingDistance + 0.2f;
        }

        void FaceTowards(Vector3 point, float dt)
        {
            Vector3 to = point - transform.position;
            to.y = 0f;
            if (to.sqrMagnitude < 0.0001f) return;
            transform.rotation = Quaternion.RotateTowards(transform.rotation, Quaternion.LookRotation(to), 240f * dt);
        }

        Vector3 RandomPoint(Vector3 center, float radius)
        {
            for (int i = 0; i < 12; i++)
            {
                Vector2 r = Random.insideUnitCircle * radius;
                Vector3 candidate = center + new Vector3(r.x, 0f, r.y);
                NavMeshHit hit;
                if (NavMesh.SamplePosition(candidate, out hit, 2.5f, NavMesh.AllAreas) && Mathf.Abs(hit.position.y - center.y) < 0.6f)
                    return hit.position;
            }
            return center;
        }

        /// <summary>Called by the jumpscare: stop moving and hand the body over.</summary>
        public void PrepareForAttack()
        {
            Current = State.Attack;
            if (agent != null)
            {
                if (agent.isOnNavMesh) agent.ResetPath();
                agent.enabled = false;
            }
            anim.speed = 0f;
            anim.run = 0f;
            anim.turnRate = 0f;
            anim.confused = 0f;
            anim.reachWeight = 0f;
            Threat = 1f;
            if (breath != null) breath.volume = 1f;
            if (drone != null) drone.volume = 0f;
        }

        /// <summary>Test helper: put the enemy somewhere and let it stand still for a moment.</summary>
        public void DebugWarp(Vector3 position, float yaw)
        {
            NavMeshHit hit;
            if (NavMesh.SamplePosition(position, out hit, 4f, NavMesh.AllAreas)) position = hit.position;
            if (agent != null && agent.enabled && agent.isOnNavMesh) agent.Warp(position);
            else transform.position = position;
            transform.rotation = Quaternion.Euler(0f, yaw, 0f);
            prevYaw = yaw;
            awareness = 0f;
            SetState(State.Patrol);
            Stop();
            waitTimer = 3f;
        }

        public void DebugConfuse()
        {
            lastKnown = transform.position;
            SetState(State.Confused);
        }
    }
}

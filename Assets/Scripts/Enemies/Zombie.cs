using System.Collections.Generic;
using UnityEngine;
using UnityEngine.AI;

namespace ZombieStrike
{
    /// <summary>
    /// A blocky zombie: rises from the ground, chases the player with NavMesh pathfinding,
    /// swipes when close, reacts to hits and falls over when killed.
    /// </summary>
    public class Zombie : MonoBehaviour
    {
        public static readonly List<Zombie> All = new List<Zombie>();

        public ZombieKind Kind { get; private set; }
        public bool Alive { get; private set; }
        public float Health { get; private set; }

        NavMeshAgent agent;
        Transform model, body, legL, legR, armL, armR, head;
        Renderer[] renderers;
        MaterialPropertyBlock flashBlock;
        Collider bodyCollider, headCollider;

        float scale, speed, damage, attackRange, reach, cooldown;
        float repathTimer, attackTimer, attackAnim = -1f, groanTimer, phase, riseT, flashT, staggerT, deathT, seed;
        bool rising = true, swingHit;
        Quaternion fallFrom, fallTo;

        const float RiseTime = 1.1f;
        const float AttackLength = 0.6f;

        static readonly Color[] SkinTones =
        {
            new Color(0.45f, 0.58f, 0.36f), new Color(0.52f, 0.6f, 0.43f), new Color(0.4f, 0.5f, 0.42f)
        };
        static readonly Color[] ShirtColors =
        {
            new Color(0.25f, 0.3f, 0.48f), new Color(0.52f, 0.13f, 0.1f), new Color(0.38f, 0.32f, 0.23f),
            new Color(0.46f, 0.46f, 0.43f), new Color(0.2f, 0.34f, 0.23f), new Color(0.58f, 0.52f, 0.36f)
        };
        static readonly Color[] PantsColors =
        {
            new Color(0.15f, 0.17f, 0.23f), new Color(0.27f, 0.23f, 0.18f), new Color(0.12f, 0.12f, 0.13f)
        };

        public static Zombie Spawn(ZombieKind kind, Vector3 position, int wave)
        {
            var go = new GameObject(kind.ToString());
            go.layer = Layers.Zombie;
            go.transform.position = position;
            PlayerController p = PlayerController.I;
            if (p != null)
            {
                Vector3 d = p.transform.position - position;
                d.y = 0f;
                if (d.sqrMagnitude > 0.01f) go.transform.rotation = Quaternion.LookRotation(d);
            }
            var z = go.AddComponent<Zombie>();
            z.Setup(kind, wave);
            return z;
        }

        void Setup(ZombieKind kind, int wave)
        {
            Kind = kind;
            Alive = true;
            seed = Random.value * 100f;
            float waveBoost = Mathf.Min(1f + 0.06f * (wave - 1), 2.2f);
            float speedBoost = Mathf.Min(1f + 0.03f * (wave - 1), 1.35f);
            switch (kind)
            {
                case ZombieKind.Runner:
                    scale = 0.95f; Health = 65f * waveBoost; speed = Random.Range(3.5f, 4.1f) * speedBoost; damage = 7f; cooldown = 0.8f;
                    break;
                case ZombieKind.Brute:
                    scale = 1.45f; Health = 450f * waveBoost; speed = 1.35f * speedBoost; damage = 22f; cooldown = 1.3f;
                    break;
                default:
                    scale = 1f; Health = 100f * waveBoost; speed = Random.Range(1.45f, 2.0f) * speedBoost; damage = 10f; cooldown = 1.0f;
                    break;
            }
            attackRange = 1.55f * (kind == ZombieKind.Brute ? 1.2f : 1f);
            reach = attackRange + 0.45f;
            groanTimer = Random.Range(0.5f, 4f);

            BuildBody();

            var rb = gameObject.AddComponent<Rigidbody>();
            rb.isKinematic = true;
            rb.useGravity = false;

            var bc = gameObject.AddComponent<BoxCollider>();
            bc.center = new Vector3(0f, 0.78f * scale, 0f);
            bc.size = new Vector3(0.62f, 1.5f, 0.45f) * scale;
            bodyCollider = bc;
            var hbBody = gameObject.AddComponent<ZombieHitbox>();
            hbBody.Owner = this;

            agent = gameObject.AddComponent<NavMeshAgent>();
            agent.radius = 0.32f * scale;
            agent.height = 1.8f * scale;
            agent.speed = speed;
            agent.acceleration = 14f;
            agent.angularSpeed = 540f;
            agent.stoppingDistance = attackRange * 0.75f;
            agent.autoBraking = true;
            agent.obstacleAvoidanceType = ObstacleAvoidanceType.LowQualityObstacleAvoidance;
            agent.avoidancePriority = Random.Range(30, 70);
            if (agent.isOnNavMesh)
            {
                agent.Warp(transform.position);
                agent.isStopped = true;
            }

            model.localPosition = new Vector3(0f, -1.9f * scale, 0f);
            if (Fx.I != null) Fx.I.Dirt(transform.position, 14);
            All.Add(this);
        }

        void BuildBody()
        {
            int L = Layers.Zombie;
            Color skin = Kind == ZombieKind.Runner ? new Color(0.66f, 0.68f, 0.57f) :
                Kind == ZombieKind.Brute ? new Color(0.36f, 0.47f, 0.3f) : SkinTones[Random.Range(0, SkinTones.Length)];
            Color shirt = Kind == ZombieKind.Brute ? new Color(0.22f, 0.2f, 0.2f) : ShirtColors[Random.Range(0, ShirtColors.Length)];
            Color pants = PantsColors[Random.Range(0, PantsColors.Length)];
            Material skinM = Art.Lit(skin, "grime");
            Material shirtM = Art.Lit(shirt, "grime");
            Material pantsM = Art.Lit(pants, "grime");
            Material bloodM = Art.Lit(new Color(0.35f, 0.03f, 0.03f), "grime");
            Material eyeM = Art.Unlit(Kind == ZombieKind.Runner ? new Color(1f, 0.85f, 0.2f) : new Color(1f, 0.12f, 0.08f));
            Material mouthM = Art.Unlit(new Color(0.08f, 0.02f, 0.02f));

            float wide = Kind == ZombieKind.Brute ? 1.25f : (Kind == ZombieKind.Runner ? 0.9f : 1f);

            model = new GameObject("Model").transform;
            model.SetParent(transform, false);
            model.localScale = Vector3.one * scale;
            model.gameObject.layer = L;
            body = new GameObject("Body").transform;
            body.SetParent(model, false);
            body.gameObject.layer = L;

            legL = Pivot(body, new Vector3(-0.13f, 0.85f, 0f));
            legR = Pivot(body, new Vector3(0.13f, 0.85f, 0f));
            Art.Box(legL, new Vector3(0f, -0.42f, 0f), new Vector3(0.21f, 0.84f, 0.24f), pantsM, Vector3.zero, L);
            Art.Box(legR, new Vector3(0f, -0.42f, 0f), new Vector3(0.21f, 0.84f, 0.24f), pantsM, Vector3.zero, L);

            Transform torso = Pivot(body, new Vector3(0f, 0.85f, 0f));
            torso.localRotation = Quaternion.Euler(Kind == ZombieKind.Runner ? 16f : 7f, 0f, 0f);
            Art.Box(torso, new Vector3(0f, 0.35f, 0f), new Vector3(0.56f * wide, 0.7f, 0.32f * wide), shirtM, Vector3.zero, L);
            Art.Box(torso, new Vector3(0.08f, 0.42f, 0.165f * wide), new Vector3(0.22f, 0.2f, 0.02f), bloodM, Vector3.zero, L);

            armL = Pivot(torso, new Vector3(-0.37f * wide, 0.62f, 0f));
            armR = Pivot(torso, new Vector3(0.37f * wide, 0.62f, 0f));
            float armThick = 0.17f * wide;
            Art.Box(armL, new Vector3(0f, -0.3f, 0f), new Vector3(armThick, 0.66f, armThick), skinM, Vector3.zero, L);
            Art.Box(armR, new Vector3(0f, -0.3f, 0f), new Vector3(armThick, 0.66f, armThick), skinM, Vector3.zero, L);
            Art.Box(armL, new Vector3(0f, -0.08f, 0f), new Vector3(armThick + 0.02f, 0.2f, armThick + 0.02f), shirtM, Vector3.zero, L);
            Art.Box(armR, new Vector3(0f, -0.08f, 0f), new Vector3(armThick + 0.02f, 0.2f, armThick + 0.02f), shirtM, Vector3.zero, L);

            head = Pivot(torso, new Vector3(0f, 0.7f, 0f));
            Art.Box(head, new Vector3(0f, 0.2f, 0.02f), new Vector3(0.4f, 0.4f, 0.4f), skinM, Vector3.zero, L);
            Art.Box(head, new Vector3(-0.09f, 0.25f, 0.225f), new Vector3(0.085f, 0.055f, 0.02f), eyeM, Vector3.zero, L);
            Art.Box(head, new Vector3(0.09f, 0.25f, 0.225f), new Vector3(0.085f, 0.055f, 0.02f), eyeM, Vector3.zero, L);
            Art.Box(head, new Vector3(0f, 0.1f, 0.222f), new Vector3(0.2f, 0.06f, 0.02f), mouthM, Vector3.zero, L);
            Art.Box(head, new Vector3(-0.06f, 0.36f, 0.15f), new Vector3(0.18f, 0.06f, 0.16f), bloodM, Vector3.zero, L);

            var headCol = head.gameObject.AddComponent<BoxCollider>();
            headCol.center = new Vector3(0f, 0.2f, 0.02f);
            headCol.size = new Vector3(0.46f, 0.46f, 0.46f);
            headCollider = headCol;
            var hb = head.gameObject.AddComponent<ZombieHitbox>();
            hb.Owner = this;
            hb.IsHead = true;

            renderers = GetComponentsInChildren<Renderer>();
            flashBlock = new MaterialPropertyBlock();
        }

        static Transform Pivot(Transform parent, Vector3 localPos)
        {
            var t = new GameObject("Pivot").transform;
            t.SetParent(parent, false);
            t.localPosition = localPos;
            t.gameObject.layer = parent.gameObject.layer;
            return t;
        }

        void OnDestroy()
        {
            All.Remove(this);
        }

        bool AgentReady { get { return agent != null && agent.enabled && agent.isOnNavMesh; } }

        void Update()
        {
            float dt = Time.deltaTime;
            if (!Alive)
            {
                UpdateDeath(dt);
                return;
            }
            UpdateFlash(dt);

            GameManager gm = GameManager.I;
            PlayerController player = PlayerController.I;
            if (gm == null || player == null || gm.State == GameState.Menu)
            {
                return;
            }

            if (rising)
            {
                riseT += dt;
                model.localPosition = new Vector3(0f, Mathf.Lerp(-1.9f * scale, 0f, Ease.OutCubic(riseT / RiseTime)), 0f);
                Animate(dt, 0f);
                if (riseT >= RiseTime)
                {
                    rising = false;
                    if (AgentReady) agent.isStopped = false;
                }
                return;
            }

            Vector3 toPlayer = player.transform.position - transform.position;
            toPlayer.y = 0f;
            float dist = toPlayer.magnitude;
            bool canHunt = player.Alive && gm.State == GameState.Playing;

            repathTimer -= dt;
            if (repathTimer <= 0f)
            {
                repathTimer = 0.25f + Random.value * 0.15f;
                if (AgentReady && canHunt) agent.SetDestination(player.transform.position);
            }

            if (staggerT > 0f) staggerT -= dt;
            attackTimer -= dt;

            if (attackAnim >= 0f)
            {
                attackAnim += dt;
                if (!swingHit && attackAnim >= AttackLength * 0.55f)
                {
                    swingHit = true;
                    if (canHunt && dist <= reach * scale) player.TakeDamage(damage, transform.position);
                }
                if (attackAnim >= AttackLength) attackAnim = -1f;
            }
            else if (canHunt && dist <= attackRange * scale && attackTimer <= 0f && staggerT <= 0f)
            {
                attackAnim = 0f;
                swingHit = false;
                attackTimer = cooldown;
                if (Sfx.I != null) Sfx.I.PlayAt("zombie_attack", transform.position + Vector3.up * 1.6f, 0.9f, PitchForKind());
            }

            bool hold = !canHunt || dist <= attackRange * scale * 0.9f || staggerT > 0f;
            if (AgentReady)
            {
                agent.isStopped = hold;
            }
            else if (!hold && canHunt)
            {
                // fallback when no NavMesh is available: walk straight at the player
                transform.position += toPlayer.normalized * speed * dt;
            }

            if (dist > 0.01f && (hold || !AgentReady))
            {
                transform.rotation = Quaternion.RotateTowards(transform.rotation, Quaternion.LookRotation(toPlayer), 360f * dt);
            }

            float moveSpeed = AgentReady ? agent.velocity.magnitude : (hold ? 0f : speed);
            Animate(dt, moveSpeed);

            groanTimer -= dt;
            if (groanTimer <= 0f)
            {
                groanTimer = Random.Range(4f, 9f);
                if (dist < 32f && Sfx.I != null)
                {
                    string clip = Kind == ZombieKind.Brute && Random.value < 0.5f ? "brute_roar" : "zombie_groan" + Random.Range(1, 5);
                    Sfx.I.PlayAt(clip, transform.position + Vector3.up * 1.6f, 0.85f, PitchForKind());
                }
            }
        }

        float PitchForKind()
        {
            if (Kind == ZombieKind.Brute) return Random.Range(0.7f, 0.8f);
            if (Kind == ZombieKind.Runner) return Random.Range(1.1f, 1.25f);
            return Random.Range(0.88f, 1.08f);
        }

        void Animate(float dt, float moveSpeed)
        {
            float rate = Kind == ZombieKind.Runner ? 1.25f : (Kind == ZombieKind.Brute ? 0.75f : 0.95f);
            phase += dt * (0.4f + moveSpeed * rate);
            float moving = Mathf.Clamp01(moveSpeed / Mathf.Max(speed * 0.5f, 0.1f));
            float amp = (Kind == ZombieKind.Runner ? 42f : 26f) * moving;
            float s = Mathf.Sin(phase * Mathf.PI);
            legL.localRotation = Quaternion.Euler(s * amp, 0f, 0f);
            legR.localRotation = Quaternion.Euler(-s * amp, 0f, 0f);

            float t = Time.time + seed;
            float armBase = -80f + Mathf.Sin(t * 2.1f) * 6f;
            float lift = 0f;
            if (attackAnim >= 0f)
            {
                float a = attackAnim / AttackLength;
                lift = a < 0.45f ? Mathf.Lerp(0f, -55f, a / 0.45f) : Mathf.Lerp(-55f, 50f, (a - 0.45f) / 0.55f);
            }
            armL.localRotation = Quaternion.Euler(armBase + lift + s * amp * 0.15f, 0f, -6f);
            armR.localRotation = Quaternion.Euler(armBase + lift - s * amp * 0.15f + Mathf.Sin(t * 1.7f) * 5f, 0f, 6f);
            head.localRotation = Quaternion.Euler(-6f + Mathf.Sin(t * 0.8f) * 6f, Mathf.Sin(t * 0.6f) * 10f, Mathf.Sin(t * 0.9f) * 12f);
            body.localPosition = new Vector3(0f, Mathf.Abs(s) * 0.05f * moving, 0f);
            body.localRotation = Quaternion.Euler(0f, 0f, Mathf.Sin(phase * Mathf.PI * 0.5f) * 5f * moving);
        }

        /// <returns>true if this hit killed the zombie.</returns>
        public bool TakeDamage(float amount, Vector3 dir, bool headshot)
        {
            if (!Alive) return false;
            Health -= amount;
            flashT = 0.08f;
            SetFlash(true);
            staggerT = Kind == ZombieKind.Brute ? 0.05f : 0.14f;
            if (AgentReady && Kind != ZombieKind.Brute)
            {
                Vector3 push = dir;
                push.y = 0f;
                agent.Move(push.normalized * 0.12f);
            }
            if (Health <= 0f)
            {
                Die(dir, headshot);
                return true;
            }
            return false;
        }

        void UpdateFlash(float dt)
        {
            if (flashT <= 0f) return;
            flashT -= dt;
            if (flashT <= 0f) SetFlash(false);
        }

        void SetFlash(bool on)
        {
            if (renderers == null) return;
            if (on)
            {
                flashBlock.SetColor("_Color", new Color(1f, 0.55f, 0.5f));
                foreach (Renderer r in renderers) if (r != null) r.SetPropertyBlock(flashBlock);
            }
            else
            {
                foreach (Renderer r in renderers) if (r != null) r.SetPropertyBlock(null);
            }
        }

        void Die(Vector3 dir, bool headshot)
        {
            Alive = false;
            All.Remove(this);
            SetFlash(false);
            if (agent != null) agent.enabled = false;
            if (bodyCollider != null) bodyCollider.enabled = false;
            if (headCollider != null) headCollider.enabled = false;
            deathT = 0f;
            Vector3 flat = dir;
            flat.y = 0f;
            if (flat.sqrMagnitude < 0.001f) flat = -transform.forward;
            Vector3 axis = Vector3.Cross(Vector3.up, flat.normalized);
            fallFrom = model.rotation;
            fallTo = Quaternion.AngleAxis(88f, axis) * Quaternion.AngleAxis(Random.Range(-20f, 20f), Vector3.up) * model.rotation;
            if (headshot)
            {
                Vector3 hp = head.position + Vector3.up * 0.2f * scale;
                head.gameObject.SetActive(false);
                if (Fx.I != null) Fx.I.Blood(hp, Vector3.up + flat.normalized, 28);
            }
            if (Fx.I != null) Fx.I.BloodDecal(transform.position + flat.normalized * 0.9f * scale);
            if (Sfx.I != null) Sfx.I.PlayAt("zombie_death", transform.position + Vector3.up * 1.4f, 1f, PitchForKind());
            Pickup.TryDrop(Kind, transform.position);
            if (GameManager.I != null) GameManager.I.OnZombieKilled(this, headshot);
        }

        void UpdateDeath(float dt)
        {
            deathT += dt;
            model.rotation = Quaternion.Slerp(fallFrom, fallTo, Ease.InQuad(deathT / 0.5f));
            if (deathT > 2.6f) transform.position += Vector3.down * 0.45f * dt;
            if (deathT > 5f) Destroy(gameObject);
        }
    }
}

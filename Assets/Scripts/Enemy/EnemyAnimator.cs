using UnityEngine;

namespace GridProto
{
    /// <summary>
    /// Procedural animation for the enemy skeleton (rest pose: T-pose with every bone axis-aligned, so all
    /// angles below are relative to it). Walk / run cycles matched to the ground speed, idle breathing,
    /// a hunched hunting stance, leaning into turns, head tracking, a confused look-around with a head
    /// scratch, door reaching, and two-bone IK arms for the throat grab and the punches.
    /// </summary>
    public class EnemyAnimator : MonoBehaviour
    {
        [Header("Skeleton")]
        public Transform hips;
        public Transform spine, chest, neck, head;
        public Transform upperArmL, lowerArmL, handL, fingersL;
        public Transform upperArmR, lowerArmR, handR, fingersR;
        public Transform upperLegL, lowerLegL, footL;
        public Transform upperLegR, lowerLegR, footR;

        [Header("Audio")]
        public AudioSource feet;

        // ---- set by EnemyAI / Jumpscare every frame
        [System.NonSerialized] public float speed;        // ground speed, m/s
        [System.NonSerialized] public float run;          // 0 = walking style, 1 = sprinting style
        [System.NonSerialized] public float turnRate;     // degrees per second
        [System.NonSerialized] public float aggression;   // hunched, tense hunting stance
        [System.NonSerialized] public float confused;     // look-around layer
        [System.NonSerialized] public bool hasLookTarget;
        [System.NonSerialized] public Vector3 lookTarget;
        [System.NonSerialized] public float reachWeight;  // right hand reaches for reachTarget (door handle)
        [System.NonSerialized] public Vector3 reachTarget;
        [System.NonSerialized] public float grabWeight;   // left hand to grabTarget (the player's throat)
        [System.NonSerialized] public Vector3 grabTarget;
        [System.NonSerialized] public float punchWeight;  // right fist to punchTarget
        [System.NonSerialized] public Vector3 punchTarget;

        Vector3 hipsRest;
        float phase, clock, confusedClock;
        float move, runBlend, turn, confusedBlend, lookYaw, lookPitch;
        int lastStep, stepCount;
        bool ready;

        void Awake()
        {
            ready = hips != null && spine != null && chest != null && neck != null && head != null
                 && upperArmL != null && lowerArmL != null && handL != null
                 && upperArmR != null && lowerArmR != null && handR != null
                 && upperLegL != null && lowerLegL != null && footL != null
                 && upperLegR != null && lowerLegR != null && footR != null;
            if (ready) hipsRest = hips.localPosition;
            else Debug.LogWarning("[GridProto] enemy skeleton is incomplete");
        }

        void LateUpdate()
        {
            if (!ready) return;
            float dt = Time.deltaTime;
            if (dt <= 0f) return;
            clock += dt;

            move = Mathf.Lerp(move, Mathf.Clamp01((speed - 0.05f) / 0.7f), 1f - Mathf.Exp(-8f * dt));
            runBlend = Mathf.Lerp(runBlend, Mathf.Clamp01(run), 1f - Mathf.Exp(-5f * dt));
            turn = Mathf.Lerp(turn, turnRate, 1f - Mathf.Exp(-6f * dt));
            confusedBlend = Mathf.Lerp(confusedBlend, Mathf.Clamp01(confused), 1f - Mathf.Exp(-4f * dt));
            if (confused > 0.01f) confusedClock += dt;
            else confusedClock = 0f;

            // gait cycle: one cycle = two steps; longer strides when sprinting
            float cycle = Mathf.Lerp(1.5f, 2.6f, runBlend);
            phase += 2f * Mathf.PI * speed * dt / cycle;
            if (phase > 2000f) phase -= 2f * Mathf.PI * 300f;
            int step = Mathf.FloorToInt((phase - Mathf.PI * 0.5f) / Mathf.PI);
            if (step != lastStep)
            {
                lastStep = step;
                if (move > 0.3f) PlayStep();
            }

            float s = Mathf.Sin(phase), c = Mathf.Cos(phase);
            float m = move, r = runBlend, a = Mathf.Clamp01(aggression);
            float breathe = Mathf.Sin(clock * 2f * Mathf.PI * 0.3f);

            float thighAmp = Mathf.Lerp(24f, 44f, r) * m;
            float kneeIdle = 9f * a * (1f - m);
            float kneeBase = Mathf.Lerp(5f, 16f, r) * m;
            float kneeSwing = Mathf.Lerp(50f, 95f, r) * m;
            float armDown = Mathf.Lerp(Mathf.Lerp(80f, 76f, a), 70f, r * m);
            float armSwing = Mathf.Lerp(18f, 44f, r) * m;
            float elbow = Mathf.Lerp(Mathf.Lerp(10f, 28f, a), Mathf.Lerp(22f, 95f, r), m);
            float lean = Mathf.Lerp(2f, 14f, r) * m + a * 5f;
            float bob = Mathf.Lerp(0.022f, 0.06f, r) * m;
            float curl = Mathf.Lerp(Mathf.Lerp(20f, 55f, a), 80f, r * m);
            float roll = Mathf.Clamp(-turn * 0.035f, -12f, 12f) * m;   // lean into turns
            float swayYaw = confusedBlend > 0.01f ? Mathf.Sin(confusedClock * 1.6f - 0.4f) * 16f * confusedBlend : 0f;

            // ---- body
            float hipsPitch = lean * 0.25f;
            hips.localPosition = hipsRest + new Vector3(0f, bob * Mathf.Cos(2f * phase) * 0.5f - 0.05f * r * m - 0.04f * a * (1f - m), 0f);
            hips.localRotation = Quaternion.Euler(hipsPitch, 7f * s * m, roll);
            spine.localRotation = Quaternion.Euler(lean * 0.4f + breathe * 0.8f * (1f - m), -4f * s * m + swayYaw * 0.5f, 0f);
            chest.localRotation = Quaternion.Euler(lean * 0.35f + breathe * 1.3f * (1f - m), -7f * s * m + swayYaw * 0.5f, 0f);
            float torsoPitch = hipsPitch + lean * 0.75f;

            // ---- legs: thighs swing opposite, knees fold during the swing, feet stay roughly level
            float thL = -thighAmp * s - hipsPitch - kneeIdle * 0.5f;
            float thR = thighAmp * s - hipsPitch - kneeIdle * 0.5f;
            float knL = kneeBase + kneeIdle + kneeSwing * Mathf.Pow(Mathf.Max(0f, c), 1.3f);
            float knR = kneeBase + kneeIdle + kneeSwing * Mathf.Pow(Mathf.Max(0f, -c), 1.3f);
            upperLegL.localRotation = Quaternion.Euler(thL, 0f, 0f);
            lowerLegL.localRotation = Quaternion.Euler(knL, 0f, 0f);
            footL.localRotation = Quaternion.Euler(-(hipsPitch + thL + knL) * 0.85f, 0f, 0f);
            upperLegR.localRotation = Quaternion.Euler(thR, 0f, 0f);
            lowerLegR.localRotation = Quaternion.Euler(knR, 0f, 0f);
            footR.localRotation = Quaternion.Euler(-(hipsPitch + thR + knR) * 0.85f, 0f, 0f);

            // ---- arms: lowered from the T-pose, swinging against the legs, elbows bent more when running
            float swL = armSwing * s, swR = -armSwing * s;
            float forward = a * 14f * (1f - m);   // hands slightly raised in front when stalking
            upperArmL.localRotation = Quaternion.Euler(swL - torsoPitch - forward, 0f, armDown);
            upperArmR.localRotation = Quaternion.Euler(swR - torsoPitch - forward, 0f, -armDown);
            lowerArmL.localRotation = Quaternion.Euler(0f, elbow + 14f * Mathf.Max(0f, -s) * m, 0f);
            lowerArmR.localRotation = Quaternion.Euler(0f, -(elbow + 14f * Mathf.Max(0f, s) * m), 0f);
            handL.localRotation = Quaternion.Euler(0f, 6f, 0f);
            handR.localRotation = Quaternion.Euler(0f, -6f, 0f);
            if (fingersL != null) fingersL.localRotation = Quaternion.Euler(0f, 0f, curl);
            if (fingersR != null) fingersR.localRotation = Quaternion.Euler(0f, 0f, -curl);

            // ---- head: tracks its target or looks around when confused, and stays level while leaning
            float wantYaw = 0f, wantPitch = 0f;
            if (hasLookTarget)
            {
                Vector3 local = transform.InverseTransformDirection(lookTarget - head.position);
                wantYaw = Mathf.Clamp(Mathf.Atan2(local.x, local.z) * Mathf.Rad2Deg, -75f, 75f);
                wantPitch = Mathf.Clamp(-Mathf.Atan2(local.y, new Vector2(local.x, local.z).magnitude) * Mathf.Rad2Deg, -35f, 40f);
            }
            if (confusedBlend > 0.01f)
            {
                wantYaw = Mathf.Lerp(wantYaw, Mathf.Sin(confusedClock * 1.6f) * 62f, confusedBlend);
                wantPitch = Mathf.Lerp(wantPitch, 8f + 6f * Mathf.Sin(confusedClock * 0.9f), confusedBlend);
            }
            lookYaw = Mathf.Lerp(lookYaw, wantYaw, 1f - Mathf.Exp(-7f * dt));
            lookPitch = Mathf.Lerp(lookPitch, wantPitch, 1f - Mathf.Exp(-7f * dt));
            float levelPitch = -torsoPitch * 0.8f + 7f * a;   // chin slightly down when hunting
            neck.localRotation = Quaternion.Euler(levelPitch * 0.4f + lookPitch * 0.4f, lookYaw * 0.4f, 0f);
            head.localRotation = Quaternion.Euler(levelPitch * 0.6f + lookPitch * 0.6f, lookYaw * 0.6f + 3f * Mathf.Sin(clock * 0.7f) * (1f - m), 0f);

            // ---- IK layers
            if (confusedBlend > 0.05f)
            {
                // now and then the right hand scratches the side of the head
                float cyc = confusedClock % 5f;
                float scratch = Mathf.Clamp01(Mathf.Min((cyc - 2.3f) / 0.35f, (4.3f - cyc) / 0.35f)) * confusedBlend;
                if (scratch > 0.001f)
                {
                    Vector3 target = head.position + transform.right * 0.12f + transform.up * (0.1f + 0.015f * Mathf.Sin(clock * 22f))
                                   + transform.forward * 0.02f;
                    SolveArm(upperArmR, lowerArmR, handR, target, upperArmR.position + transform.right * 0.4f - transform.up * 0.1f, scratch);
                }
            }
            if (reachWeight > 0.001f)
                SolveArm(upperArmR, lowerArmR, handR, reachTarget, upperArmR.position + transform.right * 0.35f - transform.up * 0.45f, Mathf.Clamp01(reachWeight));
            if (grabWeight > 0.001f)
            {
                SolveArm(upperArmL, lowerArmL, handL, grabTarget, upperArmL.position - transform.right * 0.35f - transform.up * 0.45f, Mathf.Clamp01(grabWeight));
                if (fingersL != null) fingersL.localRotation = Quaternion.Euler(0f, 0f, Mathf.Lerp(curl, 62f, grabWeight));
            }
            if (punchWeight > 0.001f)
            {
                SolveArm(upperArmR, lowerArmR, handR, punchTarget, upperArmR.position + transform.right * 0.45f - transform.up * 0.35f, Mathf.Clamp01(punchWeight));
                if (fingersR != null) fingersR.localRotation = Quaternion.Euler(0f, 0f, -Mathf.Lerp(curl, 100f, punchWeight));
            }
        }

        /// <summary>Two-bone IK: bends the elbow towards the pole so the wrist reaches the target.</summary>
        static void SolveArm(Transform upper, Transform lower, Transform hand, Vector3 target, Vector3 pole, float weight)
        {
            Vector3 a = upper.position, b = lower.position, c = hand.position;
            float l1 = Vector3.Distance(a, b), l2 = Vector3.Distance(b, c);
            if (l1 < 0.0001f || l2 < 0.0001f) return;
            Vector3 toTarget = Vector3.Lerp(c, target, weight) - a;
            float d = Mathf.Clamp(toTarget.magnitude, Mathf.Abs(l1 - l2) + 0.01f, (l1 + l2) * 0.999f);
            Vector3 dir = toTarget.sqrMagnitude > 1e-8f ? toTarget.normalized : (b - a).normalized;
            float cosA = Mathf.Clamp((l1 * l1 + d * d - l2 * l2) / (2f * l1 * d), -1f, 1f);
            float sinA = Mathf.Sqrt(Mathf.Max(0f, 1f - cosA * cosA));
            Vector3 bend = Vector3.ProjectOnPlane(pole - a, dir);
            if (bend.sqrMagnitude < 1e-6f) bend = Vector3.ProjectOnPlane(Vector3.down, dir);
            bend.Normalize();
            Vector3 elbow = a + dir * (l1 * cosA) + bend * (l1 * sinA);
            upper.rotation = Quaternion.FromToRotation(b - a, elbow - a) * upper.rotation;
            Vector3 nb = lower.position, nc = hand.position;
            lower.rotation = Quaternion.FromToRotation(nc - nb, a + dir * d - nb) * lower.rotation;
        }

        void PlayStep()
        {
            if (feet == null) return;
            stepCount++;
            feet.pitch = Random.Range(0.86f, 1f);
            feet.PlayOneShot(ProtoAudio.EnemyStep(stepCount), Mathf.Lerp(0.45f, 1f, runBlend));
        }
    }
}

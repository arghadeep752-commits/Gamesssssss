using UnityEngine;

namespace NightClass
{
    /// <summary>
    /// Procedural animation for the teacher's jointed body: a stiff, upright walk with the skirt
    /// swaying, a leaning chase with the ruler raised, a slow look-around while searching, the
    /// jumpscare lunge, and collapsing while burned. The head turns to track the player.
    /// </summary>
    public class TeacherRig : MonoBehaviour
    {
        public Transform hips, spine, chest, neck, head, jaw, skirt;
        public Transform legL, shinL, footL, legR, shinR, footR;
        public Transform shoulderL, elbowL, handL, shoulderR, elbowR, handR;
        public Renderer[] tintable;
        public Light eyeGlow;

        [Header("Realistic (animated) teacher")]
        public Animator animator;
        public SkinnedMeshRenderer face;
        public Transform headBone, spineBone, armL, armR;
        int bsJaw = -1, bsStretch = -1, bsWideL = -1, bsWideR = -1, bsBrowL = -1, bsBrowR = -1, bsFrownL = -1, bsFrownR = -1, bsBlinkL = -1, bsBlinkR = -1, bsSneerL = -1, bsSneerR = -1;
        float blinkT = 2f, blinkW;
        Quaternion headExtra = Quaternion.identity;

        [HideInInspector] public float speed;
        [HideInInspector] public bool chasing, searching;
        [HideInInspector] public Vector3? lookTarget;

        Quaternion qHips, qSpine, qChest, qNeck, qHead, qJaw, qSkirt, qLegL, qShinL, qFootL, qLegR, qShinR, qFootR;
        Quaternion qShL, qElL, qHaL, qShR, qElR, qHaR;
        Vector3 hipsPos;
        float phase, amp, chaseW, attackW, burnW, alertT, lookW;
        bool attack, burned;
        Quaternion headLook = Quaternion.identity;
        MaterialPropertyBlock mpb;
        Color[] baseColors;

        static int Shape(Mesh m, string key)
        {
            if (m == null) return -1;
            for (int i = 0; i < m.blendShapeCount; i++)
                if (m.GetBlendShapeName(i).Contains(key)) return i;
            return -1;
        }

        void SetShape(int i, float w)
        {
            if (i >= 0 && face != null) face.SetBlendShapeWeight(i, Mathf.Clamp(w, 0f, 100f));
        }

        void Awake()
        {
            if (face != null)
            {
                Mesh fm = face.sharedMesh;
                bsJaw = Shape(fm, "JawOpen"); bsStretch = Shape(fm, "MouthStretch");
                bsWideL = Shape(fm, "EyeWideLeft"); bsWideR = Shape(fm, "EyeWideRight");
                bsBrowL = Shape(fm, "BrowDownLeft"); bsBrowR = Shape(fm, "BrowDownRight");
                bsFrownL = Shape(fm, "MouthFrownLeft"); bsFrownR = Shape(fm, "MouthFrownRight");
                bsBlinkL = Shape(fm, "EyeBlinkLeft"); bsBlinkR = Shape(fm, "EyeBlinkRight");
                bsSneerL = Shape(fm, "MouthUpperUpLeft"); bsSneerR = Shape(fm, "MouthUpperUpRight");
            }
            qHips = R(hips); qSpine = R(spine); qChest = R(chest); qNeck = R(neck); qHead = R(head); qJaw = R(jaw); qSkirt = R(skirt);
            qLegL = R(legL); qShinL = R(shinL); qFootL = R(footL); qLegR = R(legR); qShinR = R(shinR); qFootR = R(footR);
            qShL = R(shoulderL); qElL = R(elbowL); qHaL = R(handL); qShR = R(shoulderR); qElR = R(elbowR); qHaR = R(handR);
            hipsPos = hips != null ? hips.localPosition : Vector3.zero;
            mpb = new MaterialPropertyBlock();
            if (tintable != null)
            {
                baseColors = new Color[tintable.Length];
                for (int i = 0; i < tintable.Length; i++)
                {
                    Material m = tintable[i] != null ? tintable[i].sharedMaterial : null;
                    baseColors[i] = m != null && m.HasProperty("_BaseColor") ? m.GetColor("_BaseColor") : Color.white;
                }
            }
        }

        static Quaternion R(Transform t) { return t != null ? t.localRotation : Quaternion.identity; }
        static void Set(Transform t, Quaternion b, Quaternion a) { if (t != null) t.localRotation = b * a; }
        static Quaternion E(float x, float y, float z) { return Quaternion.Euler(x, y, z); }

        public void Alert() { alertT = 0.6f; }
        public void SetAttack(bool on) { attack = on; if (on) attackW = 1f; }
        public void SetBurned(bool on) { burned = on; }

        void LateUpdate()
        {
            if (animator != null) { AnimatedLate(); return; }
            float dt = Time.deltaTime;
            float stride = chasing ? 1.7f : 1.15f;
            phase += speed * dt * (Mathf.PI * 2f / stride);
            amp = Mathf.MoveTowards(amp, Mathf.Clamp01(speed / 1.4f), dt * 3f);
            chaseW = Mathf.MoveTowards(chaseW, chasing ? 1f : 0f, dt * 3f);
            attackW = Mathf.MoveTowards(attackW, attack ? 1f : 0f, dt * 6f);
            burnW = Mathf.MoveTowards(burnW, burned ? 1f : 0f, dt * (burned ? 1.6f : 0.5f));
            if (alertT > 0f) alertT -= dt;

            float s = Mathf.Sin(phase), c = Mathf.Cos(phase);
            float t = Time.time;

            // hips: bob + sway, collapse when burning
            if (hips != null)
            {
                float bob = Mathf.Abs(s) * 0.035f * amp;
                hips.localPosition = hipsPos + new Vector3(0f, bob - burnW * 0.48f, 0f);
                Set(hips, qHips, E(burnW * 8f, s * 6f * amp, s * 3f * amp));
            }
            float lean = chaseW * 16f + burnW * 48f + attackW * 10f + Mathf.Sin(t * 1.1f) * 0.8f;
            Set(spine, qSpine, E(lean * 0.5f, -s * 4f * amp, 0f));
            float breathe = Mathf.Sin(t * 1.6f) * 1.2f;
            Set(chest, qChest, E(lean * 0.5f + breathe, -s * 3f * amp, 0f));

            // legs (mostly hidden by the long dress, the shoes show)
            float legSwing = 26f * amp * (1f + chaseW * 0.4f);
            float kneeL = Mathf.Max(0f, -c) * 38f * amp + burnW * 80f;
            float kneeR = Mathf.Max(0f, c) * 38f * amp + burnW * 80f;
            Set(legL, qLegL, E(s * legSwing - burnW * 70f, 0f, 0f));
            Set(legR, qLegR, E(-s * legSwing - burnW * 70f, 0f, 0f));
            Set(shinL, qShinL, E(kneeL, 0f, 0f));
            Set(shinR, qShinR, E(kneeR, 0f, 0f));
            Set(footL, qFootL, E(-kneeL * 0.4f, 0f, 0f));
            Set(footR, qFootR, E(-kneeR * 0.4f, 0f, 0f));

            // skirt follows the stride a little
            Set(skirt, qSkirt, E(s * 2.5f * amp + chaseW * -6f, s * 4f * amp, c * 2f * amp));

            // arms: walk swing -> chase (ruler raised) -> attack (both arms up) -> burned (shielding face)
            // left arm hangs on -X: negative Z swings it outward, positive Z inward (and the mirror for the right arm)
            Quaternion walkL = E(-s * 20f * amp, 0f, -6f), walkR = E(s * 20f * amp, 0f, 6f);
            Quaternion elbowWalk = E(-12f - 8f * amp, 0f, 0f);
            float wave = Mathf.Sin(t * 9f) * 12f;
            Quaternion chaseL = E(-75f + s * 10f, 0f, -10f), chaseR = E(-150f + wave, 0f, 14f);
            Quaternion attackL = E(-155f, 0f, -30f), attackR = E(-160f, 0f, 30f);
            Quaternion burnL = E(-115f + Mathf.Sin(t * 13f) * 8f, 0f, 35f), burnR = E(-115f + Mathf.Cos(t * 11f) * 8f, 0f, -35f);
            Quaternion armL = Quaternion.Slerp(walkL, chaseL, chaseW);
            Quaternion armR = Quaternion.Slerp(walkR, chaseR, chaseW);
            armL = Quaternion.Slerp(armL, burnL, burnW);
            armR = Quaternion.Slerp(armR, burnR, burnW);
            armL = Quaternion.Slerp(armL, attackL, attackW);
            armR = Quaternion.Slerp(armR, attackR, attackW);
            Set(shoulderL, qShL, armL);
            Set(shoulderR, qShR, armR);
            Quaternion elL = Quaternion.Slerp(elbowWalk, E(-35f, 0f, 0f), Mathf.Max(chaseW, burnW));
            Quaternion elR = Quaternion.Slerp(elbowWalk, E(-50f, 0f, 0f), Mathf.Max(chaseW, burnW));
            elL = Quaternion.Slerp(elL, E(-25f, 0f, 0f), attackW);
            elR = Quaternion.Slerp(elR, E(-20f, 0f, 0f), attackW);
            Set(elbowL, qElL, elL);
            Set(elbowR, qElR, elR);
            Set(handL, qHaL, E(attackW * -20f, 0f, 0f));
            Set(handR, qHaR, E(chaseW * 25f, 0f, 0f));

            // head: search sweep, alert jerk, look at the player
            float sweep = searching ? Mathf.Sin(t * 0.9f) * 55f : 0f;
            float jerk = alertT > 0f ? Mathf.Sin(alertT * 40f) * 4f : 0f;
            Quaternion anim = E(-lean * 0.35f + burnW * 25f + jerk, sweep, Mathf.Sin(t * 0.7f) * 2f);
            lookW = Mathf.MoveTowards(lookW, lookTarget.HasValue && burnW < 0.5f ? 1f : 0f, dt * 4f);
            if (lookTarget.HasValue && head != null && neck != null)
            {
                Vector3 local = neck.InverseTransformDirection(lookTarget.Value - head.position);
                float yaw = Mathf.Clamp(Mathf.Atan2(local.x, local.z) * Mathf.Rad2Deg, -75f, 75f);
                float pitch = Mathf.Clamp(-Mathf.Atan2(local.y, new Vector2(local.x, local.z).magnitude) * Mathf.Rad2Deg, -40f, 40f);
                headLook = Quaternion.Slerp(headLook, E(pitch, yaw, 0f), dt * 8f);
            }
            Quaternion headRot = Quaternion.Slerp(anim, headLook, lookW);
            if (attackW > 0.01f) headRot = Quaternion.Slerp(headRot, E(-14f + Mathf.Sin(t * 47f) * 3f, Mathf.Sin(t * 31f) * 4f, Mathf.Sin(t * 23f) * 6f), attackW);
            Set(neck, qNeck, E(burnW * 15f, 0f, 0f));
            Set(head, qHead, headRot);
            Set(jaw, qJaw, E(attackW * 30f + chaseW * 6f + burnW * 22f + (alertT > 0f ? 10f : 0f), 0f, 0f));

            if (eyeGlow != null) eyeGlow.intensity = Mathf.Lerp(0.15f, 0.9f, Mathf.Max(chaseW, attackW)) * (1f - burnW);
            Tint(burnW);
        }

        /// <summary>Motion-captured body (Animator) + procedural head tracking, face and lunge on top.</summary>
        void AnimatedLate()
        {
            float dt = Time.deltaTime;
            float t = Time.time;
            chaseW = Mathf.MoveTowards(chaseW, chasing ? 1f : 0f, dt * 3f);
            attackW = Mathf.MoveTowards(attackW, attack ? 1f : 0f, dt * 6f);
            burnW = Mathf.MoveTowards(burnW, burned ? 1f : 0f, dt * (burned ? 1.6f : 0.5f));
            if (alertT > 0f) alertT -= dt;
            animator.SetFloat("Speed", speed, 0.12f, dt);
            animator.SetBool("Search", searching && !chasing && !burned);
            animator.SetBool("Attack", attack);
            animator.SetBool("Burn", burned);
            animator.speed = chasing ? 1.08f : 1f;

            Vector3 right = transform.right;
            // lean into the chase; lunge with both arms reaching out for you on the catch
            if (spineBone != null)
                spineBone.rotation = Quaternion.AngleAxis(chaseW * 9f + attackW * 14f + burnW * 22f, right) * spineBone.rotation;
            if (attackW > 0.01f)
            {
                if (armL != null) armL.rotation = Quaternion.AngleAxis(-78f * attackW, right) * Quaternion.AngleAxis(12f * attackW, transform.forward) * armL.rotation;
                if (armR != null) armR.rotation = Quaternion.AngleAxis(-82f * attackW, right) * Quaternion.AngleAxis(-12f * attackW, transform.forward) * armR.rotation;
            }

            // head turns to keep you in sight
            lookW = Mathf.MoveTowards(lookW, lookTarget.HasValue && burnW < 0.5f && attackW < 0.5f ? 1f : 0f, dt * 4f);
            if (headBone != null)
            {
                Quaternion want = Quaternion.identity;
                if (lookTarget.HasValue)
                {
                    Vector3 to = lookTarget.Value - headBone.position;
                    Vector3 f = transform.forward;
                    float yaw = Mathf.Clamp(Vector3.SignedAngle(Vector3.ProjectOnPlane(f, Vector3.up), Vector3.ProjectOnPlane(to, Vector3.up), Vector3.up), -70f, 70f);
                    float pitch = Mathf.Clamp(-Mathf.Atan2(to.y, new Vector2(to.x, to.z).magnitude) * Mathf.Rad2Deg, -35f, 35f);
                    want = Quaternion.AngleAxis(yaw, Vector3.up) * Quaternion.AngleAxis(pitch, right);
                }
                float jerk = alertT > 0f ? Mathf.Sin(alertT * 40f) * 4f : 0f;
                headExtra = Quaternion.Slerp(headExtra, want, dt * 7f);
                Quaternion shake = attackW > 0.01f ? Quaternion.Euler(Mathf.Sin(t * 47f) * 3f * attackW, Mathf.Sin(t * 31f) * 3f * attackW, Mathf.Sin(t * 23f) * 5f * attackW) : Quaternion.identity;
                headBone.rotation = Quaternion.Slerp(Quaternion.identity, headExtra, lookW) * Quaternion.AngleAxis(jerk, right) * shake * headBone.rotation;
            }

            // face: stern frown, wide eyes in the chase, screaming mouth on the catch
            if (face != null)
            {
                blinkT -= dt;
                if (blinkT <= 0f) { blinkT = Random.Range(2.5f, 6f); blinkW = 1f; }
                blinkW = Mathf.MoveTowards(blinkW, 0f, dt * 7f);
                float blink = attackW > 0.3f ? 0f : blinkW * 100f;
                float brow = Mathf.Max(45f, chaseW * 85f, attackW * 100f);
                SetShape(bsBrowL, brow); SetShape(bsBrowR, brow);
                SetShape(bsFrownL, 35f + chaseW * 40f); SetShape(bsFrownR, 35f + chaseW * 40f);
                SetShape(bsSneerL, chaseW * 35f + attackW * 70f); SetShape(bsSneerR, chaseW * 35f + attackW * 70f);
                SetShape(bsWideL, Mathf.Max(chaseW * 55f, attackW * 100f)); SetShape(bsWideR, Mathf.Max(chaseW * 55f, attackW * 100f));
                SetShape(bsJaw, attackW * 100f + burnW * 75f + chaseW * 12f + (alertT > 0f ? 45f : 0f));
                SetShape(bsStretch, attackW * 80f + burnW * 55f);
                SetShape(bsBlinkL, blink + burnW * 60f); SetShape(bsBlinkR, blink + burnW * 60f);
            }
            if (eyeGlow != null) eyeGlow.intensity = Mathf.Lerp(0.15f, 0.9f, Mathf.Max(chaseW, attackW)) * (1f - burnW);
            Tint(burnW);
        }

        float lastTint = -1f;
        void Tint(float b)
        {
            if (tintable == null || Mathf.Abs(b - lastTint) < 0.01f) return;
            lastTint = b;
            for (int i = 0; i < tintable.Length; i++)
            {
                if (tintable[i] == null) continue;
                tintable[i].GetPropertyBlock(mpb);
                mpb.SetColor("_BaseColor", Color.Lerp(baseColors[i], new Color(0.05f, 0.04f, 0.035f), b * 0.85f));
                tintable[i].SetPropertyBlock(mpb);
            }
        }
    }
}

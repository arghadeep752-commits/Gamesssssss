using System.Collections;
using UnityEngine;

namespace GridProto
{
    /// <summary>
    /// The catch: the enemy steps in, grabs the player by the throat and lifts them off the ground,
    /// then punches them in the face three times. The screen goes black and the "caught" screen appears.
    /// </summary>
    [DefaultExecutionOrder(100)]   // runs after the enemy's animation every frame
    public class Jumpscare : MonoBehaviour
    {
        public PlayerController player;
        public Hud hud;
        public Light faceLight;    // lights only the enemy, switched on during the attack
        public AudioSource sfx;    // 2D

        public bool Active { get; private set; }
        public bool Finished { get; private set; }
        public float GrabProgress { get; private set; }
        public int Impacts { get; private set; }

        EnemyAI enemy;
        EnemyAnimator anim;
        Transform cam, pivot;
        Camera camera3d;
        Quaternion look;
        float lift, shake, kickPitch, kickRoll, recoil, eyeHeight;

        public void Begin(EnemyAI who)
        {
            if (Active || who == null || player == null) return;
            Active = true;
            enemy = who;
            anim = who.anim;
            StartCoroutine(Sequence());
        }

        IEnumerator Sequence()
        {
            player.SetControlEnabled(false);
            if (hud != null) hud.SetControlsVisible(false);
            camera3d = player.playerCamera;
            cam = camera3d.transform;
            pivot = player.cameraPivot;
            eyeHeight = player.EyeHeight;
            enemy.PrepareForAttack();

            // the enemy steps right up to the player and they face each other
            Vector3 p = player.transform.position;
            Vector3 dir = enemy.transform.position - p;
            dir.y = 0f;
            if (dir.sqrMagnitude < 0.0001f) dir = player.transform.forward;
            dir.Normalize();
            enemy.transform.position = p + dir * 0.6f;
            enemy.transform.rotation = Quaternion.LookRotation(-dir, Vector3.up);
            player.transform.rotation = Quaternion.LookRotation(dir, Vector3.up);
            look = cam.rotation;
            if (faceLight != null) faceLight.enabled = true;
            Play(ProtoAudio.Scream, 1f);
            if (hud != null) hud.Flash(new Color(1f, 1f, 1f, 0.5f));
            anim.aggression = 1f;
            anim.hasLookTarget = true;
            shake = 0.8f;

            // 1) grabs the throat and lifts the player off the ground
            float t = 0f;
            while (t < 0.6f)
            {
                t += Time.deltaTime;
                GrabProgress = Mathf.Clamp01(t / 0.35f);
                anim.grabWeight = Smooth(GrabProgress);
                lift = Smooth(Mathf.Clamp01((t - 0.15f) / 0.45f)) * 0.14f;
                shake = Mathf.Max(shake, 0.45f);
                yield return null;
            }
            Play(ProtoAudio.Choke, 0.9f);
            t = 0f;
            while (t < 0.45f)
            {
                t += Time.deltaTime;
                shake = Mathf.Max(shake, 0.4f);
                yield return null;
            }

            // 2) three punches to the face
            for (int i = 0; i < 3; i++)
            {
                t = 0f;
                while (t < 0.3f)   // wind up
                {
                    t += Time.deltaTime;
                    anim.punchWeight = Mathf.MoveTowards(anim.punchWeight, 1f, Time.deltaTime * 6f);
                    anim.punchTarget = WindUpPoint();
                    yield return null;
                }
                t = 0f;
                while (t < 0.08f)  // strike
                {
                    t += Time.deltaTime;
                    anim.punchWeight = 1f;
                    anim.punchTarget = Vector3.Lerp(WindUpPoint(), FacePoint(), Smooth(Mathf.Clamp01(t / 0.08f)));
                    yield return null;
                }
                Impact(i);
                t = 0f;
                while (t < 0.38f)  // pull back
                {
                    t += Time.deltaTime;
                    anim.punchTarget = Vector3.Lerp(FacePoint(), WindUpPoint(), Smooth(Mathf.Clamp01(t / 0.38f)) * 0.7f);
                    yield return null;
                }
            }

            // 3) knocked out
            Play(ProtoAudio.Ringing, 0.7f);
            if (hud != null) hud.FadeToBlack(0.9f);
            t = 0f;
            while (t < 1.1f)
            {
                t += Time.deltaTime;
                yield return null;
            }
            Finished = true;
            if (hud != null) hud.ShowCaught();
        }

        void LateUpdate()
        {
            if (!Active || cam == null || enemy == null) return;
            float dt = Time.deltaTime;

            // lifted by the throat, shaking, knocked back by each punch
            Vector3 jitter = Random.insideUnitSphere * 0.01f * shake;
            pivot.localPosition = new Vector3(0f, eyeHeight + lift, -recoil) + jitter;

            // the camera is forced to look into the mask
            Vector3 face = anim.head.position + enemy.transform.up * 0.13f + enemy.transform.forward * 0.1f;
            Vector3 toFace = face - cam.position;
            if (toFace.sqrMagnitude > 0.0001f)
                look = Quaternion.Slerp(look, Quaternion.LookRotation(toFace, Vector3.up), 1f - Mathf.Exp(-12f * dt));
            cam.rotation = look * Quaternion.Euler(-kickPitch, 0f, kickRoll);
            camera3d.fieldOfView = Mathf.Lerp(camera3d.fieldOfView, 55f, 1f - Mathf.Exp(-5f * dt));

            kickPitch = Mathf.Lerp(kickPitch, 0f, 1f - Mathf.Exp(-7f * dt));
            kickRoll = Mathf.Lerp(kickRoll, 0f, 1f - Mathf.Exp(-5f * dt));
            recoil = Mathf.Lerp(recoil, 0f, 1f - Mathf.Exp(-9f * dt));
            shake = Mathf.MoveTowards(shake, 0f, dt * 2.5f);

            // where the hands go next frame
            anim.grabTarget = cam.position + cam.forward * 0.14f - cam.up * 0.2f;
            anim.lookTarget = cam.position;
        }

        Vector3 FacePoint()
        {
            return cam.position + cam.forward * 0.11f;
        }

        Vector3 WindUpPoint()
        {
            Transform e = enemy.transform;
            return anim.chest.position + e.right * 0.3f - e.forward * 0.16f + Vector3.up * 0.05f;
        }

        void Impact(int index)
        {
            Impacts = index + 1;
            Play(ProtoAudio.Punch, 1f);
            kickPitch = 13f + index * 3f;
            kickRoll = (index % 2 == 0 ? 1f : -1f) * (8f + index * 2f);
            recoil = 0.06f;
            shake = 1.3f;
            if (hud != null) hud.Flash(new Color(0.75f, 0f, 0f, 0.6f + index * 0.1f));
        }

        void Play(AudioClip clip, float volume)
        {
            if (sfx != null && clip != null) sfx.PlayOneShot(clip, volume);
        }

        static float Smooth(float x)
        {
            return x * x * (3f - 2f * x);
        }
    }
}

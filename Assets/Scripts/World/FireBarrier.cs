using System.Collections;
using UnityEngine;
using UnityEngine.AI;

namespace NightClass
{
    /// <summary>A fire blocking the west corridor until the sprinklers are turned on.</summary>
    public class FireBarrier : MonoBehaviour
    {
        public ParticleSystem[] flames;
        public ParticleSystem steam;
        public Light fireLight;
        public Collider blocker;
        public NavMeshObstacle obstacle;
        public bool Burning { get; private set; } = true;
        AudioSource loop;
        float baseIntensity, lastWarn;

        void Start()
        {
            if (fireLight != null) baseIntensity = fireLight.intensity;
            loop = Sfx.Loop(gameObject, GameAssets.I.fireLoop, 0.7f, 18f);
        }

        void Update()
        {
            if (!Burning || fireLight == null) return;
            float n = Mathf.PerlinNoise(Time.time * 6f, 1.7f);
            fireLight.intensity = baseIntensity * (0.75f + 0.5f * n);
        }

        void OnTriggerEnter(Collider c)
        {
            if (!Burning || c.GetComponent<FPController>() == null) return;
            if (Time.time - lastWarn > 4f)
            {
                lastWarn = Time.time;
                NCGame.I.Message("It's too hot to get through. Is there a way to put the fire out?", 3f);
            }
        }

        public void Extinguish()
        {
            if (!Burning) return;
            Burning = false;
            Progress.FireOut = true;
            StartCoroutine(Out());
        }

        IEnumerator Out()
        {
            foreach (ParticleSystem f in flames)
                if (f != null) f.Stop(true, ParticleSystemStopBehavior.StopEmitting);
            if (steam != null) steam.Play(true);
            Sfx.Play3D(GameAssets.I.steam, transform.position, 1f, 1f, 25f);
            float t = 0f;
            float v0 = loop != null ? loop.volume : 0f;
            while (t < 1f)
            {
                t += Time.deltaTime / 2.5f;
                if (fireLight != null) fireLight.intensity = baseIntensity * (1f - t);
                if (loop != null) loop.volume = v0 * (1f - t);
                yield return null;
            }
            if (fireLight != null) fireLight.enabled = false;
            if (loop != null) loop.Stop();
            if (blocker != null) blocker.enabled = false;
            if (obstacle != null) obstacle.enabled = false;
            NCGame.I.Message("The fire is out.", 2.5f);
        }
    }
}

using System.Collections.Generic;
using UnityEngine;

namespace ZombieStrike
{
    /// <summary>Plays the game's sounds from pooled audio sources.</summary>
    public class Sfx : MonoBehaviour
    {
        public static Sfx I { get; private set; }

        readonly Dictionary<string, AudioClip> clips = new Dictionary<string, AudioClip>();
        AudioSource[] flat;
        AudioSource[] world;
        int nextFlat, nextWorld;
        AudioSource gun, ambience, heartbeat;
        float heartbeatTarget;

        void Awake()
        {
            I = this;
            flat = new AudioSource[6];
            for (int i = 0; i < flat.Length; i++) flat[i] = MakeSource("Sfx2D", false);
            world = new AudioSource[12];
            for (int i = 0; i < world.Length; i++) world[i] = MakeSource("Sfx3D", true);
            gun = MakeSource("Gun", false);
            ambience = MakeSource("Ambience", false);
            ambience.loop = true;
            heartbeat = MakeSource("Heartbeat", false);
            heartbeat.loop = true;
        }

        AudioSource MakeSource(string name, bool spatial)
        {
            var go = new GameObject(name);
            go.transform.SetParent(transform, false);
            var s = go.AddComponent<AudioSource>();
            s.playOnAwake = false;
            s.dopplerLevel = 0f;
            if (spatial)
            {
                s.spatialBlend = 1f;
                s.rolloffMode = AudioRolloffMode.Linear;
                s.minDistance = 2f;
                s.maxDistance = 35f;
            }
            else
            {
                s.spatialBlend = 0f;
            }
            return s;
        }

        public AudioClip Clip(string name)
        {
            AudioClip c;
            if (clips.TryGetValue(name, out c)) return c;
            c = Resources.Load<AudioClip>("Audio/" + name);
            if (c == null) Debug.LogWarning("[ZS] missing sound " + name);
            clips[name] = c;
            return c;
        }

        public void Play2D(string name, float volume = 1f, float pitch = 1f)
        {
            AudioClip c = Clip(name);
            if (c == null) return;
            AudioSource s = flat[nextFlat];
            nextFlat = (nextFlat + 1) % flat.Length;
            s.Stop();
            s.clip = c;
            s.volume = volume;
            s.pitch = pitch;
            s.Play();
        }

        public void PlayAt(string name, Vector3 position, float volume = 1f, float pitch = 1f, float maxDistance = 35f)
        {
            AudioClip c = Clip(name);
            if (c == null) return;
            AudioSource s = world[nextWorld];
            nextWorld = (nextWorld + 1) % world.Length;
            s.Stop();
            s.transform.position = position;
            s.clip = c;
            s.volume = volume;
            s.pitch = pitch;
            s.maxDistance = maxDistance;
            s.Play();
        }

        public void Gunshot()
        {
            AudioClip c = Clip(Random.value < 0.5f ? "gunshot1" : "gunshot2");
            if (c == null) return;
            gun.pitch = Random.Range(0.94f, 1.06f);
            gun.PlayOneShot(c, 0.85f);
        }

        public void StartAmbience()
        {
            AudioClip c = Clip("ambience");
            if (c == null || ambience.isPlaying) return;
            ambience.clip = c;
            ambience.volume = 0.45f;
            ambience.Play();
        }

        public void SetHeartbeat(float amount)
        {
            heartbeatTarget = Mathf.Clamp01(amount);
        }

        void Update()
        {
            if (heartbeatTarget > 0.01f && !heartbeat.isPlaying)
            {
                AudioClip c = Clip("heartbeat");
                if (c != null)
                {
                    heartbeat.clip = c;
                    heartbeat.volume = 0f;
                    heartbeat.Play();
                }
            }
            if (heartbeat.isPlaying)
            {
                heartbeat.volume = Mathf.MoveTowards(heartbeat.volume, heartbeatTarget, Time.unscaledDeltaTime);
                heartbeat.pitch = 0.9f + heartbeatTarget * 0.35f;
                if (heartbeatTarget <= 0.01f && heartbeat.volume <= 0.01f) heartbeat.Stop();
            }
        }
    }
}

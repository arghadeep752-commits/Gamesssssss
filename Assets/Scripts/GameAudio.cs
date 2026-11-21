using System.Collections.Generic;
using UnityEngine;

namespace TradersMadness
{
    /// <summary>Plays the recorded sounds (Resources/Sounds/*.ogg). Missing files are simply silent.
    /// Volumes are in decibels (0 dB = the file as recorded).</summary>
    public class GameAudio : MonoBehaviour
    {
        readonly Dictionary<string, AudioClip> cache = new Dictionary<string, AudioClip>();
        readonly Dictionary<string, AudioSource> loops = new Dictionary<string, AudioSource>();
        readonly List<AudioSource> oneShots = new List<AudioSource>();

        public static float Lin(float db)
        {
            return Mathf.Clamp01(Mathf.Pow(10f, db / 20f));
        }

        public AudioClip Clip(string n)
        {
            AudioClip c;
            if (cache.TryGetValue(n, out c)) return c;
            c = Resources.Load<AudioClip>("Sounds/" + n);
            cache[n] = c;
            return c;
        }

        public bool Has(string n)
        {
            return Clip(n) != null;
        }

        AudioSource Source(bool spatial)
        {
            for (int i = oneShots.Count - 1; i >= 0; i--)
            {
                AudioSource s = oneShots[i];
                if (s == null) { oneShots.RemoveAt(i); continue; }
                if (!s.isPlaying && s.spatialBlend == (spatial ? 1f : 0f)) return s;
            }
            var go = new GameObject(spatial ? "Sound 3D" : "Sound");
            go.transform.SetParent(transform, false);
            AudioSource src = go.AddComponent<AudioSource>();
            src.playOnAwake = false;
            src.spatialBlend = spatial ? 1f : 0f;
            if (spatial)
            {
                src.rolloffMode = AudioRolloffMode.Logarithmic;
                src.minDistance = 3f;
                src.maxDistance = 30f;
                src.dopplerLevel = 0f;
            }
            oneShots.Add(src);
            return src;
        }

        public void Play(string n, float db = 0f, float pitch = 1f)
        {
            AudioClip c = Clip(n);
            if (c == null) return;
            AudioSource s = Source(false);
            s.clip = c;
            s.volume = Lin(db);
            s.pitch = pitch;
            s.Play();
        }

        public void Play3D(string n, Vector3 pos, float db = 0f, float pitch = 1f)
        {
            AudioClip c = Clip(n);
            if (c == null) return;
            AudioSource s = Source(true);
            s.transform.position = pos;
            s.clip = c;
            s.volume = Lin(db);
            s.pitch = pitch;
            s.Play();
        }

        public void Loop(string n, float db = 0f)
        {
            AudioSource s;
            if (loops.TryGetValue(n, out s) && s != null)
            {
                s.volume = Lin(db);
                if (!s.isPlaying) s.Play();
                return;
            }
            AudioClip c = Clip(n);
            if (c == null) return;
            var go = new GameObject("Loop " + n);
            go.transform.SetParent(transform, false);
            s = go.AddComponent<AudioSource>();
            s.playOnAwake = false;
            s.spatialBlend = 0f;
            s.loop = true;
            s.clip = c;
            s.volume = Lin(db);
            s.Play();
            loops[n] = s;
        }

        public void Stop(string n)
        {
            AudioSource s;
            if (loops.TryGetValue(n, out s) && s != null) s.Stop();
        }

        public void StopAll()
        {
            foreach (var kv in loops)
                if (kv.Value != null) kv.Value.Stop();
            foreach (AudioSource s in oneShots)
                if (s != null) s.Stop();
        }

        public void SetVol(string n, float db)
        {
            AudioSource s;
            if (loops.TryGetValue(n, out s) && s != null) s.volume = Lin(db);
        }
    }
}

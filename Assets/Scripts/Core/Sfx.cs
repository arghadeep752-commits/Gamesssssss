using UnityEngine;

namespace NightClass
{
    /// <summary>Small pooled one-shot audio player (2D and 3D).</summary>
    public static class Sfx
    {
        static AudioSource[] pool;
        static int next;
        static Transform root;

        static void Ensure()
        {
            if (pool != null && root != null) return;
            var go = new GameObject("SfxPool");
            Object.DontDestroyOnLoad(go);
            root = go.transform;
            pool = new AudioSource[24];
            for (int i = 0; i < pool.Length; i++)
            {
                var c = new GameObject("sfx" + i);
                c.transform.SetParent(root, false);
                var s = c.AddComponent<AudioSource>();
                s.playOnAwake = false;
                s.dopplerLevel = 0f;
                s.rolloffMode = AudioRolloffMode.Linear;
                pool[i] = s;
            }
        }

        public static AudioClip Pick(AudioClip[] clips)
        {
            if (clips == null || clips.Length == 0) return null;
            return clips[Random.Range(0, clips.Length)];
        }

        static AudioSource Next()
        {
            Ensure();
            for (int k = 0; k < pool.Length; k++)
            {
                AudioSource s = pool[(next + k) % pool.Length];
                if (!s.isPlaying) { next = (next + k + 1) % pool.Length; return s; }
            }
            AudioSource r = pool[next];
            next = (next + 1) % pool.Length;
            return r;
        }

        public static AudioSource Play2D(AudioClip clip, float volume = 1f, float pitch = 1f)
        {
            if (clip == null) return null;
            AudioSource s = Next();
            s.transform.position = Vector3.zero;
            s.spatialBlend = 0f;
            s.clip = clip;
            s.volume = volume;
            s.pitch = pitch;
            s.loop = false;
            s.Play();
            return s;
        }

        public static AudioSource Play3D(AudioClip clip, Vector3 pos, float volume = 1f, float pitch = 1f, float maxDistance = 30f)
        {
            if (clip == null) return null;
            AudioSource s = Next();
            s.transform.position = pos;
            s.spatialBlend = 1f;
            s.minDistance = 1.2f;
            s.maxDistance = maxDistance;
            s.clip = clip;
            s.volume = volume;
            s.pitch = pitch;
            s.loop = false;
            s.Play();
            return s;
        }

        /// <summary>A looping 3D source attached to a transform.</summary>
        public static AudioSource Loop(GameObject host, AudioClip clip, float volume, float maxDistance = 20f, bool spatial = true)
        {
            var s = host.AddComponent<AudioSource>();
            s.clip = clip;
            s.loop = true;
            s.volume = volume;
            s.spatialBlend = spatial ? 1f : 0f;
            s.rolloffMode = AudioRolloffMode.Linear;
            s.minDistance = 1f;
            s.maxDistance = maxDistance;
            s.dopplerLevel = 0f;
            s.playOnAwake = false;
            if (clip != null) s.Play();
            return s;
        }
    }
}

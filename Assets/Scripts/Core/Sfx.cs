using UnityEngine;

namespace RealFPS
{
    /// <summary>Small pooled one-shot audio helper.</summary>
    public static class Sfx
    {
        static AudioSource ui;
        static AudioSource[] pool;
        static int next;

        static void Init()
        {
            if (ui != null) return;
            var go = new GameObject("Sfx");
            Object.DontDestroyOnLoad(go);
            ui = go.AddComponent<AudioSource>();
            ui.playOnAwake = false;
            ui.spatialBlend = 0f;
            ui.ignoreListenerPause = true;
            pool = new AudioSource[8];
            for (int i = 0; i < pool.Length; i++)
            {
                var c = new GameObject("Sfx3D" + i);
                c.transform.SetParent(go.transform);
                var s = c.AddComponent<AudioSource>();
                s.playOnAwake = false;
                s.spatialBlend = 1f;
                s.rolloffMode = AudioRolloffMode.Linear;
                s.minDistance = 2f;
                s.maxDistance = 40f;
                s.dopplerLevel = 0f;
                pool[i] = s;
            }
        }

        public static void Play2D(AudioClip clip, float volume = 1f, float pitch = 1f)
        {
            if (clip == null) return;
            Init();
            ui.pitch = pitch;
            ui.PlayOneShot(clip, volume);
        }

        public static void Play3D(AudioClip clip, Vector3 pos, float volume = 1f, float pitch = 1f, float maxDistance = 40f)
        {
            if (clip == null) return;
            Init();
            AudioSource s = pool[next];
            next = (next + 1) % pool.Length;
            s.transform.position = pos;
            s.pitch = pitch;
            s.maxDistance = maxDistance;
            s.PlayOneShot(clip, volume);
        }

        public static AudioClip Pick(AudioClip[] clips)
        {
            if (clips == null || clips.Length == 0) return null;
            return clips[Random.Range(0, clips.Length)];
        }
    }
}

using UnityEngine;

namespace GridProto
{
    /// <summary>Sound effects synthesized in code (footsteps, door, wind), so no audio files are needed.</summary>
    public static class ProtoAudio
    {
        const int Rate = 44100;

        static AudioClip[] footsteps;
        static AudioClip doorOpen, doorShut, thump, wind, click;

        public static AudioClip Footstep(int index)
        {
            if (footsteps == null)
            {
                footsteps = new AudioClip[4];
                for (int k = 0; k < footsteps.Length; k++) footsteps[k] = MakeFootstep(k);
            }
            int i = index % footsteps.Length;
            if (i < 0) i += footsteps.Length;
            return footsteps[i];
        }

        public static AudioClip DoorOpen { get { if (doorOpen == null) doorOpen = MakeDoorOpen(); return doorOpen; } }
        public static AudioClip DoorShut { get { if (doorShut == null) doorShut = MakeDoorShut(); return doorShut; } }
        public static AudioClip Thump { get { if (thump == null) thump = MakeThump(); return thump; } }
        public static AudioClip Wind { get { if (wind == null) wind = MakeWind(); return wind; } }
        public static AudioClip Click { get { if (click == null) click = MakeClick(); return click; } }

        static AudioClip Make(string name, float[] data)
        {
            AudioClip clip = AudioClip.Create(name, data.Length, 1, Rate, false);
            clip.SetData(data, 0);
            return clip;
        }

        static float Noise(System.Random r)
        {
            return (float)(r.NextDouble() * 2.0 - 1.0);
        }

        static void Normalize(float[] d, float peak)
        {
            float max = 0.0001f;
            for (int i = 0; i < d.Length; i++)
            {
                float a = Mathf.Abs(d[i]);
                if (a > max) max = a;
            }
            float k = peak / max;
            for (int i = 0; i < d.Length; i++) d[i] *= k;
        }

        // short metallic tick starting at `start` seconds
        static float Tick(float t, float start, float freq, System.Random r)
        {
            float tt = t - start;
            if (tt < 0f || tt > 0.03f) return 0f;
            float env = Mathf.Exp(-tt * 180f);
            return (Mathf.Sin(2f * Mathf.PI * freq * tt) * 0.7f + Noise(r) * 0.3f) * env;
        }

        static AudioClip MakeFootstep(int seed)
        {
            var r = new System.Random(101 + seed * 17);
            int n = (int)(Rate * 0.2f);
            var d = new float[n];
            float lp = 0f, lp2 = 0f;
            float cutoff = 0.10f + 0.03f * seed;
            float thumpFreq = 70f + 9f * seed;
            for (int i = 0; i < n; i++)
            {
                float t = i / (float)Rate;
                float env = Mathf.Exp(-t * 32f) * Mathf.Clamp01(t / 0.003f);
                lp += (Noise(r) - lp) * cutoff;
                lp2 += (lp - lp2) * 0.5f;
                float body = Mathf.Sin(2f * Mathf.PI * thumpFreq * t) * Mathf.Exp(-t * 45f);
                float t2 = t - 0.035f;
                float scuff = t2 > 0f ? Noise(r) * Mathf.Exp(-t2 * 70f) * 0.12f : 0f;
                d[i] = (lp2 * 1.6f + body * 0.55f) * env + scuff;
            }
            Normalize(d, 0.9f);
            return Make("footstep_" + seed, d);
        }

        static AudioClip MakeDoorOpen()
        {
            var r = new System.Random(7);
            int n = (int)(Rate * 1.1f);
            var d = new float[n];
            float phase = 0f, air = 0f;
            for (int i = 0; i < n; i++)
            {
                float t = i / (float)Rate;
                float s = Tick(t, 0f, 2600f, r) * 0.8f + Tick(t, 0.045f, 1900f, r) * 0.6f;   // latch
                if (t > 0.08f && t < 0.95f)
                {
                    // hinge creak: a stick-slip tone that slowly rises
                    float ct = (t - 0.08f) / 0.87f;
                    float f = Mathf.Lerp(210f, 330f, ct) * (1f + 0.04f * Mathf.Sin(t * 37f));
                    phase += 2f * Mathf.PI * f / Rate;
                    float pulses = Mathf.Pow(0.5f + 0.5f * Mathf.Sin(t * 2f * Mathf.PI * 23f), 6f);
                    float tone = Mathf.Sin(phase) * 0.6f + Mathf.Sin(phase * 2.01f) * 0.3f + Mathf.Sin(phase * 3.03f) * 0.15f;
                    s += tone * pulses * Mathf.Sin(ct * Mathf.PI) * 0.22f;
                }
                air += (Noise(r) - air) * 0.02f;
                s += air * Mathf.Sin(Mathf.Clamp01((t - 0.1f) / 0.8f) * Mathf.PI) * 0.5f;
                d[i] = s;
            }
            Normalize(d, 0.8f);
            return Make("door_open", d);
        }

        static AudioClip MakeDoorShut()
        {
            var r = new System.Random(11);
            int n = (int)(Rate * 0.6f);
            var d = new float[n];
            float lp = 0f;
            for (int i = 0; i < n; i++)
            {
                float t = i / (float)Rate;
                float body = Mathf.Sin(2f * Mathf.PI * 62f * t) * Mathf.Exp(-t * 14f)
                           + Mathf.Sin(2f * Mathf.PI * 118f * t) * Mathf.Exp(-t * 22f) * 0.5f;
                lp += (Noise(r) - lp) * 0.08f;
                float knock = lp * Mathf.Exp(-t * 40f) * 1.4f;
                d[i] = (body * 0.9f + knock) * Mathf.Clamp01(t / 0.002f) + Tick(t, 0.012f, 2300f, r) * 0.5f;
            }
            Normalize(d, 0.95f);
            return Make("door_shut", d);
        }

        static AudioClip MakeThump()
        {
            var r = new System.Random(5);
            int n = (int)(Rate * 0.25f);
            var d = new float[n];
            float lp = 0f;
            for (int i = 0; i < n; i++)
            {
                float t = i / (float)Rate;
                lp += (Noise(r) - lp) * 0.06f;
                d[i] = (Mathf.Sin(2f * Mathf.PI * 55f * t) * Mathf.Exp(-t * 20f) + lp * Mathf.Exp(-t * 30f) * 1.2f) * Mathf.Clamp01(t / 0.002f);
            }
            Normalize(d, 0.8f);
            return Make("thump", d);
        }

        static AudioClip MakeWind()
        {
            var r = new System.Random(3);
            float length = 8f;
            int n = (int)(Rate * length);
            var d = new float[n];
            float low = 0f, high = 0f;
            for (int i = 0; i < n; i++)
            {
                float t = i / (float)Rate;
                float x = Noise(r);
                low += (x - low) * 0.012f;
                high += (x - high) * 0.06f;
                float gust = 0.55f + 0.25f * Mathf.Sin(2f * Mathf.PI * t / length)
                                   + 0.2f * Mathf.Sin(2f * Mathf.PI * 3f * t / length + 1.3f);
                d[i] = (low * 2.2f + high * 0.35f) * gust;
            }
            // seamless loop: start one second in and cross-fade the tail into the skipped second
            int fade = Rate;
            int m = n - fade;
            var o = new float[m];
            for (int i = 0; i < m; i++) o[i] = d[i + fade];
            for (int k = 0; k < fade; k++)
            {
                float w = k / (float)fade;
                o[m - fade + k] = d[m + k] * (1f - w) + d[k] * w;
            }
            Normalize(o, 0.6f);
            return Make("wind", o);
        }

        static AudioClip MakeClick()
        {
            int n = (int)(Rate * 0.03f);
            var d = new float[n];
            for (int i = 0; i < n; i++)
            {
                float t = i / (float)Rate;
                d[i] = Mathf.Sin(2f * Mathf.PI * 1800f * t) * Mathf.Exp(-t * 220f);
            }
            Normalize(d, 0.5f);
            return Make("click", d);
        }
    }
}

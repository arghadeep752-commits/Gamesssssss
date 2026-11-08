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

        // ---------------- enemy and jumpscare sounds
        static AudioClip[] enemySteps;
        static AudioClip growl, roar, scream, choke, punch, heartbeat, drone, ringing;

        public static AudioClip EnemyStep(int index)
        {
            if (enemySteps == null)
            {
                enemySteps = new AudioClip[3];
                for (int k = 0; k < enemySteps.Length; k++) enemySteps[k] = MakeEnemyStep(k);
            }
            int i = index % enemySteps.Length;
            if (i < 0) i += enemySteps.Length;
            return enemySteps[i];
        }

        public static AudioClip Growl { get { if (growl == null) growl = MakeGrowl(); return growl; } }
        public static AudioClip Roar { get { if (roar == null) roar = MakeRoar(); return roar; } }
        public static AudioClip Scream { get { if (scream == null) scream = MakeScream(); return scream; } }
        public static AudioClip Choke { get { if (choke == null) choke = MakeChoke(); return choke; } }
        public static AudioClip Punch { get { if (punch == null) punch = MakePunch(); return punch; } }
        public static AudioClip Heartbeat { get { if (heartbeat == null) heartbeat = MakeHeartbeat(); return heartbeat; } }
        public static AudioClip Drone { get { if (drone == null) drone = MakeDrone(); return drone; } }
        public static AudioClip Ringing { get { if (ringing == null) ringing = MakeRinging(); return ringing; } }

        static float Saw(float cycles)
        {
            return 2f * (cycles - Mathf.Floor(cycles + 0.5f));
        }

        static float Drive(float x, float amount)
        {
            return (float)System.Math.Tanh(x * amount);
        }

        // turns a buffer into a seamless loop by cross-fading its tail into its skipped head
        static float[] Loop(float[] d, int fade)
        {
            int m = d.Length - fade;
            var o = new float[m];
            for (int i = 0; i < m; i++) o[i] = d[i + fade];
            for (int k = 0; k < fade; k++)
            {
                float w = k / (float)fade;
                o[m - fade + k] = d[m + k] * (1f - w) + d[k] * w;
            }
            return o;
        }

        static AudioClip MakeEnemyStep(int seed)
        {
            var r = new System.Random(301 + seed * 13);
            int n = (int)(Rate * 0.3f);
            var d = new float[n];
            float lp = 0f, lp2 = 0f;
            float f = 48f + seed * 6f;
            for (int i = 0; i < n; i++)
            {
                float t = i / (float)Rate;
                lp += (Noise(r) - lp) * 0.07f;
                lp2 += (lp - lp2) * 0.35f;
                float body = Mathf.Sin(2f * Mathf.PI * f * t) * Mathf.Exp(-t * 26f);
                float env = Mathf.Exp(-t * 22f) * Mathf.Clamp01(t / 0.004f);
                float t2 = t - 0.05f;
                float scrape = t2 > 0f ? Noise(r) * Mathf.Exp(-t2 * 40f) * 0.1f : 0f;
                d[i] = (lp2 * 2.2f + body * 0.9f) * env + scrape;
            }
            Normalize(d, 0.95f);
            return Make("enemy_step_" + seed, d);
        }

        // heavy breathing with a growl underneath (loops)
        static AudioClip MakeGrowl()
        {
            var r = new System.Random(41);
            float length = 3.6f;
            int n = (int)(Rate * length);
            var d = new float[n];
            float bp1 = 0f, bp2 = 0f, phase = 0f;
            for (int i = 0; i < n; i++)
            {
                float t = i / (float)Rate;
                float breath = Mathf.Sin(2f * Mathf.PI * t / 1.8f);          // two breaths per loop
                float inhale = Mathf.Clamp01(breath), exhale = Mathf.Clamp01(-breath);
                float x = Noise(r);
                bp1 += (x - bp1) * 0.18f;
                bp2 += (bp1 - bp2) * 0.18f;
                float air = (bp1 - bp2) * (0.5f * inhale + 0.9f * exhale);
                float f = 62f + 10f * Mathf.Sin(2f * Mathf.PI * t / 1.8f * 3f);
                phase += f / Rate;
                float rasp = Saw(phase) * (0.6f + 0.4f * Mathf.Sin(2f * Mathf.PI * 23f * t)) * exhale * 0.5f;
                d[i] = Drive(air * 2.5f + rasp, 1.6f);
            }
            float[] o = Loop(d, Rate / 2);
            Normalize(o, 0.75f);
            return Make("growl", o);
        }

        static AudioClip MakeRoar()
        {
            var r = new System.Random(77);
            int n = (int)(Rate * 1.4f);
            var d = new float[n];
            float p1 = 0f, p2 = 0f, p3 = 0f, bp1 = 0f, bp2 = 0f;
            for (int i = 0; i < n; i++)
            {
                float t = i / (float)Rate;
                float env = Mathf.Clamp01(t / 0.06f) * Mathf.Exp(-Mathf.Max(0f, t - 0.5f) * 3.2f);
                float f = Mathf.Lerp(105f, 80f, t / 1.4f) * (1f + 0.05f * Mathf.Sin(2f * Mathf.PI * 7f * t));
                p1 += f / Rate; p2 += f * 1.51f / Rate; p3 += f * 0.5f / Rate;
                float x = Noise(r);
                bp1 += (x - bp1) * 0.3f; bp2 += (bp1 - bp2) * 0.3f;
                float s = Saw(p1) * 0.6f + Saw(p2) * 0.3f + Mathf.Sin(2f * Mathf.PI * p3) * 0.5f + (bp1 - bp2) * 1.6f;
                d[i] = Drive(s * env, 2.4f);
            }
            Normalize(d, 0.95f);
            return Make("roar", d);
        }

        static AudioClip MakeScream()
        {
            var r = new System.Random(13);
            int n = (int)(Rate * 1.5f);
            var d = new float[n];
            float a = 0f, b = 0f, c = 0f, hp = 0f, prev = 0f;
            for (int i = 0; i < n; i++)
            {
                float t = i / (float)Rate;
                float env = Mathf.Clamp01(t / 0.02f) * Mathf.Exp(-Mathf.Max(0f, t - 0.35f) * 2.6f);
                float f = Mathf.Lerp(520f, 260f, Mathf.Pow(t / 1.5f, 0.6f)) * (1f + 0.06f * Mathf.Sin(2f * Mathf.PI * 11f * t));
                a += f / Rate; b += f * 1.012f / Rate; c += f * 0.497f / Rate;
                float x = Noise(r);
                hp = 0.92f * (hp + x - prev); prev = x;   // hiss
                float s = Saw(a) * 0.5f + Saw(b) * 0.5f + Saw(c) * 0.35f + hp * 0.45f;
                d[i] = Drive(s * env, 3f);
            }
            Normalize(d, 1f);
            return Make("scream", d);
        }

        static AudioClip MakeChoke()
        {
            var r = new System.Random(19);
            int n = (int)(Rate * 1.1f);
            var d = new float[n];
            float lp = 0f, ph = 0f;
            for (int i = 0; i < n; i++)
            {
                float t = i / (float)Rate;
                float env = Mathf.Clamp01(t / 0.05f) * Mathf.Clamp01((1.1f - t) / 0.2f);
                lp += (Noise(r) - lp) * 0.12f;
                float gurgle = Mathf.Pow(0.5f + 0.5f * Mathf.Sin(2f * Mathf.PI * (17f + 6f * Mathf.Sin(t * 5f)) * t), 3f);
                ph += (140f + 30f * Mathf.Sin(t * 9f)) / Rate;
                d[i] = (lp * 2f * gurgle + Saw(ph) * 0.15f * gurgle) * env;
            }
            Normalize(d, 0.8f);
            return Make("choke", d);
        }

        static AudioClip MakePunch()
        {
            var r = new System.Random(23);
            int n = (int)(Rate * 0.45f);
            var d = new float[n];
            float lp = 0f;
            for (int i = 0; i < n; i++)
            {
                float t = i / (float)Rate;
                lp += (Noise(r) - lp) * 0.25f;
                float crack = Noise(r) * Mathf.Exp(-t * 160f) * 0.9f;
                float thud = Mathf.Sin(2f * Mathf.PI * (95f - 40f * t) * t) * Mathf.Exp(-t * 14f);
                float body = lp * Mathf.Exp(-t * 30f) * 1.5f;
                d[i] = Drive(crack + thud * 1.2f + body, 1.8f) * Mathf.Clamp01(t / 0.001f);
            }
            Normalize(d, 1f);
            return Make("punch", d);
        }

        static AudioClip MakeHeartbeat()
        {
            int n = (int)(Rate * 0.9f);
            var d = new float[n];
            for (int i = 0; i < n; i++)
            {
                float t = i / (float)Rate;
                float lub = Pulse(t, 0f, 52f), dub = Pulse(t, 0.24f, 60f) * 0.7f;
                d[i] = lub + dub;
            }
            Normalize(d, 0.9f);
            return Make("heartbeat", d);
        }

        static float Pulse(float t, float start, float freq)
        {
            float tt = t - start;
            if (tt < 0f) return 0f;
            return Mathf.Sin(2f * Mathf.PI * freq * tt) * Mathf.Exp(-tt * 18f) * Mathf.Clamp01(tt / 0.006f);
        }

        // low pulsing tension drone while being chased (loops)
        static AudioClip MakeDrone()
        {
            var r = new System.Random(29);
            float length = 4f;
            int n = (int)(Rate * length);
            var d = new float[n];
            float p1 = 0f, p2 = 0f, lp = 0f;
            for (int i = 0; i < n; i++)
            {
                float t = i / (float)Rate;
                p1 += 55f / Rate; p2 += 58.5f / Rate;
                lp += (Noise(r) - lp) * 0.01f;
                float pulse = 0.65f + 0.35f * Mathf.Sin(2f * Mathf.PI * 2f * t / length * 4f);
                d[i] = (Mathf.Sin(2f * Mathf.PI * p1) * 0.5f + Saw(p2) * 0.18f + lp * 1.5f) * pulse;
            }
            float[] o = Loop(d, Rate / 2);
            Normalize(o, 0.6f);
            return Make("drone", o);
        }

        static AudioClip MakeRinging()
        {
            int n = (int)(Rate * 2.5f);
            var d = new float[n];
            for (int i = 0; i < n; i++)
            {
                float t = i / (float)Rate;
                d[i] = (Mathf.Sin(2f * Mathf.PI * 3900f * t) * 0.6f + Mathf.Sin(2f * Mathf.PI * 4140f * t) * 0.4f)
                     * Mathf.Clamp01(t / 0.05f) * Mathf.Exp(-t * 1.2f);
            }
            Normalize(d, 0.35f);
            return Make("ringing", d);
        }

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

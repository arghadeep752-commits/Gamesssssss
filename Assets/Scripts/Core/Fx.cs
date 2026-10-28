using System.Collections.Generic;
using UnityEngine;

namespace ZombieStrike
{
    /// <summary>Particles (blood, sparks, dust, fire), bullet tracers and blood decals.</summary>
    public class Fx : MonoBehaviour
    {
        public static Fx I { get; private set; }

        ParticleSystem blood, bloodMist, sparks, dust, dirt;
        readonly List<LineRenderer> tracers = new List<LineRenderer>();
        readonly List<float> tracerTime = new List<float>();
        int nextTracer;
        readonly List<Transform> decals = new List<Transform>();
        int nextDecal;
        const float TracerLife = 0.06f;

        void Awake()
        {
            I = this;
            blood = MakeBurst("Blood", Art.AlphaBlend("particle"), 220,
                new Color(0.55f, 0.02f, 0.02f, 1f), new Color(0.32f, 0f, 0f, 1f),
                0.35f, 0.75f, 1.5f, 4.5f, 0.05f, 0.14f, 2.2f, 35f);
            bloodMist = MakeBurst("BloodMist", Art.AlphaBlend("particle"), 60,
                new Color(0.5f, 0.03f, 0.03f, 0.55f), new Color(0.3f, 0f, 0f, 0.45f),
                0.3f, 0.5f, 0.3f, 1.0f, 0.3f, 0.6f, 0.2f, 50f);
            sparks = MakeBurst("Sparks", Art.Additive("particle"), 160,
                new Color(1f, 0.85f, 0.45f, 1f), new Color(1f, 0.55f, 0.15f, 1f),
                0.12f, 0.3f, 3f, 8f, 0.03f, 0.06f, 1.2f, 30f);
            var sparksRenderer = sparks.GetComponent<ParticleSystemRenderer>();
            sparksRenderer.renderMode = ParticleSystemRenderMode.Stretch;
            sparksRenderer.velocityScale = 0.035f;
            sparksRenderer.lengthScale = 1.2f;
            dust = MakeBurst("Dust", Art.AlphaBlend("particle"), 80,
                new Color(0.55f, 0.53f, 0.5f, 0.6f), new Color(0.4f, 0.38f, 0.36f, 0.5f),
                0.4f, 0.9f, 0.4f, 1.4f, 0.15f, 0.35f, -0.05f, 25f);
            dirt = MakeBurst("Dirt", Art.AlphaBlend("particle"), 120,
                new Color(0.25f, 0.2f, 0.15f, 0.9f), new Color(0.15f, 0.12f, 0.1f, 0.8f),
                0.5f, 1.0f, 1.0f, 3.0f, 0.1f, 0.3f, 1.5f, 40f);

            for (int i = 0; i < 6; i++)
            {
                var go = new GameObject("Tracer");
                go.transform.SetParent(transform, false);
                var lr = go.AddComponent<LineRenderer>();
                lr.sharedMaterial = Art.Additive("tracer");
                lr.positionCount = 2;
                lr.useWorldSpace = true;
                lr.startWidth = 0.035f;
                lr.endWidth = 0.012f;
                lr.startColor = new Color(1f, 0.9f, 0.55f, 0.9f);
                lr.endColor = new Color(1f, 0.6f, 0.2f, 0.15f);
                lr.numCapVertices = 0;
                lr.textureMode = LineTextureMode.Stretch;
                Art.Plain(lr);
                lr.enabled = false;
                tracers.Add(lr);
                tracerTime.Add(0f);
            }
        }

        static ParticleSystem MakeBurst(string name, Material mat, int max, Color c1, Color c2,
            float life1, float life2, float speed1, float speed2, float size1, float size2, float gravity, float coneAngle)
        {
            var go = new GameObject(name);
            go.transform.SetParent(I != null ? I.transform : null, false);
            var ps = go.AddComponent<ParticleSystem>();
            ps.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            ParticleSystem.MainModule main = ps.main;
            main.loop = true;
            main.playOnAwake = false;
            main.maxParticles = max;
            main.simulationSpace = ParticleSystemSimulationSpace.World;
            main.startLifetime = new ParticleSystem.MinMaxCurve(life1, life2);
            main.startSpeed = new ParticleSystem.MinMaxCurve(speed1, speed2);
            main.startSize = new ParticleSystem.MinMaxCurve(size1, size2);
            main.startColor = new ParticleSystem.MinMaxGradient(c1, c2);
            main.gravityModifier = gravity;
            main.startRotation = new ParticleSystem.MinMaxCurve(0f, Mathf.PI * 2f);

            ParticleSystem.EmissionModule em = ps.emission;
            em.rateOverTime = 0f;

            ParticleSystem.ShapeModule shape = ps.shape;
            shape.enabled = true;
            shape.shapeType = ParticleSystemShapeType.Cone;
            shape.angle = coneAngle;
            shape.radius = 0.03f;

            ParticleSystem.ColorOverLifetimeModule col = ps.colorOverLifetime;
            col.enabled = true;
            var g = new Gradient();
            g.SetKeys(
                new[] { new GradientColorKey(Color.white, 0f), new GradientColorKey(Color.white, 1f) },
                new[] { new GradientAlphaKey(1f, 0f), new GradientAlphaKey(0.8f, 0.6f), new GradientAlphaKey(0f, 1f) });
            col.color = new ParticleSystem.MinMaxGradient(g);

            var r = go.GetComponent<ParticleSystemRenderer>();
            r.sharedMaterial = mat;
            r.renderMode = ParticleSystemRenderMode.Billboard;
            Art.Plain(r);
            ps.Play();
            return ps;
        }

        static void Burst(ParticleSystem ps, Vector3 pos, Vector3 dir, int count)
        {
            if (ps == null || count <= 0) return;
            ps.transform.position = pos;
            ps.transform.rotation = Quaternion.LookRotation(dir.sqrMagnitude > 0.0001f ? dir : Vector3.up);
            ps.Emit(count);
        }

        public void Blood(Vector3 pos, Vector3 dir, int count)
        {
            Burst(blood, pos, dir, count);
            Burst(bloodMist, pos, dir, Mathf.Max(1, count / 4));
        }

        public void Impact(Vector3 pos, Vector3 normal)
        {
            Burst(sparks, pos + normal * 0.02f, normal, 7);
            Burst(dust, pos + normal * 0.05f, normal, 3);
        }

        public void Dirt(Vector3 pos, int count)
        {
            Burst(dirt, pos + Vector3.up * 0.1f, Vector3.up, count);
        }

        public void Tracer(Vector3 from, Vector3 to)
        {
            LineRenderer lr = tracers[nextTracer];
            tracerTime[nextTracer] = TracerLife;
            nextTracer = (nextTracer + 1) % tracers.Count;
            lr.SetPosition(0, from);
            lr.SetPosition(1, to);
            lr.enabled = true;
        }

        public void BloodDecal(Vector3 pos)
        {
            Transform d;
            if (decals.Count < 24)
            {
                var go = Art.MeshObject(transform, Art.Quad(Color.white), Art.Transparent("blood"),
                    Vector3.zero, Vector3.zero, Vector3.one, 0);
                go.name = "BloodDecal";
                d = go.transform;
                decals.Add(d);
            }
            else
            {
                d = decals[nextDecal];
                nextDecal = (nextDecal + 1) % decals.Count;
            }
            d.position = new Vector3(pos.x, 0.015f + decals.Count * 0.0004f, pos.z);
            d.rotation = Quaternion.Euler(90f, Random.Range(0f, 360f), 0f);
            float s = Random.Range(1.0f, 1.8f);
            d.localScale = new Vector3(s, s, 1f);
        }

        /// <summary>Looping fire for burning barrels.</summary>
        public static ParticleSystem MakeFire(Transform parent, Vector3 localPos, float size)
        {
            var go = new GameObject("Fire");
            go.transform.SetParent(parent, false);
            go.transform.localPosition = localPos;
            go.transform.localRotation = Quaternion.Euler(-90f, 0f, 0f);
            var ps = go.AddComponent<ParticleSystem>();
            ps.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            ParticleSystem.MainModule main = ps.main;
            main.loop = true;
            main.maxParticles = 80;
            main.simulationSpace = ParticleSystemSimulationSpace.World;
            main.startLifetime = new ParticleSystem.MinMaxCurve(0.45f, 0.9f);
            main.startSpeed = new ParticleSystem.MinMaxCurve(0.6f * size, 1.5f * size);
            main.startSize = new ParticleSystem.MinMaxCurve(0.3f * size, 0.6f * size);
            main.startColor = new ParticleSystem.MinMaxGradient(new Color(1f, 0.62f, 0.18f, 1f), new Color(1f, 0.32f, 0.06f, 1f));
            main.startRotation = new ParticleSystem.MinMaxCurve(0f, Mathf.PI * 2f);
            main.gravityModifier = -0.15f;

            ParticleSystem.EmissionModule em = ps.emission;
            em.rateOverTime = 26f;

            ParticleSystem.ShapeModule shape = ps.shape;
            shape.enabled = true;
            shape.shapeType = ParticleSystemShapeType.Cone;
            shape.angle = 10f;
            shape.radius = 0.25f * size;

            ParticleSystem.ColorOverLifetimeModule col = ps.colorOverLifetime;
            col.enabled = true;
            var g = new Gradient();
            g.SetKeys(
                new[] { new GradientColorKey(Color.white, 0f), new GradientColorKey(new Color(1f, 0.45f, 0.2f), 0.5f), new GradientColorKey(new Color(0.6f, 0.1f, 0.05f), 1f) },
                new[] { new GradientAlphaKey(0f, 0f), new GradientAlphaKey(0.9f, 0.15f), new GradientAlphaKey(0.5f, 0.6f), new GradientAlphaKey(0f, 1f) });
            col.color = new ParticleSystem.MinMaxGradient(g);

            ParticleSystem.SizeOverLifetimeModule sol = ps.sizeOverLifetime;
            sol.enabled = true;
            sol.size = new ParticleSystem.MinMaxCurve(1f, new AnimationCurve(new Keyframe(0f, 0.6f), new Keyframe(0.3f, 1f), new Keyframe(1f, 0.2f)));

            var r = go.GetComponent<ParticleSystemRenderer>();
            r.sharedMaterial = Art.Additive("particle");
            r.renderMode = ParticleSystemRenderMode.Billboard;
            Art.Plain(r);
            ps.Play();
            return ps;
        }

        void Update()
        {
            float dt = Time.deltaTime;
            for (int i = 0; i < tracers.Count; i++)
            {
                if (tracerTime[i] <= 0f) continue;
                tracerTime[i] -= dt;
                if (tracerTime[i] <= 0f) tracers[i].enabled = false;
            }
        }
    }
}

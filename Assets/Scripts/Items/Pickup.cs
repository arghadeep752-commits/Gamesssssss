using System.Collections.Generic;
using UnityEngine;

namespace ZombieStrike
{
    /// <summary>Ammo boxes and med-kits dropped by zombies. Walk over them to collect.</summary>
    public class Pickup : MonoBehaviour
    {
        public static readonly List<Pickup> All = new List<Pickup>();

        const float Lifetime = 35f;
        const int AmmoAmount = 60;
        const float HealAmount = 35f;

        PickupKind kind;
        Transform visual, glow;
        float age, seed;

        public static void TryDrop(ZombieKind from, Vector3 position)
        {
            float r = Random.value;
            if (from == ZombieKind.Brute)
            {
                Spawn(PickupKind.Ammo, position + new Vector3(0.6f, 0f, 0.3f));
                if (Random.value < 0.6f) Spawn(PickupKind.Health, position + new Vector3(-0.6f, 0f, -0.3f));
                return;
            }
            if (r < 0.2f) Spawn(PickupKind.Ammo, position);
            else if (r < 0.29f) Spawn(PickupKind.Health, position);
        }

        public static Pickup Spawn(PickupKind kind, Vector3 position)
        {
            if (All.Count >= 12) Destroy(All[0].gameObject);
            var go = new GameObject(kind + " Pickup");
            go.transform.position = new Vector3(position.x, 0f, position.z);
            var p = go.AddComponent<Pickup>();
            p.Build(kind);
            return p;
        }

        void Build(PickupKind k)
        {
            kind = k;
            seed = Random.value * 10f;
            visual = new GameObject("Visual").transform;
            visual.SetParent(transform, false);
            visual.localPosition = new Vector3(0f, 0.45f, 0f);
            Color glowColor;
            if (kind == PickupKind.Ammo)
            {
                Material box = Art.Lit(new Color(0.3f, 0.36f, 0.2f), "grime");
                Material band = Art.Unlit(new Color(0.95f, 0.75f, 0.15f));
                Material brass = Art.Lit(new Color(0.85f, 0.65f, 0.25f));
                Art.Box(visual, Vector3.zero, new Vector3(0.55f, 0.32f, 0.34f), box, Vector3.zero, 0);
                Art.Box(visual, new Vector3(0f, 0f, 0f), new Vector3(0.56f, 0.07f, 0.35f), band, Vector3.zero, 0);
                for (int i = 0; i < 3; i++)
                    Art.Box(visual, new Vector3(-0.12f + i * 0.12f, 0.22f, 0f), new Vector3(0.05f, 0.14f, 0.05f), brass, Vector3.zero, 0);
                glowColor = new Color(1f, 0.75f, 0.2f, 1f);
            }
            else
            {
                Material box = Art.Lit(new Color(0.92f, 0.92f, 0.9f));
                Material cross = Art.Unlit(new Color(0.9f, 0.08f, 0.08f));
                Art.Box(visual, Vector3.zero, new Vector3(0.48f, 0.34f, 0.34f), box, Vector3.zero, 0);
                Art.Box(visual, new Vector3(0f, 0.172f, 0f), new Vector3(0.28f, 0.01f, 0.09f), cross, Vector3.zero, 0);
                Art.Box(visual, new Vector3(0f, 0.172f, 0f), new Vector3(0.09f, 0.01f, 0.28f), cross, Vector3.zero, 0);
                Art.Box(visual, new Vector3(0f, 0f, 0.172f), new Vector3(0.22f, 0.07f, 0.01f), cross, Vector3.zero, 0);
                Art.Box(visual, new Vector3(0f, 0f, 0.172f), new Vector3(0.07f, 0.22f, 0.01f), cross, Vector3.zero, 0);
                glowColor = new Color(0.3f, 1f, 0.4f, 1f);
            }
            var g = Art.MeshObject(transform, Art.Quad(glowColor), Art.Additive("particle"),
                new Vector3(0f, 0.5f, 0f), Vector3.zero, Vector3.one * 1.4f, 0);
            glow = g.transform;
            All.Add(this);
        }

        void OnDestroy()
        {
            All.Remove(this);
        }

        void Update()
        {
            float dt = Time.deltaTime;
            age += dt;
            float t = age + seed;
            visual.localRotation = Quaternion.Euler(0f, t * 90f, 0f);
            visual.localPosition = new Vector3(0f, 0.45f + Mathf.Sin(t * 3f) * 0.07f, 0f);

            Camera cam = Camera.main;
            if (cam != null) glow.rotation = Quaternion.LookRotation(glow.position - cam.transform.position);
            float pulse = 1.2f + Mathf.Sin(t * 5f) * 0.25f;
            glow.localScale = new Vector3(pulse, pulse, pulse);

            if (age > Lifetime - 5f)
            {
                bool show = Mathf.Repeat(age * 6f, 1f) > 0.35f;
                visual.gameObject.SetActive(show);
                glow.gameObject.SetActive(show);
            }
            if (age > Lifetime)
            {
                Destroy(gameObject);
                return;
            }

            PlayerController p = PlayerController.I;
            if (p == null || !p.Alive || GameManager.I == null || GameManager.I.State != GameState.Playing) return;
            Vector3 d = p.transform.position - transform.position;
            d.y = 0f;
            if (d.sqrMagnitude > 1.5f * 1.5f) return;

            bool used;
            string text;
            if (kind == PickupKind.Ammo)
            {
                used = p.Gun != null && p.Gun.AddReserve(AmmoAmount);
                text = "+" + AmmoAmount + " AMMO";
            }
            else
            {
                used = p.Heal(HealAmount);
                text = "+" + (int)HealAmount + " HEALTH";
            }
            if (!used) return;
            if (Sfx.I != null) Sfx.I.Play2D("pickup", 0.8f);
            if (HUD.I != null) HUD.I.Popup(text, kind == PickupKind.Ammo ? new Color(1f, 0.82f, 0.3f) : new Color(0.4f, 1f, 0.5f));
            Destroy(gameObject);
        }
    }
}

using UnityEngine;

namespace NightClass
{
    /// <summary>
    /// One item in hand at a time (Granny style). Dropped items are thrown a little and make noise.
    /// The burning torch lights the way and its flame drives the teacher off for 30 seconds.
    /// </summary>
    public class Inventory : MonoBehaviour
    {
        public static Inventory I { get; private set; }
        public ItemType Held { get; private set; }
        public Transform viewRoot;
        public GameObject[] views = new GameObject[8];
        public PickupItem[] templates = new PickupItem[8];
        public Light torchLight;
        public ParticleSystem flameBurst;
        public Light flameFlash;
        float cooldown, flashT, swayT;
        Vector3 viewBase;

        void Awake()
        {
            I = this;
            if (viewRoot != null) viewBase = viewRoot.localPosition;
            ShowView();
        }

        public bool CanFire { get { return Held == ItemType.Torch && cooldown <= 0f; } }
        public float FireCooldown01 { get { return Mathf.Clamp01(cooldown / 5f); } }

        public bool Take(PickupItem p)
        {
            if (Held != ItemType.None)
            {
                NCGame.I.Message("Your hands are full. Drop the " + Items.Name(Held) + " first.", 2.5f);
                return false;
            }
            Held = p.type;
            Sfx.Play2D(GameAssets.I.pickup, 0.6f);
            switch (p.type)
            {
                case ItemType.Torch: Progress.TorchTaken = true; break;
                case ItemType.CodeNote: Progress.NoteTaken = true; NCGame.I.Message("The note says: GARAGE  4  7  1  9", 4f); break;
                case ItemType.SafeKey: Progress.SafeKeyTaken = true; break;
                case ItemType.MainKey: Progress.MainKeyTaken = true; break;
                case ItemType.Hammer: Progress.HammerTaken = true; break;
            }
            ShowView();
            return true;
        }

        public void Consume()
        {
            Held = ItemType.None;
            ShowView();
        }

        public void Drop()
        {
            if (Held == ItemType.None || FPController.I == null || FPController.I.Hidden) return;
            Transform c = FPController.I.Cam != null ? FPController.I.Cam.transform : transform;
            Vector3 pos = c.position + c.forward * 0.55f - Vector3.up * 0.15f;
            // never spawn inside a wall
            RaycastHit hit;
            if (Physics.Raycast(c.position, c.forward, out hit, 0.75f, 1 << 0, QueryTriggerInteraction.Ignore))
                pos = hit.point - c.forward * 0.25f;
            PickupItem item = Spawn(Held, pos);
            if (item != null)
            {
                Rigidbody rb = item.GetComponent<Rigidbody>();
                if (rb != null)
                {
                    rb.linearVelocity = c.forward * 2.4f + Vector3.up * 0.8f;
                    rb.angularVelocity = Random.insideUnitSphere * 4f;
                }
            }
            Sfx.Play2D(GameAssets.I.drop, 0.35f, 1.1f);
            Held = ItemType.None;
            ShowView();
        }

        public void DropOnCatch(Vector3 where)
        {
            if (Held == ItemType.None) return;
            Spawn(Held, where + Vector3.up * 0.4f);
            Held = ItemType.None;
            ShowView();
        }

        PickupItem Spawn(ItemType t, Vector3 pos)
        {
            PickupItem tpl = templates[(int)t];
            if (tpl == null) return null;
            GameObject go = Instantiate(tpl.gameObject, pos, Random.rotation);
            go.SetActive(true);
            PickupItem p = go.GetComponent<PickupItem>();
            p.isTemplate = false;
            p.locked = false;
            Rigidbody rb = go.GetComponent<Rigidbody>();
            if (rb != null) { rb.isKinematic = false; rb.WakeUp(); }
            return p;
        }

        public void Fire()
        {
            if (!CanFire || FPController.I == null) return;
            cooldown = 5f;
            flashT = 0.6f;
            if (flameBurst != null) flameBurst.Play(true);
            Sfx.Play2D(GameAssets.I.fireWhoosh, 0.85f);
            TeacherAI t = TeacherAI.I;
            if (t != null && FPController.I.Cam != null)
            {
                Transform c = FPController.I.Cam.transform;
                Vector3 to = t.transform.position + Vector3.up * 1.2f - c.position;
                if (to.magnitude < 3.6f && Vector3.Angle(c.forward, to) < 45f) t.Burn();
            }
        }

        void ShowView()
        {
            for (int i = 0; i < views.Length; i++)
                if (views[i] != null) views[i].SetActive(i == (int)Held);
            if (torchLight != null) torchLight.enabled = Held == ItemType.Torch;
        }

        void Update()
        {
            if (cooldown > 0f) cooldown -= Time.deltaTime;
            bool show = NCGame.I != null && NCGame.I.State == GameState.Playing && FPController.I != null && !FPController.I.Hidden;
            if (viewRoot != null && viewRoot.gameObject.activeSelf != show) viewRoot.gameObject.SetActive(show);
            if (torchLight != null && Held == ItemType.Torch)
            {
                float n = Mathf.PerlinNoise(Time.time * 7f, 0.3f);
                torchLight.intensity = 2.1f + n * 0.9f + (flashT > 0f ? 4f * flashT : 0f);
                torchLight.range = 7.5f + n * 0.8f;
            }
            if (flameFlash != null)
            {
                flameFlash.enabled = flashT > 0f;
                flameFlash.intensity = 10f * flashT;
            }
            if (flashT > 0f) flashT -= Time.deltaTime;
            if (viewRoot != null && FPController.I != null)
            {
                float sp = FPController.I.Speed;
                swayT += Time.deltaTime * (1f + sp * 1.6f);
                float a = Mathf.Clamp01(sp / 3f);
                viewRoot.localPosition = viewBase + new Vector3(Mathf.Cos(swayT) * 0.008f * a, Mathf.Sin(swayT * 2f) * 0.006f * a + Mathf.Sin(Time.time * 1.3f) * 0.002f, 0f);
            }
        }
    }
}

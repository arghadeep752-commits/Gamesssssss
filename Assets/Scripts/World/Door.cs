using UnityEngine;

namespace NightClass
{
    /// <summary>Hinged door. Swings away from whoever opens it; the teacher opens unlocked doors in her way.</summary>
    public class Door : Interactable
    {
        public Transform hinge;
        public float openAngle = 100f;
        public bool locked;
        public ItemType key = ItemType.None;
        public string lockedText = "It's locked.";
        public bool IsOpen { get; private set; }
        float angle, target, closedYaw;
        bool init;

        void Init()
        {
            if (init) return;
            init = true;
            if (hinge == null) hinge = transform;
            closedYaw = hinge.localEulerAngles.y;
        }

        void Awake() { Init(); }

        public override string Prompt()
        {
            if (locked) return "Try the door";
            return IsOpen ? "Close the door" : "Open the door";
        }

        public override void Interact()
        {
            if (locked)
            {
                if (key != ItemType.None && Holding(key))
                {
                    locked = false;
                    Sfx.Play3D(GameAssets.I.keypadOk, hinge.position, 0.6f);
                    Msg("Unlocked.", 2f);
                }
                else
                {
                    Sfx.Play3D(GameAssets.I.doorLocked, hinge.position, 0.8f);
                    Msg(lockedText, 3f);
                    return;
                }
            }
            if (IsOpen) Close();
            else Open(FPController.I != null ? FPController.I.transform.position : hinge.position + hinge.forward);
        }

        public void Open(Vector3 from)
        {
            Init();
            float side = Vector3.Dot(from - hinge.position, hinge.forward) >= 0f ? 1f : -1f;
            target = side * openAngle;
            if (!IsOpen) Sfx.Play3D(GameAssets.I.doorOpen, hinge.position, 0.7f, Random.Range(0.92f, 1.08f));
            IsOpen = true;
        }

        public void Close()
        {
            Init();
            target = 0f;
            if (IsOpen) Sfx.Play3D(GameAssets.I.doorClose, hinge.position, 0.7f, Random.Range(0.92f, 1.08f));
            IsOpen = false;
        }

        public void Slam()
        {
            Init();
            target = 0f;
            IsOpen = false;
            Sfx.Play3D(GameAssets.I.slam, hinge.position, 1f);
        }

        public void TeacherOpen(Vector3 from)
        {
            if (!locked && !IsOpen) Open(from);
        }

        void Update()
        {
            if (Mathf.Approximately(angle, target)) return;
            float speed = target == 0f ? 260f : 200f;
            angle = Mathf.MoveTowards(angle, target, speed * Time.deltaTime);
            hinge.localRotation = Quaternion.Euler(0f, closedYaw + angle, 0f);
        }
    }
}

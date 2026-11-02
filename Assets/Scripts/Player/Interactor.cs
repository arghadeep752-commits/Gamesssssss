using UnityEngine;

namespace NightClass
{
    /// <summary>Looks at the centre of the screen for something to use and drives the hand button.</summary>
    public class Interactor : MonoBehaviour
    {
        public static Interactor I { get; private set; }
        public float range = 2.4f;
        public Hud hud;
        Interactable current;
        const int Mask = (1 << 0) | (1 << 9) | (1 << 10);

        void Awake() { I = this; }

        public Interactable Current { get { return current; } }

        void Update()
        {
            current = null;
            NCGame g = NCGame.I;
            FPController p = FPController.I;
            if (g == null || p == null || g.State != GameState.Playing || p.Hidden || p.Cam == null)
            {
                if (hud != null) hud.SetInteract(false, "");
                return;
            }
            Transform c = p.Cam.transform;
            RaycastHit hit;
            if (Physics.SphereCast(c.position, 0.1f, c.forward, out hit, range, Mask, QueryTriggerInteraction.Collide))
            {
                Interactable it = hit.collider.GetComponentInParent<Interactable>();
                if (it != null && it.enabled && it.Available) current = it;
            }
            if (hud != null) hud.SetInteract(current != null, current != null ? current.Prompt() : "");
        }

        public void Use()
        {
            if (current != null && current.Available) current.Interact();
        }
    }
}

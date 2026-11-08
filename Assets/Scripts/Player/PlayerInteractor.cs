using UnityEngine;

namespace GridProto
{
    /// <summary>Finds the nearest usable object in front of the player and uses it when interact is pressed.</summary>
    public class PlayerInteractor : MonoBehaviour
    {
        public PlayerController player;
        public Transform view;

        public Interactable Current { get; private set; }

        void Update()
        {
            if (Time.timeScale <= 0f) return;
            Current = FindBest();
            if (TouchState.InteractPressed)
            {
                TouchState.InteractPressed = false;
                if (Current != null) Current.Interact(player);
            }
        }

        Interactable FindBest()
        {
            if (player == null || view == null) return null;
            Vector3 eye = view.position;
            Vector3 forward = view.forward;
            forward.y = 0f;
            if (forward.sqrMagnitude < 0.0001f) forward = player.transform.forward;
            forward.Normalize();

            Interactable best = null;
            float bestScore = float.MaxValue;
            var all = Interactable.All;
            for (int i = 0; i < all.Count; i++)
            {
                Interactable it = all[i];
                if (it == null || !it.isActiveAndEnabled) continue;
                Vector3 to = it.FocusPosition - eye;
                if (Mathf.Abs(to.y) > 2f) continue;
                Vector3 flat = new Vector3(to.x, 0f, to.z);
                float distance = flat.magnitude;
                if (distance > it.range) continue;
                float facing = distance > 0.05f ? Vector3.Dot(forward, flat / distance) : 1f;
                if (facing < -0.15f) continue;   // behind the player
                if (!it.CanInteract(player)) continue;
                float score = distance - facing;
                if (score < bestScore)
                {
                    bestScore = score;
                    best = it;
                }
            }
            return best;
        }
    }
}

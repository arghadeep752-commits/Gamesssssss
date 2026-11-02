using UnityEngine;

namespace NightClass
{
    /// <summary>A hidden chalk drawing in the gym storage room.</summary>
    public class EasterEgg : Interactable
    {
        public Renderer drawing;
        float glow;

        public override string Prompt() { return "Touch the drawing"; }

        public override void Interact()
        {
            glow = 1f;
            Sfx.Play2D(GameAssets.I.musicBox, 0.7f);
            Msg("Scratched under the drawing: \"WE ALL GOT OUT. YOU CAN TOO.\"", 4.5f);
        }

        void Update()
        {
            if (glow <= 0f || drawing == null) return;
            glow -= Time.deltaTime * 0.25f;
            drawing.material.SetColor("_EmissionColor", new Color(0.6f, 0.9f, 1f) * Mathf.Max(0f, glow) * 1.5f);
        }
    }
}

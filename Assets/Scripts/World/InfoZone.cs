using UnityEngine;

namespace NightClass
{
    /// <summary>Shows a tip the first time the player walks in.</summary>
    public class InfoZone : MonoBehaviour
    {
        [TextArea] public string text;
        public float seconds = 4f;
        bool done;

        void OnTriggerEnter(Collider c)
        {
            if (done || c.GetComponent<FPController>() == null || NCGame.I == null || NCGame.I.State != GameState.Playing) return;
            done = true;
            NCGame.I.Message(text, seconds);
        }
    }
}

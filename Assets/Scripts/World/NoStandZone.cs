using UnityEngine;

namespace NightClass
{
    /// <summary>Crawl spaces (the vent, under the stage): the player stays crouched inside.</summary>
    public class NoStandZone : MonoBehaviour
    {
        void OnTriggerEnter(Collider c)
        {
            FPController p = c.GetComponent<FPController>();
            if (p != null) p.EnterNoStand();
        }

        void OnTriggerExit(Collider c)
        {
            FPController p = c.GetComponent<FPController>();
            if (p != null) p.ExitNoStand();
        }
    }
}

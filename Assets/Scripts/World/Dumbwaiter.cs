using System.Collections;
using UnityEngine;

namespace NightClass
{
    /// <summary>The broken food elevator in the cafeteria. With the spring it brings the main key down.</summary>
    public class Dumbwaiter : Interactable
    {
        public Transform car;
        public Vector3 downOffset = new Vector3(0f, -1.6f, 0f);
        public PickupItem contents;
        bool fixedUp;

        public override bool Available { get { return !fixedUp; } }
        public override string Prompt() { return Holding(ItemType.Spring) ? "Repair the food elevator" : "Food elevator"; }

        public override void Interact()
        {
            if (!Holding(ItemType.Spring))
            {
                Msg("The food elevator is jammed. A spring is missing from its mechanism.", 3.5f);
                return;
            }
            fixedUp = true;
            Inv.Consume();
            Progress.ElevatorFixed = true;
            StartCoroutine(Run());
        }

        IEnumerator Run()
        {
            Sfx.Play3D(GameAssets.I.motor, transform.position, 0.9f, 1.1f, 30f);
            TeacherAI.HearNoise(transform.position, 14f);
            Vector3 p0 = car.localPosition;
            float t = 0f;
            while (t < 1f)
            {
                t += Time.deltaTime / 3.2f;
                car.localPosition = p0 + downOffset * Mathf.SmoothStep(0f, 1f, t);
                yield return null;
            }
            Sfx.Play3D(GameAssets.I.trapdoor, transform.position, 0.5f, 1.4f);
            Collider own = GetComponent<Collider>();
            if (own != null) own.enabled = false;   // let the hand reach the key in the car
            if (contents != null) contents.Unlock();
            Msg("Something came down with the elevator...", 2.5f);
        }
    }
}

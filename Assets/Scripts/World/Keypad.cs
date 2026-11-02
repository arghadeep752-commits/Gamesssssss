using System.Collections;
using UnityEngine;
using UnityEngine.AI;

namespace NightClass
{
    /// <summary>Garage keypad: with the principal's note the roller door rolls up.</summary>
    public class Keypad : Interactable
    {
        public Transform rollerDoor;
        public float rollHeight = 2.6f;
        public NavMeshObstacle obstacle;
        public Renderer led;
        bool open, busy;

        public override bool Available { get { return !open && !busy; } }
        public override string Prompt() { return Holding(ItemType.CodeNote) ? "Enter the code" : "Garage keypad"; }

        public override void Interact()
        {
            if (!Holding(ItemType.CodeNote))
            {
                Sfx.Play3D(GameAssets.I.keypadNo, transform.position, 0.7f);
                Msg("The garage keypad wants a 4-digit code.", 3f);
                return;
            }
            StartCoroutine(Enter());
        }

        IEnumerator Enter()
        {
            busy = true;
            for (int i = 0; i < 4; i++)
            {
                Sfx.Play3D(GameAssets.I.keypadBeep, transform.position, 0.6f, 1f + i * 0.08f);
                yield return new WaitForSeconds(0.28f);
            }
            Sfx.Play3D(GameAssets.I.keypadOk, transform.position, 0.7f);
            if (led != null) led.material.SetColor("_EmissionColor", new Color(0.1f, 2.2f, 0.3f));
            Inv.Consume();
            open = true;
            Progress.GarageOpen = true;
            Sfx.Play3D(GameAssets.I.motor, rollerDoor.position, 0.9f, 0.8f, 30f);
            TeacherAI.HearNoise(rollerDoor.position, 18f);
            Vector3 p0 = rollerDoor.localPosition;
            float t = 0f;
            while (t < 1f)
            {
                t += Time.deltaTime / 3f;
                rollerDoor.localPosition = p0 + Vector3.up * rollHeight * Mathf.SmoothStep(0f, 1f, t);
                yield return null;
            }
            if (obstacle != null) obstacle.enabled = false;
            Collider c = rollerDoor.GetComponent<Collider>();
            if (c != null) c.enabled = false;
            busy = false;
            Msg("The garage is open.", 2.5f);
        }
    }
}

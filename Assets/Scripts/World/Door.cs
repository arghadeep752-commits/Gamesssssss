using UnityEngine;

namespace GridProto
{
    /// <summary>A hinged door that swings open away from the player and closes again.</summary>
    public class Door : Interactable
    {
        public Transform hinge;
        public float openAngle = 92f;
        [Tooltip("+1 if a positive hinge angle swings the door towards the outside")]
        public float outsideSwingSign = 1f;
        [Tooltip("World direction from the door towards the outside")]
        public Vector3 outsideDirection = Vector3.back;
        public float smoothTime = 0.32f;
        public AudioSource audioSource;

        float angle, targetAngle, angleVelocity;
        bool open, shutPending;

        public bool IsOpen { get { return open; } }

        public override string Prompt { get { return open ? "CLOSE" : "OPEN"; } }

        public override bool CanInteract(PlayerController player)
        {
            if (!open) return true;
            // never swing the door shut through a player standing in the doorway
            Vector3 d = player.transform.position - FocusPosition;
            d.y = 0f;
            return d.magnitude > 0.75f;
        }

        public override void Interact(PlayerController player)
        {
            Toggle(player.transform.position);
            NoiseSystem.Emit(FocusPosition, 14f);   // the enemy hears the door
        }

        /// <summary>Used by the enemy: pushes the door open, away from whoever is opening it.</summary>
        public void OpenAwayFrom(Vector3 position)
        {
            if (!open) Toggle(position);
        }

        void Toggle(Vector3 actorPosition)
        {
            if (!open)
            {
                Vector3 toActor = actorPosition - FocusPosition;
                bool actorOutside = Vector3.Dot(toActor, outsideDirection) > 0f;
                targetAngle = (actorOutside ? -outsideSwingSign : outsideSwingSign) * openAngle;   // away from them
                open = true;
                shutPending = false;
                Play(ProtoAudio.DoorOpen, 0.9f);
            }
            else
            {
                targetAngle = 0f;
                open = false;
                shutPending = true;
            }
        }

        void Update()
        {
            angle = Mathf.SmoothDamp(angle, targetAngle, ref angleVelocity, smoothTime);
            if (shutPending && Mathf.Abs(angle) < 2.5f)
            {
                shutPending = false;
                angle = 0f;
                angleVelocity = 0f;
                Play(ProtoAudio.DoorShut, 1f);
            }
            if (hinge != null) hinge.localRotation = Quaternion.Euler(0f, angle, 0f);
        }

        void Play(AudioClip clip, float volume)
        {
            if (audioSource == null || clip == null) return;
            audioSource.pitch = Random.Range(0.96f, 1.04f);
            audioSource.PlayOneShot(clip, volume);
        }
    }
}

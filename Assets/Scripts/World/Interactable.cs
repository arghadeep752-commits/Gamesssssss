using System.Collections.Generic;
using UnityEngine;

namespace GridProto
{
    /// <summary>Something the player can use with the interact button when standing close to it.</summary>
    public abstract class Interactable : MonoBehaviour
    {
        public static readonly List<Interactable> All = new List<Interactable>();

        [Tooltip("The point the player has to be close to (defaults to this transform)")]
        public Transform focusPoint;
        public float range = 2.4f;

        public Vector3 FocusPosition { get { return focusPoint != null ? focusPoint.position : transform.position; } }

        protected virtual void OnEnable()
        {
            if (!All.Contains(this)) All.Add(this);
        }

        protected virtual void OnDisable()
        {
            All.Remove(this);
        }

        /// <summary>Text on the interact button, e.g. "OPEN".</summary>
        public abstract string Prompt { get; }

        public virtual bool CanInteract(PlayerController player)
        {
            return true;
        }

        public abstract void Interact(PlayerController player);
    }
}

using UnityEngine;

namespace Moulika
{
    /// <summary>Data the editor puts on the Moulika prefab: how fast her walk and run clips travel, her animation
    /// component and her body (its own file: Unity only saves components whose class name matches the file name).</summary>
    public class MoulikaRig : MonoBehaviour
    {
        public float walkNat = 1.25f;    // metres per second the walk clip covers at speed 1
        public float runNat = 3.3f;
        public Animation anim;
        public Renderer body;
    }
}

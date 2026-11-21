using UnityEngine;

namespace TradersMadness
{
    /// <summary>Data the editor puts on the Trader prefab: how fast his walk and run clips travel, his animation
    /// component and his body (its own file: Unity only saves components whose class name matches the file name).</summary>
    public class TraderRig : MonoBehaviour
    {
        public float walkNat = 1.3f;     // metres per second the walk clip covers at speed 1
        public float runNat = 3.2f;
        public Animation anim;
        public Renderer body;
    }
}

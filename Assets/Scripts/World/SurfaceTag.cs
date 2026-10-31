using UnityEngine;

namespace RealFPS
{
    /// <summary>Marks a collider's footstep surface (pier = wood, rocks = rock).</summary>
    public class SurfaceTag : MonoBehaviour
    {
        public Surface surface = Surface.Rock;
    }
}

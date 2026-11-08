using UnityEngine;

namespace GridProto
{
    /// <summary>Sounds the enemy can hear: running footsteps, landing after a jump, the door.</summary>
    public static class NoiseSystem
    {
        /// <summary>position, radius in metres</summary>
        public static event System.Action<Vector3, float> OnNoise;

        public static void Emit(Vector3 position, float radius)
        {
            if (OnNoise != null) OnNoise(position, radius);
        }
    }
}

using UnityEngine;

namespace ZombieStrike
{
    /// <summary>Marks a zombie collider so bullets know who they hit (and whether it was the head).</summary>
    public class ZombieHitbox : MonoBehaviour
    {
        public Zombie Owner;
        public bool IsHead;
    }
}

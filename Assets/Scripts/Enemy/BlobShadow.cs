using UnityEngine;

namespace GridProto
{
    /// <summary>Soft contact shadow under the enemy that follows the floor (the house lighting is baked, so
    /// moving things get this instead of a real-time shadow).</summary>
    public class BlobShadow : MonoBehaviour
    {
        public Transform target;
        public Transform blob;
        public float size = 1.15f;
        int mask;

        void Start()
        {
            mask = ~((1 << 1) | (1 << 2) | (1 << 9) | (1 << 10));
        }

        void LateUpdate()
        {
            if (target == null || blob == null) return;
            RaycastHit hit;
            Vector3 origin = target.position + Vector3.up * 0.6f;
            if (Physics.Raycast(origin, Vector3.down, out hit, 2.5f, mask, QueryTriggerInteraction.Ignore))
            {
                blob.gameObject.SetActive(true);
                blob.position = hit.point + hit.normal * 0.012f;
                blob.rotation = Quaternion.FromToRotation(Vector3.up, hit.normal) * Quaternion.Euler(0f, target.eulerAngles.y, 0f);
                float h = Mathf.Clamp01(1f - (target.position.y - hit.point.y) / 1.5f);
                blob.localScale = new Vector3(size, 1f, size * 1.15f) * (0.7f + 0.3f * h);
            }
            else blob.gameObject.SetActive(false);
        }
    }
}

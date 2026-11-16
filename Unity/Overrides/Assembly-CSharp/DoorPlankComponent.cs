using System.Collections;
using UnityEngine;

/// <summary>A plank nailed across a door from the other side. Tapped from that side, it falls off.</summary>
public class DoorPlankComponent : MonoBehaviour
{
    private bool isRemoved;

    public void RemovePlank()
    {
        if (isRemoved) return;
        isRemoved = true;
        StartCoroutine(DropPlankAnimation());
    }

    private IEnumerator DropPlankAnimation()
    {
        var audio = GetComponent<AudioSource>();
        if (audio != null && audio.clip != null) audio.Play();
        foreach (Collider c in GetComponentsInChildren<Collider>()) c.enabled = false;
        float elapsed = 0f;
        Vector3 startPos = transform.position;
        Quaternion startRot = transform.rotation;
        Vector3 floor = startPos + Vector3.down * 1.0f;
        if (Physics.Raycast(startPos, Vector3.down, out RaycastHit hit, 3f, Physics.DefaultRaycastLayers, QueryTriggerInteraction.Ignore))
            floor = hit.point + Vector3.up * 0.04f;
        Quaternion endRot = Quaternion.Euler(0f, startRot.eulerAngles.y + 25f, 88f);
        while (elapsed < 0.6f)
        {
            elapsed += Time.deltaTime;
            float t = elapsed / 0.6f;
            transform.position = Vector3.Lerp(startPos, floor, t * t);
            transform.rotation = Quaternion.Slerp(startRot, endRot, t);
            yield return null;
        }
        transform.position = floor;
        transform.rotation = endRot;
        GrannyAI.AlertAll(transform.position, "plank fell");
    }

    public bool IsRemoved()
    {
        return isRemoved;
    }
}

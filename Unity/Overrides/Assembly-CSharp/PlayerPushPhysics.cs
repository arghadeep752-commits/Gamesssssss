using UnityEngine;

/// <summary>Walking into loose physics objects (chairs, boxes, the vase) pushes them.</summary>
public class PlayerPushPhysics : MonoBehaviour
{
    public float pushPower;

    private void OnControllerColliderHit(ControllerColliderHit hit)
    {
        Rigidbody body = hit.collider.attachedRigidbody;
        if (body == null || body.isKinematic) return;
        if (hit.moveDirection.y < -0.3f) return;
        Vector3 push = new Vector3(hit.moveDirection.x, 0f, hit.moveDirection.z);
        body.linearVelocity = push * (pushPower > 0f ? pushPower : 2f);
    }
}

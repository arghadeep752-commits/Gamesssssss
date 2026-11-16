using UnityEngine;

public class PlayerPushPhysics : MonoBehaviour
{
	[Tooltip("How hard the player pushes physics objects when running into them")]
	public float pushPower;

	private void OnControllerColliderHit(ControllerColliderHit hit)
	{
	}
}

using UnityEngine;

public class CutObjectPhysics : MonoBehaviour
{
	[Header("Sideways Fall Settings")]
	[Tooltip("How much push force is applied to the side")]
	public float sidewaysForce;

	[Tooltip("How much rotational spin is applied to make it tip over")]
	public float tipTorque;

	private Rigidbody rb;

	private void Awake()
	{
	}

	public void TriggerSidewaysFall(Vector3 cutterPosition)
	{
	}
}

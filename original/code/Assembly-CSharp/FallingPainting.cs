using UnityEngine;

[RequireComponent(typeof(Rigidbody))]
public class FallingPainting : MonoBehaviour
{
	[Header("Sound Settings")]
	public float noiseRadius;

	public LayerMask grannyLayer;

	private bool hasFallen;

	private void OnCollisionEnter(Collision collision)
	{
	}

	private void TriggerNoise()
	{
	}

	private void OnDrawGizmosSelected()
	{
	}
}

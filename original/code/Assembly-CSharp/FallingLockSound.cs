using UnityEngine;

public class FallingLockSound : MonoBehaviour
{
	public AudioSource audioSource;

	public AudioClip floorImpactSound;

	private bool hasLanded;

	private void OnCollisionEnter(Collision collision)
	{
	}
}

using UnityEngine;

public class CreakingFloor : MonoBehaviour
{
	[Header("Audio Settings")]
	public AudioSource audioSource;

	public AudioClip[] creakSounds;

	[Tooltip("How far (meters) Granny hears this creak on NORMAL mode")]
	[Header("Granny Hearing Range Per Difficulty")]
	public float normalHearingRadius;

	[Tooltip("HARD mode: Granny hears the creak from anywhere in the house")]
	public bool hardHearsFromAnywhere;

	[Tooltip("EXTREME mode: Granny hears the creak from anywhere in the house")]
	public bool extremeHearsFromAnywhere;

	[Header("Cooldown")]
	public float cooldownTime;

	private bool isCoolingDown;

	private void OnTriggerEnter(Collider other)
	{
	}

	private string GetDifficulty()
	{
		return null;
	}

	private void PlayCreakSoundAndAlert()
	{
	}

	private void AlertGranny(Vector3 noisePosition, string difficulty)
	{
	}

	private void ResetCooldown()
	{
	}

	private void OnDrawGizmosSelected()
	{
	}
}

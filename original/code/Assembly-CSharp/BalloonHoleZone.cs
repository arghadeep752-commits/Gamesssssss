using UnityEngine;

public class BalloonHoleZone : MonoBehaviour
{
	[Tooltip("Drag the HotAirBalloonEscape script from your main balloon parent here")]
	public HotAirBalloonEscape mainBalloonScript;

	[Header("Audio Settings")]
	[Tooltip("Drop your tape repair sound effect clip here")]
	public AudioClip repairSound;

	public void FixHoleWithTape()
	{
	}
}

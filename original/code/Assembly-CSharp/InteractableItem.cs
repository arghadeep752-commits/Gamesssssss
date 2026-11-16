using UnityEngine;

[RequireComponent(typeof(AudioSource))]
public class InteractableItem : MonoBehaviour
{
	[Header("Item Info")]
	public string itemName;

	[Header("Multi-Hold Point Setting")]
	public string targetHoldPointName;

	[Header("Audio Settings")]
	public AudioClip pickupSound;

	public AudioClip dropSound;

	[Tooltip("Volume of the drop sound when the item lands inside a Silent Ground Zone. 0 = no sound at all, 0.2 = soft thud on grass.")]
	[Header("Silent Ground (e.g. grass outside)")]
	[Range(0f, 1f)]
	public float silentGroundVolume;

	[Header("Impact Settings")]
	[Tooltip("The item has to hit something at least this fast to make a sound / alert Granny")]
	public float minImpactSpeed;

	[Tooltip("Bounces within this time only count as ONE noise (so a bouncing item doesn't spam Granny)")]
	public float noiseCooldown;

	[HideInInspector]
	public bool isHeld;

	private AudioSource myAudioSource;

	private float lastNoiseTime;

	private void Awake()
	{
	}

	public virtual void UseItem()
	{
	}

	private void OnCollisionEnter(Collision collision)
	{
	}
}

using UnityEngine;

public class DoorLockComponent : MonoBehaviour
{
	public LockType lockType;

	public string requiredItemName;

	private MainDoorEscape doorManager;

	[Header("Audio")]
	public AudioSource audioSource;

	public AudioClip interactionSound;

	[Header("Specific to Padlock Code")]
	public Rigidbody padlockCodeRigidbody;

	[Header("Specific to Chain")]
	public GameObject tightChains;

	public GameObject hangingChains;

	private void Start()
	{
	}

	public void Interact(string heldItem)
	{
	}

	private void BreakPlank()
	{
	}

	private void DropPadlockCode()
	{
	}

	private void UnlockPadlock()
	{
	}

	private void CutChains()
	{
	}

	private void PlaySoundAndAlertGranny()
	{
	}

	public void AlertGrannyAI()
	{
	}
}

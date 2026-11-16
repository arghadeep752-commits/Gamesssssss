using System.Collections;
using UnityEngine;

/// <summary>Extreme mode: put the missing handle on the lever, pull it, and the fence in front of the exit goes away.</summary>
public class LeverInteractable : MonoBehaviour
{
    [Header("Linked Extreme Lock")]
    public ExtremeFenceLock targetFence;

    [Header("Lever States")]
    public bool hasHandlePlaced;
    public bool isPulled;

    [Header("Visual References")]
    public GameObject missingHandleVisual;
    public Transform rotatingHandlePivot;

    [Header("Rotation Settings")]
    public Vector3 pulledRotationAngles;
    public float pullSpeed;

    [Header("Audio Settings")]
    public AudioSource audioSource;
    public AudioClip leverPullSound;

    [Header("Inventory Settings")]
    public string requiredItemName;

    private void Start()
    {
        if (missingHandleVisual != null) missingHandleVisual.SetActive(hasHandlePlaced);
        if (audioSource == null) audioSource = GetComponent<AudioSource>();
    }

    public void InteractWithLever(GameObject player)
    {
        if (isPulled) return;
        if (!hasHandlePlaced)
        {
            if (!CheckPlayerInventory(player))
            {
                DimnightUtil.Notify("I need to find the missing Lever Handle!");
                return;
            }
            RemoveItemFromInventory(player);
            hasHandlePlaced = true;
            if (missingHandleVisual != null) missingHandleVisual.SetActive(true);
            return;
        }
        isPulled = true;
        enabled = false;
        StartCoroutine(RotateLeverDownRoutine());
    }

    private IEnumerator RotateLeverDownRoutine()
    {
        if (leverPullSound != null)
        {
            if (audioSource != null) audioSource.PlayOneShot(leverPullSound);
            else DimnightUtil.PlayAt(leverPullSound, transform.position);
        }
        if (rotatingHandlePivot != null)
        {
            Quaternion targetRotation = rotatingHandlePivot.localRotation * Quaternion.Euler(pulledRotationAngles);
            float speed = pullSpeed > 0f ? pullSpeed : 2f;
            while (Quaternion.Angle(rotatingHandlePivot.localRotation, targetRotation) > 0.5f)
            {
                rotatingHandlePivot.localRotation = Quaternion.Slerp(rotatingHandlePivot.localRotation, targetRotation, Time.deltaTime * speed * 3f);
                yield return null;
            }
            rotatingHandlePivot.localRotation = targetRotation;
        }
        else yield return new WaitForSeconds(0.5f);
        if (targetFence != null) targetFence.UnlockAndRemoveFence();
    }

    private bool CheckPlayerInventory(GameObject player)
    {
        MobilePickUpScript pickup = player != null ? player.GetComponentInChildren<MobilePickUpScript>() : null;
        if (pickup == null) pickup = MobilePickUpScript.Instance;
        return pickup != null && GameSave.SameItem(pickup.GetHeldItemName(), string.IsNullOrEmpty(requiredItemName) ? "LeverHandle" : requiredItemName);
    }

    private void RemoveItemFromInventory(GameObject player)
    {
        MobilePickUpScript pickup = player != null ? player.GetComponentInChildren<MobilePickUpScript>() : null;
        if (pickup == null) pickup = MobilePickUpScript.Instance;
        if (pickup != null) pickup.ConsumeHeldItem();
    }
}

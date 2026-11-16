using UnityEngine;
using UnityEngine.UI;

/// <summary>A place to hide: under a bed, in the coffin, in the car (or a locker). Hands are empty while hiding.</summary>
public class HidingSpot : MonoBehaviour
{
    public enum HidingType
    {
        Bed = 0,
        Locker = 1,
        Coffin = 2,
        Car = 3
    }

    [Header("Configuration")]
    public HidingType spotType;
    public Transform hidePosition;

    [Header("Granny (Car only, optional)")]
    public Transform grannyApproachPoint;

    [Header("Camera")]
    public float bedNearClipPlane;

    [Header("UI Reference")]
    public GameObject dropButton;

    [Header("Animations (Optional)")]
    public Animator doorAnimator;
    public string openTriggerName;
    public string closeTriggerName;

    private Camera playerCamera;
    private float originalNearClip;
    private bool isInsideSpot;

    [HideInInspector]
    public float rotationY;

    public bool IsPlayerInside => isInsideSpot;

    private void Awake()
    {
        if (hidePosition == null) hidePosition = transform;
    }

    private Camera Cam()
    {
        if (playerCamera == null) playerCamera = Camera.main;
        return playerCamera;
    }

    public void PlayOpenAnimation()
    {
        if (doorAnimator != null && !string.IsNullOrEmpty(openTriggerName)) doorAnimator.SetTrigger(openTriggerName);
    }

    public void PlayCloseAnimation()
    {
        if (doorAnimator != null && !string.IsNullOrEmpty(closeTriggerName)) doorAnimator.SetTrigger(closeTriggerName);
    }

    public void OnEnterHidingSpot()
    {
        isInsideSpot = true;
        Camera c = Cam();
        if (c != null)
        {
            originalNearClip = c.nearClipPlane;
            if (bedNearClipPlane > 0f) c.nearClipPlane = bedNearClipPlane;
        }
        PlayCloseAnimation();
        SetHandItemsActive(false);
        SetDropButtonActive(false);
    }

    public void OnExitHidingSpot()
    {
        if (!isInsideSpot) return;
        isInsideSpot = false;
        Camera c = Cam();
        if (c != null && originalNearClip > 0f) c.nearClipPlane = originalNearClip;
        PlayOpenAnimation();
        SetHandItemsActive(true);
        SetDropButtonActive(CheckIfPlayerHasItem());
    }

    public void ForceHideDropButton()
    {
        SetDropButtonActive(false);
    }

    private bool CheckIfPlayerHasItem()
    {
        return MobilePickUpScript.Instance != null && MobilePickUpScript.Instance.GetHeldItem() != null;
    }

    private void SetHandItemsActive(bool isActive)
    {
        if (MobilePickUpScript.Instance == null) return;
        InteractableItem item = MobilePickUpScript.Instance.GetHeldItem();
        if (item != null) item.gameObject.SetActive(isActive);
    }

    private void SetDropButtonActive(bool isActive)
    {
        if (dropButton == null) FindDropButtonInScene();
        if (dropButton != null) dropButton.SetActive(isActive);
    }

    private void FindDropButtonInScene()
    {
        if (MobilePickUpScript.Instance != null && MobilePickUpScript.Instance.dropButton != null)
            dropButton = MobilePickUpScript.Instance.dropButton.gameObject;
    }

    public void OnHoverEnter()
    {
    }

    public void OnHoverExit()
    {
    }
}

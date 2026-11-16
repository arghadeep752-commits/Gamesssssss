using UnityEngine;
using UnityEngine.UI;

/// <summary>
/// The hand button's other half in Granny 4 EndGame (doors, locks, planks, the balloon). In Granny Dimnight every
/// hand-button action goes through MobilePickUpScript, which looks at the same things; this keeps the held item's
/// name for the scripts that read it and forwards taps.
/// </summary>
public class PlayerInteractionEngine : MonoBehaviour
{
    [Header("Detection Settings")]
    public float reachDistance;

    [Header("Mobile UI Link")]
    public GameObject mobileHandButton;
    public GameObject hideInButtonReference;

    [Header("Inventory Link")]
    public string currentlyHeldItem;

    private MobilePickUpScript pickup;

    private void Start()
    {
        pickup = GetComponent<MobilePickUpScript>();
        if (reachDistance <= 0f) reachDistance = 2f;
    }

    private void Update()
    {
        if (pickup == null) pickup = GetComponent<MobilePickUpScript>();
        if (pickup != null) currentlyHeldItem = pickup.GetHeldItemName();
    }

    private void ClearTargets()
    {
    }

    private void ExecuteInteraction()
    {
        if (pickup != null) pickup.OnInteractButtonPressed();
    }

    public void OnHandButtonTapped()
    {
        ExecuteInteraction();
    }
}

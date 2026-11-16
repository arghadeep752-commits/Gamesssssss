using UnityEngine;

/// <summary>Shows the hide button for this spot while the player is close enough to it.</summary>
public class HidingSpotDistanceTracker : MonoBehaviour
{
    [Header("Distance Settings")]
    public float activationDistance;

    private HidingSpot hidingSpot;
    private Transform playerTransform;
    private PlayerHidingController hidingController;
    private bool playerIsClose;
    private bool wasHidingLastFrame;

    private void Start()
    {
        hidingSpot = GetComponent<HidingSpot>();
        if (hidingSpot == null) hidingSpot = GetComponentInParent<HidingSpot>();
        if (hidingSpot == null) hidingSpot = GetComponentInChildren<HidingSpot>();
        GameObject p = GameSave.PlayerObject();
        if (p != null)
        {
            playerTransform = p.transform;
            hidingController = p.GetComponent<PlayerHidingController>();
        }
        if (activationDistance <= 0f) activationDistance = 2f;
    }

    private void Update()
    {
        if (hidingSpot == null || playerTransform == null || hidingController == null) return;
        bool hiding = CheckIfPlayerIsHiding();
        Vector3 a = transform.position, b = playerTransform.position;
        a.y = b.y = 0f;
        bool close = Vector3.Distance(a, b) <= activationDistance && Mathf.Abs(transform.position.y - playerTransform.position.y) < 2.5f;
        if (close && !playerIsClose) hidingController.SetNearbyHidingSpot(hidingSpot);
        else if (!close && playerIsClose && !hiding) hidingController.ClearNearbyHidingSpot(hidingSpot);
        else if (close && wasHidingLastFrame && !hiding) hidingController.SetNearbyHidingSpot(hidingSpot);
        playerIsClose = close;
        wasHidingLastFrame = hiding;
    }

    private bool CheckIfPlayerIsHiding()
    {
        return hidingController != null && hidingController.IsCurrentlyHiding;
    }

    private void OnDisable()
    {
        if (playerIsClose && hidingController != null && hidingSpot != null) hidingController.ClearNearbyHidingSpot(hidingSpot);
        playerIsClose = false;
    }
}

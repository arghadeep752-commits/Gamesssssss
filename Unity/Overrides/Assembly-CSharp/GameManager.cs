using System.Collections;
using UnityEngine;
using UnityEngine.AI;

/// <summary>New day after being caught: the player is put back at the wake-up point and Granny back at her spawn.</summary>
public class GameManager : MonoBehaviour
{
    [Header("Player & Camera Setup")]
    public GameObject playerGameObject;
    public Transform playerSpawnPoint;
    public MonoBehaviour wakeUpScript;

    [Header("Granny Setup")]
    public Transform grannySpawnPoint;

    [Header("Inventory / Item Drop Settings")]
    public MonoBehaviour playerPickupScript;

    public static GameManager Instance { get; private set; }

    private void Awake()
    {
        Instance = this;
        if (playerGameObject == null) playerGameObject = GameSave.PlayerObject();
    }

    public void ResetPlayerForNextDay()
    {
        StartCoroutine(SafeTeleportRoutine());
    }

    /// <summary>Puts the player at the wake-up point (used at the start of every day).</summary>
    public void PlacePlayerAtSpawn()
    {
        if (playerGameObject == null || playerSpawnPoint == null) return;
        var cc = playerGameObject.GetComponent<CharacterController>();
        if (cc != null) cc.enabled = false;
        playerGameObject.transform.SetPositionAndRotation(playerSpawnPoint.position, Quaternion.Euler(0f, playerSpawnPoint.eulerAngles.y, 0f));
        if (cc != null) cc.enabled = true;
        Physics.SyncTransforms();
    }

    private IEnumerator SafeTeleportRoutine()
    {
        MobilePickUpScript pickupScript = playerGameObject != null ? playerGameObject.GetComponent<MobilePickUpScript>() : null;
        if (pickupScript != null) pickupScript.SetTeleportingState(true);
        var hiding = playerGameObject != null ? playerGameObject.GetComponent<PlayerHidingController>() : null;
        if (hiding != null) hiding.ForceResetHidingState();
        var crouch = playerGameObject != null ? playerGameObject.GetComponent<MobileCrouchController>() : null;
        if (crouch != null) crouch.ForceStandReset();
        CharacterController charController = playerGameObject != null ? playerGameObject.GetComponent<CharacterController>() : null;
        FPSController fpsController = playerGameObject != null ? playerGameObject.GetComponent<FPSController>() : null;
        PlacePlayerAtSpawn();
        if (fpsController != null) { fpsController.ResetGravityVelocity(); fpsController.ResetMovementState(); }
        GrannyAI granny = FindFirstObjectByType<GrannyAI>();
        if (granny != null) granny.ResetAIStateForNextDay();
        if (JumpscareCoordinator.Instance != null) JumpscareCoordinator.Instance.ResetForNewDay();
        OutdoorAmbientZone.OnNewDay();
        yield return null;
        if (pickupScript != null) pickupScript.SetTeleportingState(false);
        var wake = playerGameObject != null ? playerGameObject.GetComponent<PlayerWakeUp>() : null;
        if (wake != null) wake.HoldLyingInBed();     // DayManager starts the wake-up once "Day N" has been shown
        else if (fpsController != null) fpsController.enabled = true;
        if (charController != null) charController.enabled = true;
    }
}

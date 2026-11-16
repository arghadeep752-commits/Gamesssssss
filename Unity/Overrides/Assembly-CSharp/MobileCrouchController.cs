using System.Collections;
using UnityEngine;
using UnityEngine.UI;

/// <summary>
/// Crouch / stand button: the camera drops (relative to its real standing height), the collider shrinks, walking
/// slows down. He can't stand up under a table or bed. The button shows the crouch / stand picture.
/// </summary>
public class MobileCrouchController : MonoBehaviour
{
    [Header("Setup References")]
    public Transform playerCamera;
    public Button crouchButton;

    [Header("Movement Script Reference")]
    public MonoBehaviour playerMovementScript;

    [Header("Button Sprite Configuration")]
    public Sprite standingSprite;
    public Sprite crouchingSprite;

    [Header("Camera Height Configuration")]
    public float timeToCrouch;
    public float standingLocalY;
    public float crouchDropAmount;

    [Header("Collider Height Configuration")]
    public float standingColliderHeight;
    public float crouchingColliderHeight;

    [Header("Speed Settings")]
    public float standingMovementSpeed;
    public float crouchingMovementSpeed;

    [Header("Obstacle Detection Mask")]
    public LayerMask obstacleLayers;

    private bool isCrouching;
    private Image buttonImage;
    private CapsuleCollider playerCollider;
    private CharacterController playerController;
    private PlayerHidingController hidingController;
    private float originalStandingY;
    private bool inputLocked;
    private Vector3 controllerCenterStanding;
    private Vector3 colliderCenterStanding;
    private Coroutine cameraRoutine;
    private int lastToggleFrame = -1;
    private bool listening;

    public bool IsCrouching => isCrouching;

    private void Awake()
    {
        playerCollider = GetComponent<CapsuleCollider>();
        playerController = GetComponent<CharacterController>();
        hidingController = GetComponent<PlayerHidingController>();
        if (crouchButton != null) buttonImage = crouchButton.image;
        if (playerController != null) controllerCenterStanding = playerController.center;
        if (playerCollider != null) colliderCenterStanding = playerCollider.center;
    }

    private void Start()
    {
        if (playerCamera == null)
        {
            Camera c = GetComponentInChildren<Camera>(true);
            if (c != null) playerCamera = c.transform;
        }
        originalStandingY = playerCamera != null ? playerCamera.localPosition.y : standingLocalY;
        if (timeToCrouch <= 0f) timeToCrouch = 0.25f;
        if (standingColliderHeight <= 0f) standingColliderHeight = playerController != null ? playerController.height : 2f;
        if (crouchingColliderHeight <= 0f) crouchingColliderHeight = standingColliderHeight * 0.5f;
        if (crouchButton != null && !listening)
        {
            crouchButton.onClick.AddListener(ToggleCrouch);
            listening = true;
        }
        if (buttonImage != null && crouchingSprite != null) buttonImage.sprite = crouchingSprite;
    }

    private void Update()
    {
        if (!Application.isMobilePlatform && Input.GetKeyDown(KeyCode.C)) ToggleCrouch();
    }

    public void ToggleCrouch()
    {
        if (!GameSave.FirstThisFrame(ref lastToggleFrame)) return;
        if (inputLocked) return;
        if (hidingController != null && (hidingController.IsCurrentlyHiding || hidingController.IsExiting)) return;
        if (isCrouching)
        {
            if (IsCeilingBlocking()) return;
            SetCrouched(false);
        }
        else
        {
            SetCrouched(true);
        }
    }

    private void SetCrouched(bool crouch)
    {
        isCrouching = crouch;
        if (cameraRoutine != null) StopCoroutine(cameraRoutine);
        cameraRoutine = StartCoroutine(CameraOnlyTransition());
        UpdateColliderDimensions(crouch ? crouchingColliderHeight : standingColliderHeight);
        ApplyMovementSpeed(crouch ? crouchingMovementSpeed : standingMovementSpeed);
        // the button shows what the next tap does: crouching -> "stand" picture
        if (buttonImage != null)
        {
            Sprite s = crouch ? standingSprite : crouchingSprite;
            if (s != null) buttonImage.sprite = s;
        }
    }

    /// <summary>A crouching player stands up before the death animation; returns how long that takes.</summary>
    public float StandUpForDeath()
    {
        if (!isCrouching) return 0f;
        SetCrouched(false);
        return timeToCrouch;
    }

    public void SetInputLocked(bool locked)
    {
        inputLocked = locked;
        if (crouchButton != null) crouchButton.interactable = !locked;
    }

    private IEnumerator CameraOnlyTransition()
    {
        if (playerCamera == null) yield break;
        float targetCameraY = isCrouching ? originalStandingY - crouchDropAmount : originalStandingY;
        float currentCameraY = playerCamera.localPosition.y;
        float elapsed = 0f;
        while (elapsed < timeToCrouch)
        {
            elapsed += Time.deltaTime;
            float t = Mathf.SmoothStep(0f, 1f, elapsed / timeToCrouch);
            Vector3 p = playerCamera.localPosition;
            p.y = Mathf.Lerp(currentCameraY, targetCameraY, t);
            playerCamera.localPosition = p;
            yield return null;
        }
        Vector3 end = playerCamera.localPosition;
        end.y = targetCameraY;
        playerCamera.localPosition = end;
        cameraRoutine = null;
    }

    private void UpdateColliderDimensions(float targetHeight)
    {
        float drop = (standingColliderHeight - targetHeight) * 0.5f;
        if (playerController != null)
        {
            playerController.height = targetHeight;
            playerController.center = controllerCenterStanding - new Vector3(0f, drop, 0f);
        }
        if (playerCollider != null)
        {
            playerCollider.height = targetHeight;
            playerCollider.center = colliderCenterStanding - new Vector3(0f, drop, 0f);
        }
    }

    private bool IsCeilingBlocking()
    {
        float radius = playerController != null ? playerController.radius * 0.9f : 0.3f;
        Vector3 centre = transform.position + (playerController != null ? playerController.center : Vector3.zero);
        Vector3 top = centre + Vector3.up * (crouchingColliderHeight * 0.5f - radius);
        float distance = standingColliderHeight - crouchingColliderHeight;
        int mask = obstacleLayers.value == 0 ? Physics.DefaultRaycastLayers : obstacleLayers.value;
        RaycastHit[] hits = Physics.SphereCastAll(top, radius, Vector3.up, distance, mask, QueryTriggerInteraction.Ignore);
        foreach (RaycastHit h in hits)
            if (h.collider != null && !h.collider.transform.IsChildOf(transform)) return true;
        return false;
    }

    public void ForceStandReset()
    {
        if (cameraRoutine != null) { StopCoroutine(cameraRoutine); cameraRoutine = null; }
        isCrouching = false;
        if (playerCamera != null)
        {
            Vector3 p = playerCamera.localPosition;
            p.y = originalStandingY;
            playerCamera.localPosition = p;
        }
        UpdateColliderDimensions(standingColliderHeight);
        ApplyMovementSpeed(standingMovementSpeed);
        if (buttonImage != null && crouchingSprite != null) buttonImage.sprite = crouchingSprite;
        inputLocked = false;
        if (crouchButton != null) crouchButton.interactable = true;
    }

    private void ApplyMovementSpeed(float newSpeed)
    {
        if (newSpeed <= 0f) return;
        if (!TrySetSpeed(playerMovementScript, newSpeed)) TrySetSpeed(GetComponent<FPSController>(), newSpeed);
    }

    private bool TrySetSpeed(MonoBehaviour script, float speedValue)
    {
        var fps = script as FPSController;
        if (fps == null) return false;
        fps.moveSpeed = speedValue;
        return true;
    }
}

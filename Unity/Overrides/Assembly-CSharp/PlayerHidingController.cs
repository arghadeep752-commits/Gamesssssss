using System;
using System.Collections;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

/// <summary>
/// Hiding Granny style: near a bed, the coffin or the car the hide button appears; tap it to slide in, look left and
/// right (up to 90 degrees) with a finger, tap it again to come out where you were. Walking, crouching and the
/// settings button are off while hiding.
/// </summary>
public class PlayerHidingController : MonoBehaviour
{
    [Header("Bed Item Drop Settings")]
    public Transform dropSpawnPoint;

    [Header("UI Setup")]
    public GameObject mobileHidingButton;
    public GameObject mobileCoffinButton;
    public GameObject mobileCarButton;

    [Header("UI Controls")]
    public GameObject joystickUI;
    public GameObject crouchButtonUI;
    public GameObject settingsButtonUI;

    [Header("Camera Configuration")]
    public Transform playerCamera;

    private const float HORIZONTAL_LOOK_LIMIT = 90f;

    [Header("Same Camera Height (Standing & Crouching)")]
    public bool holdStandingCameraHeight;
    public float cameraHeightBlendSpeed;

    [Header("Smooth Look While Hiding")]
    public float lookSmoothing;

    [Header("Transition Settings")]
    public float transitionSpeed;

    private bool isHiding;
    private bool isExiting;
    private bool exitLocked;
    private Vector3 preHidePosition;
    private Quaternion preHideRotation;
    private HidingSpot nearbySpot;
    private HidingSpot currentSpot;
    private CharacterController characterController;
    private FPSController fpsControllerScript;
    private Quaternion originalCameraLocalRotation;
    private float rotationY;
    private float targetRotationY;
    private Vector3 standingCameraLocalPos;
    private bool hasSavedCameraPose;
    private Quaternion hidingLookRot;
    private Vector3 heldCameraLocalPos;
    private int lookFingerId = -1;
    private bool entering;
    private int lastTapFrame = -1;
    private bool hooked;

    public static PlayerHidingController ActiveHidingBed { get; private set; }

    public bool IsCurrentlyHiding => isHiding || entering;
    public bool IsExiting => isExiting;
    public Vector3 PreHidePosition => preHidePosition;
    public HidingSpot CurrentSpot => currentSpot;

    public void SetExitLocked(bool locked)
    {
        exitLocked = locked;
    }

    private void Awake()
    {
        characterController = GetComponent<CharacterController>();
        fpsControllerScript = GetComponent<FPSController>();
    }

    private void Start()
    {
        if (playerCamera == null)
        {
            Camera c = GetComponentInChildren<Camera>(true);
            if (c != null) playerCamera = c.transform;
        }
        if (playerCamera != null)
        {
            standingCameraLocalPos = playerCamera.localPosition;
            originalCameraLocalRotation = playerCamera.localRotation;
            hasSavedCameraPose = true;
        }
        if (transitionSpeed <= 0f) transitionSpeed = 8f;
        if (lookSmoothing <= 0f) lookSmoothing = 20f;
        FindSettingsButton();
        Hook(mobileHidingButton, OnHidingButtonTapped);
        Hook(mobileCoffinButton, OnCoffinButtonTapped);
        Hook(mobileCarButton, OnCarButtonTapped);
        hooked = true;
        ToggleActiveInteractionButton(false);
    }

    private void Hook(GameObject go, UnityEngine.Events.UnityAction action)
    {
        if (hooked || go == null) return;
        Button b = go.GetComponent<Button>();
        if (b != null) b.onClick.AddListener(action);
    }

    public void SetNearbyHidingSpot(HidingSpot spot)
    {
        if (spot == null) return;
        nearbySpot = spot;
        if (!isHiding && !isExiting) ToggleActiveInteractionButton(true);
    }

    public void ClearNearbyHidingSpot(HidingSpot spot)
    {
        if (nearbySpot != spot) return;
        nearbySpot = null;
        if (!isHiding && !entering) ToggleActiveInteractionButton(false);
    }

    public void OnHidingButtonTapped() { Tapped(); }
    public void OnCoffinButtonTapped() { Tapped(); }
    public void OnCarButtonTapped() { Tapped(); }

    private void Tapped()
    {
        if (!GameSave.FirstThisFrame(ref lastTapFrame)) return;
        if (isExiting || entering) return;
        if (isHiding) { if (!exitLocked) ExitHiding(); return; }
        if (nearbySpot != null) EnterHiding(nearbySpot);
    }

    public void EnterHiding(HidingSpot spot)
    {
        if (spot == null || isHiding || isExiting || entering) return;
        var wake = GetComponent<PlayerWakeUp>();
        if (wake != null && wake.IsWakingUp) return;
        preHidePosition = transform.position;
        preHideRotation = transform.rotation;
        currentSpot = spot;
        entering = true;
        if (spot.spotType == HidingSpot.HidingType.Bed) ActiveHidingBed = this;
        if (characterController != null) characterController.enabled = false;
        if (fpsControllerScript != null) fpsControllerScript.enabled = false;
        if (joystickUI != null) joystickUI.SetActive(false);
        if (crouchButtonUI != null) crouchButtonUI.SetActive(false);
        if (settingsButtonUI != null) settingsButtonUI.SetActive(false);
        spot.OnEnterHidingSpot();
        rotationY = targetRotationY = 0f;
        Transform target = spot.hidePosition != null ? spot.hidePosition : spot.transform;
        Quaternion yaw = Quaternion.Euler(0f, target.eulerAngles.y, 0f);
        StartCoroutine(TransitionToPoint(target.position, yaw, () =>
        {
            entering = false;
            isHiding = true;
            ToggleActiveInteractionButton(true);
        }));
    }

    private void ExitHiding()
    {
        if (!isHiding) return;
        isHiding = false;
        isExiting = true;
        HidingSpot spot = currentSpot;
        StartCoroutine(TransitionToPoint(preHidePosition, preHideRotation, () =>
        {
            isExiting = false;
            FinishExit(spot);
        }));
    }

    private void FinishExit(HidingSpot spot)
    {
        if (spot != null) spot.OnExitHidingSpot();
        currentSpot = null;
        if (ActiveHidingBed == this) ActiveHidingBed = null;
        if (characterController != null) characterController.enabled = true;
        if (fpsControllerScript != null)
        {
            fpsControllerScript.enabled = true;
            fpsControllerScript.ResetMovementState();
        }
        if (joystickUI != null) joystickUI.SetActive(true);
        if (crouchButtonUI != null) crouchButtonUI.SetActive(true);
        if (settingsButtonUI != null) settingsButtonUI.SetActive(true);
        if (playerCamera != null) playerCamera.localRotation = Quaternion.Euler(playerCamera.localEulerAngles.x, 0f, 0f);
        ToggleActiveInteractionButton(nearbySpot != null);
    }

    private void ToggleActiveInteractionButton(bool state)
    {
        HidingSpot spot = currentSpot != null ? currentSpot : nearbySpot;
        HidingSpot.HidingType type = spot != null ? spot.spotType : HidingSpot.HidingType.Bed;
        GameObject want = type == HidingSpot.HidingType.Coffin ? mobileCoffinButton
                        : type == HidingSpot.HidingType.Car ? mobileCarButton : mobileHidingButton;
        if (want == null) want = mobileHidingButton;
        foreach (GameObject b in new[] { mobileHidingButton, mobileCoffinButton, mobileCarButton })
            if (b != null) b.SetActive(state && b == want);
    }

    private void Update()
    {
        if (!isHiding || playerCamera == null) return;
        float dx = ReadHidingLookInput();
        targetRotationY = Mathf.Clamp(targetRotationY + dx, -HORIZONTAL_LOOK_LIMIT, HORIZONTAL_LOOK_LIMIT);
        rotationY = Mathf.Lerp(rotationY, targetRotationY, 1f - Mathf.Exp(-lookSmoothing * Time.deltaTime));
    }

    private float ReadHidingLookInput()
    {
        float sens = fpsControllerScript != null ? fpsControllerScript.mouseSensitivity * Mathf.Max(0.05f, fpsControllerScript.touchLookScale) : 0.4f;
        for (int i = 0; i < Input.touchCount; i++)
        {
            Touch t = Input.GetTouch(i);
            if (t.phase == TouchPhase.Began && lookFingerId < 0)
            {
                bool overUi = EventSystem.current != null && EventSystem.current.IsPointerOverGameObject(t.fingerId);
                if (!overUi) lookFingerId = t.fingerId;
            }
            if (t.fingerId == lookFingerId)
            {
                if (t.phase == TouchPhase.Ended || t.phase == TouchPhase.Canceled) { lookFingerId = -1; return 0f; }
                if (t.phase == TouchPhase.Moved) return t.deltaPosition.x * sens;
            }
        }
        if (Input.touchCount == 0) lookFingerId = -1;
        if (!Application.isMobilePlatform && Input.GetMouseButton(1)) return Input.GetAxis("Mouse X") * sens * 8f;
        return 0f;
    }

    private void LateUpdate()
    {
        if (!isHiding || currentSpot == null || playerCamera == null) return;
        Transform target = currentSpot.hidePosition != null ? currentSpot.hidePosition : currentSpot.transform;
        transform.position = target.position;
        transform.rotation = Quaternion.Euler(0f, target.eulerAngles.y, 0f);
        if (holdStandingCameraHeight && hasSavedCameraPose)
            playerCamera.localPosition = Vector3.MoveTowards(playerCamera.localPosition, standingCameraLocalPos, Mathf.Max(1f, cameraHeightBlendSpeed) * Time.deltaTime);
        hidingLookRot = Quaternion.Euler(target.eulerAngles.x, target.eulerAngles.y + rotationY, 0f);
        playerCamera.rotation = hidingLookRot;
    }

    private IEnumerator TransitionToPoint(Vector3 targetPos, Quaternion targetRot, Action onComplete)
    {
        float time = 0f;
        Vector3 startPos = transform.position;
        Quaternion startRot = transform.rotation;
        float duration = Mathf.Clamp(Vector3.Distance(startPos, targetPos) / Mathf.Max(1f, transitionSpeed * 0.25f), 0.25f, 0.8f);
        while (time < duration)
        {
            time += Time.deltaTime;
            float t = Mathf.SmoothStep(0f, 1f, time / duration);
            transform.position = Vector3.Lerp(startPos, targetPos, t);
            transform.rotation = Quaternion.Slerp(startRot, targetRot, t);
            yield return null;
        }
        transform.position = targetPos;
        transform.rotation = targetRot;
        if (onComplete != null) onComplete();
    }

    /// <summary>Death or a new day: out of the hiding spot at once, controls back as they were.</summary>
    public void ForceResetHidingState()
    {
        StopAllCoroutines();
        HidingSpot spot = currentSpot;
        bool wasIn = isHiding || entering || isExiting;
        isHiding = false;
        isExiting = false;
        entering = false;
        exitLocked = false;
        if (wasIn)
        {
            if (spot != null) spot.OnExitHidingSpot();
            if (ActiveHidingBed == this) ActiveHidingBed = null;
        }
        currentSpot = null;
        if (characterController != null) characterController.enabled = true;
        if (playerCamera != null && hasSavedCameraPose) playerCamera.localPosition = standingCameraLocalPos;
        ToggleActiveInteractionButton(false);
    }

    private void FindSettingsButton()
    {
        if (settingsButtonUI != null) return;
        var settings = FindFirstObjectByType<GameSettingsManager>();
        if (settings == null) return;
        GameObject go = GameObject.Find("Setting");
        if (go != null && go.GetComponent<Button>() != null) settingsButtonUI = go;
    }
}

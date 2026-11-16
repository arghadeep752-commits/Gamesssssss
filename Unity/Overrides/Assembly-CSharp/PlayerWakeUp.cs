using System.Collections;
using System.Collections.Generic;
using TMPro;
using UnityEngine;
using UnityEngine.Events;
using UnityEngine.UI;

/// <summary>
/// Granny-style wake-up at the start of every day: eyes open in bed looking at the ceiling, the player rolls onto
/// his right side, gets up a little dizzy, and only then can he move, look around and use the buttons.
/// </summary>
public class PlayerWakeUp : MonoBehaviour
{
    [Header("Setup References")]
    public Transform playerCamera;
    public MonoBehaviour fpsController;
    public Image blinkOverlay;
    public TMP_Text dayTextMesh;

    [Header("Bed Wake Up Setup")]
    public Transform bedWakeUpPoint;
    public float lyingLookUpPitch;
    public float lookUpHoldTime;
    public float rollToSideDuration;
    public float sidePauseTime;
    public float sideRollAngle;
    public UnityEvent onWakeUpComplete;

    [Header("Item Hold Points Setup")]
    public List<GameObject> allItemHoldPoints;

    [Header("Granny Style Input Restrictions")]
    public MonoBehaviour screenRotationScript;
    public GameObject joystickUIContainer;
    public GameObject crouchButtonUI;
    public Image bedHideButtonImage;

    [Header("Cinematic Timings")]
    public float riseDuration;
    public AudioClip wakeUpGroan;

    [Header("Granny Wake Up Feel (optional tuning)")]
    public float settleDuration;
    public float dizzySwayAmount;
    public bool useEyeFocusFov;
    public float squintFovReduction;

    private AudioSource audioSource;
    private Coroutine activeWakeUpRoutine;
    private Vector3 originalStandingLocalPos;
    private bool hasSavedOriginalPos;
    private GameObject currentlyHeldItemPoint;
    private bool isWakingUp;
    private bool lyingPhaseActive;
    private Button cachedBedHideButton;
    private Camera playerCam;
    private float originalFov;
    private bool hasSavedFov;
    private bool bodyRotationCaptured;
    private Quaternion lockedBodyRotation;
    private bool camPoseRemembered;
    private Vector3 rememberedCamPos;
    private Quaternion rememberedCamRot;
    private GameObject mobileCanvas;

    public bool IsWakingUp => isWakingUp;

    private void Awake()
    {
        audioSource = GetComponent<AudioSource>();
        if (audioSource == null) { audioSource = gameObject.AddComponent<AudioSource>(); audioSource.playOnAwake = false; }
        if (playerCamera == null) { Camera c = GetComponentInChildren<Camera>(true); if (c != null) playerCamera = c.transform; }
        if (playerCamera != null)
        {
            playerCam = playerCamera.GetComponent<Camera>();
            originalStandingLocalPos = playerCamera.localPosition;
            hasSavedOriginalPos = true;
            if (playerCam != null) { originalFov = playerCam.fieldOfView; hasSavedFov = true; }
        }
        if (fpsController == null) fpsController = GetComponent<FPSController>();
        if (rollToSideDuration <= 0f) rollToSideDuration = 1.5f;
        if (riseDuration <= 0f) riseDuration = 3f;
        if (sideRollAngle == 0f) sideRollAngle = 80f;
        if (lyingLookUpPitch == 0f) lyingLookUpPitch = -80f;
    }

    private void OnEnable()
    {
    }

    public void ResetWakeUpState()
    {
        if (activeWakeUpRoutine != null) { StopCoroutine(activeWakeUpRoutine); activeWakeUpRoutine = null; }
        isWakingUp = false;
        lyingPhaseActive = false;
        if (playerCamera != null && hasSavedOriginalPos)
        {
            playerCamera.localPosition = originalStandingLocalPos;
            playerCamera.localRotation = Quaternion.identity;
        }
        if (playerCam != null && hasSavedFov) playerCam.fieldOfView = originalFov;
        SetOverlay(0f);
        ApplyInputLock(false);
    }

    private void OnDrawGizmosSelected()
    {
        if (bedWakeUpPoint == null) return;
        Gizmos.color = Color.cyan;
        Gizmos.DrawWireSphere(bedWakeUpPoint.position, 0.15f);
        Gizmos.DrawLine(bedWakeUpPoint.position, bedWakeUpPoint.position + bedWakeUpPoint.forward * 0.6f);
    }

    private void SetOverlay(float a)
    {
        if (blinkOverlay == null) return;
        Color c = blinkOverlay.color;
        c.a = a;
        blinkOverlay.color = c;
        blinkOverlay.raycastTarget = false;
    }

    private void ApplyInputLock(bool locked)
    {
        if (fpsController != null) fpsController.enabled = !locked;
        if (joystickUIContainer != null) joystickUIContainer.SetActive(!locked);
        if (crouchButtonUI != null) crouchButtonUI.SetActive(!locked);
        if (bedHideButtonImage != null)
        {
            if (cachedBedHideButton == null) cachedBedHideButton = bedHideButtonImage.GetComponent<Button>();
            if (cachedBedHideButton != null) cachedBedHideButton.interactable = !locked;
        }
        var crouch = GetComponent<MobileCrouchController>();
        if (crouch != null) crouch.SetInputLocked(locked);
        if (MobilePickUpScript.Instance != null) MobilePickUpScript.Instance.SetTeleportingState(locked);
        if (mobileCanvas == null && JumpscareCoordinator.Instance != null) mobileCanvas = JumpscareCoordinator.Instance.mobileControlsCanvas;
        if (mobileCanvas == null) mobileCanvas = GameObject.Find("MobileControlsCanvas");
        if (mobileCanvas != null) mobileCanvas.SetActive(!locked);
    }

    private void Update()
    {
    }

    private void LateUpdate()
    {
        if (lyingPhaseActive && camPoseRemembered && playerCamera != null)
            playerCamera.SetPositionAndRotation(rememberedCamPos, rememberedCamRot);
    }

    private void RememberCamPose()
    {
        if (playerCamera == null) return;
        rememberedCamPos = playerCamera.position;
        rememberedCamRot = playerCamera.rotation;
        camPoseRemembered = true;
    }

    private Quaternion BedYaw()
    {
        Transform bed = bedWakeUpPoint != null ? bedWakeUpPoint : transform;
        return Quaternion.Euler(0f, bed.eulerAngles.y, 0f);
    }

    private Vector3 BedPos()
    {
        return bedWakeUpPoint != null ? bedWakeUpPoint.position : transform.position + Vector3.up * 0.3f;
    }

    /// <summary>Keeps the player lying in bed (eyes closed, no controls) until BeginWakeUp.</summary>
    public void HoldLyingInBed()
    {
        if (activeWakeUpRoutine != null) { StopCoroutine(activeWakeUpRoutine); activeWakeUpRoutine = null; }
        isWakingUp = true;
        ApplyInputLock(true);
        SetOverlay(1f);
        if (playerCamera == null) return;
        if (playerCam != null && hasSavedFov) playerCam.fieldOfView = originalFov - (useEyeFocusFov ? squintFovReduction : 0f);
        playerCamera.SetPositionAndRotation(BedPos(), BedYaw() * Quaternion.Euler(lyingLookUpPitch, 0f, 0f));
        RememberCamPose();
        lyingPhaseActive = true;
    }

    public void BeginWakeUp()
    {
        if (activeWakeUpRoutine != null) StopCoroutine(activeWakeUpRoutine);
        if (!lyingPhaseActive) HoldLyingInBed();
        activeWakeUpRoutine = StartCoroutine(GrannyRightSideWakeUpSequence());
    }

    private IEnumerator InputLockEnforcer()
    {
        while (isWakingUp)
        {
            if (fpsController != null && fpsController.enabled) fpsController.enabled = false;
            yield return null;
        }
    }

    private void ApplyPoseWithBreathing(Vector3 basePos, Quaternion baseRot, float weight)
    {
        if (playerCamera == null) return;
        float b = Mathf.Sin(Time.time * 1.6f) * 0.012f * weight;
        playerCamera.SetPositionAndRotation(basePos + Vector3.up * b, baseRot * Quaternion.Euler(b * 40f, 0f, 0f));
    }

    private static float Dt()
    {
        return Mathf.Min(Time.deltaTime, 0.05f);
    }

    private IEnumerator LyingBreathing(Vector3 basePos, Quaternion baseRot)
    {
        while (lyingPhaseActive)
        {
            ApplyPoseWithBreathing(basePos, baseRot, 1f);
            yield return null;
        }
    }

    private IEnumerator HoldWithBreathing(Vector3 basePos, Quaternion baseRot, float duration)
    {
        float held = 0f;
        while (held < duration)
        {
            held += Dt();
            ApplyPoseWithBreathing(basePos, baseRot, 1f);
            yield return null;
        }
    }

    private static float Seg(float t, float a, float b)
    {
        return Mathf.Clamp01((t - a) / Mathf.Max(0.0001f, b - a));
    }

    private IEnumerator GrannyRightSideWakeUpSequence()
    {
        isWakingUp = true;
        StartCoroutine(InputLockEnforcer());
        PlayerHidingController hidingCtrl = GetComponent<PlayerHidingController>();
        if (hidingCtrl != null) hidingCtrl.ForceResetHidingState();
        lyingPhaseActive = false;
        Vector3 bedPos = BedPos();
        Quaternion bedYaw = BedYaw();
        Vector3 bedRight = bedYaw * Vector3.right;
        Quaternion bedLyingRot = bedYaw * Quaternion.Euler(lyingLookUpPitch, 0f, 0f);

        // eyes open
        float elapsed = 0f;
        while (elapsed < 1.1f)
        {
            elapsed += Dt();
            float k = elapsed / 1.1f;
            SetOverlay(1f - Mathf.SmoothStep(0f, 1f, k));
            if (playerCam != null && hasSavedFov && useEyeFocusFov) playerCam.fieldOfView = Mathf.Lerp(originalFov - squintFovReduction, originalFov - squintFovReduction * 0.5f, k);
            ApplyPoseWithBreathing(bedPos, bedLyingRot, 1f);
            yield return null;
        }
        SetOverlay(0f);
        yield return HoldWithBreathing(bedPos, bedLyingRot, Mathf.Max(0.2f, lookUpHoldTime));

        // roll onto the right side
        Vector3 sideRestPos = bedPos + bedRight * 0.25f + Vector3.down * 0.05f;
        Quaternion sideRestRot = bedYaw * Quaternion.Euler(0f, 90f, 0f) * Quaternion.Euler(10f, 0f, sideRollAngle);
        float rollElapsed = 0f;
        while (rollElapsed < rollToSideDuration)
        {
            rollElapsed += Dt();
            float k = Mathf.SmoothStep(0f, 1f, rollElapsed / rollToSideDuration);
            ApplyPoseWithBreathing(Vector3.Lerp(bedPos, sideRestPos, k), Quaternion.Slerp(bedLyingRot, sideRestRot, k), 1f);
            yield return null;
        }
        if (sidePauseTime > 0f) yield return HoldWithBreathing(sideRestPos, sideRestRot, sidePauseTime);

        // get up
        if (wakeUpGroan != null && audioSource != null) audioSource.PlayOneShot(wakeUpGroan);
        if (playerCamera != null && hasSavedOriginalPos)
        {
            Transform camParent = playerCamera.parent;
            Vector3 standingLocalPos = originalStandingLocalPos;
            Quaternion standingLocalRot = Quaternion.identity;
            float settleElapsed = 0f;
            float textFadeElapsed = 0f;
            Color textColor = dayTextMesh != null ? dayTextMesh.color : Color.white;
            elapsed = 0f;
            while (elapsed < riseDuration)
            {
                elapsed += Dt();
                float k = Mathf.SmoothStep(0f, 1f, elapsed / riseDuration);
                Vector3 standPos = camParent != null ? camParent.TransformPoint(standingLocalPos) : standingLocalPos;
                Quaternion standRot = camParent != null ? camParent.rotation * standingLocalRot : standingLocalRot;
                Vector3 pos = Vector3.Lerp(sideRestPos, standPos, k) + Vector3.up * Mathf.Sin(k * Mathf.PI) * 0.15f;
                float sway = Mathf.Sin(elapsed * 2.2f) * 4f * dizzySwayAmount * (1f - k);
                Quaternion rot = Quaternion.Slerp(sideRestRot, standRot, k) * Quaternion.Euler(0f, 0f, sway);
                playerCamera.SetPositionAndRotation(pos, rot);
                if (playerCam != null && hasSavedFov && useEyeFocusFov) playerCam.fieldOfView = Mathf.Lerp(originalFov - squintFovReduction * 0.5f, originalFov, k);
                if (dayTextMesh != null && dayTextMesh.gameObject.activeInHierarchy)
                {
                    textFadeElapsed += Dt();
                    Color c = textColor;
                    c.a = Mathf.Clamp01(1f - textFadeElapsed / 1.5f) * textColor.a;
                    dayTextMesh.color = c;
                }
                yield return null;
            }
            while (settleElapsed < settleDuration)
            {
                settleElapsed += Dt();
                float k = settleElapsed / Mathf.Max(0.01f, settleDuration);
                float sway = Mathf.Sin(settleElapsed * 3f) * 2f * dizzySwayAmount * (1f - k);
                playerCamera.localPosition = standingLocalPos;
                playerCamera.localRotation = Quaternion.Euler(0f, 0f, sway);
                yield return null;
            }
            playerCamera.localPosition = standingLocalPos;
            playerCamera.localRotation = standingLocalRot;
        }
        if (playerCam != null && hasSavedFov) playerCam.fieldOfView = originalFov;
        var fps = fpsController as FPSController;
        isWakingUp = false;
        ApplyInputLock(false);
        if (fps != null) fps.ResetMovementState();
        activeWakeUpRoutine = null;
        if (onWakeUpComplete != null) onWakeUpComplete.Invoke();
    }

    private IEnumerator FadeOverlay(float startAlpha, float endAlpha, float duration)
    {
        float elapsed = 0f;
        Color col = blinkOverlay != null ? blinkOverlay.color : Color.black;
        while (elapsed < duration)
        {
            elapsed += Dt();
            SetOverlay(Mathf.Lerp(startAlpha, endAlpha, elapsed / duration));
            yield return null;
        }
        SetOverlay(endAlpha);
    }
}

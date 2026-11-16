using System.Collections;
using System.Reflection;
using UnityEngine;
using UnityEngine.AI;

/// <summary>
/// The player's side of being caught: controls go, the view turns to Granny's face, she hits him, he is knocked
/// back and falls to the floor (rolling over, a small bounce), the held item drops where he fell, and the screen
/// fades to the next day. Under a bed he stares at her face as she drops down instead.
/// </summary>
public class JumpscareCoordinator : MonoBehaviour
{
    public enum PlayerHidingState
    {
        None = 0,
        InCoffin = 1,
        UnderBed = 2
    }

    public static JumpscareCoordinator Instance;

    [Header("Player References")]
    public Transform playerTransform;
    public Transform playerCamera;
    public MonoBehaviour cameraLookScript;

    [Header("Granny Standard References")]
    public Animator grannyAnimator;
    public Transform grannyTransform;
    public AudioSource grannyAudioSource;

    [Header("Granny Bed 1 Special References")]
    public Animator bedGrannyAnimator;
    public Transform bedLookTarget;

    [Header("Granny Bed 2 Special References")]
    public Animator bed2GrannyAnimator;
    public Transform bed2LookTarget;

    [Header("Granny Bed 3 Special References")]
    public Animator bed3GrannyAnimator;
    public Transform bed3LookTarget;

    [Header("Jumpscare Assets")]
    public AudioClip standardHitSound;
    public AudioClip coffinJumpscareSound;
    public AudioClip bedJumpscareSound;

    [Header("Timing Customization")]
    public float delayBeforeFloorFall;
    public float bedKillAnimationDuration;
    public float delayAfterBedKill;

    [Header("Bed Death Fade")]
    public bool useBedDeathFadeTiming;
    public float bedDeathFadeDelay;
    public float bedDeathFadeDuration;

    [Header("Natural Fall (standing / coffin / car kill)")]
    public float fallGravity;
    public float lyingCameraHeight;
    public float fallRollAngle;
    public float fallPitchUp;
    public float knockbackSpeed;
    public float knockbackDeceleration;
    public float bounceRestitution;
    public float fallSettleTime;

    [Header("Look At Granny's Head (until she hits him)")]
    public float lookAtGrannyTurnSpeed;
    public float bedHeadContactDuration;

    [Header("UI Blackout & Lock")]
    public CanvasGroup gameHUD;
    public GameObject mobileControlsCanvas;

    [HideInInspector]
    public PlayerHidingState currentHidingState;

    private bool hasPullOutPoint;
    private Vector3 pullOutPoint;
    private bool isRotationLocked;
    private Quaternion lockedCameraRotation;
    private Quaternion lockedPlayerRotation;
    private bool isFallPoseHeld;
    private Vector3 heldCamPos;
    private Quaternion heldCamRot;
    private Vector3 heldRootPos;
    private float heldUntilTime;
    private MonoBehaviour killFpsRef;
    private PlayerWakeUp cachedWakeUp;
    private FieldInfo wakingField;
    private bool isBedViewHeld;
    private bool isHeadTracking;
    private Transform grannyFaceTarget;
    private bool faceTargetSearched;
    private GrannyAI cachedGrannyAI;
    private bool running;
    private AudioSource ownAudio;

    public void SetPullOutPoint(Vector3 point)
    {
        pullOutPoint = point;
        hasPullOutPoint = true;
    }

    private void Awake()
    {
        Instance = this;
        ownAudio = gameObject.AddComponent<AudioSource>();
        ownAudio.playOnAwake = false;
        ownAudio.spatialBlend = 0f;
        if (playerTransform == null) { GameObject p = GameSave.PlayerObject(); if (p != null) playerTransform = p.transform; }
        if (playerCamera == null && playerTransform != null) { Camera c = playerTransform.GetComponentInChildren<Camera>(); if (c != null) playerCamera = c.transform; }
        if (fallGravity <= 0f) fallGravity = 14f;
        if (lyingCameraHeight <= 0f) lyingCameraHeight = 0.3f;
        if (lookAtGrannyTurnSpeed <= 0f) lookAtGrannyTurnSpeed = 10f;
        if (delayBeforeFloorFall <= 0f) delayBeforeFloorFall = 0.8f;
    }

    private void LateUpdate()
    {
        if (playerCamera == null) return;
        if (isHeadTracking)
        {
            Vector3 d = GetGrannyLookPoint() - playerCamera.position;
            if (d.sqrMagnitude > 0.0001f)
                playerCamera.rotation = Quaternion.Slerp(playerCamera.rotation, Quaternion.LookRotation(d), 1f - Mathf.Exp(-lookAtGrannyTurnSpeed * Time.deltaTime));
        }
        else if (isFallPoseHeld)
        {
            if (ShouldReleaseHeldPose()) { isFallPoseHeld = false; return; }
            playerCamera.SetPositionAndRotation(heldCamPos, heldCamRot);
        }
    }

    public void StartKillSequence()
    {
        if (running) return;
        running = true;
        StartCoroutine(ExecuteKillSequence());
    }

    /// <summary>Called by GameManager when the next day starts.</summary>
    public void ResetForNewDay()
    {
        StopAllCoroutines();
        running = false;
        isHeadTracking = false;
        isFallPoseHeld = false;
        isBedViewHeld = false;
        hasPullOutPoint = false;
        currentHidingState = PlayerHidingState.None;
        if (gameHUD != null) gameHUD.alpha = 1f;
    }

    private bool IsActorCollider(Transform t)
    {
        if (t == null) return false;
        if (playerTransform != null && t.IsChildOf(playerTransform)) return true;
        if (grannyTransform != null && t.IsChildOf(grannyTransform)) return true;
        return false;
    }

    private float FindFloorHeightBelow(Vector3 fromPos, out bool found)
    {
        RaycastHit[] hits = Physics.RaycastAll(fromPos + Vector3.up * 0.2f, Vector3.down, 4f, Physics.DefaultRaycastLayers, QueryTriggerInteraction.Ignore);
        float best = float.MinValue;
        found = false;
        foreach (RaycastHit h in hits)
        {
            if (IsActorCollider(h.collider.transform)) continue;
            if (h.point.y > best) { best = h.point.y; found = true; }
        }
        return found ? best : fromPos.y - 1.6f;
    }

    private bool IsBlockedHorizontally(Vector3 origin, Vector3 direction, float distance)
    {
        foreach (RaycastHit h in Physics.SphereCastAll(origin, 0.12f, direction, distance, Physics.DefaultRaycastLayers, QueryTriggerInteraction.Ignore))
            if (!IsActorCollider(h.collider.transform)) return true;
        return false;
    }

    private bool IsPlayerWakingUp()
    {
        if (cachedWakeUp == null && playerTransform != null) cachedWakeUp = playerTransform.GetComponent<PlayerWakeUp>();
        return cachedWakeUp != null && cachedWakeUp.IsWakingUp && !running;
    }

    private bool ShouldReleaseHeldPose()
    {
        return IsPlayerWakingUp();
    }

    private GrannyAI GetGrannyAI()
    {
        if (cachedGrannyAI == null)
        {
            if (grannyTransform != null) cachedGrannyAI = grannyTransform.GetComponent<GrannyAI>();
            if (cachedGrannyAI == null) cachedGrannyAI = GrannyAI.Instance;
        }
        return cachedGrannyAI;
    }

    private Vector3 GetGrannyLookPoint()
    {
        GrannyAI g = GetGrannyAI();
        if (g != null) return g.GetHeadLookPoint();
        Transform face = FindGrannyFaceTarget();
        if (face != null) return face.position;
        return grannyTransform != null ? grannyTransform.position + Vector3.up * 1.5f : playerCamera.position + playerCamera.forward;
    }

    private Transform FindGrannyFaceTarget()
    {
        if (faceTargetSearched) return grannyFaceTarget;
        faceTargetSearched = true;
        if (grannyTransform != null) grannyFaceTarget = GameSave.FindDeep(grannyTransform, "GrannyHeadPos") ?? GameSave.FindDeep(grannyTransform, "Bip01 Head");
        if (grannyFaceTarget == null) grannyFaceTarget = bedLookTarget;
        return grannyFaceTarget;
    }

    private void Play(AudioClip clip)
    {
        if (clip == null) return;
        if (grannyAudioSource != null) grannyAudioSource.PlayOneShot(clip);
        else ownAudio.PlayOneShot(clip);
    }

    private IEnumerator NaturalFallToFloor()
    {
        if (playerCamera == null) yield break;
        Quaternion startRot = playerCamera.rotation;
        Vector3 pos = playerCamera.position;
        float restY = FindFloorHeightBelow(pos, out bool _) + lyingCameraHeight;
        float totalDrop = Mathf.Max(0.3f, pos.y - restY);
        Vector3 knockDirection = grannyTransform != null ? playerCamera.position - grannyTransform.position : -playerCamera.forward;
        knockDirection.y = 0f;
        knockDirection = knockDirection.sqrMagnitude > 0.001f ? knockDirection.normalized : -playerCamera.forward;
        float verticalSpeed = 0f;
        float horizontalSpeed = knockbackSpeed > 0f ? knockbackSpeed : 1.8f;
        float maxProgress = 0f;
        int bounces = 0;
        bool landed = false;
        float settleTimer = 0f;
        float safetyTimer = 0f;
        Vector3 flatFwd = startRot * Vector3.forward;
        flatFwd.y = 0f;
        if (flatFwd.sqrMagnitude < 0.001f) flatFwd = Vector3.forward;
        Quaternion endRot = Quaternion.LookRotation(flatFwd.normalized) * Quaternion.Euler(-fallPitchUp - 25f, 0f, fallRollAngle);
        while (safetyTimer < 4f)
        {
            float dt = Mathf.Min(Time.deltaTime, 0.05f);
            safetyTimer += dt;
            verticalSpeed -= fallGravity * dt;
            pos.y += verticalSpeed * dt;
            if (horizontalSpeed > 0f)
            {
                Vector3 step = knockDirection * horizontalSpeed * dt;
                if (!IsBlockedHorizontally(pos, knockDirection, step.magnitude + 0.15f)) pos += step;
                horizontalSpeed = Mathf.Max(0f, horizontalSpeed - (knockbackDeceleration > 0f ? knockbackDeceleration : 5f) * dt);
            }
            if (pos.y <= restY)
            {
                pos.y = restY;
                if (bounces < 1 && bounceRestitution > 0f && Mathf.Abs(verticalSpeed) > 1f)
                {
                    verticalSpeed = -verticalSpeed * bounceRestitution;
                    bounces++;
                }
                else
                {
                    verticalSpeed = 0f;
                    landed = true;
                }
            }
            float progress = Mathf.Clamp01(1f - (pos.y - restY) / totalDrop);
            maxProgress = Mathf.Max(maxProgress, progress);
            playerCamera.SetPositionAndRotation(pos, Quaternion.Slerp(startRot, endRot, Mathf.SmoothStep(0f, 1f, maxProgress)));
            if (landed)
            {
                settleTimer += dt;
                if (settleTimer >= Mathf.Max(0.05f, fallSettleTime)) break;
            }
            yield return null;
        }
        heldCamPos = playerCamera.position;
        heldCamRot = playerCamera.rotation;
        isFallPoseHeld = true;
    }

    private void DropPlayerHeldItemAtCurrentPosition()
    {
        if (MobilePickUpScript.Instance != null) MobilePickUpScript.Instance.DropItemOnDeath();
    }

    private IEnumerator BedHeadContactRoutine(float duration)
    {
        isHeadTracking = true;
        yield return new WaitForSeconds(Mathf.Max(0.1f, duration));
        isHeadTracking = false;
        if (playerCamera != null)
        {
            heldCamPos = playerCamera.position;
            heldCamRot = playerCamera.rotation;
            isFallPoseHeld = true;
        }
    }

    private IEnumerator ExecuteKillSequence()
    {
        float fadeDurationOverride = 0f;
        Transform player = playerTransform;
        killFpsRef = player != null ? player.GetComponent<FPSController>() : null;
        if (killFpsRef != null) killFpsRef.enabled = false;
        var crouch = player != null ? player.GetComponent<MobileCrouchController>() : null;
        if (crouch != null) crouch.SetInputLocked(true);
        var hiding = player != null ? player.GetComponent<PlayerHidingController>() : null;
        if (hiding != null) hiding.SetExitLocked(true);
        if (mobileControlsCanvas != null) mobileControlsCanvas.SetActive(false);
        if (MobilePickUpScript.Instance != null) MobilePickUpScript.Instance.SetTeleportingState(true);
        GrannyAI granny = GetGrannyAI();
        NavMeshAgent mainAgent = granny != null ? granny.GetComponent<NavMeshAgent>() : null;
        if (mainAgent != null && mainAgent.isOnNavMesh) { mainAgent.isStopped = true; mainAgent.velocity = Vector3.zero; }

        if (currentHidingState == PlayerHidingState.UnderBed)
        {
            Play(bedJumpscareSound != null ? bedJumpscareSound : standardHitSound);
            float contact = bedHeadContactDuration > 0f ? bedHeadContactDuration : 1.2f;
            yield return BedHeadContactRoutine(contact);
            if (useBedDeathFadeTiming)
            {
                yield return new WaitForSeconds(Mathf.Max(0f, bedDeathFadeDelay - contact));
                fadeDurationOverride = bedDeathFadeDuration;
            }
            else yield return new WaitForSeconds(Mathf.Max(0f, bedKillAnimationDuration + delayAfterBedKill - contact));
            DropPlayerHeldItemAtCurrentPosition();
        }
        else
        {
            if ((currentHidingState == PlayerHidingState.InCoffin || hasPullOutPoint) && player != null)
            {
                if (hiding != null) hiding.ForceResetHidingState();
                var cc = player.GetComponent<CharacterController>();
                if (cc != null) cc.enabled = false;
                Vector3 p = hasPullOutPoint ? pullOutPoint : player.position;
                if (NavMesh.SamplePosition(p, out NavMeshHit hit, 2f, NavMesh.AllAreas)) p = hit.position + Vector3.up * (cc != null ? cc.height * 0.5f : 1f);
                player.position = p;
                if (granny != null)
                {
                    Vector3 d = granny.transform.position - p;
                    d.y = 0f;
                    if (d.sqrMagnitude > 0.01f) player.rotation = Quaternion.LookRotation(d);
                }
                if (cc != null) cc.enabled = true;
                Play(coffinJumpscareSound != null && currentHidingState == PlayerHidingState.InCoffin ? coffinJumpscareSound : standardHitSound);
            }
            else Play(standardHitSound);
            isHeadTracking = true;
            float forceAlignTime = 0f;
            while (forceAlignTime < delayBeforeFloorFall)
            {
                forceAlignTime += Time.deltaTime;
                yield return null;
            }
            isHeadTracking = false;
            DropPlayerHeldItemAtCurrentPosition();
            yield return NaturalFallToFloor();
        }

        if (DayManager.Instance != null)
        {
            if (fadeDurationOverride > 0f) DayManager.Instance.TriggerNextDayScreen(fadeDurationOverride);
            else DayManager.Instance.TriggerNextDayScreen();
        }
        currentHidingState = PlayerHidingState.None;
        hasPullOutPoint = false;
        running = false;
    }
}

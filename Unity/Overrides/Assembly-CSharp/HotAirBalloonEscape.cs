using System.Collections;
using UnityEngine;
using UnityEngine.AI;

/// <summary>
/// The hot air balloon escape in the garden: tape the rip, put the gas cylinder in the basket, light the burner with
/// the lighter (Granny vanishes while it inflates), and cut the anchor ropes with the chain cutter. Once it is inflated
/// it tries to take off: with the ropes cut it flies away (balloon ending); still tied down, the ropes hold it, it tears
/// and crashes - the balloon is wrecked, the player wakes up on the grass and Granny is back.
/// </summary>
public class HotAirBalloonEscape : MonoBehaviour
{
    [Header("Item Checklists")]
    public bool isRepairedWithTape;
    public bool hasGasCylinder;
    public bool isIgnitedWithLighter;
    public bool ropesCutWithChainCutter;

    [Header("Setup References")]
    public Animator balloonFabricAnimator;
    public ParticleSystem burnerFlameParticles;
    public GameObject burnerFlameEffect;
    public Transform player;

    [Header("Granny Management")]
    public GameObject grannyObject;
    public Transform grannyRespawnPoint;

    [Header("UI & Fade Cutscene Settings")]
    public Animator screenFadeAnimator;
    public GameObject gameplayUI;

    [Header("Inflation Settings")]
    public float inflationDuration;

    [Header("Setup References")]
    public GameObject basketCylinderVisual;

    [Header("Normal Flight Settings")]
    public string escapeSceneName;
    public string mainMenuSceneName;
    public float riseSpeed;
    public float forwardSpeed;
    public float escapeDuration;

    [Header("Rope Visual Link")]
    public GameObject dynamicRopeObject;

    [Header("Crash Sequence Settings")]
    public GameObject crashCutsceneCamera;
    public string fabricCrashAnimationState;
    public float crashRiseHeight;
    public float riseDuration;
    public float fallDuration;
    public GameObject explosionParticles;
    public GameObject ruinedSmokeParticles;
    public GameObject balloonVisualMesh;
    public GameObject crashedBalloonVisualMesh;
    public Transform wakeUpPoint;
    public AudioClip crashSound;

    private AudioSource audioSource;
    private bool isWorkingAndInflated;
    private bool sequenceStarted;
    private bool isDestroyed;
    private GameObject mainPlayerCameraObject;
    private bool inflating;

    private void Start()
    {
        audioSource = GetComponent<AudioSource>();
        if (audioSource == null) { audioSource = gameObject.AddComponent<AudioSource>(); audioSource.spatialBlend = 1f; audioSource.playOnAwake = false; }
        if (player == null) { GameObject p = GameSave.PlayerObject(); if (p != null) player = p.transform; }
        if (player != null) { Camera c = player.GetComponentInChildren<Camera>(true); if (c != null) mainPlayerCameraObject = c.gameObject; }
        if (basketCylinderVisual != null) basketCylinderVisual.SetActive(hasGasCylinder);
        if (burnerFlameEffect != null) burnerFlameEffect.SetActive(false);
        if (burnerFlameParticles != null) burnerFlameParticles.Stop();
        if (crashCutsceneCamera != null) crashCutsceneCamera.SetActive(false);
        if (crashedBalloonVisualMesh != null) crashedBalloonVisualMesh.SetActive(false);
        if (ruinedSmokeParticles != null) ruinedSmokeParticles.SetActive(false);
        if (explosionParticles != null) explosionParticles.SetActive(false);
    }

    public bool IsDestroyed()
    {
        return isDestroyed;
    }

    public void UseTape()
    {
        if (isDestroyed || isRepairedWithTape) return;
        isRepairedWithTape = true;
        Debug.Log("Balloon holes repaired with tape!");
    }

    public void InsertCylinder()
    {
        if (isDestroyed || hasGasCylinder) return;
        hasGasCylinder = true;
        if (basketCylinderVisual != null) basketCylinderVisual.SetActive(true);
        Debug.Log("Gas cylinder installed in the burner basket layout!");
    }

    public void UseLighter()
    {
        if (isDestroyed || isIgnitedWithLighter) return;
        if (!isRepairedWithTape) { DimnightUtil.Notify("I need Duct Tape to fix this rip"); return; }
        if (!hasGasCylinder) { DimnightUtil.Notify("I need a Gas Cylinder!"); return; }
        isIgnitedWithLighter = true;
        if (burnerFlameEffect != null) burnerFlameEffect.SetActive(true);
        if (burnerFlameParticles != null) { burnerFlameParticles.gameObject.SetActive(true); burnerFlameParticles.Play(); }
        DisappearGranny();
        StartCoroutine(InflateBalloonRoutine());
    }

    private void DisappearGranny()
    {
        if (grannyObject == null && GrannyAI.Instance != null) grannyObject = GrannyAI.Instance.gameObject;
        if (grannyObject != null) grannyObject.SetActive(false);
        Debug.Log("Granny vanished on balloon ignition!");
    }

    public void CutRopes()
    {
        if (isDestroyed || ropesCutWithChainCutter) return;
        ropesCutWithChainCutter = true;
        if (dynamicRopeObject != null) dynamicRopeObject.SetActive(false);
        Debug.Log("Anchor ropes cleanly cut with the chain cutter!");
        if (isWorkingAndInflated) TriggerLaunchAttempt();
    }

    private IEnumerator InflateBalloonRoutine()
    {
        inflating = true;
        DimnightUtil.FireAny(balloonFabricAnimator, "Inflate", "inflate", "Inflated");
        yield return new WaitForSeconds(inflationDuration > 0f ? inflationDuration : 8f);
        inflating = false;
        isWorkingAndInflated = true;
        TriggerLaunchAttempt();
    }

    public void TriggerLaunchAttempt()
    {
        if (isDestroyed || sequenceStarted) return;
        if (!isRepairedWithTape) { DimnightUtil.Notify("I need Duct Tape to fix this rip"); return; }
        if (!hasGasCylinder) { DimnightUtil.Notify("I need a Gas Cylinder!"); return; }
        if (!isIgnitedWithLighter) { DimnightUtil.Notify("I need to light the gas cylinder"); return; }
        if (inflating || !isWorkingAndInflated) return;
        sequenceStarted = true;
        enabled = false;
        if (ropesCutWithChainCutter) StartCoroutine(NormalEscapeRoutine());
        else StartCoroutine(RopeCrashRoutine());
    }

    private IEnumerator NormalEscapeRoutine()
    {
        if (gameplayUI != null) gameplayUI.SetActive(false);
        LockPlayerToBasket();
        DimnightUtil.FireAny(balloonFabricAnimator, "FlyAway", "Fly");
        float timer = 0f;
        float duration = escapeDuration > 0f ? escapeDuration : 8f;
        bool faded = false;
        while (timer < duration)
        {
            timer += Time.deltaTime;
            float ease = Mathf.Clamp01(timer / 1.5f);
            transform.position += (Vector3.up * riseSpeed + transform.forward * forwardSpeed * Mathf.Clamp01(timer / 3f)) * ease * Time.deltaTime;
            if (!faded && timer > duration - 1.5f) { faded = true; DimnightUtil.FadeToBlack(screenFadeAnimator); }
            yield return null;
        }
        DimnightUtil.LoadScene(escapeSceneName, "Scene_BalloonEscape");
    }

    private IEnumerator RopeCrashRoutine()
    {
        if (gameplayUI != null) gameplayUI.SetActive(false);
        LockPlayerToBasket();
        if (crashCutsceneCamera != null)
        {
            crashCutsceneCamera.SetActive(true);
            if (mainPlayerCameraObject != null) mainPlayerCameraObject.SetActive(false);
        }
        Vector3 startPos = transform.position;
        Vector3 peakPos = startPos + Vector3.up * (crashRiseHeight > 0f ? crashRiseHeight : 4f);
        float elapsed = 0f;
        float rise = riseDuration > 0f ? riseDuration : 7f;
        while (elapsed < rise)
        {
            elapsed += Time.deltaTime;
            float k = Mathf.SmoothStep(0f, 1f, elapsed / rise);
            transform.position = Vector3.Lerp(startPos, peakPos, k) + new Vector3(Mathf.Sin(elapsed * 9f), 0f, Mathf.Cos(elapsed * 7f)) * 0.05f * k;
            yield return null;
        }
        // the ropes hold it down: the fabric tears and it drops
        if (dynamicRopeObject != null) dynamicRopeObject.SetActive(false);
        if (!string.IsNullOrEmpty(fabricCrashAnimationState)) DimnightUtil.Fire(balloonFabricAnimator, fabricCrashAnimationState);
        if (burnerFlameEffect != null) burnerFlameEffect.SetActive(false);
        if (burnerFlameParticles != null) burnerFlameParticles.Stop();
        Vector3 crashAirPos = transform.position;
        Vector3 groundTarget = startPos;
        Quaternion initialRot = transform.rotation;
        Quaternion crashRotTarget = initialRot * Quaternion.Euler(18f, 0f, 12f);
        elapsed = 0f;
        float fall = fallDuration > 0f ? fallDuration : 1f;
        while (elapsed < fall)
        {
            elapsed += Time.deltaTime;
            float k = Mathf.Clamp01(elapsed / fall);
            transform.position = Vector3.Lerp(crashAirPos, groundTarget, k * k);
            transform.rotation = Quaternion.Slerp(initialRot, crashRotTarget, k);
            yield return null;
        }
        transform.position = groundTarget;
        if (crashSound != null) audioSource.PlayOneShot(crashSound);
        if (explosionParticles != null) explosionParticles.SetActive(true);
        DimnightUtil.FadeToBlack(screenFadeAnimator);
        yield return new WaitForSeconds(1.5f);

        isDestroyed = true;
        if (balloonVisualMesh != null) balloonVisualMesh.SetActive(false);
        if (crashedBalloonVisualMesh != null) crashedBalloonVisualMesh.SetActive(true);
        if (ruinedSmokeParticles != null) ruinedSmokeParticles.SetActive(true);
        if (basketCylinderVisual != null) basketCylinderVisual.SetActive(false);
        foreach (BalloonHoleZone z in GetComponentsInChildren<BalloonHoleZone>(true)) z.enabled = false;
        foreach (BalloonCylinderSlot z in GetComponentsInChildren<BalloonCylinderSlot>(true)) z.enabled = false;
        foreach (BalloonBurnerZone z in GetComponentsInChildren<BalloonBurnerZone>(true)) z.enabled = false;
        foreach (RopeAnchorInteraction a in FindObjectsByType<RopeAnchorInteraction>(FindObjectsSortMode.None)) a.enabled = false;

        // wake up on the grass
        if (player != null)
        {
            player.SetParent(null, true);
            CharacterController cc = player.GetComponent<CharacterController>();
            if (cc != null) cc.enabled = false;
            if (wakeUpPoint != null) player.SetPositionAndRotation(wakeUpPoint.position, Quaternion.Euler(0f, wakeUpPoint.eulerAngles.y, 0f));
            if (cc != null) cc.enabled = true;
            FPSController fps = player.GetComponent<FPSController>();
            if (fps != null) fps.enabled = true;
            MobileCrouchController crouch = player.GetComponent<MobileCrouchController>();
            if (crouch != null) crouch.SetInputLocked(false);
        }
        if (crashCutsceneCamera != null) crashCutsceneCamera.SetActive(false);
        if (mainPlayerCameraObject != null) mainPlayerCameraObject.SetActive(true);
        if (MobilePickUpScript.Instance != null) MobilePickUpScript.Instance.SetTeleportingState(false);
        RespawnGrannyAfterCrash();
        yield return new WaitForSeconds(0.5f);
        DimnightUtil.FadeToClear(screenFadeAnimator);
        if (gameplayUI != null) gameplayUI.SetActive(true);
    }

    private void RespawnGrannyAfterCrash()
    {
        if (grannyObject == null) return;
        if (grannyRespawnPoint != null)
        {
            NavMeshAgent agent = grannyObject.GetComponent<NavMeshAgent>();
            Vector3 p = grannyRespawnPoint.position;
            if (NavMesh.SamplePosition(p, out NavMeshHit hit, 3f, NavMesh.AllAreas)) p = hit.position;
            if (agent != null) agent.enabled = false;
            grannyObject.transform.SetPositionAndRotation(p, grannyRespawnPoint.rotation);
            if (agent != null) agent.enabled = true;
        }
        grannyObject.SetActive(true);
        Debug.Log("Granny respawned after crash!");
    }

    private void LockPlayerToBasket()
    {
        if (player == null) return;
        if (MobilePickUpScript.Instance != null) MobilePickUpScript.Instance.SetTeleportingState(true);
        FPSController fps = player.GetComponent<FPSController>();
        if (fps != null) fps.enabled = false;
        MobileCrouchController crouch = player.GetComponent<MobileCrouchController>();
        if (crouch != null) crouch.SetInputLocked(true);
        CharacterController cc = player.GetComponent<CharacterController>();
        if (cc != null) cc.enabled = false;
        Transform basket = basketCylinderVisual != null ? basketCylinderVisual.transform.parent : null;
        Vector3 center = basket != null ? basket.position : transform.position;
        Vector3 flat = player.position - center;
        flat.y = 0f;
        if (flat.magnitude > 0.6f) player.position = new Vector3(center.x, player.position.y, center.z) + flat.normalized * 0.4f;
        player.SetParent(transform, true);
    }
}

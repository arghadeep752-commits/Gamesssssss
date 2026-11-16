using System.Collections;
using UnityEngine;

/// <summary>
/// The main-door locks: the wooden plank (Hammer), the code padlock (Padlock Code), the padlock (Padlock Key), the chain
/// (Chain Cutter), the secret bookshelf slot (Secret Book) and the master key door. The master key opens the door only
/// when every lock that is on the door in this mode is gone, then the escape cutscene plays.
/// </summary>
public class EscapeLockElement : MonoBehaviour
{
    [Header("Lock Configuration")]
    public EscapeLockType lockType;
    public string requiredItemName;
    public string missingItemAlertText;
    public bool isUnlocked;
    public bool requiredForEscape;

    [Header("Audio")]
    public AudioSource audioSource;
    public AudioClip interactionSound;

    [Header("Chain Cut Visual Toggles")]
    public GameObject tightChainsGroup;
    public GameObject looseChainsGroup;

    [Header("Secret Bookshelf Settings")]
    public Vector3 bookshelfSlideOffset;
    public float bookshelfSlideSpeed;

    [Header("Master Key Win Condition Scene")]
    public string winSceneName;

    [Header("Fall To Floor When Unlocked (Plank / Padlocks / Chain lock)")]
    public bool fallOnUnlock;
    public float popOffForce;
    public bool alertGrannyOnLand;
    public AudioClip landSound;
    public float landSoundVolume;
    public float minImpactSpeed;
    public string fallenLayerName;

    private bool isFalling;
    private bool hasLanded;
    private float fallStartTime;
    private static bool plankCleared;
    private static bool codeCleared;
    private static bool padlockCleared;
    private static bool chainCleared;
    private static bool bookshelfCleared;

    [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)]
    private static void ResetStaticStates()
    {
        plankCleared = codeCleared = padlockCleared = chainCleared = bookshelfCleared = false;
    }

    private void Awake()
    {
        // a new game in the same session starts with every lock back on the door
        if (lockType == EscapeLockType.MasterKeyDoor) ResetStaticStates();
    }

    private static bool IsDoorLock(EscapeLockType t)
    {
        return t == EscapeLockType.WoodenPlank || t == EscapeLockType.PadlockCode || t == EscapeLockType.PadlockKey || t == EscapeLockType.Chain;
    }

    private static bool TypeCleared(EscapeLockType t)
    {
        switch (t)
        {
            case EscapeLockType.WoodenPlank: return plankCleared;
            case EscapeLockType.PadlockCode: return codeCleared;
            case EscapeLockType.PadlockKey: return padlockCleared;
            case EscapeLockType.Chain: return chainCleared;
            case EscapeLockType.SecretBookshelf: return bookshelfCleared;
        }
        return false;
    }

    private static void SetCleared(EscapeLockType t)
    {
        switch (t)
        {
            case EscapeLockType.WoodenPlank: plankCleared = true; break;
            case EscapeLockType.PadlockCode: codeCleared = true; break;
            case EscapeLockType.PadlockKey: padlockCleared = true; break;
            case EscapeLockType.Chain: chainCleared = true; break;
            case EscapeLockType.SecretBookshelf: bookshelfCleared = true; break;
        }
    }

    public bool IsEffectivelyUnlocked()
    {
        return isUnlocked || TypeCleared(lockType);
    }

    private bool BlocksEscape()
    {
        // locks switched off in this mode (e.g. Extra Locks off) are inactive and never block the door
        return requiredForEscape && IsDoorLock(lockType) && gameObject.activeInHierarchy && !IsEffectivelyUnlocked();
    }

    public static bool AreAllDoorLocksCleared()
    {
        return CountLockedDoorLocks() == 0;
    }

    public static int CountLockedDoorLocks()
    {
        int n = 0;
        foreach (EscapeLockElement e in FindObjectsByType<EscapeLockElement>(FindObjectsInactive.Include, FindObjectsSortMode.None))
            if (e.BlocksEscape()) n++;
        return n;
    }

    public static void LogLockedDoorLocks()
    {
        foreach (EscapeLockElement e in FindObjectsByType<EscapeLockElement>(FindObjectsInactive.Include, FindObjectsSortMode.None))
            if (e.BlocksEscape()) Debug.Log("[EscapeSystem] STILL LOCKED: '" + GetPath(e.transform) + "' (Lock Type: " + e.lockType + ")");
    }

    private static string GetPath(Transform t)
    {
        string p = t.name;
        while (t.parent != null) { t = t.parent; p = t.name + "/" + p; }
        return p;
    }

    public static bool SceneHasDoorLocks()
    {
        foreach (EscapeLockElement e in FindObjectsByType<EscapeLockElement>(FindObjectsInactive.Include, FindObjectsSortMode.None))
            if (IsDoorLock(e.lockType) || e.lockType == EscapeLockType.MasterKeyDoor) return true;
        return false;
    }

    public void InteractWithLock(string itemInHand)
    {
        if (isUnlocked) return;
        MobilePickUpScript pickup = MobilePickUpScript.Instance;
        if (!GameSave.SameItem(itemInHand, requiredItemName))
        {
            string msg = missingItemAlertText;
            if (string.IsNullOrEmpty(msg)) msg = lockType == EscapeLockType.MasterKeyDoor ? "I need the Master Key." : "Door Cannot Be Opened Yet";
            DimnightUtil.Notify(msg);
            return;
        }
        if (lockType == EscapeLockType.MasterKeyDoor)
        {
            CheckFinalEscapeState(pickup);
            return;
        }

        isUnlocked = true;
        SetCleared(lockType);
        PlayLockSound();
        if (lockType == EscapeLockType.PadlockKey || lockType == EscapeLockType.PadlockCode || lockType == EscapeLockType.SecretBookshelf)
            if (pickup != null) pickup.ConsumeHeldItem();

        switch (lockType)
        {
            case EscapeLockType.SecretBookshelf:
                if (looseChainsGroup != null) looseChainsGroup.SetActive(true);
                enabled = false;
                if (GetComponent<SecretBookshelfDoor>() == null && bookshelfSlideOffset != Vector3.zero) StartCoroutine(SlideBookshelfRoutine());
                break;
            case EscapeLockType.Chain:
                if (tightChainsGroup != null && tightChainsGroup != gameObject && !transform.IsChildOf(tightChainsGroup.transform)) tightChainsGroup.SetActive(false);
                if (looseChainsGroup != null) looseChainsGroup.SetActive(true);
                if (fallOnUnlock) ActivateFallingPhysics();
                else gameObject.SetActive(false);
                break;
            default:
                if (fallOnUnlock) ActivateFallingPhysics();
                else gameObject.SetActive(false);
                break;
        }
    }

    private void ActivateFallingPhysics()
    {
        enabled = false;  // no more hand button on it
        DropToFloor();
    }

    private void DropToFloor()
    {
        isFalling = true;
        hasLanded = false;
        fallStartTime = Time.time;
        transform.SetParent(null, true);
        foreach (Collider c in GetComponentsInChildren<Collider>()) c.isTrigger = false;
        Rigidbody rb = GetComponent<Rigidbody>();
        if (rb == null) rb = gameObject.AddComponent<Rigidbody>();
        rb.isKinematic = false;
        rb.useGravity = true;
        rb.interpolation = RigidbodyInterpolation.Interpolate;
        rb.collisionDetectionMode = CollisionDetectionMode.ContinuousDynamic;
        Vector3 push = Vector3.zero;
        GameObject player = GameSave.PlayerObject();
        if (player != null) { push = player.transform.position - transform.position; push.y = 0f; }
        if (push.sqrMagnitude > 0.001f) rb.AddForce(push.normalized * (popOffForce > 0f ? popOffForce : 1.2f), ForceMode.Impulse);
        CutObjectPhysics cut = GetComponent<CutObjectPhysics>();
        if (cut != null && player != null) cut.TriggerSidewaysFall(player.transform.position);
        if (!string.IsNullOrEmpty(fallenLayerName))
        {
            int layer = LayerMask.NameToLayer(fallenLayerName);
            if (layer >= 0) SetLayerRecursively(transform, layer);
        }
        StartCoroutine(LandFallbackRoutine());
    }

    private void OnCollisionEnter(Collision collision)
    {
        if (!isFalling || hasLanded || Time.time - fallStartTime < 0.1f) return;
        if (collision.collider.GetComponentInParent<CharacterController>() != null) return;
        if (collision.relativeVelocity.magnitude < (minImpactSpeed > 0f ? minImpactSpeed : 0.5f)) return;
        OnLanded(collision.contactCount > 0 ? collision.GetContact(0).point : transform.position);
    }

    private IEnumerator LandFallbackRoutine()
    {
        yield return new WaitForSeconds(3f);
        if (!hasLanded) OnLanded(transform.position);
    }

    private void OnLanded(Vector3 point)
    {
        hasLanded = true;
        isFalling = false;
        if (landSound != null) DimnightUtil.PlayAt(landSound, point, landSoundVolume > 0f ? landSoundVolume : 1f);
        if (alertGrannyOnLand && !GameSave.IsPractice && !SilentGroundZone.IsSilentAt(point))
            GrannyAI.AlertAll(point, name + " hit the floor");
    }

    private void SetLayerRecursively(Transform t, int layer)
    {
        t.gameObject.layer = layer;
        foreach (Transform c in t) SetLayerRecursively(c, layer);
    }

    private IEnumerator SlideBookshelfRoutine()
    {
        Vector3 startPos = transform.position;
        Vector3 targetPos = startPos + transform.TransformDirection(bookshelfSlideOffset);
        float elapsedTime = 0f;
        float duration = Mathf.Max(0.1f, bookshelfSlideOffset.magnitude / Mathf.Max(0.01f, bookshelfSlideSpeed));
        while (elapsedTime < duration)
        {
            elapsedTime += Time.deltaTime;
            transform.position = Vector3.Lerp(startPos, targetPos, Mathf.SmoothStep(0f, 1f, elapsedTime / duration));
            yield return null;
        }
        transform.position = targetPos;
    }

    private void CheckFinalEscapeState(MobilePickUpScript mobilePickup)
    {
        if (!AreAllDoorLocksCleared())
        {
            LogLockedDoorLocks();
            Debug.Log("[ESCAPE] Master Key picked up. Open all the locks, then use it on the main door.");
            DimnightUtil.Notify("The door is still held by other locks!");
            return;
        }
        isUnlocked = true;
        enabled = false;
        PlayLockSound();
        Debug.Log("[ESCAPE] Master Key picked up and every lock is open! Loading cutscene...");
        if (mobilePickup != null) mobilePickup.SetTeleportingState(true);
        StartCoroutine(LoadWinScene());
    }

    private IEnumerator LoadWinScene()
    {
        DoorInteractable door = GetComponentInParent<DoorInteractable>();
        if (door != null) door.SetOpen(true, true);
        yield return new WaitForSeconds(1f);
        DimnightUtil.LoadScene(winSceneName, "EscapeCutScene");
    }

    private void PlayLockSound()
    {
        if (interactionSound == null) return;
        if (audioSource != null && audioSource.isActiveAndEnabled) audioSource.PlayOneShot(interactionSound);
        else DimnightUtil.PlayAt(interactionSound, transform.position);
    }
}

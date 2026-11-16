using System.Collections;
using UnityEngine;
using UnityEngine.AI;

/// <summary>
/// A hinged door or cupboard door: tap to open / close. A locked one (Gold Key, Car Key, Padlock Key, Master Key)
/// rattles and says what it needs, and opens with the right key in hand (the key stays in the lock).
/// Granny opens doors in her way with OpenForGranny().
/// </summary>
[RequireComponent(typeof(AudioSource))]
public class DoorInteractable : MonoBehaviour, IInteractable
{
    public enum LockType
    {
        None = 0,
        PadlockKey = 1,
        MasterKey = 2,
        GoldKey = 3,
        CarKey = 4
    }

    [Header("Door Movement Settings")]
    public float openAngle;
    public float doorSpeed;

    [Header("Lock Settings")]
    public LockType requiredLock;
    public string lockedNotificationText;

    [Header("Locked Door Rattle")]
    public float lockedRattleAngle;
    public float lockedRattleDuration;
    public int lockedRattleCount;

    [Header("Audio & Effects")]
    public AudioClip openSound;
    public AudioClip closeSound;
    public AudioClip lockedSound;

    [HideInInspector]
    public bool isOpen;

    private bool isMoving;
    private bool isShaking;
    private NavMeshObstacle navMeshObstacle;
    private AudioSource myAudioSource;
    private Collider doorCollider;
    private Quaternion closedRotation;
    private Quaternion openRotation;
    private Quaternion targetRotation;
    private bool initialised;

    public bool IsLocked => requiredLock != LockType.None;
    public bool IsMoving => isMoving;

    protected virtual void Start()
    {
        Init();
    }

    protected void Init()
    {
        if (initialised) return;
        initialised = true;
        myAudioSource = GetComponent<AudioSource>();
        if (myAudioSource != null) { myAudioSource.playOnAwake = false; if (myAudioSource.spatialBlend == 0f) myAudioSource.spatialBlend = 1f; }
        navMeshObstacle = GetComponentInChildren<NavMeshObstacle>();
        doorCollider = GetComponentInChildren<Collider>();
        if (openAngle == 0f) openAngle = 90f;
        if (doorSpeed <= 0f) doorSpeed = 5f;
        closedRotation = transform.localRotation;
        openRotation = closedRotation * Quaternion.Euler(0f, openAngle, 0f);
        if (isOpen)
        {
            // the scene was saved closed; "isOpen" only marks a door that starts open
            transform.localRotation = openRotation;
        }
        targetRotation = isOpen ? openRotation : closedRotation;
        UpdateObstacle();
    }

    protected virtual void Update()
    {
        if (isShaking) return;
        if (Quaternion.Angle(transform.localRotation, targetRotation) > 0.1f)
        {
            isMoving = true;
            transform.localRotation = Quaternion.RotateTowards(transform.localRotation, targetRotation, doorSpeed * 30f * Time.deltaTime);
        }
        else if (isMoving)
        {
            transform.localRotation = targetRotation;
            isMoving = false;
        }
    }

    public static string KeyName(LockType lockType)
    {
        switch (lockType)
        {
            case LockType.PadlockKey: return "Padlock Key";
            case LockType.MasterKey: return "Master Key";
            case LockType.GoldKey: return "Gold Key";
            case LockType.CarKey: return "Car Key";
            default: return "";
        }
    }

    public void Interact(string heldItemName)
    {
        Init();
        if (isShaking) return;
        if (requiredLock != LockType.None)
        {
            if (GameSave.SameItem(heldItemName, KeyName(requiredLock)))
            {
                requiredLock = LockType.None;
                if (MobilePickUpScript.Instance != null) MobilePickUpScript.Instance.ConsumeHeldItem();
            }
            else
            {
                TriggerLockedBehavior();
                return;
            }
        }
        SetOpen(!isOpen, true);
    }

    public void SetOpen(bool open, bool withSound)
    {
        Init();
        isOpen = open;
        targetRotation = isOpen ? openRotation : closedRotation;
        if (withSound && myAudioSource != null)
        {
            AudioClip clip = isOpen ? openSound : closeSound;
            if (clip != null) myAudioSource.PlayOneShot(clip);
        }
        UpdateObstacle();
    }

    /// <summary>Granny opens a closed door in her way (locked doors only if she is allowed to).</summary>
    public bool OpenForGranny(bool canOpenLocked)
    {
        Init();
        if (isOpen) return true;
        if (requiredLock != LockType.None && !canOpenLocked) return false;
        SetOpen(true, true);
        return true;
    }

    private void UpdateObstacle()
    {
        // an open door leaf is something to walk around; a closed one Granny opens herself
        if (navMeshObstacle != null) navMeshObstacle.enabled = isOpen;
    }

    private void TriggerLockedBehavior()
    {
        if (myAudioSource != null && lockedSound != null) myAudioSource.PlayOneShot(lockedSound);
        string msg = string.IsNullOrEmpty(lockedNotificationText) ? "It's locked." : lockedNotificationText;
        if (MobilePickUpScript.Instance != null) MobilePickUpScript.Instance.ShowLockedNotification(msg);
        if (!isMoving) StartCoroutine(ShakeDoorRoutine());
    }

    private IEnumerator ShakeDoorRoutine()
    {
        isShaking = true;
        Quaternion originalLocalRotation = transform.localRotation;
        float direction = Mathf.Sign(openAngle);
        int pushes = Mathf.Max(1, lockedRattleCount);
        float total = lockedRattleDuration > 0f ? lockedRattleDuration : 0.35f;
        float angle = lockedRattleAngle > 0f ? lockedRattleAngle : 2.5f;
        float elapsed = 0f;
        while (elapsed < total)
        {
            elapsed += Time.deltaTime;
            float phase = elapsed / total * pushes * Mathf.PI;
            float a = Mathf.Abs(Mathf.Sin(phase)) * angle * direction;
            transform.localRotation = originalLocalRotation * Quaternion.Euler(0f, a, 0f);
            yield return null;
        }
        transform.localRotation = originalLocalRotation;
        isShaking = false;
    }
}

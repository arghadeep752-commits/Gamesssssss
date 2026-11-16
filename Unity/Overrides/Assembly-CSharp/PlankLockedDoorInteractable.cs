using System.Collections;
using UnityEngine;
using UnityEngine.AI;

/// <summary>A door blocked by a plank on the other side: it won't open until the plank is knocked off from there.</summary>
public class PlankLockedDoorInteractable : MonoBehaviour, IInteractable
{
    public enum LockType
    {
        None = 0,
        PadlockKey = 1,
        MasterKey = 2,
        GoldKey = 3
    }

    [Header("Door Movement Settings")]
    public float openAngle;
    public float doorSpeed;

    [Header("Lock Settings")]
    public LockType requiredLock;
    public string lockedNotificationText;

    [Header("Audio & Effects")]
    public AudioClip openSound;
    public AudioClip closeSound;
    public AudioClip lockedSound;

    [Header("Plank Blocker Reference")]
    public DoorPlankComponent blockingPlank;

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

    public bool IsBlocked => (blockingPlank != null && !blockingPlank.IsRemoved()) || requiredLock != LockType.None;

    private void Start()
    {
        myAudioSource = GetComponent<AudioSource>();
        if (myAudioSource == null) { myAudioSource = gameObject.AddComponent<AudioSource>(); myAudioSource.spatialBlend = 1f; }
        navMeshObstacle = GetComponentInChildren<NavMeshObstacle>();
        doorCollider = GetComponentInChildren<Collider>();
        if (blockingPlank == null) blockingPlank = GetComponentInChildren<DoorPlankComponent>();
        if (openAngle == 0f) openAngle = 90f;
        if (doorSpeed <= 0f) doorSpeed = 5f;
        closedRotation = transform.localRotation;
        openRotation = closedRotation * Quaternion.Euler(0f, openAngle, 0f);
        targetRotation = closedRotation;
        if (navMeshObstacle != null) navMeshObstacle.enabled = false;
    }

    private void Update()
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

    public void Interact(string heldItemName)
    {
        if (isShaking) return;
        if (blockingPlank != null && !blockingPlank.IsRemoved())
        {
            TriggerLockedBehavior();
            return;
        }
        if (requiredLock != LockType.None)
        {
            string need = requiredLock == LockType.PadlockKey ? "Padlock Key" : requiredLock == LockType.MasterKey ? "Master Key" : "Gold Key";
            if (!GameSave.SameItem(heldItemName, need)) { TriggerLockedBehavior(); return; }
            requiredLock = LockType.None;
            if (MobilePickUpScript.Instance != null) MobilePickUpScript.Instance.ConsumeHeldItem();
        }
        OpenOrClose(!isOpen);
    }

    public void OpenOrClose(bool open)
    {
        isOpen = open;
        targetRotation = isOpen ? openRotation : closedRotation;
        AudioClip clip = isOpen ? openSound : closeSound;
        if (clip != null && myAudioSource != null) myAudioSource.PlayOneShot(clip);
        if (navMeshObstacle != null) navMeshObstacle.enabled = isOpen;
    }

    private void TriggerLockedBehavior()
    {
        if (lockedSound != null && myAudioSource != null) myAudioSource.PlayOneShot(lockedSound);
        string msg = string.IsNullOrEmpty(lockedNotificationText) ? "It won't open." : lockedNotificationText;
        if (MobilePickUpScript.Instance != null) MobilePickUpScript.Instance.ShowLockedNotification(msg);
        if (!isMoving) StartCoroutine(ShakeDoorRoutine());
    }

    private IEnumerator ShakeDoorRoutine()
    {
        isShaking = true;
        Quaternion originalLocalRotation = transform.localRotation;
        float elapsed = 0f;
        while (elapsed < 0.35f)
        {
            elapsed += Time.deltaTime;
            float a = Mathf.Abs(Mathf.Sin(elapsed / 0.35f * 2f * Mathf.PI)) * 2.5f * Mathf.Sign(openAngle);
            transform.localRotation = originalLocalRotation * Quaternion.Euler(0f, a, 0f);
            yield return null;
        }
        transform.localRotation = originalLocalRotation;
        isShaking = false;
    }
}

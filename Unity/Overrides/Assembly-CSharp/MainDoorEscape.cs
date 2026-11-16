using UnityEngine;

/// <summary>
/// The main door's old lock system (tick boxes). The door's EscapeLockElement locks are used when the scene has them;
/// this is only the fallback for a door that has none.
/// </summary>
public class MainDoorEscape : MonoBehaviour
{
    [Header("Lock States (old lock system - DoorLockComponent)")]
    public bool isPlankBroken;
    public bool isPadlockUnlocked;
    public bool isPadlockCodeCleared;
    public bool isChainCut;

    [Header("References")]
    public string escapeSceneName;
    public AudioSource doorAudioSource;
    public AudioClip doorRattleSound;

    [Header("Master Key Check")]
    public string masterKeyItemName;

    private bool escaping;

    public void TryMasterKeyEscape()
    {
        if (escaping) return;
        MobilePickUpScript pickup = MobilePickUpScript.Instance;
        if (EscapeLockElement.SceneHasDoorLocks())
        {
            // the new lock system decides: hand the held item to the master key lock
            foreach (EscapeLockElement e in FindObjectsByType<EscapeLockElement>(FindObjectsSortMode.None))
                if (e.lockType == EscapeLockType.MasterKeyDoor && !e.isUnlocked)
                {
                    e.InteractWithLock(pickup != null ? pickup.GetHeldItemName() : "");
                    return;
                }
            return;
        }
        if (!IsHoldingMasterKey(pickup))
        {
            PlayRattle();
            DimnightUtil.Notify("I need the Master Key.");
            return;
        }
        if (!AllLocksCleared())
        {
            Debug.Log("[MainDoorEscape] Old lock tick boxes: Plank " + isPlankBroken + ", Padlock " + isPadlockUnlocked + ", Code " + isPadlockCodeCleared + ", Chain " + isChainCut);
            PlayRattle();
            DimnightUtil.Notify("The door is still held by other locks!");
            return;
        }
        TriggerEscapeSequence();
    }

    private bool AllLocksCleared()
    {
        return isPlankBroken && isPadlockUnlocked && isPadlockCodeCleared && isChainCut;
    }

    private bool IsHoldingMasterKey(MobilePickUpScript pickup)
    {
        if (pickup == null) return false;
        string held = Clean(pickup.GetHeldItemName());
        return held.Length > 0 && (held == Clean(masterKeyItemName) || held == Clean("Master Key"));
    }

    private static string Clean(string s)
    {
        return GameSave.Clean(s);
    }

    private void PlayRattle()
    {
        if (doorRattleSound == null) return;
        if (doorAudioSource != null) doorAudioSource.PlayOneShot(doorRattleSound);
        else DimnightUtil.PlayAt(doorRattleSound, transform.position);
    }

    private void TriggerEscapeSequence()
    {
        escaping = true;
        if (MobilePickUpScript.Instance != null) MobilePickUpScript.Instance.SetTeleportingState(true);
        DimnightUtil.LoadScene(escapeSceneName, "EscapeCutScene");
    }
}

using UnityEngine;

/// <summary>
/// A room Granny walks to on her rounds. A waypoint locked by default (a locked bedroom, the secret room behind the
/// bookshelf) is skipped until it is unlocked - by UnlockWaypoint(), or automatically by GrannyAI once she can
/// reach it without passing a locked door.
/// </summary>
public class GrannyPatrolWaypoint : MonoBehaviour
{
    [Header("Progression Settings")]
    public bool isLockedByDefault;

    [HideInInspector]
    public bool isUnlocked;

    private void Awake()
    {
        isUnlocked = !isLockedByDefault;
    }

    public void UnlockWaypoint()
    {
        isUnlocked = true;
    }
}

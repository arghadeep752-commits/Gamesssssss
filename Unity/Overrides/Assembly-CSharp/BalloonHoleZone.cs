using UnityEngine;

/// <summary>The rip in the balloon fabric: fixed with duct tape.</summary>
public class BalloonHoleZone : MonoBehaviour
{
    public HotAirBalloonEscape mainBalloonScript;

    [Header("Audio Settings")]
    public AudioClip repairSound;

    public void FixHoleWithTape()
    {
        if (mainBalloonScript == null) mainBalloonScript = GetComponentInParent<HotAirBalloonEscape>();
        if (mainBalloonScript == null || mainBalloonScript.IsDestroyed() || mainBalloonScript.isRepairedWithTape) return;
        if (repairSound != null) DimnightUtil.PlayAt(repairSound, transform.position);
        if (MobilePickUpScript.Instance != null) MobilePickUpScript.Instance.ConsumeHeldItem();
        mainBalloonScript.UseTape();
        enabled = false;
    }
}

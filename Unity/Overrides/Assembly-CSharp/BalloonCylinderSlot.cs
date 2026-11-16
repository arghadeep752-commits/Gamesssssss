using UnityEngine;

/// <summary>The burner slot in the balloon basket: the gas cylinder goes here.</summary>
public class BalloonCylinderSlot : MonoBehaviour
{
    public HotAirBalloonEscape mainBalloonScript;

    public void InsertCylinderFromPlayer()
    {
        if (mainBalloonScript == null) mainBalloonScript = GetComponentInParent<HotAirBalloonEscape>();
        if (mainBalloonScript == null || mainBalloonScript.IsDestroyed() || mainBalloonScript.hasGasCylinder) return;
        if (MobilePickUpScript.Instance != null) MobilePickUpScript.Instance.ConsumeHeldItem();
        mainBalloonScript.InsertCylinder();
        enabled = false;
    }
}

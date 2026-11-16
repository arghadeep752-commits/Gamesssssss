using UnityEngine;

/// <summary>The gas burner: lit with the lighter once the cylinder is in.</summary>
public class BalloonBurnerZone : MonoBehaviour
{
    public HotAirBalloonEscape mainBalloonScript;

    public void OnBurnerIgnited()
    {
        if (mainBalloonScript == null) mainBalloonScript = GetComponentInParent<HotAirBalloonEscape>();
        if (mainBalloonScript == null || mainBalloonScript.IsDestroyed() || mainBalloonScript.isIgnitedWithLighter) return;
        mainBalloonScript.UseLighter();
        if (mainBalloonScript.isIgnitedWithLighter) enabled = false;
    }
}

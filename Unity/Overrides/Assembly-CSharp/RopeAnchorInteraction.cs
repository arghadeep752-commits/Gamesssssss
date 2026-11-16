using UnityEngine;

/// <summary>The wooden anchor block holding the balloon down: its ropes are cut with the chain cutter.</summary>
public class RopeAnchorInteraction : MonoBehaviour
{
    public HotAirBalloonEscape mainBalloonScript;

    public void InteractWithAnchor(string heldItem)
    {
        if (mainBalloonScript == null) mainBalloonScript = FindFirstObjectByType<HotAirBalloonEscape>();
        if (mainBalloonScript == null || mainBalloonScript.IsDestroyed() || mainBalloonScript.ropesCutWithChainCutter) return;
        if (!GameSave.SameItem(heldItem, "Chain Cutter"))
        {
            DimnightUtil.Notify("I need a chain cutter!");
            return;
        }
        mainBalloonScript.CutRopes();
        enabled = false;
    }
}

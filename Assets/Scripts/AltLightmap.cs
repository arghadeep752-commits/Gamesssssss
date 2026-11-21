using UnityEngine;

namespace TradersMadness
{
    /// <summary>A second baked lightmap for a room object (the trading room with the power on). The editor fills it in;
    /// Level switches to it when the fuse goes in.</summary>
    public class AltLightmap : MonoBehaviour
    {
        public Texture2D onLightmap;
        public float onGain = -1f;

        public void Apply(bool on, MaterialPropertyBlock mpb)
        {
            var r = GetComponent<Renderer>();
            if (r == null || onLightmap == null) return;
            r.GetPropertyBlock(mpb);
            if (on) mpb.SetTexture("_LM", onLightmap);
            else mpb.Clear();
            r.SetPropertyBlock(mpb);
        }
    }
}

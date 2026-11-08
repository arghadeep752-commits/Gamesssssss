using UnityEngine.UI;

namespace GridProto
{
    /// <summary>An invisible touch area: receives touches but draws no pixels (no wasted fill rate).</summary>
    public class RaycastArea : MaskableGraphic
    {
        protected override void OnPopulateMesh(VertexHelper vh)
        {
            vh.Clear();
        }
    }
}

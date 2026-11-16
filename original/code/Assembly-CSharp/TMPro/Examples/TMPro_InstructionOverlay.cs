using UnityEngine;

namespace TMPro.Examples
{
	public class TMPro_InstructionOverlay : MonoBehaviour
	{
		public enum FpsCounterAnchorPositions
		{
			TopLeft = 0,
			BottomLeft = 1,
			TopRight = 2,
			BottomRight = 3
		}

		public FpsCounterAnchorPositions AnchorPosition;

		private const string instructions = "Camera Control - <#ffff00>Shift + RMB\n</color>Zoom - <#ffff00>Mouse wheel.";

		private TextMeshPro m_TextMeshPro;

		private TextContainer m_textContainer;

		private Transform m_frameCounter_transform;

		private Camera m_camera;

		private void Awake()
		{
		}

		private void Set_FrameCounter_Position(FpsCounterAnchorPositions anchor_position)
		{
		}
	}
}

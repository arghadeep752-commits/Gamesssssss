using UnityEngine;

namespace TMPro.Examples
{
	public class TMP_UiFrameRateCounter : MonoBehaviour
	{
		public enum FpsCounterAnchorPositions
		{
			TopLeft = 0,
			BottomLeft = 1,
			TopRight = 2,
			BottomRight = 3
		}

		public float UpdateInterval;

		private float m_LastInterval;

		private int m_Frames;

		public FpsCounterAnchorPositions AnchorPosition;

		private string htmlColorTag;

		private const string fpsLabel = "{0:2}</color> <#8080ff>FPS \n<#FF8000>{1:2} <#8080ff>MS";

		private TextMeshProUGUI m_TextMeshPro;

		private RectTransform m_frameCounter_transform;

		private FpsCounterAnchorPositions last_AnchorPosition;

		private void Awake()
		{
		}

		private void Start()
		{
		}

		private void Update()
		{
		}

		private void Set_FrameCounter_Position(FpsCounterAnchorPositions anchor_position)
		{
		}
	}
}

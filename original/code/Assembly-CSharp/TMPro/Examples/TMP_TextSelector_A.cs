using UnityEngine;
using UnityEngine.EventSystems;

namespace TMPro.Examples
{
	public class TMP_TextSelector_A : MonoBehaviour, IPointerEnterHandler, IEventSystemHandler, IPointerExitHandler
	{
		private TextMeshPro m_TextMeshPro;

		private Camera m_Camera;

		private bool m_isHoveringObject;

		private int m_selectedLink;

		private int m_lastCharIndex;

		private int m_lastWordIndex;

		private void Awake()
		{
		}

		private void LateUpdate()
		{
		}

		public void OnPointerEnter(PointerEventData eventData)
		{
		}

		public void OnPointerExit(PointerEventData eventData)
		{
		}
	}
}

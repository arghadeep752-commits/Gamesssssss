using UnityEngine;
using UnityEngine.EventSystems;

namespace TMPro.Examples
{
	public class TMP_TextSelector_B : MonoBehaviour, IPointerEnterHandler, IEventSystemHandler, IPointerExitHandler, IPointerClickHandler, IPointerUpHandler
	{
		public RectTransform TextPopup_Prefab_01;

		private RectTransform m_TextPopup_RectTransform;

		private TextMeshProUGUI m_TextPopup_TMPComponent;

		private const string k_LinkText = "You have selected link <#ffff00>";

		private const string k_WordText = "Word Index: <#ffff00>";

		private TextMeshProUGUI m_TextMeshPro;

		private Canvas m_Canvas;

		private Camera m_Camera;

		private bool isHoveringObject;

		private int m_selectedWord;

		private int m_selectedLink;

		private int m_lastIndex;

		private Matrix4x4 m_matrix;

		private TMP_MeshInfo[] m_cachedMeshInfoVertexData;

		private void Awake()
		{
		}

		private void OnEnable()
		{
		}

		private void OnDisable()
		{
		}

		private void ON_TEXT_CHANGED(Object obj)
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

		public void OnPointerClick(PointerEventData eventData)
		{
		}

		public void OnPointerUp(PointerEventData eventData)
		{
		}

		private void RestoreCachedVertexAttributes(int index)
		{
		}
	}
}

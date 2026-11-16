using UnityEngine;

namespace TMPro.Examples
{
	public class TMP_ExampleScript_01 : MonoBehaviour
	{
		public enum objectType
		{
			TextMeshPro = 0,
			TextMeshProUGUI = 1
		}

		public objectType ObjectType;

		public bool isStatic;

		private TMP_Text m_text;

		private const string k_label = "The count is <#0080ff>{0}</color>";

		private int count;

		private void Awake()
		{
		}

		private void Update()
		{
		}
	}
}

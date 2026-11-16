using UnityEngine;

namespace TMPro.Examples
{
	public class TMP_TextEventCheck : MonoBehaviour
	{
		public TMP_TextEventHandler TextEventHandler;

		private TMP_Text m_TextComponent;

		private void OnEnable()
		{
		}

		private void OnDisable()
		{
		}

		private void OnCharacterSelection(char c, int index)
		{
		}

		private void OnSpriteSelection(char c, int index)
		{
		}

		private void OnWordSelection(string word, int firstCharacterIndex, int length)
		{
		}

		private void OnLineSelection(string lineText, int firstCharacterIndex, int length)
		{
		}

		private void OnLinkSelection(string linkID, string linkText, int linkIndex)
		{
		}
	}
}

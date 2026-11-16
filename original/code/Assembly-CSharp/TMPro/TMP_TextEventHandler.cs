using System;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.Events;

namespace TMPro
{
	public class TMP_TextEventHandler : MonoBehaviour, IPointerEnterHandler, IEventSystemHandler, IPointerExitHandler
	{
		[Serializable]
		public class CharacterSelectionEvent : UnityEvent<char, int>
		{
		}

		[Serializable]
		public class SpriteSelectionEvent : UnityEvent<char, int>
		{
		}

		[Serializable]
		public class WordSelectionEvent : UnityEvent<string, int, int>
		{
		}

		[Serializable]
		public class LineSelectionEvent : UnityEvent<string, int, int>
		{
		}

		[Serializable]
		public class LinkSelectionEvent : UnityEvent<string, string, int>
		{
		}

		[SerializeField]
		private CharacterSelectionEvent m_OnCharacterSelection;

		[SerializeField]
		private SpriteSelectionEvent m_OnSpriteSelection;

		[SerializeField]
		private WordSelectionEvent m_OnWordSelection;

		[SerializeField]
		private LineSelectionEvent m_OnLineSelection;

		[SerializeField]
		private LinkSelectionEvent m_OnLinkSelection;

		private TMP_Text m_TextComponent;

		private Camera m_Camera;

		private Canvas m_Canvas;

		private int m_selectedLink;

		private int m_lastCharIndex;

		private int m_lastWordIndex;

		private int m_lastLineIndex;

		public CharacterSelectionEvent onCharacterSelection
		{
			get
			{
				return null;
			}
			set
			{
			}
		}

		public SpriteSelectionEvent onSpriteSelection
		{
			get
			{
				return null;
			}
			set
			{
			}
		}

		public WordSelectionEvent onWordSelection
		{
			get
			{
				return null;
			}
			set
			{
			}
		}

		public LineSelectionEvent onLineSelection
		{
			get
			{
				return null;
			}
			set
			{
			}
		}

		public LinkSelectionEvent onLinkSelection
		{
			get
			{
				return null;
			}
			set
			{
			}
		}

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

		private void SendOnCharacterSelection(char character, int characterIndex)
		{
		}

		private void SendOnSpriteSelection(char character, int characterIndex)
		{
		}

		private void SendOnWordSelection(string word, int charIndex, int length)
		{
		}

		private void SendOnLineSelection(string line, int charIndex, int length)
		{
		}

		private void SendOnLinkSelection(string linkID, string linkText, int linkIndex)
		{
		}
	}
}

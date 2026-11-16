using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.CompilerServices;
using UnityEngine;

namespace TMPro.Examples
{
	public class TextConsoleSimulator : MonoBehaviour
	{
		[CompilerGenerated]
		private sealed class _003CRevealCharacters_003Ed__7 : IEnumerator<object>, IEnumerator, IDisposable
		{
			private int _003C_003E1__state;

			private object _003C_003E2__current;

			public TMP_Text textComponent;

			public TextConsoleSimulator _003C_003E4__this;

			private TMP_TextInfo _003CtextInfo_003E5__2;

			private int _003CtotalVisibleCharacters_003E5__3;

			private int _003CvisibleCount_003E5__4;

			object IEnumerator<object>.Current
			{
				[DebuggerHidden]
				get
				{
					return null;
				}
			}

			object IEnumerator.Current
			{
				[DebuggerHidden]
				get
				{
					return null;
				}
			}

			[DebuggerHidden]
			public _003CRevealCharacters_003Ed__7(int _003C_003E1__state)
			{
			}

			[DebuggerHidden]
			void IDisposable.Dispose()
			{
			}

			private bool MoveNext()
			{
				return false;
			}

			bool IEnumerator.MoveNext()
			{
				//ILSpy generated this explicit interface implementation from .override directive in MoveNext
				return this.MoveNext();
			}

			[DebuggerHidden]
			void IEnumerator.Reset()
			{
			}
		}

		[CompilerGenerated]
		private sealed class _003CRevealWords_003Ed__8 : IEnumerator<object>, IEnumerator, IDisposable
		{
			private int _003C_003E1__state;

			private object _003C_003E2__current;

			public TMP_Text textComponent;

			private int _003CtotalWordCount_003E5__2;

			private int _003CtotalVisibleCharacters_003E5__3;

			private int _003Ccounter_003E5__4;

			private int _003CvisibleCount_003E5__5;

			object IEnumerator<object>.Current
			{
				[DebuggerHidden]
				get
				{
					return null;
				}
			}

			object IEnumerator.Current
			{
				[DebuggerHidden]
				get
				{
					return null;
				}
			}

			[DebuggerHidden]
			public _003CRevealWords_003Ed__8(int _003C_003E1__state)
			{
			}

			[DebuggerHidden]
			void IDisposable.Dispose()
			{
			}

			private bool MoveNext()
			{
				return false;
			}

			bool IEnumerator.MoveNext()
			{
				//ILSpy generated this explicit interface implementation from .override directive in MoveNext
				return this.MoveNext();
			}

			[DebuggerHidden]
			void IEnumerator.Reset()
			{
			}
		}

		private TMP_Text m_TextComponent;

		private bool hasTextChanged;

		private void Awake()
		{
		}

		private void Start()
		{
		}

		private void OnEnable()
		{
		}

		private void OnDisable()
		{
		}

		private void ON_TEXT_CHANGED(UnityEngine.Object obj)
		{
		}

		[IteratorStateMachine(typeof(_003CRevealCharacters_003Ed__7))]
		private IEnumerator RevealCharacters(TMP_Text textComponent)
		{
			return null;
		}

		[IteratorStateMachine(typeof(_003CRevealWords_003Ed__8))]
		private IEnumerator RevealWords(TMP_Text textComponent)
		{
			return null;
		}
	}
}

using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.CompilerServices;
using UnityEngine;

namespace TMPro.Examples
{
	public class VertexZoom : MonoBehaviour
	{
		[CompilerGenerated]
		private sealed class _003C_003Ec__DisplayClass10_0
		{
			public List<float> modifiedCharScale;

			public Comparison<int> _003C_003E9__0;

			internal int _003CAnimateVertexColors_003Eb__0(int a, int b)
			{
				return 0;
			}
		}

		[CompilerGenerated]
		private sealed class _003CAnimateVertexColors_003Ed__10 : IEnumerator<object>, IEnumerator, IDisposable
		{
			private int _003C_003E1__state;

			private object _003C_003E2__current;

			public VertexZoom _003C_003E4__this;

			private _003C_003Ec__DisplayClass10_0 _003C_003E8__1;

			private TMP_TextInfo _003CtextInfo_003E5__2;

			private TMP_MeshInfo[] _003CcachedMeshInfoVertexData_003E5__3;

			private List<int> _003CscaleSortingOrder_003E5__4;

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
			public _003CAnimateVertexColors_003Ed__10(int _003C_003E1__state)
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

		public float AngleMultiplier;

		public float SpeedMultiplier;

		public float CurveScale;

		private TMP_Text m_TextComponent;

		private bool hasTextChanged;

		private void Awake()
		{
		}

		private void OnEnable()
		{
		}

		private void OnDisable()
		{
		}

		private void Start()
		{
		}

		private void ON_TEXT_CHANGED(UnityEngine.Object obj)
		{
		}

		[IteratorStateMachine(typeof(_003CAnimateVertexColors_003Ed__10))]
		private IEnumerator AnimateVertexColors()
		{
			return null;
		}
	}
}

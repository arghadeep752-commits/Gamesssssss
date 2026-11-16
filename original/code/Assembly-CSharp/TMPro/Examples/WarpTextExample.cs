using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.CompilerServices;
using UnityEngine;

namespace TMPro.Examples
{
	public class WarpTextExample : MonoBehaviour
	{
		[CompilerGenerated]
		private sealed class _003CWarpText_003Ed__8 : IEnumerator<object>, IEnumerator, IDisposable
		{
			private int _003C_003E1__state;

			private object _003C_003E2__current;

			public WarpTextExample _003C_003E4__this;

			private float _003Cold_CurveScale_003E5__2;

			private AnimationCurve _003Cold_curve_003E5__3;

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
			public _003CWarpText_003Ed__8(int _003C_003E1__state)
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

		public AnimationCurve VertexCurve;

		public float AngleMultiplier;

		public float SpeedMultiplier;

		public float CurveScale;

		private void Awake()
		{
		}

		private void Start()
		{
		}

		private AnimationCurve CopyAnimationCurve(AnimationCurve curve)
		{
			return null;
		}

		[IteratorStateMachine(typeof(_003CWarpText_003Ed__8))]
		private IEnumerator WarpText()
		{
			return null;
		}
	}
}

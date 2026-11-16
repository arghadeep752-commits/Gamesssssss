using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.CompilerServices;
using UnityEngine;

public class DoorPlankComponent : MonoBehaviour
{
	[CompilerGenerated]
	private sealed class _003CDropPlankAnimation_003Ed__2 : IEnumerator<object>, IEnumerator, IDisposable
	{
		private int _003C_003E1__state;

		private object _003C_003E2__current;

		public DoorPlankComponent _003C_003E4__this;

		private float _003Celapsed_003E5__2;

		private Vector3 _003CstartPos_003E5__3;

		private Quaternion _003CstartRot_003E5__4;

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
		public _003CDropPlankAnimation_003Ed__2(int _003C_003E1__state)
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

	private bool isRemoved;

	public void RemovePlank()
	{
	}

	[IteratorStateMachine(typeof(_003CDropPlankAnimation_003Ed__2))]
	private IEnumerator DropPlankAnimation()
	{
		return null;
	}

	public bool IsRemoved()
	{
		return false;
	}
}

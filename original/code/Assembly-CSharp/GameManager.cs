using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.CompilerServices;
using UnityEngine;
using UnityEngine.AI;

public class GameManager : MonoBehaviour
{
	[CompilerGenerated]
	private sealed class _003CSafeTeleportRoutine_003Ed__11 : IEnumerator<object>, IEnumerator, IDisposable
	{
		private int _003C_003E1__state;

		private object _003C_003E2__current;

		public GameManager _003C_003E4__this;

		private MobilePickUpScript _003CpickupScript_003E5__2;

		private GameObject _003CobjectToPreserve_003E5__3;

		private Transform _003CdynamicHoldDestination_003E5__4;

		private CharacterController _003CcharController_003E5__5;

		private MonoBehaviour _003CfpsController_003E5__6;

		private GrannyAI _003Cgranny_003E5__7;

		private NavMeshAgent _003CgrannyAgent_003E5__8;

		private Vector3 _003CtargetGrannyPos_003E5__9;

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
		public _003CSafeTeleportRoutine_003Ed__11(int _003C_003E1__state)
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

	[Header("Player & Camera Setup")]
	public GameObject playerGameObject;

	public Transform playerSpawnPoint;

	public MonoBehaviour wakeUpScript;

	[Header("Granny Setup")]
	public Transform grannySpawnPoint;

	[Header("Inventory / Item Drop Settings")]
	public MonoBehaviour playerPickupScript;

	public static GameManager Instance { get; private set; }

	private void Awake()
	{
	}

	public void ResetPlayerForNextDay()
	{
	}

	[IteratorStateMachine(typeof(_003CSafeTeleportRoutine_003Ed__11))]
	private IEnumerator SafeTeleportRoutine()
	{
		return null;
	}
}

using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Reflection;
using System.Runtime.CompilerServices;
using UnityEngine;
using UnityEngine.AI;

[DefaultExecutionOrder(2000)]
[RequireComponent(typeof(NavMeshAgent))]
[RequireComponent(typeof(AudioSource))]
public class GrannyAI : MonoBehaviour
{
	public enum AIState
	{
		Patrol = 0,
		Chase = 1,
		Attack = 2,
		KillSequence = 3,
		InvestigateSound = 4
	}

	private class DoorInfo
	{
		public DoorInteractable door;

		public Collider[] colliders;

		public Renderer[] renderers;
	}

	private enum DoorPhase
	{
		None = 0,
		Waiting = 1,
		Passing = 2
	}

	[CompilerGenerated]
	private sealed class _003CBedJumpscareSequence_003Ed__178 : IEnumerator<object>, IEnumerator, IDisposable
	{
		private int _003C_003E1__state;

		private object _003C_003E2__current;

		public GrannyAI _003C_003E4__this;

		public HidingSpot bedSpot;

		private float _003Cwaited_003E5__2;

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
		public _003CBedJumpscareSequence_003Ed__178(int _003C_003E1__state)
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
	private sealed class _003CCarJumpscareSequence_003Ed__182 : IEnumerator<object>, IEnumerator, IDisposable
	{
		private int _003C_003E1__state;

		private object _003C_003E2__current;

		public GrannyAI _003C_003E4__this;

		public HidingSpot carSpot;

		public PlayerHidingController hidingController;

		private Vector3 _003CentryPoint_003E5__2;

		private float _003CwaitedAtSpot_003E5__3;

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
		public _003CCarJumpscareSequence_003Ed__182(int _003C_003E1__state)
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
	private sealed class _003CCoffinJumpscareSequence_003Ed__181 : IEnumerator<object>, IEnumerator, IDisposable
	{
		private int _003C_003E1__state;

		private object _003C_003E2__current;

		public GrannyAI _003C_003E4__this;

		public HidingSpot coffinSpot;

		private float _003CwaitedAtSpot_003E5__2;

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
		public _003CCoffinJumpscareSequence_003Ed__181(int _003C_003E1__state)
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
	private sealed class _003CStandIdleAfterKill_003Ed__176 : IEnumerator<object>, IEnumerator, IDisposable
	{
		private int _003C_003E1__state;

		private object _003C_003E2__current;

		public GrannyAI _003C_003E4__this;

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
		public _003CStandIdleAfterKill_003Ed__176(int _003C_003E1__state)
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
	private sealed class _003CStandardKillSequence_003Ed__175 : IEnumerator<object>, IEnumerator, IDisposable
	{
		private int _003C_003E1__state;

		private object _003C_003E2__current;

		public GrannyAI _003C_003E4__this;

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
		public _003CStandardKillSequence_003Ed__175(int _003C_003E1__state)
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
	private sealed class _003CVoiceLineRoutine_003Ed__119 : IEnumerator<object>, IEnumerator, IDisposable
	{
		private int _003C_003E1__state;

		private object _003C_003E2__current;

		public GrannyAI _003C_003E4__this;

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
		public _003CVoiceLineRoutine_003Ed__119(int _003C_003E1__state)
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
	private sealed class _003CWonderAndGiveUpRoutine_003Ed__150 : IEnumerator<object>, IEnumerator, IDisposable
	{
		private int _003C_003E1__state;

		private object _003C_003E2__current;

		public GrannyAI _003C_003E4__this;

		private float _003CwonderElapsed_003E5__2;

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
		public _003CWonderAndGiveUpRoutine_003Ed__150(int _003C_003E1__state)
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

	[Header("AI State")]
	public AIState currentState;

	[Tooltip("ON: the values below are used for each mode. OFF: the single 'Active Values' further down are used for every mode.")]
	[Header("===== DIFFICULTY SETTINGS (edit per mode) =====")]
	public bool useDifficultySettings;

	[Tooltip("ON: changes you make in Play mode apply instantly (great for testing). Remember Unity resets Play-mode changes when you stop.")]
	public bool liveTuningInPlayMode;

	[Tooltip("Which mode is running right now (read only, for checking)")]
	public string activeDifficulty;

	public GrannyDifficultySettings easy;

	public GrannyDifficultySettings normal;

	public GrannyDifficultySettings hard;

	public GrannyDifficultySettings extreme;

	private GrannyDifficultySettings activeSettings;

	[Header("Movement & Speed Settings")]
	[Header("===== ACTIVE VALUES (set automatically from the mode above) =====")]
	public float patrolSpeed;

	public float chaseSpeed;

	[Tooltip("Speed when going to check a noise")]
	public float investigateSpeed;

	public float angularTurnSpeed;

	public float accelerationRate;

	[Tooltip("ON: she keeps her full speed (patrol / chase / investigate) while going round corners - tables, sofas, stairs. OFF: Unity slows her down in turns.")]
	public bool keepFullSpeedOnTurns;

	[Tooltip("She only slows down this close to where she is going, so she still stops smoothly (meters)")]
	public float brakeDistance;

	[Header("Waypoint Patrol Settings")]
	public List<Transform> patrolWaypoints;

	private Transform currentTargetWaypoint;

	[Header("Patrol Waiting Settings")]
	public float minWaitTime;

	public float maxWaitTime;

	private float patrolWaitTimer;

	private bool isWaitingAtPoint;

	[Header("Advanced Vision Settings")]
	public Transform player;

	[Tooltip("Maximum horizontal/overall distance at which Granny can see the player.")]
	public float viewDistance;

	[Tooltip("Vision cone angle.")]
	public float viewAngle;

	[Tooltip("Distance where Granny can detect the player regardless of view angle, as long as height and obstacles allow it.")]
	public float proximityRange;

	[Tooltip("Maximum vertical difference between Granny and the player for vision/chase/attack.")]
	public float maxFloorHeightDifference;

	[Tooltip("Extra vertical tolerance allowed when attacking. Keep this small so Granny cannot hit players far above/below her.")]
	public float maxAttackHeightDifference;

	[Tooltip("Layers that block Granny's vision and attacks. Include Floor, Walls, Environment, etc. Do NOT include the Player layer.")]
	public LayerMask obstacleMask;

	[Tooltip("Set this to the layer your stairs are on (create a 'Stairs' layer and put the stairs objects on it).")]
	[Header("Stairs Settings")]
	public LayerMask stairsLayer;

	[Tooltip("Allowed height difference for vision/chase when Granny or the player is on stairs.")]
	public float stairsHeightDifference;

	[Tooltip("Allowed height difference for attacking when Granny AND the player are BOTH on stairs.")]
	public float stairsAttackHeightDifference;

	[Tooltip("Attack range used only when Granny AND the player are BOTH on stairs. Otherwise the normal Attack Range is used.")]
	public float stairsAttackRange;

	[Tooltip("How far below the feet to look for the stairs layer.")]
	public float stairsDetectDistance;

	[Header("Sound Investigation Settings")]
	public float soundInvestigateWaitTime;

	private Vector3 targetSoundPosition;

	[Tooltip("How far (meters) Granny stops short of a noise (dropped item, creaking floor). She stands on her side of it, facing it.")]
	[Header("Item Drop Investigation")]
	public float itemStandOffDistance;

	[Tooltip("Show Granny's hearing decisions in the Console (turn off when everything works)")]
	public bool debugNoiseLogs;

	private bool hasInvestigateLookTarget;

	private Vector3 investigateLookTarget;

	private float investigateStartTime;

	[Tooltip("How long Granny keeps heading toward the player's last known direction after losing sight before giving up.")]
	[Header("Chase Persistence Settings")]
	public float loseSightGraceTime;

	private float loseSightTimer;

	[Header("Tight Space / Unreachable Settings")]
	public float maxUnreachableChaseTime;

	private float unreachableTimer;

	private bool isGivingUpChase;

	[Tooltip("While chasing, if she is barely moving and can't hit the player for this long, she gives up (e.g. player under a table she can't get under)")]
	public float maxStuckChaseTime;

	[Tooltip("Below this speed she counts as 'stuck' while chasing")]
	public float stuckSpeedThreshold;

	[Tooltip("After giving up, she ignores the player for this long IF he stays in that same hiding spot")]
	public float ignoreAfterGiveUpTime;

	[Tooltip("If the player moves further than this from where she gave up, she can see him again right away")]
	public float ignoreAfterGiveUpRadius;

	private float stuckTimer;

	private float giveUpIgnoreUntil;

	private Vector3 giveUpIgnorePosition;

	[Header("Attack Settings")]
	public float attackRange;

	public float attackCooldown;

	private float nextAttackTime;

	[Tooltip("How long Granny stands at the bed before dropping down for the bed kill. The player can get out and escape during this time - then she attacks him normally instead.")]
	[Header("Bed Kill")]
	public float bedKillWaitTime;

	[Header("Seeing The Player Hide")]
	[Tooltip("If she saw the player within this many seconds before he got into a hiding spot (bed / car / coffin), it counts as 'she saw him hide' and she WILL come and kill him there.")]
	public float sawHideGraceTime;

	[Header("Car Kill")]
	[Tooltip("How far OUTSIDE the player's entry point Granny stands, on the side he got in from (meters). The player is pulled out between her and the car.")]
	public float carGrannyStandOff;

	[Tooltip("How long she stands at the car door before pulling the player out (seconds)")]
	public float carKillWaitTime;

	[Tooltip("Only used if NO Head Look Target is assigned below: height above Granny's feet that the player looks at.")]
	[Header("Kill Sequence View Lock")]
	public float killLookHeight;

	[Tooltip("How fast the view turns to face Granny when she catches the player. Higher = faster.")]
	public float killViewTurnSpeed;

	[Tooltip("Keep the camera locked on Granny's face for the WHOLE kill, until the player is dead and the next day starts. Untick to let the JumpscareCoordinator control the camera instead.")]
	public bool keepViewLockedUntilDeath;

	[Tooltip("Extra pause after a crouching player has stood up, before her death animation starts")]
	public float standUpExtraDelay;

	[Header("Death Look Target  (DRAG GRANNY'S HEAD HERE)")]
	[Tooltip("Drag Granny's head bone here (in the Hierarchy: Granny > ... > Hips > Spine > ... > Head), or an empty object placed on her face and parented to her head. In EVERY death animation (standing, bed, car, coffin) the player looks exactly at this point.")]
	public Transform headLookTarget;

	[Tooltip("Fine tune: moves the look point away from the head object, in metres, in the head's own directions. Use it to aim at her face instead of the centre of her head (try Z = 0.1).")]
	public Vector3 headLookOffset;

	[Header("Animations")]
	public Animator animator;

	[Header("Audio Settings")]
	public AudioClip walkSound;

	public AudioClip chaseSound;

	public AudioClip hitSound;

	public float footstepInterval;

	[Range(0f, 1f)]
	[Header("Chase Music Fade")]
	[Tooltip("Volume of the chase music while she is chasing")]
	public float chaseMusicVolume;

	[Tooltip("Seconds the chase music takes to fade out after she loses the player")]
	public float chaseMusicFadeOutTime;

	[Header("Voice Lines")]
	public List<AudioClip> grannyVoiceLines;

	[Tooltip("Drag every door Granny should stop at and open (the door object, or its parent). She stands at a closed door, waits, opens it, then carries on chasing / investigating / patrolling.")]
	[Header("===== DOORS (drag every door here) =====")]
	public List<GameObject> doorObjects;

	[Tooltip("ON: if the list above is empty, every DoorInteractable in the scene is used.")]
	public bool autoFindDoorsIfListEmpty;

	[Tooltip("How long she stands at a closed door before opening it (seconds)")]
	public float doorOpenDelay;

	[Tooltip("After she opens it, how long she waits for the door to swing open before walking through (seconds)")]
	public float doorPassDelay;

	[Tooltip("How far from the closed door she stops (meters, from her centre). Keep it a bit bigger than her NavMeshAgent Radius.")]
	public float doorStopDistance;

	[Tooltip("ON: she can open locked doors too. OFF: a locked door stops her - she gives up the chase / noise and patrols somewhere else.")]
	public bool grannyCanOpenLockedDoors;

	[Tooltip("Optional: name of an Animator Trigger to play when she opens a door (e.g. OpenDoor). Leave empty if you have no door animation.")]
	public string doorOpenAnimTrigger;

	[Tooltip("Show door decisions in the Console (turn off when everything works)")]
	public bool debugDoorLogs;

	[Tooltip("Draw a box around each door in the Scene view when Granny is selected (green = OK, red = no DoorInteractable found, yellow = she is opening it)")]
	public bool showDoorGizmos;

	private AudioSource audioSource;

	private AudioSource musicSource;

	private NavMeshAgent agent;

	private bool playerInSight;

	private bool isKilling;

	private float footstepTimer;

	private Coroutine voiceLineCoroutine;

	private bool wasPlayerHidingLastFrame;

	private bool witnessedPlayerHideThisSession;

	private bool isPlayerHiddenNow;

	private HidingSpot hiddenSpot;

	private PlayerHidingController trackedHidingController;

	private FieldInfo trackedSpotField;

	private float lastSeenPlayerTime;

	private bool killViewLocked;

	private Camera killLockCamera;

	private Quaternion killLockRotation;

	private MonoBehaviour killLockFps;

	private bool fpsDisabledByKillLock;

	private readonly List<DoorInfo> doorInfos;

	private DoorPhase doorPhase;

	private DoorInfo currentDoor;

	private float doorTimer;

	private bool doorStopInSequence;

	private float nextDoorPathCheck;

	private DoorInteractable lastOpenedDoor;

	private float lastOpenedDoorIgnoreUntil;

	private NavMeshPath doorCheckPath;

	private const float DoorPathMargin = 0.1f;

	private int EffectiveObstacleMask => 0;

	private float CurrentAttackRange => 0f;

	private void Start()
	{
	}

	private void InitializeAI()
	{
	}

	private void ApplyDifficultySettings()
	{
	}

	private void ApplySettingsValues(GrannyDifficultySettings s)
	{
	}

	[IteratorStateMachine(typeof(_003CVoiceLineRoutine_003Ed__119))]
	private IEnumerator VoiceLineRoutine()
	{
		return null;
	}

	private void Update()
	{
	}

	private void HandleChaseMusicFade()
	{
	}

	private void MaintainSpeedOnTurns()
	{
	}

	private void LateUpdate()
	{
	}

	public Vector3 GetHeadLookPoint()
	{
		return default;
	}

	private void BeginKillViewLock()
	{
	}

	private void ReleaseKillViewLock()
	{
	}

	private bool IsOnStairs(Transform t)
	{
		return false;
	}

	private bool AnyoneOnStairs()
	{
		return false;
	}

	private bool BothOnStairs()
	{
		return false;
	}

	private bool IsPlayerAtSameHeight()
	{
		return false;
	}

	private bool IsPlayerAtAttackHeight()
	{
		return false;
	}

	private void RefreshHidingTracking()
	{
	}

	private bool TryHandleHiddenPlayerJumpscare()
	{
		return false;
	}

	private void HandleCustomRotation()
	{
	}

	private void UpdateAnimatorParameters()
	{
	}

	private void CalculateRealisticIndoorPatrolRoute()
	{
	}

	private void AbandonChaseWithNearestWaypoint()
	{
	}

	private void PatrolBehavior()
	{
	}

	private void CheckForPlayerRealistically()
	{
	}

	public void HearNoise(Vector3 noiseLocation)
	{
	}

	private bool CanReactToNoise(string what)
	{
		return false;
	}

	private void StartInvestigation(Vector3 destination)
	{
	}

	private Vector3 GetStandPointNearItem(Vector3 itemPos)
	{
		return default;
	}

	private void InvestigateSoundBehavior()
	{
	}

	private void ChaseBehavior()
	{
	}

	[IteratorStateMachine(typeof(_003CWonderAndGiveUpRoutine_003Ed__150))]
	private IEnumerator WonderAndGiveUpRoutine()
	{
		return null;
	}

	private void TriggerChaseState()
	{
	}

	private void ResolveDoors()
	{
	}

	private void AddDoor(DoorInteractable door)
	{
	}

	private static DoorInteractable FindDoorComponent(GameObject go)
	{
		return null;
	}

	private static bool TryGetDoorBounds(Collider[] colliders, Renderer[] renderers, out Bounds bounds)
	{
		bounds = default;
		return false;
	}

	private bool IsDoorClosedAndRelevant(DoorInfo info, out Bounds bounds)
	{
		bounds = default;
		return false;
	}

	private static bool InsideFlat(Bounds b, Vector3 p, float margin)
	{
		return false;
	}

	private float PathEntryDistance(Vector3[] corners, Bounds b, float maxDistance)
	{
		return 0f;
	}

	private DoorInfo FindDoorOnPath()
	{
		return null;
	}

	private bool PathCrossesDoor(DoorInfo info, Vector3 target)
	{
		return false;
	}

	private bool CanCheckDoorsNow()
	{
		return false;
	}

	private bool HandleDoorsInUpdate()
	{
		return false;
	}

	private bool TickDoorDuringSequence()
	{
		return false;
	}

	private void StartDoorStop(DoorInfo info, bool inSequence)
	{
	}

	private void UpdateDoorStop()
	{
	}

	private bool ShouldStopWaitingAtDoor()
	{
		return false;
	}

	private void HandleLockedDoor()
	{
	}

	private void CancelDoorStop()
	{
	}

	private void FaceCurrentDoor()
	{
	}

	private void PlayDoorOpenAnimation()
	{
	}

	private bool HasClearAttackLine()
	{
		return false;
	}

	private void OnDrawGizmosSelected()
	{
	}

	private void TriggerPlayerItemDrop()
	{
	}

	private void AttackBehavior()
	{
	}

	[IteratorStateMachine(typeof(_003CStandardKillSequence_003Ed__175))]
	private IEnumerator StandardKillSequence()
	{
		return null;
	}

	[IteratorStateMachine(typeof(_003CStandIdleAfterKill_003Ed__176))]
	private IEnumerator StandIdleAfterKill()
	{
		return null;
	}

	private void HandleFootsteps(float currentSpeedSetting)
	{
	}

	[IteratorStateMachine(typeof(_003CBedJumpscareSequence_003Ed__178))]
	private IEnumerator BedJumpscareSequence(HidingSpot bedSpot)
	{
		return null;
	}

	private bool IsPlayerStillHidingIn(HidingSpot spot)
	{
		return false;
	}

	private void AbortBedJumpscare()
	{
	}

	[IteratorStateMachine(typeof(_003CCoffinJumpscareSequence_003Ed__181))]
	private IEnumerator CoffinJumpscareSequence(HidingSpot coffinSpot, PlayerHidingController hidingController)
	{
		return null;
	}

	[IteratorStateMachine(typeof(_003CCarJumpscareSequence_003Ed__182))]
	private IEnumerator CarJumpscareSequence(HidingSpot carSpot, PlayerHidingController hidingController)
	{
		return null;
	}

	private Vector3 GetCarEntryPoint(HidingSpot carSpot, PlayerHidingController hidingController)
	{
		return default;
	}

	private Vector3 GetGrannyStandPointForCar(HidingSpot carSpot, Vector3 entryPoint)
	{
		return default;
	}

	public void ResetAIStateForNextDay()
	{
	}
}

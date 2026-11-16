using System.Collections;
using System.Collections.Generic;
using System.Reflection;
using UnityEngine;
using UnityEngine.AI;

/// <summary>
/// Granny: patrols the house room by room, hears dropped items, creaking floors and falling things and goes to look,
/// sees the player in her vision cone (or right behind her when close), chases him, opens doors in her way (she
/// stops, waits, opens, walks through), gives up when she can't reach him, and catches him. If she saw him hide
/// (bed, car, coffin) she comes and gets him there. Numbers per mode come from easy / normal / hard / extreme.
/// </summary>
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
        public PlankLockedDoorInteractable plankDoor;
        public Collider[] colliders;
        public Renderer[] renderers;
    }

    private enum DoorPhase
    {
        None = 0,
        Waiting = 1,
        Passing = 2
    }

    [Header("AI State")]
    public AIState currentState;

    [Header("===== DIFFICULTY SETTINGS (edit per mode) =====")]
    public bool useDifficultySettings;
    public bool liveTuningInPlayMode;
    public string activeDifficulty;
    public GrannyDifficultySettings easy;
    public GrannyDifficultySettings normal;
    public GrannyDifficultySettings hard;
    public GrannyDifficultySettings extreme;
    private GrannyDifficultySettings activeSettings;

    [Header("Movement & Speed Settings")]
    public float patrolSpeed;
    public float chaseSpeed;
    public float investigateSpeed;
    public float angularTurnSpeed;
    public float accelerationRate;
    public bool keepFullSpeedOnTurns;
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
    public float viewDistance;
    public float viewAngle;
    public float proximityRange;
    public float maxFloorHeightDifference;
    public float maxAttackHeightDifference;
    public LayerMask obstacleMask;

    [Header("Stairs Settings")]
    public LayerMask stairsLayer;
    public float stairsHeightDifference;
    public float stairsAttackHeightDifference;
    public float stairsAttackRange;
    public float stairsDetectDistance;

    public float soundInvestigateWaitTime;
    private Vector3 targetSoundPosition;

    [Header("Item Drop Investigation")]
    public float itemStandOffDistance;
    public bool debugNoiseLogs;
    private bool hasInvestigateLookTarget;
    private Vector3 investigateLookTarget;
    private float investigateStartTime;

    [Header("Chase Persistence Settings")]
    public float loseSightGraceTime;
    private float loseSightTimer;

    [Header("Tight Space / Unreachable Settings")]
    public float maxUnreachableChaseTime;
    private float unreachableTimer;
    private bool isGivingUpChase;
    public float maxStuckChaseTime;
    public float stuckSpeedThreshold;
    public float ignoreAfterGiveUpTime;
    public float ignoreAfterGiveUpRadius;
    private float stuckTimer;
    private float giveUpIgnoreUntil;
    private Vector3 giveUpIgnorePosition;

    [Header("Attack Settings")]
    public float attackRange;
    public float attackCooldown;
    private float nextAttackTime;

    [Header("Bed Kill")]
    public float bedKillWaitTime;

    [Header("Seeing The Player Hide")]
    public float sawHideGraceTime;

    [Header("Car Kill")]
    public float carGrannyStandOff;
    public float carKillWaitTime;

    [Header("Kill Sequence View Lock")]
    public float killLookHeight;
    public float killViewTurnSpeed;
    public bool keepViewLockedUntilDeath;
    public float standUpExtraDelay;

    [Header("Death Look Target  (DRAG GRANNY'S HEAD HERE)")]
    public Transform headLookTarget;
    public Vector3 headLookOffset;

    [Header("Animations")]
    public Animator animator;

    [Header("Audio Settings")]
    public AudioClip walkSound;
    public AudioClip chaseSound;
    public AudioClip hitSound;
    public float footstepInterval;

    [Header("Chase Music Fade")]
    public float chaseMusicVolume;
    public float chaseMusicFadeOutTime;

    [Header("Voice Lines")]
    public List<AudioClip> grannyVoiceLines;

    [Header("===== DOORS (drag every door here) =====")]
    public List<GameObject> doorObjects;
    public bool autoFindDoorsIfListEmpty;
    public float doorOpenDelay;
    public float doorPassDelay;
    public float doorStopDistance;
    public bool grannyCanOpenLockedDoors;
    public string doorOpenAnimTrigger;
    public bool debugDoorLogs;
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
    private float lastSeenPlayerTime = -100f;
    private bool killViewLocked;
    private Camera killLockCamera;
    private Quaternion killLockRotation;
    private MonoBehaviour killLockFps;
    private bool fpsDisabledByKillLock;
    private readonly List<DoorInfo> doorInfos = new List<DoorInfo>();
    private DoorPhase doorPhase;
    private DoorInfo currentDoor;
    private float doorTimer;
    private bool doorStopInSequence;
    private float nextDoorPathCheck;
    private DoorInteractable lastOpenedDoor;
    private float lastOpenedDoorIgnoreUntil;
    private NavMeshPath doorCheckPath;
    private const float DoorPathMargin = 0.1f;

    private readonly Dictionary<string, AnimatorControllerParameterType> animParams = new Dictionary<string, AnimatorControllerParameterType>();
    private Coroutine sequenceRoutine;
    private Coroutine wonderRoutine;
    private Transform spawnPoint;
    private Vector3 startPosition;
    private Quaternion startRotation;
    private float dayStartTime;
    private float nextWaypointUnlockCheck;
    private readonly List<Transform> recentWaypoints = new List<Transform>();
    private float musicTargetVolume;
    private bool active = true;

    private static readonly List<GrannyAI> all = new List<GrannyAI>();
    public static GrannyAI Instance { get; private set; }

    private int EffectiveObstacleMask
    {
        get
        {
            int mask = obstacleMask.value != 0 ? obstacleMask.value : Physics.DefaultRaycastLayers;
            if (player != null) mask &= ~(1 << player.gameObject.layer);
            int held = LayerMask.NameToLayer("HeldItem");
            if (held >= 0) mask &= ~(1 << held);
            int item = LayerMask.NameToLayer("InteractableItem");
            if (item >= 0) mask &= ~(1 << item);
            mask &= ~(1 << gameObject.layer);
            return mask;
        }
    }

    private float CurrentAttackRange => BothOnStairs() && stairsAttackRange > 0f ? stairsAttackRange : attackRange;

    public bool IsChasing => currentState == AIState.Chase || currentState == AIState.Attack;
    public bool IsKilling => isKilling;

    /// <summary>Every Granny in the scene hears a noise at this point (dropped item, falling plank, bell...).</summary>
    public static void AlertAll(Vector3 position, string what)
    {
        for (int i = 0; i < all.Count; i++)
            if (all[i] != null && all[i].isActiveAndEnabled) all[i].HearNoise(position, what);
    }

    private void OnEnable()
    {
        if (!all.Contains(this)) all.Add(this);
        Instance = this;
    }

    private void OnDisable()
    {
        all.Remove(this);
        if (Instance == this) Instance = null;
        if (musicSource != null) musicSource.Stop();
    }

    private void Start()
    {
        InitializeAI();
    }

    private void InitializeAI()
    {
        agent = GetComponent<NavMeshAgent>();
        if (animator == null) animator = GetComponentInChildren<Animator>();
        audioSource = GetComponent<AudioSource>();
        if (audioSource == null) audioSource = gameObject.AddComponent<AudioSource>();
        audioSource.spatialBlend = 1f;
        musicSource = gameObject.AddComponent<AudioSource>();
        musicSource.spatialBlend = 0f;
        musicSource.loop = true;
        musicSource.playOnAwake = false;
        musicSource.volume = 0f;
        var rb = GetComponent<Rigidbody>();
        if (rb != null) { rb.isKinematic = true; rb.useGravity = false; }
        if (player == null)
        {
            GameObject p = GameSave.PlayerObject();
            if (p != null) player = p.transform;
        }
        if (animator != null)
        {
            foreach (AnimatorControllerParameter prm in animator.parameters) animParams[prm.name] = prm.type;
            animator.applyRootMotion = false;
        }
        startPosition = transform.position;
        startRotation = transform.rotation;
        if (GameManager.Instance != null && GameManager.Instance.grannySpawnPoint != null) spawnPoint = GameManager.Instance.grannySpawnPoint;
        doorCheckPath = new NavMeshPath();
        if (attackRange <= 0f) attackRange = 1.8f;
        if (attackCooldown <= 0f) attackCooldown = 2f;
        if (doorOpenDelay < 0f) doorOpenDelay = 0.8f;
        if (doorStopDistance <= 0f) doorStopDistance = 1.0f;
        if (footstepInterval <= 0f) footstepInterval = 0.55f;
        if (chaseMusicVolume <= 0f) chaseMusicVolume = 0.6f;
        if (chaseMusicFadeOutTime <= 0f) chaseMusicFadeOutTime = 3f;
        if (sawHideGraceTime <= 0f) sawHideGraceTime = 1.5f;
        if (killViewTurnSpeed <= 0f) killViewTurnSpeed = 8f;
        ApplyDifficultySettings();
        ResolveDoors();

        if (GameSave.IsPractice)
        {
            // Practice: Granny is not at home
            active = false;
            gameObject.SetActive(false);
            return;
        }
        if (agent != null)
        {
            agent.angularSpeed = angularTurnSpeed > 0f ? angularTurnSpeed : 720f;
            agent.acceleration = accelerationRate > 0f ? accelerationRate : 16f;
            agent.autoBraking = !keepFullSpeedOnTurns;
            agent.stoppingDistance = 0.3f;
            if (!agent.isOnNavMesh && NavMesh.SamplePosition(transform.position, out NavMeshHit hit, 4f, NavMesh.AllAreas))
                agent.Warp(hit.position);
        }
        dayStartTime = Time.time;
        currentState = AIState.Patrol;
        SetSpeed(patrolSpeed);
        CalculateRealisticIndoorPatrolRoute();
        voiceLineCoroutine = StartCoroutine(VoiceLineRoutine());
    }

    private void ApplyDifficultySettings()
    {
        activeDifficulty = GameSave.Difficulty;
        if (!useDifficultySettings) return;
        GrannyDifficultySettings s;
        switch (activeDifficulty)
        {
            case "Easy": s = easy; break;
            case "Hard": s = hard; break;
            case "Extreme": s = extreme; break;
            default: s = normal; break;
        }
        if (s == null) return;
        activeSettings = s;
        ApplySettingsValues(s);
    }

    private void ApplySettingsValues(GrannyDifficultySettings s)
    {
        if (s.patrolSpeed > 0f) patrolSpeed = s.patrolSpeed;
        if (s.chaseSpeed > 0f) chaseSpeed = s.chaseSpeed;
        if (s.investigateSpeed > 0f) investigateSpeed = s.investigateSpeed;
        if (s.viewDistance > 0f) viewDistance = s.viewDistance;
        if (s.viewAngle > 0f) viewAngle = s.viewAngle;
        if (s.proximityRange > 0f) proximityRange = s.proximityRange;
        if (s.loseSightGraceTime > 0f) loseSightGraceTime = s.loseSightGraceTime;
        if (s.attackRange > 0f) attackRange = s.attackRange;
        if (s.soundInvestigateWaitTime > 0f) soundInvestigateWaitTime = s.soundInvestigateWaitTime;
        if (s.minWaitTime > 0f) minWaitTime = s.minWaitTime;
        if (s.maxWaitTime > 0f) maxWaitTime = s.maxWaitTime;
        if (s.bedKillWaitTime > 0f) bedKillWaitTime = s.bedKillWaitTime;
    }

    private IEnumerator VoiceLineRoutine()
    {
        while (true)
        {
            yield return new WaitForSeconds(Random.Range(9f, 20f));
            if (isKilling || grannyVoiceLines == null || grannyVoiceLines.Count == 0 || audioSource == null) continue;
            AudioClip clip = grannyVoiceLines[Random.Range(0, grannyVoiceLines.Count)];
            if (clip != null) audioSource.PlayOneShot(clip, 0.9f);
        }
    }

    private void Update()
    {
        if (!active || agent == null || !agent.enabled) return;
        if (!agent.isOnNavMesh)
        {
            if (NavMesh.SamplePosition(transform.position, out NavMeshHit hit, 4f, NavMesh.AllAreas)) agent.Warp(hit.position);
            return;
        }
        if (liveTuningInPlayMode && useDifficultySettings && activeSettings != null) ApplySettingsValues(activeSettings);
        RefreshHidingTracking();
        HandleChaseMusicFade();
        if (Time.time >= nextWaypointUnlockCheck) { nextWaypointUnlockCheck = Time.time + 3f; AutoUnlockWaypoints(); }
        if (isKilling)
        {
            UpdateAnimatorParameters();
            return;
        }
        if (sequenceRoutine != null)
        {
            HandleCustomRotation();
            UpdateAnimatorParameters();
            HandleFootsteps(agent.speed);
            return;
        }
        if (HandleDoorsInUpdate())
        {
            UpdateAnimatorParameters();
            return;
        }
        CheckForPlayerRealistically();
        switch (currentState)
        {
            case AIState.Patrol: PatrolBehavior(); break;
            case AIState.Chase: ChaseBehavior(); break;
            case AIState.InvestigateSound: InvestigateSoundBehavior(); break;
            case AIState.Attack: AttackBehavior(); break;
        }
        MaintainSpeedOnTurns();
        HandleCustomRotation();
        UpdateAnimatorParameters();
        HandleFootsteps(agent.speed);
    }

    private void SetSpeed(float s)
    {
        if (agent != null) agent.speed = Mathf.Max(0.1f, s);
    }

    private void HandleChaseMusicFade()
    {
        if (musicSource == null) return;
        musicTargetVolume = IsChasing || isKilling ? chaseMusicVolume : 0f;
        float rate = musicTargetVolume > musicSource.volume ? chaseMusicVolume / 0.5f : chaseMusicVolume / Mathf.Max(0.1f, chaseMusicFadeOutTime);
        musicSource.volume = Mathf.MoveTowards(musicSource.volume, musicTargetVolume, rate * Time.deltaTime);
        if (musicTargetVolume > 0f && !musicSource.isPlaying && chaseSound != null)
        {
            musicSource.clip = chaseSound;
            musicSource.Play();
        }
        else if (musicTargetVolume == 0f && musicSource.volume <= 0.001f && musicSource.isPlaying) musicSource.Stop();
    }

    private void MaintainSpeedOnTurns()
    {
        if (!keepFullSpeedOnTurns || agent == null || !agent.hasPath) return;
        agent.autoBraking = agent.remainingDistance < Mathf.Max(0.2f, brakeDistance);
    }

    private void LateUpdate()
    {
        if (killViewLocked && killLockCamera != null)
        {
            Vector3 look = GetHeadLookPoint() - killLockCamera.transform.position;
            if (look.sqrMagnitude > 0.0001f)
            {
                Quaternion want = Quaternion.LookRotation(look);
                killLockCamera.transform.rotation = Quaternion.Slerp(killLockCamera.transform.rotation, want, 1f - Mathf.Exp(-killViewTurnSpeed * Time.deltaTime));
            }
        }
    }

    public Vector3 GetHeadLookPoint()
    {
        Transform head = headLookTarget;
        if (head == null && animator != null && animator.isHuman) head = animator.GetBoneTransform(HumanBodyBones.Head);
        if (head == null)
        {
            head = GameSave.FindDeep(transform, "Bip01 Head");
            if (head != null) headLookTarget = head;
        }
        if (head != null) return head.position + head.rotation * headLookOffset;
        return transform.position + Vector3.up * (killLookHeight > 0f ? killLookHeight : 1.55f);
    }

    private void BeginKillViewLock()
    {
        if (player == null) return;
        killLockCamera = player.GetComponentInChildren<Camera>();
        killLockFps = player.GetComponent<FPSController>();
        if (killLockFps != null && killLockFps.enabled) { killLockFps.enabled = false; fpsDisabledByKillLock = true; }
        killViewLocked = true;
    }

    private void ReleaseKillViewLock()
    {
        killViewLocked = false;
        if (fpsDisabledByKillLock && killLockFps != null) killLockFps.enabled = true;
        fpsDisabledByKillLock = false;
    }

    private bool IsOnStairs(Transform t)
    {
        if (t == null || stairsLayer.value == 0) return false;
        float d = stairsDetectDistance > 0f ? stairsDetectDistance : 3f;
        return Physics.Raycast(t.position + Vector3.up * 0.5f, Vector3.down, d, stairsLayer, QueryTriggerInteraction.Ignore);
    }

    private bool AnyoneOnStairs()
    {
        return IsOnStairs(transform) || IsOnStairs(player);
    }

    private bool BothOnStairs()
    {
        return IsOnStairs(transform) && IsOnStairs(player);
    }

    private float PlayerFeetY()
    {
        if (player == null) return 0f;
        var cc = player.GetComponent<CharacterController>();
        return cc != null ? player.position.y + cc.center.y - cc.height * 0.5f : player.position.y - 1f;
    }

    private bool IsPlayerAtSameHeight()
    {
        if (player == null) return false;
        float dy = Mathf.Abs(PlayerFeetY() - transform.position.y);
        float allowed = AnyoneOnStairs() && stairsHeightDifference > 0f ? stairsHeightDifference : (maxFloorHeightDifference > 0f ? maxFloorHeightDifference : 2f);
        return dy <= allowed;
    }

    private bool IsPlayerAtAttackHeight()
    {
        if (player == null) return false;
        float dy = Mathf.Abs(PlayerFeetY() - transform.position.y);
        float allowed = BothOnStairs() && stairsAttackHeightDifference > 0f ? stairsAttackHeightDifference : (maxAttackHeightDifference > 0f ? maxAttackHeightDifference : 1f);
        return dy <= allowed;
    }

    private void RefreshHidingTracking()
    {
        if (player == null) return;
        if (trackedHidingController == null) trackedHidingController = player.GetComponent<PlayerHidingController>();
        bool hidingNow = trackedHidingController != null && trackedHidingController.IsCurrentlyHiding;
        if (hidingNow && !wasPlayerHidingLastFrame)
        {
            hiddenSpot = trackedHidingController.CurrentSpot;
            witnessedPlayerHideThisSession = Time.time - lastSeenPlayerTime <= sawHideGraceTime;
            if (debugNoiseLogs) Debug.Log("[Granny] player hid in " + (hiddenSpot != null ? hiddenSpot.name : "?") + ", seen: " + witnessedPlayerHideThisSession);
        }
        if (!hidingNow)
        {
            hiddenSpot = null;
            if (wasPlayerHidingLastFrame) witnessedPlayerHideThisSession = false;
        }
        isPlayerHiddenNow = hidingNow;
        wasPlayerHidingLastFrame = hidingNow;
    }

    private bool TryHandleHiddenPlayerJumpscare()
    {
        if (!isPlayerHiddenNow || !witnessedPlayerHideThisSession || hiddenSpot == null || sequenceRoutine != null) return false;
        switch (hiddenSpot.spotType)
        {
            case HidingSpot.HidingType.Bed: sequenceRoutine = StartCoroutine(BedJumpscareSequence(hiddenSpot)); break;
            case HidingSpot.HidingType.Coffin: sequenceRoutine = StartCoroutine(CoffinJumpscareSequence(hiddenSpot, trackedHidingController)); break;
            case HidingSpot.HidingType.Car: sequenceRoutine = StartCoroutine(CarJumpscareSequence(hiddenSpot, trackedHidingController)); break;
            default: sequenceRoutine = StartCoroutine(CoffinJumpscareSequence(hiddenSpot, trackedHidingController)); break;
        }
        return true;
    }

    private void HandleCustomRotation()
    {
        if (agent == null) return;
        Vector3 dir = Vector3.zero;
        if (agent.velocity.sqrMagnitude > 0.05f) dir = agent.velocity;
        else if (currentState == AIState.InvestigateSound && hasInvestigateLookTarget) dir = investigateLookTarget - transform.position;
        else if ((currentState == AIState.Chase || currentState == AIState.Attack) && player != null) dir = player.position - transform.position;
        dir.y = 0f;
        if (dir.sqrMagnitude < 0.0001f) return;
        agent.updateRotation = false;
        Quaternion want = Quaternion.LookRotation(dir);
        transform.rotation = Quaternion.RotateTowards(transform.rotation, want, (angularTurnSpeed > 0f ? angularTurnSpeed : 720f) * Time.deltaTime);
    }

    private void SetAnim(string[] names, object value)
    {
        if (animator == null) return;
        foreach (string n in names)
        {
            if (!animParams.TryGetValue(n, out AnimatorControllerParameterType t)) continue;
            if (t == AnimatorControllerParameterType.Float && value is float f) animator.SetFloat(n, f);
            else if (t == AnimatorControllerParameterType.Bool && value is bool b) animator.SetBool(n, b);
            else if (t == AnimatorControllerParameterType.Int && value is int i) animator.SetInteger(n, i);
            else if (t == AnimatorControllerParameterType.Trigger && value is bool tb && tb) animator.SetTrigger(n);
        }
    }

    private bool HasAnyParam(string[] names)
    {
        foreach (string n in names) if (animParams.ContainsKey(n)) return true;
        return false;
    }

    private void PlayState(string state)
    {
        if (animator == null || animator.runtimeAnimatorController == null) return;
        int hash = Animator.StringToHash(state);
        if (animator.HasState(0, hash) && !animator.GetCurrentAnimatorStateInfo(0).IsName(state)) animator.CrossFadeInFixedTime(hash, 0.2f, 0);
    }

    private static readonly string[] SpeedParams = { "Speed", "speed", "MoveSpeed", "Velocity", "velocity", "Blend", "Forward" };
    private static readonly string[] WalkParams = { "isWalking", "IsWalking", "Walk", "walk", "walking", "isMoving", "IsMoving", "Move" };
    private static readonly string[] RunParams = { "isRunning", "IsRunning", "Run", "run", "isChasing", "IsChasing", "Chase", "chase" };
    private static readonly string[] AttackParams = { "Attack", "attack", "Hit", "hit", "Kill", "kill", "isAttacking" };
    private static readonly string[] LookParams = { "Look", "look", "isLooking", "LookAround" };

    private void UpdateAnimatorParameters()
    {
        if (animator == null || isKilling) return;
        float v = agent != null ? agent.velocity.magnitude : 0f;
        bool moving = v > 0.12f;
        SetAnim(SpeedParams, v);
        SetAnim(WalkParams, moving);
        SetAnim(RunParams, IsChasing && moving);
        if (!HasAnyParam(SpeedParams) && !HasAnyParam(WalkParams))
            PlayState(moving ? "Walk" : (currentState == AIState.InvestigateSound || isWaitingAtPoint ? "Look" : "idle"));
        animator.speed = moving ? Mathf.Clamp(v / Mathf.Max(0.5f, patrolSpeed), 0.8f, 2.6f) : 1f;
    }

    private List<Transform> UsableWaypoints()
    {
        var list = new List<Transform>();
        if (patrolWaypoints == null) return list;
        foreach (Transform w in patrolWaypoints)
        {
            if (w == null || !w.gameObject.activeInHierarchy) continue;
            var wp = w.GetComponent<GrannyPatrolWaypoint>();
            if (wp != null && !wp.isUnlocked) continue;
            list.Add(w);
        }
        return list;
    }

    private void AutoUnlockWaypoints()
    {
        if (patrolWaypoints == null || agent == null || !agent.isOnNavMesh) return;
        foreach (Transform w in patrolWaypoints)
        {
            if (w == null) continue;
            var wp = w.GetComponent<GrannyPatrolWaypoint>();
            if (wp == null || wp.isUnlocked) continue;
            if (w.name.Contains("PlayerBedRoom") && Time.time - dayStartTime < 120f) continue;
            if (!NavMesh.CalculatePath(transform.position, w.position, NavMesh.AllAreas, doorCheckPath)) continue;
            if (doorCheckPath.status != NavMeshPathStatus.PathComplete) continue;
            bool blocked = false;
            foreach (DoorInfo info in doorInfos)
            {
                bool locked = (info.door != null && info.door.IsLocked && !grannyCanOpenLockedDoors) || (info.plankDoor != null && info.plankDoor.IsBlocked);
                if (!locked) continue;
                if (TryGetDoorBounds(info.colliders, info.renderers, out Bounds b) && PathEntryDistance(doorCheckPath.corners, b, 500f) < 500f) { blocked = true; break; }
            }
            if (!blocked) wp.UnlockWaypoint();
        }
    }

    private void CalculateRealisticIndoorPatrolRoute()
    {
        List<Transform> options = UsableWaypoints();
        if (options.Count == 0) { currentTargetWaypoint = null; return; }
        var fresh = new List<Transform>();
        foreach (Transform w in options) if (w != currentTargetWaypoint && !recentWaypoints.Contains(w)) fresh.Add(w);
        if (fresh.Count == 0) foreach (Transform w in options) if (w != currentTargetWaypoint) fresh.Add(w);
        if (fresh.Count == 0) fresh = options;
        currentTargetWaypoint = fresh[Random.Range(0, fresh.Count)];
        recentWaypoints.Add(currentTargetWaypoint);
        while (recentWaypoints.Count > Mathf.Max(1, options.Count / 2)) recentWaypoints.RemoveAt(0);
        isWaitingAtPoint = false;
        SetSpeed(patrolSpeed);
        if (agent != null && agent.isOnNavMesh)
        {
            agent.isStopped = false;
            agent.SetDestination(currentTargetWaypoint.position);
        }
    }

    private void AbandonChaseWithNearestWaypoint()
    {
        currentState = AIState.Patrol;
        playerInSight = false;
        loseSightTimer = unreachableTimer = stuckTimer = 0f;
        List<Transform> options = UsableWaypoints();
        Transform best = null;
        float bestD = float.MaxValue;
        foreach (Transform w in options)
        {
            float d = (w.position - transform.position).sqrMagnitude;
            if (d < bestD && d > 4f) { bestD = d; best = w; }
        }
        if (best != null)
        {
            currentTargetWaypoint = best;
            isWaitingAtPoint = false;
            SetSpeed(patrolSpeed);
            agent.isStopped = false;
            agent.SetDestination(best.position);
        }
        else CalculateRealisticIndoorPatrolRoute();
    }

    private bool Arrived()
    {
        return agent != null && !agent.pathPending && agent.remainingDistance <= agent.stoppingDistance + 0.25f;
    }

    private void PatrolBehavior()
    {
        if (currentTargetWaypoint == null) { CalculateRealisticIndoorPatrolRoute(); return; }
        if (isWaitingAtPoint)
        {
            patrolWaitTimer -= Time.deltaTime;
            if (patrolWaitTimer <= 0f) CalculateRealisticIndoorPatrolRoute();
            return;
        }
        if (Arrived())
        {
            isWaitingAtPoint = true;
            patrolWaitTimer = Random.Range(Mathf.Min(minWaitTime, maxWaitTime), Mathf.Max(minWaitTime, maxWaitTime));
            SetAnim(LookParams, true);
        }
        else if (!agent.pathPending && agent.pathStatus == NavMeshPathStatus.PathInvalid) CalculateRealisticIndoorPatrolRoute();
    }

    private void CheckForPlayerRealistically()
    {
        playerInSight = false;
        if (player == null || isPlayerHiddenNow || !player.gameObject.activeInHierarchy) return;
        if (Time.time < giveUpIgnoreUntil && (player.position - giveUpIgnorePosition).magnitude <= ignoreAfterGiveUpRadius) return;
        var wake = player.GetComponent<PlayerWakeUp>();
        if (wake != null && wake.IsWakingUp) return;
        Vector3 eye = transform.position + Vector3.up * 1.6f;
        Camera pc = player.GetComponentInChildren<Camera>();
        Vector3 target = pc != null ? pc.transform.position : player.position + Vector3.up * 0.6f;
        Vector3 to = target - eye;
        float dist = to.magnitude;
        if (dist > Mathf.Max(viewDistance, proximityRange)) return;
        if (!IsPlayerAtSameHeight()) return;
        Vector3 flat = new Vector3(to.x, 0f, to.z);
        bool inCone = Vector3.Angle(transform.forward, flat) <= viewAngle * 0.5f && dist <= viewDistance;
        bool close = dist <= proximityRange;
        if (!inCone && !close) return;
        if (Physics.Raycast(eye, to.normalized, out RaycastHit hit, dist, EffectiveObstacleMask, QueryTriggerInteraction.Ignore))
        {
            if (!hit.collider.transform.IsChildOf(player)) return;
        }
        playerInSight = true;
        lastSeenPlayerTime = Time.time;
        if (currentState == AIState.Patrol || currentState == AIState.InvestigateSound) TriggerChaseState();
    }

    public void HearNoise(Vector3 noiseLocation)
    {
        HearNoise(noiseLocation, "noise");
    }

    public void HearNoise(Vector3 noiseLocation, string what)
    {
        if (!CanReactToNoise(what)) return;
        targetSoundPosition = noiseLocation;
        StartInvestigation(GetStandPointNearItem(noiseLocation));
    }

    private bool CanReactToNoise(string what)
    {
        if (!active || isKilling || sequenceRoutine != null || agent == null || !agent.isOnNavMesh) return false;
        if (currentState == AIState.Chase || currentState == AIState.Attack) return false;
        if (debugNoiseLogs) Debug.Log("[Granny] heard " + what);
        return true;
    }

    private void StartInvestigation(Vector3 destination)
    {
        if (wonderRoutine != null) { StopCoroutine(wonderRoutine); wonderRoutine = null; }
        currentState = AIState.InvestigateSound;
        hasInvestigateLookTarget = true;
        investigateLookTarget = targetSoundPosition;
        investigateStartTime = Time.time;
        isWaitingAtPoint = false;
        patrolWaitTimer = -1f;
        SetSpeed(investigateSpeed);
        agent.isStopped = false;
        agent.SetDestination(destination);
    }

    private Vector3 GetStandPointNearItem(Vector3 itemPos)
    {
        Vector3 from = transform.position - itemPos;
        from.y = 0f;
        Vector3 p = itemPos + (from.sqrMagnitude > 0.01f ? from.normalized : Vector3.forward) * Mathf.Max(0.2f, itemStandOffDistance);
        if (NavMesh.SamplePosition(p, out NavMeshHit hit, 2.5f, NavMesh.AllAreas)) return hit.position;
        if (NavMesh.SamplePosition(itemPos, out hit, 4f, NavMesh.AllAreas)) return hit.position;
        return itemPos;
    }

    private void InvestigateSoundBehavior()
    {
        if (Time.time - investigateStartTime > 30f) { AbandonChaseWithNearestWaypoint(); return; }
        if (patrolWaitTimer < 0f)
        {
            if (Arrived() || (!agent.pathPending && agent.pathStatus != NavMeshPathStatus.PathComplete && agent.remainingDistance < 1.5f))
            {
                patrolWaitTimer = soundInvestigateWaitTime > 0f ? soundInvestigateWaitTime : 4f;
                agent.isStopped = true;
                SetAnim(LookParams, true);
            }
            return;
        }
        patrolWaitTimer -= Time.deltaTime;
        if (patrolWaitTimer <= 0f)
        {
            agent.isStopped = false;
            hasInvestigateLookTarget = false;
            AbandonChaseWithNearestWaypoint();
        }
    }

    private void ChaseBehavior()
    {
        if (player == null) { AbandonChaseWithNearestWaypoint(); return; }
        if (isPlayerHiddenNow)
        {
            if (TryHandleHiddenPlayerJumpscare()) return;
            if (wonderRoutine == null) wonderRoutine = StartCoroutine(WonderAndGiveUpRoutine());
            return;
        }
        agent.isStopped = false;
        if (playerInSight)
        {
            loseSightTimer = 0f;
            agent.SetDestination(player.position);
            float d = Vector3.Distance(new Vector3(transform.position.x, 0f, transform.position.z), new Vector3(player.position.x, 0f, player.position.z));
            if (d <= CurrentAttackRange && IsPlayerAtAttackHeight() && HasClearAttackLine() && Time.time >= nextAttackTime)
            {
                currentState = AIState.Attack;
                return;
            }
        }
        else
        {
            loseSightTimer += Time.deltaTime;
            if (loseSightTimer > loseSightGraceTime && wonderRoutine == null)
            {
                wonderRoutine = StartCoroutine(WonderAndGiveUpRoutine());
                return;
            }
        }
        if (!agent.pathPending && agent.pathStatus != NavMeshPathStatus.PathComplete) unreachableTimer += Time.deltaTime;
        else unreachableTimer = Mathf.Max(0f, unreachableTimer - Time.deltaTime);
        if (agent.velocity.magnitude < Mathf.Max(0.05f, stuckSpeedThreshold) && agent.remainingDistance > CurrentAttackRange) stuckTimer += Time.deltaTime;
        else stuckTimer = 0f;
        if ((maxUnreachableChaseTime > 0f && unreachableTimer > maxUnreachableChaseTime) || (maxStuckChaseTime > 0f && stuckTimer > maxStuckChaseTime))
        {
            giveUpIgnoreUntil = Time.time + Mathf.Max(1f, ignoreAfterGiveUpTime);
            giveUpIgnorePosition = player.position;
            isGivingUpChase = true;
            AbandonChaseWithNearestWaypoint();
            isGivingUpChase = false;
        }
    }

    private IEnumerator WonderAndGiveUpRoutine()
    {
        float wonderElapsed = 0f;
        agent.isStopped = true;
        SetAnim(LookParams, true);
        while (wonderElapsed < 2.5f)
        {
            wonderElapsed += Time.deltaTime;
            if (playerInSight && !isPlayerHiddenNow)
            {
                agent.isStopped = false;
                wonderRoutine = null;
                yield break;
            }
            yield return null;
        }
        agent.isStopped = false;
        wonderRoutine = null;
        AbandonChaseWithNearestWaypoint();
    }

    private void TriggerChaseState()
    {
        if (wonderRoutine != null) { StopCoroutine(wonderRoutine); wonderRoutine = null; }
        currentState = AIState.Chase;
        isWaitingAtPoint = false;
        hasInvestigateLookTarget = false;
        loseSightTimer = unreachableTimer = stuckTimer = 0f;
        SetSpeed(chaseSpeed);
        agent.isStopped = false;
        if (grannyVoiceLines != null && grannyVoiceLines.Count > 0 && audioSource != null && Random.value < 0.6f)
        {
            AudioClip c = grannyVoiceLines[Random.Range(0, grannyVoiceLines.Count)];
            if (c != null) audioSource.PlayOneShot(c);
        }
    }

    // ---------------------------------------------------------------- doors
    private void ResolveDoors()
    {
        doorInfos.Clear();
        if (doorObjects != null)
            foreach (GameObject go in doorObjects)
                if (go != null) AddDoor(FindDoorComponent(go), go.GetComponentInChildren<PlankLockedDoorInteractable>());
        if (doorInfos.Count == 0 || autoFindDoorsIfListEmpty)
        {
            foreach (DoorInteractable d in FindObjectsByType<DoorInteractable>(FindObjectsInactive.Exclude, FindObjectsSortMode.None)) AddDoor(d, null);
            foreach (PlankLockedDoorInteractable p in FindObjectsByType<PlankLockedDoorInteractable>(FindObjectsInactive.Exclude, FindObjectsSortMode.None)) AddDoor(null, p);
        }
    }

    private void AddDoor(DoorInteractable door, PlankLockedDoorInteractable plank)
    {
        Component c = door != null ? door : (Component)plank;
        if (c == null) return;
        foreach (DoorInfo i in doorInfos) if (i.door == door && i.plankDoor == plank) return;
        // only real doors (big enough to walk through), not cupboard doors
        Collider[] cols = c.GetComponentsInChildren<Collider>();
        Renderer[] rens = c.GetComponentsInChildren<Renderer>();
        if (TryGetDoorBounds(cols, rens, out Bounds b) && b.size.y < 1.4f) return;
        doorInfos.Add(new DoorInfo { door = door, plankDoor = plank, colliders = cols, renderers = rens });
    }

    private static DoorInteractable FindDoorComponent(GameObject go)
    {
        DoorInteractable d = go.GetComponent<DoorInteractable>();
        if (d == null) d = go.GetComponentInChildren<DoorInteractable>();
        if (d == null) d = go.GetComponentInParent<DoorInteractable>();
        return d;
    }

    private static bool TryGetDoorBounds(Collider[] colliders, Renderer[] renderers, out Bounds bounds)
    {
        bounds = new Bounds();
        bool any = false;
        if (colliders != null)
            foreach (Collider c in colliders)
            {
                if (c == null || c.isTrigger) continue;
                if (!any) { bounds = c.bounds; any = true; } else bounds.Encapsulate(c.bounds);
            }
        if (!any && renderers != null)
            foreach (Renderer r in renderers)
            {
                if (r == null) continue;
                if (!any) { bounds = r.bounds; any = true; } else bounds.Encapsulate(r.bounds);
            }
        return any;
    }

    private bool IsDoorClosedAndRelevant(DoorInfo info, out Bounds bounds)
    {
        bounds = new Bounds();
        bool closed = info.door != null ? !info.door.isOpen : (info.plankDoor != null && !info.plankDoor.isOpen);
        if (!closed) return false;
        if (info.door != null && info.door == lastOpenedDoor && Time.time < lastOpenedDoorIgnoreUntil) return false;
        return TryGetDoorBounds(info.colliders, info.renderers, out bounds);
    }

    private static bool InsideFlat(Bounds b, Vector3 p, float margin)
    {
        return p.x >= b.min.x - margin && p.x <= b.max.x + margin && p.z >= b.min.z - margin && p.z <= b.max.z + margin
            && p.y >= b.min.y - 1.5f && p.y <= b.max.y + 0.5f;
    }

    private float PathEntryDistance(Vector3[] corners, Bounds b, float maxDistance)
    {
        if (corners == null || corners.Length < 2) return float.MaxValue;
        float travelled = 0f;
        for (int i = 0; i < corners.Length - 1; i++)
        {
            Vector3 a = corners[i], c = corners[i + 1];
            float len = Vector3.Distance(a, c);
            int steps = Mathf.Max(1, Mathf.CeilToInt(len / 0.2f));
            for (int s = 0; s <= steps; s++)
            {
                float t = (float)s / steps;
                Vector3 p = Vector3.Lerp(a, c, t);
                if (InsideFlat(b, p, DoorPathMargin)) return travelled + len * t;
            }
            travelled += len;
            if (travelled > maxDistance) break;
        }
        return float.MaxValue;
    }

    private DoorInfo FindDoorOnPath()
    {
        if (agent == null || !agent.hasPath) return null;
        Vector3[] corners = agent.path.corners;
        DoorInfo best = null;
        float bestD = doorStopDistance + 0.6f;
        foreach (DoorInfo info in doorInfos)
        {
            if (!IsDoorClosedAndRelevant(info, out Bounds b)) continue;
            float d = PathEntryDistance(corners, b, bestD + 1f);
            if (d < bestD) { bestD = d; best = info; }
        }
        return best;
    }

    private bool PathCrossesDoor(DoorInfo info, Vector3 target)
    {
        if (!NavMesh.CalculatePath(transform.position, target, NavMesh.AllAreas, doorCheckPath)) return false;
        return TryGetDoorBounds(info.colliders, info.renderers, out Bounds b) && PathEntryDistance(doorCheckPath.corners, b, 500f) < 500f;
    }

    private bool CanCheckDoorsNow()
    {
        if (Time.time < nextDoorPathCheck) return false;
        nextDoorPathCheck = Time.time + 0.15f;
        return true;
    }

    private bool HandleDoorsInUpdate()
    {
        if (doorPhase != DoorPhase.None)
        {
            UpdateDoorStop();
            return true;
        }
        if (doorInfos.Count == 0 || !CanCheckDoorsNow()) return false;
        DoorInfo d = FindDoorOnPath();
        if (d == null) return false;
        StartDoorStop(d, false);
        return true;
    }

    private bool TickDoorDuringSequence()
    {
        if (doorPhase != DoorPhase.None) { UpdateDoorStop(); return true; }
        if (doorInfos.Count == 0 || !CanCheckDoorsNow()) return false;
        DoorInfo d = FindDoorOnPath();
        if (d == null) return false;
        StartDoorStop(d, true);
        return true;
    }

    private void StartDoorStop(DoorInfo info, bool inSequence)
    {
        currentDoor = info;
        doorStopInSequence = inSequence;
        doorPhase = DoorPhase.Waiting;
        doorTimer = Mathf.Max(0f, doorOpenDelay);
        agent.isStopped = true;
        agent.velocity = Vector3.zero;
        if (debugDoorLogs) Debug.Log("[Granny] stopping at door " + (info.door != null ? info.door.name : info.plankDoor.name));
    }

    private void UpdateDoorStop()
    {
        if (currentDoor == null) { CancelDoorStop(); return; }
        FaceCurrentDoor();
        doorTimer -= Time.deltaTime;
        if (doorPhase == DoorPhase.Waiting)
        {
            if (ShouldStopWaitingAtDoor()) { CancelDoorStop(); return; }
            if (doorTimer > 0f) return;
            bool opened;
            if (currentDoor.door != null)
            {
                opened = currentDoor.door.OpenForGranny(grannyCanOpenLockedDoors);
                if (opened) { lastOpenedDoor = currentDoor.door; lastOpenedDoorIgnoreUntil = Time.time + 6f; }
            }
            else if (currentDoor.plankDoor != null && !currentDoor.plankDoor.IsBlocked)
            {
                currentDoor.plankDoor.OpenOrClose(true);
                opened = true;
            }
            else opened = false;
            if (!opened) { HandleLockedDoor(); return; }
            PlayDoorOpenAnimation();
            doorPhase = DoorPhase.Passing;
            doorTimer = doorPassDelay > 0f ? doorPassDelay : 0.5f;
            return;
        }
        if (doorPhase == DoorPhase.Passing && doorTimer <= 0f) CancelDoorStop();
    }

    private bool ShouldStopWaitingAtDoor()
    {
        bool open = currentDoor.door != null ? currentDoor.door.isOpen : currentDoor.plankDoor != null && currentDoor.plankDoor.isOpen;
        return open;
    }

    private void HandleLockedDoor()
    {
        CancelDoorStop();
        if (currentState == AIState.Chase || currentState == AIState.InvestigateSound)
        {
            giveUpIgnoreUntil = Time.time + 3f;
            if (player != null) giveUpIgnorePosition = player.position;
        }
        if (sequenceRoutine != null) { StopCoroutine(sequenceRoutine); sequenceRoutine = null; }
        AbandonChaseWithNearestWaypoint();
    }

    private void CancelDoorStop()
    {
        doorPhase = DoorPhase.None;
        currentDoor = null;
        if (agent != null && agent.isOnNavMesh) agent.isStopped = false;
    }

    private void FaceCurrentDoor()
    {
        if (currentDoor == null) return;
        Component c = currentDoor.door != null ? currentDoor.door : (Component)currentDoor.plankDoor;
        if (c == null) return;
        Vector3 dir = c.transform.position - transform.position;
        dir.y = 0f;
        if (dir.sqrMagnitude > 0.01f)
            transform.rotation = Quaternion.RotateTowards(transform.rotation, Quaternion.LookRotation(dir), 360f * Time.deltaTime);
    }

    private void PlayDoorOpenAnimation()
    {
        if (animator != null && !string.IsNullOrEmpty(doorOpenAnimTrigger) && animParams.ContainsKey(doorOpenAnimTrigger))
            animator.SetTrigger(doorOpenAnimTrigger);
    }

    // ---------------------------------------------------------------- attack and kills
    private bool HasClearAttackLine()
    {
        if (player == null) return false;
        Vector3 from = transform.position + Vector3.up * 1.3f;
        Vector3 to = player.position + Vector3.up * 0.2f;
        Vector3 dir = to - from;
        if (Physics.Raycast(from, dir.normalized, out RaycastHit hit, dir.magnitude, EffectiveObstacleMask, QueryTriggerInteraction.Ignore))
            return hit.collider.transform.IsChildOf(player);
        return true;
    }

    private void OnDrawGizmosSelected()
    {
        Gizmos.color = new Color(1f, 0.3f, 0.2f, 0.4f);
        Gizmos.DrawWireSphere(transform.position, viewDistance);
        Gizmos.color = Color.red;
        Gizmos.DrawWireSphere(transform.position, attackRange);
    }

    private void TriggerPlayerItemDrop()
    {
        if (MobilePickUpScript.Instance != null) MobilePickUpScript.Instance.DropItemOnDeath();
    }

    private void AttackBehavior()
    {
        if (isKilling) return;
        nextAttackTime = Time.time + attackCooldown;
        sequenceRoutine = StartCoroutine(StandardKillSequence());
    }

    private void FacePlayerNow()
    {
        if (player == null) return;
        Vector3 d = player.position - transform.position;
        d.y = 0f;
        if (d.sqrMagnitude > 0.001f) transform.rotation = Quaternion.LookRotation(d);
    }

    private IEnumerator StandardKillSequence()
    {
        isKilling = true;
        currentState = AIState.KillSequence;
        agent.isStopped = true;
        agent.velocity = Vector3.zero;
        FacePlayerNow();
        var crouch = player != null ? player.GetComponent<MobileCrouchController>() : null;
        float standDelay = crouch != null ? crouch.StandUpForDeath() : 0f;
        if (crouch != null) crouch.SetInputLocked(true);
        if (keepViewLockedUntilDeath) BeginKillViewLock();
        if (standDelay > 0f) yield return new WaitForSeconds(standDelay + standUpExtraDelay);
        if (animator != null)
        {
            animator.speed = 1f;
            SetAnim(WalkParams, false);
            SetAnim(SpeedParams, 0f);
            if (HasAnyParam(AttackParams)) SetAnim(AttackParams, true); else PlayState("Hit");
        }
        if (hitSound != null && audioSource != null) audioSource.PlayOneShot(hitSound);
        if (JumpscareCoordinator.Instance != null)
        {
            JumpscareCoordinator.Instance.currentHidingState = JumpscareCoordinator.PlayerHidingState.None;
            JumpscareCoordinator.Instance.StartKillSequence();
        }
        else
        {
            TriggerPlayerItemDrop();
            if (DayManager.Instance != null) DayManager.Instance.TriggerNextDayScreen();
        }
        yield return StandIdleAfterKill();
    }

    private IEnumerator StandIdleAfterKill()
    {
        yield return new WaitForSeconds(1.2f);
        if (animator != null) PlayState("idle");
        ReleaseKillViewLock();
        sequenceRoutine = null;
    }

    private void HandleFootsteps(float currentSpeedSetting)
    {
        if (walkSound == null || audioSource == null || agent == null) return;
        float v = agent.velocity.magnitude;
        if (v < 0.15f) { footstepTimer = 0f; return; }
        footstepTimer -= Time.deltaTime;
        if (footstepTimer > 0f) return;
        footstepTimer = footstepInterval * Mathf.Clamp(patrolSpeed / Mathf.Max(0.3f, v), 0.45f, 1.5f);
        audioSource.PlayOneShot(walkSound, IsChasing ? 0.9f : 0.7f);
    }

    private IEnumerator GoTo(Vector3 point, float speed, float within, float timeout)
    {
        if (NavMesh.SamplePosition(point, out NavMeshHit hit, 2.5f, NavMesh.AllAreas)) point = hit.position;
        SetSpeed(speed);
        agent.isStopped = false;
        agent.SetDestination(point);
        float t = 0f;
        while (t < timeout)
        {
            if (TickDoorDuringSequence()) { yield return null; continue; }
            if (!agent.pathPending && (agent.remainingDistance <= within || (transform.position - point).magnitude <= within)) break;
            t += Time.deltaTime;
            yield return null;
        }
        agent.isStopped = true;
        agent.velocity = Vector3.zero;
    }

    private IEnumerator BedJumpscareSequence(HidingSpot bedSpot)
    {
        currentState = AIState.Chase;
        Vector3 bedPos = bedSpot.hidePosition != null ? bedSpot.hidePosition.position : bedSpot.transform.position;
        yield return GoTo(bedPos, chaseSpeed, 1.4f, 20f);
        float waited = 0f;
        float wait = bedKillWaitTime > 0f ? bedKillWaitTime : 2f;
        SetAnim(LookParams, true);
        PlayState("lookBed");
        while (waited < wait)
        {
            if (!IsPlayerStillHidingIn(bedSpot)) { AbortBedJumpscare(); yield break; }
            waited += Time.deltaTime;
            yield return null;
        }
        isKilling = true;
        currentState = AIState.KillSequence;
        if (JumpscareCoordinator.Instance != null)
        {
            JumpscareCoordinator.Instance.currentHidingState = JumpscareCoordinator.PlayerHidingState.UnderBed;
            JumpscareCoordinator.Instance.StartKillSequence();
        }
        else if (DayManager.Instance != null) DayManager.Instance.TriggerNextDayScreen();
        if (hitSound != null && audioSource != null) audioSource.PlayOneShot(hitSound);
        yield return StandIdleAfterKill();
    }

    private bool IsPlayerStillHidingIn(HidingSpot spot)
    {
        return trackedHidingController != null && trackedHidingController.IsCurrentlyHiding && trackedHidingController.CurrentSpot == spot;
    }

    private void AbortBedJumpscare()
    {
        sequenceRoutine = null;
        agent.isStopped = false;
        if (player != null && !isPlayerHiddenNow) TriggerChaseState();
        else AbandonChaseWithNearestWaypoint();
    }

    private IEnumerator CoffinJumpscareSequence(HidingSpot coffinSpot, PlayerHidingController hidingController)
    {
        currentState = AIState.Chase;
        Vector3 pos = coffinSpot.transform.position;
        yield return GoTo(pos, chaseSpeed, 1.5f, 20f);
        float waitedAtSpot = 0f;
        while (waitedAtSpot < Mathf.Max(1f, bedKillWaitTime))
        {
            if (!IsPlayerStillHidingIn(coffinSpot)) { AbortBedJumpscare(); yield break; }
            waitedAtSpot += Time.deltaTime;
            yield return null;
        }
        coffinSpot.PlayOpenAnimation();
        isKilling = true;
        currentState = AIState.KillSequence;
        if (JumpscareCoordinator.Instance != null)
        {
            JumpscareCoordinator.Instance.currentHidingState = JumpscareCoordinator.PlayerHidingState.InCoffin;
            JumpscareCoordinator.Instance.SetPullOutPoint(transform.position + transform.forward * 0.8f);
            JumpscareCoordinator.Instance.StartKillSequence();
        }
        else if (DayManager.Instance != null) DayManager.Instance.TriggerNextDayScreen();
        if (hitSound != null && audioSource != null) audioSource.PlayOneShot(hitSound);
        yield return StandIdleAfterKill();
    }

    private IEnumerator CarJumpscareSequence(HidingSpot carSpot, PlayerHidingController hidingController)
    {
        currentState = AIState.Chase;
        Vector3 entryPoint = GetCarEntryPoint(carSpot, hidingController);
        Vector3 stand = GetGrannyStandPointForCar(carSpot, entryPoint);
        yield return GoTo(stand, chaseSpeed, 0.6f, 20f);
        float waitedAtSpot = 0f;
        float wait = carKillWaitTime > 0f ? carKillWaitTime : 1.5f;
        while (waitedAtSpot < wait)
        {
            if (!IsPlayerStillHidingIn(carSpot)) { AbortBedJumpscare(); yield break; }
            waitedAtSpot += Time.deltaTime;
            yield return null;
        }
        isKilling = true;
        currentState = AIState.KillSequence;
        if (JumpscareCoordinator.Instance != null)
        {
            JumpscareCoordinator.Instance.currentHidingState = JumpscareCoordinator.PlayerHidingState.None;
            JumpscareCoordinator.Instance.SetPullOutPoint(entryPoint);
            if (hidingController != null) hidingController.ForceResetHidingState();
            JumpscareCoordinator.Instance.StartKillSequence();
        }
        else if (DayManager.Instance != null) DayManager.Instance.TriggerNextDayScreen();
        if (hitSound != null && audioSource != null) audioSource.PlayOneShot(hitSound);
        yield return StandIdleAfterKill();
    }

    private Vector3 GetCarEntryPoint(HidingSpot carSpot, PlayerHidingController hidingController)
    {
        if (hidingController != null && hidingController.PreHidePosition != Vector3.zero) return hidingController.PreHidePosition;
        return carSpot.transform.position + carSpot.transform.right * 1.2f;
    }

    private Vector3 GetGrannyStandPointForCar(HidingSpot carSpot, Vector3 entryPoint)
    {
        if (carSpot.grannyApproachPoint != null) return carSpot.grannyApproachPoint.position;
        Vector3 outward = entryPoint - carSpot.transform.position;
        outward.y = 0f;
        if (outward.sqrMagnitude < 0.01f) outward = carSpot.transform.right;
        return entryPoint + outward.normalized * (carGrannyStandOff > 0f ? carGrannyStandOff : 0.7f);
    }

    /// <summary>New day: back to her spawn point, calm, patrolling.</summary>
    public void ResetAIStateForNextDay()
    {
        if (sequenceRoutine != null) { StopCoroutine(sequenceRoutine); sequenceRoutine = null; }
        if (wonderRoutine != null) { StopCoroutine(wonderRoutine); wonderRoutine = null; }
        ReleaseKillViewLock();
        isKilling = false;
        playerInSight = false;
        witnessedPlayerHideThisSession = false;
        doorPhase = DoorPhase.None;
        currentDoor = null;
        loseSightTimer = unreachableTimer = stuckTimer = 0f;
        giveUpIgnoreUntil = 0f;
        lastSeenPlayerTime = -100f;
        dayStartTime = Time.time;
        if (musicSource != null) { musicSource.Stop(); musicSource.volume = 0f; }
        Vector3 pos = spawnPoint != null ? spawnPoint.position : startPosition;
        Quaternion rot = spawnPoint != null ? spawnPoint.rotation : startRotation;
        if (agent != null)
        {
            if (NavMesh.SamplePosition(pos, out NavMeshHit hit, 4f, NavMesh.AllAreas)) pos = hit.position;
            agent.Warp(pos);
            agent.isStopped = false;
        }
        else transform.position = pos;
        transform.rotation = rot;
        if (animator != null) { animator.speed = 1f; animator.Rebind(); animator.Update(0f); }
        currentState = AIState.Patrol;
        CalculateRealisticIndoorPatrolRoute();
    }
}

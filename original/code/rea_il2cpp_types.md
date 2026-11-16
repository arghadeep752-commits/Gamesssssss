# Game classes found by rea (il2cpp)

212 classes in the game's own code (engine and library classes left out).

## AdsManager  _(Assembly-CSharp.dll)_
- fields: Instance, androidGameId, iosGameId, testMode, androidInterstitialId, androidRewardedId, iosInterstitialId, iosRewardedId, eventMappings, interstitialEveryNTimes, loadRetryDelay, maxLoadRetries, gameId, interstitialAdUnitId, rewardedAdUnitId, eventAdTypeMap, isAdLoaded, eventFireCounts, isAdLoading, loadRetryCounts, isShowingAd, pendingRewardCallback, pendingAdClosedCallback, pendingAdUnitBeingShown
- properties: IsShowingAd, IsTestMode
- methods: get_IsShowingAd, Awake, BuildEventMap, InitializeAds, PreloadAdForEvent, IsAdReadyForEvent, HasAdForEvent, GetAdTypeForEvent, IsLoaded, IsLoading, TriggerAd, ShowRewardedAd, ShowInterstitialAd, get_IsTestMode, ShowRewardedInternal, ShowInterstitialInternal, LoadInterstitialAd, LoadRewardedAd, SafeLoad, RetryLoadAfterDelay, OnInitializationComplete, OnInitializationFailed, OnUnityAdsAdLoaded, OnUnityAdsFailedToLoad, OnUnityAdsShowFailure, OnUnityAdsShowComplete, FireAdClosedAndReload, OnUnityAdsShowStart, OnUnityAdsShowClick, .ctor

## AdsManager/<RetryLoadAfterDelay>d__48  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this, adUnitId
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## AdsManager/AdEventMapping  _(Assembly-CSharp.dll)_
- fields: eventKey, adType
- methods: .ctor

## AdsManager/AdType  _(Assembly-CSharp.dll)_
- fields: value__, None, Interstitial, Rewarded

## AdsManager/Events  _(Assembly-CSharp.dll)_
- fields: PLAYER_DEATH, GAME_END, LEVEL_COMPLETE, CONTINUE_RUN, DOUBLE_REWARD

## AntiClippingItem  _(Assembly-CSharp.dll)_
- fields: forwardDistance, sideOffset, heightOffset, visualScale, originalLocalPosition, originalLocalScale
- methods: Start, OnValidate, ApplyPositionAndScale, .ctor

## BalloonBurnerZone  _(Assembly-CSharp.dll)_
- fields: mainBalloonScript
- methods: OnBurnerIgnited, .ctor

## BalloonCylinderSlot  _(Assembly-CSharp.dll)_
- fields: mainBalloonScript
- methods: .ctor

## BalloonHoleZone  _(Assembly-CSharp.dll)_
- fields: mainBalloonScript, repairSound
- methods: FixHoleWithTape, .ctor

## CabinetInteractable  _(Assembly-CSharp.dll)_
- fields: openDistance, doorSpeed, openSound, closeSound, isOpen, isMoving, myAudioSource, closedPosition, openPosition, targetPosition
- methods: Start, Update, Interact, .ctor

## ChatController  _(Assembly-CSharp.dll)_
- fields: ChatInputField, ChatDisplayOutput, ChatScrollbar
- methods: OnEnable, OnDisable, AddToChatOutput, .ctor

## CoffinDoorInteractable  _(Assembly-CSharp.dll)_
- fields: batJumpscareSystem, jumpscareAudioClip, hasTriggeredScare
- methods: Awake, CheckForDoorOpenRoutine, TriggerBatJumpscare, .ctor

## CoffinDoorInteractable/<CheckForDoorOpenRoutine>d__4  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## CreakingFloor  _(Assembly-CSharp.dll)_
- fields: audioSource, creakSounds, normalHearingRadius, hardHearsFromAnywhere, extremeHearsFromAnywhere, cooldownTime, isCoolingDown
- methods: OnTriggerEnter, GetDifficulty, PlayCreakSoundAndAlert, AlertGranny, ResetCooldown, OnDrawGizmosSelected, .ctor

## CutObjectPhysics  _(Assembly-CSharp.dll)_
- fields: sidewaysForce, tipTorque, rb
- methods: Awake, TriggerSidewaysFall, .ctor

## DayManager  _(Assembly-CSharp.dll)_
- fields: <Instance>k__BackingField, deathCanvas, dayText, dayFont, dayStyleSaved, savedFont, savedMaterial, savedFontSize, savedFontStyle, savedColor, savedAutoSize, savedAlignment, lastDayMessage, deathFadeInDuration, dayTextHoldTime, nextDaySound, nextDaySoundVolume, showAdAfterDeath, maxWaitForAdToLoad, gameOverSceneName, maxDays, currentDay, audioSource, fadeDurationForThisDeath
- properties: Instance
- methods: get_Instance, set_Instance, Awake, Start, SaveDayTextStyle, SetDayText, LateUpdate, InitialStartDaySequence, TriggerNextDayScreen, TriggerNextDayScreen, GetDeathCanvasGroup, FadeDeathCanvasIn, ShowDeathAdOnBlackScreen, PlayNextDaySound, FadeThenGameOver, LocalNextDaySequence, GameOverSequence, .ctor

## DayManager/<>c__DisplayClass37_0  _(Assembly-CSharp.dll)_
- fields: adClosed
- methods: .ctor

## DayManager/<FadeDeathCanvasIn>d__36  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this, <group>5__2, <duration>5__3, <elapsed>5__4
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## DayManager/<FadeThenGameOver>d__39  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## DayManager/<GameOverSequence>d__41  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## DayManager/<InitialStartDaySequence>d__31  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this, <mobileCanvas>5__2
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## DayManager/<LocalNextDaySequence>d__40  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this, <mobileCanvas>5__2, <targetDropPos>5__3
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## DayManager/<ShowDeathAdOnBlackScreen>d__37  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this, <>8__1, <ads>5__2, <waited>5__3, <noAdTimer>5__4
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## DistractionObject  _(Assembly-CSharp.dll)_
- fields: resetDelay, returnSpeed, crashSound, noiseVelocityThreshold, soundAlertRadius, rb, audioSource, originalLocalPosition, originalLocalRotation, originalParent, hasCrashed, isResetting
- methods: Start, OnCollisionEnter, PlayCrashNoise, AlertGrannyAI, StartResetTimer, .ctor

## DistractionObject/<StartResetTimer>d__16  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this, <targetWorldPosition>5__2, <targetWorldRotation>5__3
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## DoorInteractable  _(Assembly-CSharp.dll)_
- fields: openAngle, doorSpeed, requiredLock, lockedNotificationText, lockedRattleAngle, lockedRattleDuration, lockedRattleCount, openSound, closeSound, lockedSound, isOpen, isMoving, isShaking, navMeshObstacle, myAudioSource, doorCollider, closedRotation, openRotation, targetRotation
- methods: Start, Update, Interact, TriggerLockedBehavior, ShakeDoorRoutine, .ctor

## DoorInteractable/<ShakeDoorRoutine>d__24  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this, <originalLocalRotation>5__2, <direction>5__3, <pushes>5__4, <elapsed>5__5
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## DoorInteractable/LockType  _(Assembly-CSharp.dll)_
- fields: value__, None, PadlockKey, MasterKey, GoldKey, CarKey

## DoorLockComponent  _(Assembly-CSharp.dll)_
- fields: lockType, requiredItemName, doorManager, audioSource, interactionSound, padlockCodeRigidbody, tightChains, hangingChains
- methods: Start, Interact, BreakPlank, DropPadlockCode, UnlockPadlock, CutChains, PlaySoundAndAlertGranny, AlertGrannyAI, .ctor

## DoorPlankComponent  _(Assembly-CSharp.dll)_
- fields: isRemoved
- methods: RemovePlank, DropPlankAnimation, IsRemoved, .ctor

## DoorPlankComponent/<DropPlankAnimation>d__2  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this, <elapsed>5__2, <startPos>5__3, <startRot>5__4
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## DrawerInteractable  _(Assembly-CSharp.dll)_
- fields: openDistance, slideSpeed, openSound, closeSound, contentsCenter, contentsSize, autoBoxShrink, settleSpeed, isOpen, myAudioSource, closedLocalPosition, openLocalPosition, targetLocalPosition, heldItems, lastWorldPosition, scanTimer, overlapBuffer
- methods: Start, Update, Interact, CaptureItemsInside, IsAlreadyHeld, AutoFitContentsBox, OnDrawGizmosSelected, .ctor

## DrawerInteractable/HeldEntry  _(Assembly-CSharp.dll)_
- fields: rb, item, wasKinematic
- methods: .ctor

## DrawerPivotAnimation  _(Assembly-CSharp.dll)_
- fields: isOpen, openDistance, slideSpeed, audioSource, openSound, closeSound, handButtonUI, interactionDistance, closedPosition, openPosition, targetPosition, playerTransform
- methods: Start, Update, Interact, .ctor

## DropdownSample  _(Assembly-CSharp.dll)_
- fields: text, dropdownWithoutPlaceholder, dropdownWithPlaceholder
- methods: OnButtonClick, .ctor

## EnvMapAnimator  _(Assembly-CSharp.dll)_
- fields: RotationSpeeds, m_textMeshPro, m_material
- methods: Awake, Start, .ctor

## EnvMapAnimator/<Start>d__4  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this, <matrix>5__2
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## EscapeItemController  _(Assembly-CSharp.dll)_
- fields: itemType, matchingHandVisual, associatedLockCube, pickupSound, groundImpactSound, escapeSceneName, escapeOnPickupIfDoorUnlocked, isPickedUp
- methods: OnTriggerEnter, SafePhysicsDrop, .ctor

## EscapeItemController/<SafePhysicsDrop>d__10  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, targetCube, <>4__this, <blockAudio>5__2
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## EscapeItemController/ItemIdentity  _(Assembly-CSharp.dll)_
- fields: value__, Hammer, ChainCutter, PadlockKey, PadlockCode, MasterKey

## EscapeLockElement  _(Assembly-CSharp.dll)_
- fields: lockType, requiredItemName, missingItemAlertText, isUnlocked, requiredForEscape, audioSource, interactionSound, tightChainsGroup, looseChainsGroup, bookshelfSlideOffset, bookshelfSlideSpeed, winSceneName, fallOnUnlock, popOffForce, alertGrannyOnLand, landSound, landSoundVolume, minImpactSpeed, fallenLayerName, isFalling, hasLanded, fallStartTime, plankCleared, codeCleared, padlockCleared, chainCleared, bookshelfCleared
- methods: ResetStaticStates, AreAllDoorLocksCleared, LogLockedDoorLocks, IsEffectivelyUnlocked, GetPath, CountLockedDoorLocks, SceneHasDoorLocks, InteractWithLock, ActivateFallingPhysics, DropToFloor, OnCollisionEnter, LandFallbackRoutine, OnLanded, SetLayerRecursively, SlideBookshelfRoutine, CheckFinalEscapeState, PlayLockSound, .ctor

## EscapeLockElement/<LandFallbackRoutine>d__38  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## EscapeLockElement/<SlideBookshelfRoutine>d__41  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this, <startPos>5__2, <targetPos>5__3, <elapsedTime>5__4
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## EscapeLockType  _(Assembly-CSharp.dll)_
- fields: value__, WoodenPlank, PadlockCode, PadlockKey, Chain, SecretBookshelf, MasterKeyDoor

## EscapeSceneController  _(Assembly-CSharp.dll)_
- fields: escapeDuration, mainMenuSceneName
- methods: Start, WaitAndGoToMenu, LoadMainMenu, .ctor

## EscapeSceneController/<WaitAndGoToMenu>d__3  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## EscapeSequenceManager  _(Assembly-CSharp.dll)_
- fields: fadeAnimator, playerObject, mainGameplayCamera, cutsceneCamera, balloonAnimator
- methods: StartEscapeCutscene, EscapeRoutine, .ctor

## EscapeSequenceManager/<EscapeRoutine>d__6  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## ExtremeFenceLock  _(Assembly-CSharp.dll)_
- fields: audioSource, fenceOpeningSound
- methods: Start, UnlockAndRemoveFence, .ctor

## FPSController  _(Assembly-CSharp.dll)_
- fields: moveSpeed, mouseSensitivity, gravity, joystick, touchLookScale, touchLookSmoothing, mobileTargetFrameRate, lookFingerId, smoothedTouchDelta, controller, cam, xRotation, velocity, hidingController, isFirstFrameAfterEnable
- methods: Start, OnEnable, ResetGravityVelocity, Update, ResetMovementState, .ctor

## FallingLockSound  _(Assembly-CSharp.dll)_
- fields: audioSource, floorImpactSound, hasLanded
- methods: OnCollisionEnter, .ctor

## FallingPainting  _(Assembly-CSharp.dll)_
- fields: noiseRadius, grannyLayer, hasFallen
- methods: OnCollisionEnter, TriggerNoise, OnDrawGizmosSelected, .ctor

## GameBackgroundOST  _(Assembly-CSharp.dll)_
- fields: <Instance>k__BackingField, ostAudioSource, targetVolume, fadeDuration, restartWhenTurnedOn, fadeRoutine, gameWantsMusic
- properties: Instance
- methods: get_Instance, set_Instance, Awake, Start, OnEnable, OnDisable, HandleMusicChanged, StartBackgroundMusic, StopBackgroundMusic, FadeOutAndStop, StartFade, FadeMusicIn, FadeMusicOut, .ctor

## GameBackgroundOST/<FadeMusicIn>d__19  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this, <elapsed>5__2
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## GameBackgroundOST/<FadeMusicOut>d__20  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this, <startVolume>5__2, <elapsed>5__3
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## GameManager  _(Assembly-CSharp.dll)_
- fields: <Instance>k__BackingField, playerGameObject, playerSpawnPoint, wakeUpScript, grannySpawnPoint, playerPickupScript
- properties: Instance
- methods: get_Instance, set_Instance, Awake, ResetPlayerForNextDay, SafeTeleportRoutine, .ctor

## GameManager/<SafeTeleportRoutine>d__11  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this, <pickupScript>5__2, <objectToPreserve>5__3, <dynamicHoldDestination>5__4, <charController>5__5, <fpsController>5__6, <granny>5__7, <grannyAgent>5__8, <targetGrannyPos>5__9
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## GameQualityApplier  _(Assembly-CSharp.dll)_
- fields: QualityIndexKey, TextureLimitKey, UnityLevelKey
- methods: ApplySavedQualityOnStartup, Apply

## GameSettingsManager  _(Assembly-CSharp.dll)_
- fields: settingsPanel, musicToggle, sensitivitySlider, quitWarningPanel, fpsController, hideWhileSettingsOpen, defaultSensitivity, isPaused, wasShowingBeforeSettings
- methods: Start, LateUpdate, HideGameplayButtons, ShowGameplayButtons, Update, OpenSettings, ResumeGame, OnMainMenuButtonClicked, CancelQuit, ConfirmQuitToMainMenu, OnMusicToggleChanged, OnSensitivitySliderChanged, ApplySensitivityState, .ctor

## GameplayManager  _(Assembly-CSharp.dll)_
- fields: <Instance>k__BackingField, currentDifficulty, darkerModeFogVolume, darkerModeAmbientColor, normalAmbientColor, extraLocksObject, extremeFenceObject, extremeLeverObject, extremeHandleObject, houseMusicSource
- properties: Instance
- methods: get_Instance, set_Instance, Awake, Start, OnPlayerCaught, OnPlayerCaught, ResetDaySequence, LoadGameSettings, OnEnable, OnDisable, OnMusicSettingChanged, ApplyHouseMusic, ApplyDifficultySettings, ApplyDarkerMode, .ctor

## GameplayManager/<ResetDaySequence>d__17  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <pTransform>5__2, <charController>5__3, <fpsController>5__4
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## GrannyAI  _(Assembly-CSharp.dll)_
- fields: currentState, useDifficultySettings, liveTuningInPlayMode, activeDifficulty, easy, normal, hard, extreme, activeSettings, patrolSpeed, chaseSpeed, investigateSpeed, angularTurnSpeed, accelerationRate, keepFullSpeedOnTurns, brakeDistance, patrolWaypoints, currentTargetWaypoint, minWaitTime, maxWaitTime, patrolWaitTimer, isWaitingAtPoint, player, viewDistance, viewAngle, proximityRange, maxFloorHeightDifference, maxAttackHeightDifference, obstacleMask, stairsLayer, stairsHeightDifference, stairsAttackHeightDifference, stairsAttackRange, stairsDetectDistance, soundInvestigateWaitTime, targetSoundPosition, itemStandOffDistance, debugNoiseLogs, hasInvestigateLookTarget, investigateLookTarget, investigateStartTime, loseSightGraceTime, loseSightTimer, maxUnreachableChaseTime, unreachableTimer, isGivingUpChase, maxStuckChaseTime, stuckSpeedThreshold, ignoreAfterGiveUpTime, ignoreAfterGiveUpRadius, stuckTimer, giveUpIgnoreUntil, giveUpIgnorePosition, attackRange, attackCooldown, nextAttackTime, bedKillWaitTime, sawHideGraceTime, carGrannyStandOff, carKillWaitTime
- properties: EffectiveObstacleMask, CurrentAttackRange
- methods: Start, InitializeAI, ApplyDifficultySettings, ApplySettingsValues, VoiceLineRoutine, Update, HandleChaseMusicFade, MaintainSpeedOnTurns, LateUpdate, GetHeadLookPoint, BeginKillViewLock, ReleaseKillViewLock, IsOnStairs, AnyoneOnStairs, BothOnStairs, get_EffectiveObstacleMask, get_CurrentAttackRange, IsPlayerAtSameHeight, IsPlayerAtAttackHeight, RefreshHidingTracking, TryHandleHiddenPlayerJumpscare, HandleCustomRotation, UpdateAnimatorParameters, CalculateRealisticIndoorPatrolRoute, AbandonChaseWithNearestWaypoint, PatrolBehavior, CheckForPlayerRealistically, HearNoise, CanReactToNoise, StartInvestigation, GetStandPointNearItem, InvestigateSoundBehavior, ChaseBehavior, WonderAndGiveUpRoutine, TriggerChaseState, ResolveDoors, AddDoor, FindDoorComponent, TryGetDoorBounds, IsDoorClosedAndRelevant, InsideFlat, PathEntryDistance, FindDoorOnPath, PathCrossesDoor, CanCheckDoorsNow, HandleDoorsInUpdate, TickDoorDuringSequence, StartDoorStop, UpdateDoorStop, ShouldStopWaitingAtDoor, HandleLockedDoor, CancelDoorStop, FaceCurrentDoor, PlayDoorOpenAnimation, HasClearAttackLine, OnDrawGizmosSelected, TriggerPlayerItemDrop, AttackBehavior, StandardKillSequence, StandIdleAfterKill, HandleFootsteps, BedJumpscareSequence, IsPlayerStillHidingIn, AbortBedJumpscare, CoffinJumpscareSequence, CarJumpscareSequence, GetCarEntryPoint, GetGrannyStandPointForCar, ResetAIStateForNextDay, .ctor

## GrannyAI/<BedJumpscareSequence>d__178  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this, bedSpot, <waited>5__2
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## GrannyAI/<CarJumpscareSequence>d__182  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this, carSpot, hidingController, <entryPoint>5__2, <waitedAtSpot>5__3
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## GrannyAI/<CoffinJumpscareSequence>d__181  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this, coffinSpot, <waitedAtSpot>5__2
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## GrannyAI/<StandIdleAfterKill>d__176  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## GrannyAI/<StandardKillSequence>d__175  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## GrannyAI/<VoiceLineRoutine>d__119  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## GrannyAI/<WonderAndGiveUpRoutine>d__150  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this, <wonderElapsed>5__2
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## GrannyAI/AIState  _(Assembly-CSharp.dll)_
- fields: value__, Patrol, Chase, Attack, KillSequence, InvestigateSound

## GrannyAI/DoorInfo  _(Assembly-CSharp.dll)_
- fields: door, colliders, renderers
- methods: .ctor

## GrannyAI/DoorPhase  _(Assembly-CSharp.dll)_
- fields: value__, None, Waiting, Passing

## GrannyDifficultySettings  _(Assembly-CSharp.dll)_
- fields: patrolSpeed, chaseSpeed, investigateSpeed, viewDistance, viewAngle, proximityRange, loseSightGraceTime, attackRange, soundInvestigateWaitTime, minWaitTime, maxWaitTime, bedKillWaitTime
- methods: .ctor, .ctor

## GrannyDrawer  _(Assembly-CSharp.dll)_
- fields: slideDistance, speed, audioSource, openSound, closeSound, isOpen, closedPosition, openPosition, targetPosition
- methods: Start, Update, ToggleDrawer, .ctor

## GrannyPatrolWaypoint  _(Assembly-CSharp.dll)_
- fields: isLockedByDefault, isUnlocked
- methods: Awake, UnlockWaypoint, .ctor

## GrannyStyleEnding  _(Assembly-CSharp.dll)_
- fields: cameraEndTarget, grannyTarget, cameraTravelDuration, lookRotationSpeed, startFadeProgressThreshold, endTextCanvasGroup, screenFadeCanvasGroup, audioSource, endSceneSoundtrack, footstepAudioSource, footstepSound, introBlackScreenDuration, enemyOneAnimator, enemyTwoAnimator, enemyAnimationTrigger, mainMenuSceneName, _travelProgress
- methods: Start, IntroThenCinematicRoutine, MoveCameraRoutine, TriggerFilmyOverlaysRoutine, FadeCanvas, .ctor

## GrannyStyleEnding/<FadeCanvas>d__21  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, cg, startAlpha, endAlpha, duration, <elapsed>5__2
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## GrannyStyleEnding/<IntroThenCinematicRoutine>d__17  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## GrannyStyleEnding/<MoveCameraRoutine>d__18  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this, <startPosition>5__2, <endPosition>5__3, <elapsed>5__4, <duration>5__5
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## GrannyStyleEnding/<TriggerFilmyOverlaysRoutine>d__20  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this, <startVolume>5__2
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## HidingCameraLook  _(Assembly-CSharp.dll)_
- fields: mobileSensitivity, pcSensitivity, targetAnchor, rotationY, HORIZONTAL_LIMIT
- methods: Activate, Deactivate, Update, .ctor

## HidingSpot  _(Assembly-CSharp.dll)_
- fields: spotType, hidePosition, grannyApproachPoint, bedNearClipPlane, dropButton, doorAnimator, openTriggerName, closeTriggerName, playerCamera, originalNearClip, isInsideSpot, rotationY
- methods: Awake, PlayOpenAnimation, PlayCloseAnimation, OnEnterHidingSpot, OnExitHidingSpot, ForceHideDropButton, CheckIfPlayerHasItem, SetHandItemsActive, SetDropButtonActive, FindDropButtonInScene, OnHoverEnter, OnHoverExit, .ctor

## HidingSpot/HidingType  _(Assembly-CSharp.dll)_
- fields: value__, Bed, Locker, Coffin, Car

## HidingSpotDistanceTracker  _(Assembly-CSharp.dll)_
- fields: activationDistance, hidingSpot, playerTransform, hidingController, playerIsClose, wasHidingLastFrame
- methods: Start, Update, CheckIfPlayerIsHiding, OnDisable, .ctor

## HidingTriggerZone  _(Assembly-CSharp.dll)_
- fields: hidingSpot
- methods: Start, OnTriggerEnter, OnTriggerExit, .ctor

## HotAirBalloonEscape  _(Assembly-CSharp.dll)_
- fields: isRepairedWithTape, hasGasCylinder, isIgnitedWithLighter, ropesCutWithChainCutter, balloonFabricAnimator, burnerFlameParticles, burnerFlameEffect, player, grannyObject, grannyRespawnPoint, screenFadeAnimator, gameplayUI, inflationDuration, basketCylinderVisual, escapeSceneName, mainMenuSceneName, riseSpeed, forwardSpeed, escapeDuration, dynamicRopeObject, crashCutsceneCamera, fabricCrashAnimationState, crashRiseHeight, riseDuration, fallDuration, explosionParticles, ruinedSmokeParticles, balloonVisualMesh, crashedBalloonVisualMesh, wakeUpPoint, crashSound, audioSource, isWorkingAndInflated, sequenceStarted, isDestroyed, mainPlayerCameraObject
- methods: Start, IsDestroyed, UseTape, InsertCylinder, UseLighter, DisappearGranny, CutRopes, InflateBalloonRoutine, TriggerLaunchAttempt, NormalEscapeRoutine, RopeCrashRoutine, RespawnGrannyAfterCrash, LockPlayerToBasket, .ctor

## HotAirBalloonEscape/<InflateBalloonRoutine>d__43  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## HotAirBalloonEscape/<NormalEscapeRoutine>d__45  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this, <timer>5__2
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## HotAirBalloonEscape/<RopeCrashRoutine>d__46  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this, <startPos>5__2, <peakPos>5__3, <elapsed>5__4, <crashAirPos>5__5, <groundTarget>5__6, <initialRot>5__7, <crashRotTarget>5__8
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## IInteractable  _(Assembly-CSharp.dll)_
- methods: Interact

## InteractableItem  _(Assembly-CSharp.dll)_
- fields: itemName, targetHoldPointName, pickupSound, dropSound, silentGroundVolume, minImpactSpeed, noiseCooldown, isHeld, myAudioSource, lastNoiseTime
- methods: Awake, UseItem, OnCollisionEnter, .ctor

## ItemBedDropHelper  _(Assembly-CSharp.dll)_
- methods: ForceDropToBedEntrance, .ctor

## ItemPresetManager  _(Assembly-CSharp.dll)_
- fields: availablePresets, allSpawnPoints, spawnedItems
- methods: Start, SpawnPresetItems, .ctor

## ItemPresetManager/ItemPlacement  _(Assembly-CSharp.dll)_
- fields: itemID, itemPrefab
- methods: .ctor

## ItemPresetManager/Preset  _(Assembly-CSharp.dll)_
- fields: presetName, itemPlacements
- methods: .ctor

## ItemRespawnZone  _(Assembly-CSharp.dll)_
- fields: respawnPoint, scatterRadius, spawnHeight
- methods: Reset, Awake, OnTriggerEnter, OnDrawGizmos, .ctor

## ItemSpawnPoint  _(Assembly-CSharp.dll)_
- fields: itemID
- methods: OnDrawGizmos, .ctor

## ItemSway  _(Assembly-CSharp.dll)_
- fields: playerTransform, playerCamera, playerRigidbody, playerController, lastPlayerPosition, swayAmount, maxSwayAmount, swaySmoothness, bobSpeed, bobAmount, obstacleLayers, detectDistance, wallPullOffset, wallRotationOffset, initialPosition, initialRotation, bobTimer
- methods: Start, Update, OnDrawGizmosSelected, .ctor

## JumpscareCoordinator  _(Assembly-CSharp.dll)_
- fields: Instance, playerTransform, playerCamera, cameraLookScript, grannyAnimator, grannyTransform, grannyAudioSource, bedGrannyAnimator, bedLookTarget, bed2GrannyAnimator, bed2LookTarget, bed3GrannyAnimator, bed3LookTarget, standardHitSound, coffinJumpscareSound, bedJumpscareSound, delayBeforeFloorFall, bedKillAnimationDuration, delayAfterBedKill, useBedDeathFadeTiming, bedDeathFadeDelay, bedDeathFadeDuration, fallGravity, lyingCameraHeight, fallRollAngle, fallPitchUp, knockbackSpeed, knockbackDeceleration, bounceRestitution, fallSettleTime, lookAtGrannyTurnSpeed, bedHeadContactDuration, gameHUD, mobileControlsCanvas, currentHidingState, hasPullOutPoint, pullOutPoint, isRotationLocked, lockedCameraRotation, lockedPlayerRotation, isFallPoseHeld, heldCamPos, heldCamRot, heldRootPos, heldUntilTime, killFpsRef, cachedWakeUp, wakingField, isBedViewHeld, isHeadTracking, grannyFaceTarget, faceTargetSearched, cachedGrannyAI
- methods: SetPullOutPoint, Awake, LateUpdate, StartKillSequence, IsActorCollider, FindFloorHeightBelow, IsBlockedHorizontally, IsPlayerWakingUp, ShouldReleaseHeldPose, GetGrannyAI, GetGrannyLookPoint, FindGrannyFaceTarget, NaturalFallToFloor, DropPlayerHeldItemAtCurrentPosition, BedHeadContactRoutine, ExecuteKillSequence, .ctor

## JumpscareCoordinator/<BedHeadContactRoutine>d__68  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this, duration
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## JumpscareCoordinator/<ExecuteKillSequence>d__69  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this, <fadeDurationOverride>5__2, <mainAgent>5__3, <forceAlignTime>5__4
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## JumpscareCoordinator/<NaturalFallToFloor>d__66  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this, <startRot>5__2, <restY>5__3, <totalDrop>5__4, <knockDirection>5__5, <pos>5__6, <verticalSpeed>5__7, <horizontalSpeed>5__8, <maxProgress>5__9, <bounces>5__10, <landed>5__11, <settleTimer>5__12, <safetyTimer>5__13
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## JumpscareCoordinator/PlayerHidingState  _(Assembly-CSharp.dll)_
- fields: value__, None, InCoffin, UnderBed

## JumpscareFadeOverlay  _(Assembly-CSharp.dll)_
- fields: overlayTex, alpha
- methods: SetupOverlay, OnGUI, .ctor

## LeverInteractable  _(Assembly-CSharp.dll)_
- fields: targetFence, hasHandlePlaced, isPulled, missingHandleVisual, rotatingHandlePivot, pulledRotationAngles, pullSpeed, audioSource, leverPullSound, requiredItemName
- methods: Start, InteractWithLever, RotateLeverDownRoutine, CheckPlayerInventory, RemoveItemFromInventory, .ctor

## LeverInteractable/<RotateLeverDownRoutine>d__12  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this, <targetRotation>5__2
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## LockType  _(Assembly-CSharp.dll)_
- fields: value__, Plank, PadlockCode, PadlockKey, Chain

## MainDoorEscape  _(Assembly-CSharp.dll)_
- fields: isPlankBroken, isPadlockUnlocked, isPadlockCodeCleared, isChainCut, escapeSceneName, doorAudioSource, doorRattleSound, masterKeyItemName
- methods: TryMasterKeyEscape, AllLocksCleared, IsHoldingMasterKey, Clean, PlayRattle, TriggerEscapeSequence, .ctor

## MainMenuManager  _(Assembly-CSharp.dll)_
- fields: gameplaySceneName, mainMenuPanel, optionsChoosePanel, goodLuckPanel, loadingPanel, darkerModeToggle, extraLocksToggle, musicToggle, menuMusicSource, qualityDropdown, defaultQualityIndex, lowTextureLimit, mediumTextureLimit, highTextureLimit, alsoChangeUnityQualityLevel, lowUnityQualityLevel, mediumUnityQualityLevel, highUnityQualityLevel, loadingText, difficultyDescriptionText, practiceText, easyText, normalText, hardText, extremeText, selectedDifficulty, isDarkerModeOn, isExtraLocksOn, isMusicOn, selectedQualityIndex, playerDarkerChoice, playerExtraLocksChoice, DarkerChoiceKey, ExtraLocksChoiceKey
- methods: Start, LoadSavedPanelPreferences, OnPlayButtonClicked, OnQuitButtonClicked, SetDifficulty, RefreshToggleInteractability, UpdateDifficultyInstruction, SetDarkerMode, SetExtraLocks, SetMusic, ApplyMenuMusic, SetQuality, ApplyAndSaveQuality, OnBackButtonClicked, OnOptionsContinueButtonClicked, OnGoodLuckContinueButtonClicked, LoadSceneWithMinimumTime, .ctor

## MainMenuManager/<LoadSceneWithMinimumTime>d__50  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this, <operation>5__2, <minimumWaitTime>5__3, <elapsedTime>5__4, <textBlinkTimer>5__5, <isTextVisible>5__6
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## MobileCrouchController  _(Assembly-CSharp.dll)_
- fields: playerCamera, crouchButton, playerMovementScript, standingSprite, crouchingSprite, timeToCrouch, standingLocalY, crouchDropAmount, standingColliderHeight, crouchingColliderHeight, standingMovementSpeed, crouchingMovementSpeed, obstacleLayers, isCrouching, buttonImage, playerCollider, playerController, hidingController, originalStandingY, inputLocked
- properties: IsCrouching
- methods: get_IsCrouching, Awake, Start, Update, ToggleCrouch, StandUpForDeath, SetInputLocked, CameraOnlyTransition, UpdateColliderDimensions, IsCeilingBlocking, ForceStandReset, ApplyMovementSpeed, TrySetSpeed, .ctor

## MobileCrouchController/<CameraOnlyTransition>d__28  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this, <targetCameraY>5__2, <currentCameraY>5__3, <elapsed>5__4
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## MobileJoystick  _(Assembly-CSharp.dll)_
- fields: joystickBackground, joystickHandle, inputVector
- properties: Horizontal, Vertical
- methods: get_Horizontal, get_Vertical, Start, OnDrag, OnPointerDown, OnPointerUp, GetInputDistance, OnDisable, .ctor

## MobilePickUpScript  _(Assembly-CSharp.dll)_
- fields: holdPoint, pickupRange, interactButton, dropButton, throwForce, itemNameText, lockedAlertText, interactPrompt, crosshairDot, autoCreatePrompt, promptSize, letterSize, promptLetter, promptRect, promptLetterText, promptVisible, useOwnTouchLook, cameraSensitivity, wallLayerMask, wallBufferOffset, heldItemCamera, pushItemAwayFromWalls, heldItemLayer, interactableLayerMask, originalItemLayer, heldItem, heldRigidbody, targetedItem, cam, xRotation, playerAudioSource, alertCoroutine, hidingController, activeHoldDestination, initialLocalPosition, heldItemOriginalScale, isTeleporting
- methods: Start, Update, SetTeleportingState, SetInteractPrompt, ApplyPromptSize, CreateDefaultPrompt, GetUsableFont, HandleTouchLook, HandleWallClipping, CheckForInteractables, UpdateButtonState, OnInteractButtonPressed, DropItem, DropItemOnDeath, DropCurrentlyHeldItem, UseHeldItem, ShowLockedNotification, DisplayAlertRoutine, ConsumeHeldItem, GetHeldItemName, RefreshHeldItemUI, SetLayerRecursively, LateUpdate, DropItemAtPosition, .ctor

## MobilePickUpScript/<>c  _(Assembly-CSharp.dll)_
- fields: <>9, <>9__46_0
- methods: .cctor, .ctor

## MobilePickUpScript/<DisplayAlertRoutine>d__54  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this, message
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## MusicSettings  _(Assembly-CSharp.dll)_
- fields: Key, OnMusicChanged
- properties: IsOn
- methods: add_OnMusicChanged, remove_OnMusicChanged, get_IsOn, SetEnabled

## ObjectPresetManager  _(Assembly-CSharp.dll)_
- fields: presetGroups
- methods: Start, ApplyRandomPreset, .ctor

## ObjectPresetManager/PresetObjectGroup  _(Assembly-CSharp.dll)_
- fields: presetName, activeObjects
- methods: .ctor

## OutdoorAmbientZone  _(Assembly-CSharp.dll)_
- fields: ambientAudioSource, fadeDuration, maxVolume, player, feetCheckDepth, allZones, mutedByDeath, zoneColliders, fadeCoroutine, playerInside, lastPlayerPos, hasLastPos
- methods: Awake, OnEnable, OnDisable, Start, Update, IsPlayerInZone, ContainsPoint, OnPlayerDied, OnNewDay, StopAmbientSoundImmediate, StartFade, FadeAudio, .ctor, .cctor

## OutdoorAmbientZone/<FadeAudio>d__23  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this, targetVolume, <startVolume>5__2, <elapsed>5__3
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## PhysicsPropHolder  _(Assembly-CSharp.dll)_
- fields: audioSource, fallSound, alertRange, triggerDistance, obstacleLayers, autoResetDelay, hasFallenFromWall, hasLandedOnGround, initialPosition, initialRotation, rb, resetCoroutine
- methods: Awake, FreezeOnWall, Update, MakePaintingFall, OnCollisionEnter, AutoResetRoutine, ResetToInitialPosition, OnDrawGizmosSelected, .ctor

## PhysicsPropHolder/<AutoResetRoutine>d__17  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## PlankLockedDoor  _(Assembly-CSharp.dll)_
- fields: blockingPlank
- methods: Awake, Interact, .ctor

## PlankLockedDoorInteractable  _(Assembly-CSharp.dll)_
- fields: openAngle, doorSpeed, requiredLock, lockedNotificationText, openSound, closeSound, lockedSound, blockingPlank, isOpen, isMoving, isShaking, navMeshObstacle, myAudioSource, doorCollider, closedRotation, openRotation, targetRotation
- methods: Start, Update, Interact, TriggerLockedBehavior, ShakeDoorRoutine, .ctor

## PlankLockedDoorInteractable/<ShakeDoorRoutine>d__22  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this, <originalLocalRotation>5__2, <elapsed>5__3
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## PlankLockedDoorInteractable/LockType  _(Assembly-CSharp.dll)_
- fields: value__, None, PadlockKey, MasterKey, GoldKey

## PlayerHidingController  _(Assembly-CSharp.dll)_
- fields: dropSpawnPoint, <ActiveHidingBed>k__BackingField, mobileHidingButton, mobileCoffinButton, mobileCarButton, joystickUI, crouchButtonUI, settingsButtonUI, playerCamera, HORIZONTAL_LOOK_LIMIT, holdStandingCameraHeight, cameraHeightBlendSpeed, lookSmoothing, transitionSpeed, isHiding, isExiting, exitLocked, preHidePosition, preHideRotation, nearbySpot, currentSpot, characterController, fpsControllerScript, originalCameraLocalRotation, rotationY, standingCameraLocalPos, hasSavedCameraPose, hidingLookRot, heldCameraLocalPos, lookFingerId
- properties: ActiveHidingBed, IsCurrentlyHiding, IsExiting, PreHidePosition
- methods: get_ActiveHidingBed, set_ActiveHidingBed, get_IsCurrentlyHiding, get_IsExiting, SetExitLocked, get_PreHidePosition, Awake, Start, SetNearbyHidingSpot, ClearNearbyHidingSpot, OnHidingButtonTapped, OnCoffinButtonTapped, OnCarButtonTapped, EnterHiding, ExitHiding, ToggleActiveInteractionButton, Update, ReadHidingLookInput, LateUpdate, TransitionToPoint, ForceResetHidingState, FindSettingsButton, .ctor

## PlayerHidingController/<>c__DisplayClass48_0  _(Assembly-CSharp.dll)_
- fields: <>4__this, exitedSpot
- methods: .ctor

## PlayerHidingController/<TransitionToPoint>d__53  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this, targetPos, targetRot, onComplete, <time>5__2, <startPos>5__3, <startRot>5__4
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## PlayerInteractionEngine  _(Assembly-CSharp.dll)_
- fields: reachDistance, mobileHandButton, hideInButtonReference, currentlyHeldItem, targetedObject, activePlank, activePlankDoor, activeDoor, activeLock, activeMasterDoor, activeDrawer, activeHidingSpot, activeBalloon, activeRopeAnchor
- methods: Start, Update, ClearTargets, ExecuteInteraction, OnHandButtonTapped, .ctor

## PlayerPushPhysics  _(Assembly-CSharp.dll)_
- fields: pushPower
- methods: OnControllerColliderHit, .ctor

## PlayerWakeUp  _(Assembly-CSharp.dll)_
- fields: playerCamera, fpsController, blinkOverlay, dayTextMesh, bedWakeUpPoint, lyingLookUpPitch, lookUpHoldTime, rollToSideDuration, sidePauseTime, sideRollAngle, onWakeUpComplete, allItemHoldPoints, screenRotationScript, joystickUIContainer, crouchButtonUI, bedHideButtonImage, riseDuration, wakeUpGroan, settleDuration, dizzySwayAmount, useEyeFocusFov, squintFovReduction, audioSource, activeWakeUpRoutine, originalStandingLocalPos, hasSavedOriginalPos, currentlyHeldItemPoint, isWakingUp, lyingPhaseActive, cachedBedHideButton, playerCam, originalFov, hasSavedFov, bodyRotationCaptured, lockedBodyRotation, camPoseRemembered, rememberedCamPos, rememberedCamRot
- methods: Awake, OnEnable, ResetWakeUpState, OnDrawGizmosSelected, ApplyInputLock, Update, LateUpdate, RememberCamPose, InputLockEnforcer, ApplyPoseWithBreathing, Dt, LyingBreathing, HoldWithBreathing, Seg, GrannyRightSideWakeUpSequence, FadeOverlay, .ctor

## PlayerWakeUp/<FadeOverlay>d__53  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this, startAlpha, endAlpha, duration, <elapsed>5__2, <col>5__3
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## PlayerWakeUp/<GrannyRightSideWakeUpSequence>d__52  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this, <hidingCtrl>5__2, <standingLocalPos>5__3, <standingLocalRot>5__4, <camParent>5__5, <bedPos>5__6, <bedRight>5__7, <bedLyingRot>5__8, <rollElapsed>5__9, <sideRestPos>5__10, <sideRestRot>5__11, <elapsed>5__12, <settleElapsed>5__13, <textFadeElapsed>5__14, <textColor>5__15
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## PlayerWakeUp/<HoldWithBreathing>d__50  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this, basePos, baseRot, duration, <held>5__2
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## PlayerWakeUp/<InputLockEnforcer>d__46  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## PlayerWakeUp/<LyingBreathing>d__49  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this, basePos, baseRot
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## RopeAnchorInteraction  _(Assembly-CSharp.dll)_
- fields: mainBalloonScript
- methods: InteractWithAnchor, .ctor

## SafeArea  _(Assembly-CSharp.dll)_
- fields: rectTransform, lastSafeArea, lastOrientation
- methods: Awake, Update, ApplySafeArea, .ctor

## SecretBookshelfDoor  _(Assembly-CSharp.dll)_
- fields: lockElement, slideOffset, slideSpeed, bookshelfAudioSource, scrapingSound, closedPosition, openPosition, standardSequenceTriggered
- methods: Start, Update, SlideOpenRoutine, .ctor

## SecretBookshelfDoor/<SlideOpenRoutine>d__10  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this, <elapsedTime>5__2, <startPos>5__3
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## SilentGroundZone  _(Assembly-CSharp.dll)_
- fields: allZones
- methods: OnEnable, OnDisable, IsSilentAt, Contains, OnDrawGizmos, .ctor, .cctor

## SmoothRope  _(Assembly-CSharp.dll)_
- fields: topPoint, bottomPoint, segments, ropeSag, lineRenderer
- methods: Start, Update, .ctor

## TimelineGameOverController  _(Assembly-CSharp.dll)_
- fields: timelineDirector, gameOverTextUI, displayDuration, mainMenuSceneName, sequenceTriggered
- methods: Start, Update, OnTimelineFinished, EndingDisplaySequence, LoadMainMenu, OnDestroy, .ctor

## TimelineGameOverController/<EndingDisplaySequence>d__8  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## TripwireTrap  _(Assembly-CSharp.dll)_
- fields: bellSound, triggerCooldown, audioSource, nextAllowedTriggerTime
- methods: Start, OnTriggerEnter, TriggerTheBell, .ctor

## UltimateEscapeEngine  _(Assembly-CSharp.dll)_
- fields: reachDistance, currentlyHeldItem, lookedAtObject, mainCam
- methods: Start, Update, TryProcessInteraction, .ctor

## UnitySourceGeneratedAssemblyMonoScriptTypes_v1  _(Assembly-CSharp.dll)_
- methods: Get, .ctor

## UnitySourceGeneratedAssemblyMonoScriptTypes_v1/MonoScriptData  _(Assembly-CSharp.dll)_
- fields: FilePathsData, TypesData, TotalTypes, TotalFiles, IsEditorOnly

## VideoGameOverController  _(Assembly-CSharp.dll)_
- fields: videoPlayer, gameOverTextUI
- methods: Start, OnVideoFinished, EndingDisplaySequence, LoadMainMenu, OnDestroy, .ctor

## VideoGameOverController/<EndingDisplaySequence>d__4  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## TMPro.TMP_DigitValidator  _(Assembly-CSharp.dll)_
- methods: Validate, .ctor

## TMPro.TMP_PhoneNumberValidator  _(Assembly-CSharp.dll)_
- methods: Validate, .ctor

## TMPro.TMP_TextEventHandler  _(Assembly-CSharp.dll)_
- fields: m_OnCharacterSelection, m_OnSpriteSelection, m_OnWordSelection, m_OnLineSelection, m_OnLinkSelection, m_TextComponent, m_Camera, m_Canvas, m_selectedLink, m_lastCharIndex, m_lastWordIndex, m_lastLineIndex
- properties: onCharacterSelection, onSpriteSelection, onWordSelection, onLineSelection, onLinkSelection
- methods: get_onCharacterSelection, set_onCharacterSelection, get_onSpriteSelection, set_onSpriteSelection, get_onWordSelection, set_onWordSelection, get_onLineSelection, set_onLineSelection, get_onLinkSelection, set_onLinkSelection, Awake, LateUpdate, OnPointerEnter, OnPointerExit, SendOnCharacterSelection, SendOnSpriteSelection, SendOnWordSelection, SendOnLineSelection, SendOnLinkSelection, .ctor

## TMPro.TMP_TextEventHandler/CharacterSelectionEvent  _(Assembly-CSharp.dll)_
- methods: .ctor

## TMPro.TMP_TextEventHandler/LineSelectionEvent  _(Assembly-CSharp.dll)_
- methods: .ctor

## TMPro.TMP_TextEventHandler/LinkSelectionEvent  _(Assembly-CSharp.dll)_
- methods: .ctor

## TMPro.TMP_TextEventHandler/SpriteSelectionEvent  _(Assembly-CSharp.dll)_
- methods: .ctor

## TMPro.TMP_TextEventHandler/WordSelectionEvent  _(Assembly-CSharp.dll)_
- methods: .ctor

## TMPro.Examples.Benchmark01  _(Assembly-CSharp.dll)_
- fields: BenchmarkType, TMProFont, TextMeshFont, m_textMeshPro, m_textContainer, m_textMesh, label01, label02, m_material01, m_material02
- methods: Start, .ctor

## TMPro.Examples.Benchmark01/<Start>d__10  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this, <i>5__2
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## TMPro.Examples.Benchmark01_UGUI  _(Assembly-CSharp.dll)_
- fields: BenchmarkType, canvas, TMProFont, TextMeshFont, m_textMeshPro, m_textMesh, label01, label02, m_material01, m_material02
- methods: Start, .ctor

## TMPro.Examples.Benchmark01_UGUI/<Start>d__10  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this, <i>5__2
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## TMPro.Examples.Benchmark02  _(Assembly-CSharp.dll)_
- fields: SpawnType, NumberOfNPC, IsTextObjectScaleStatic, floatingText_Script
- methods: Start, .ctor

## TMPro.Examples.Benchmark03  _(Assembly-CSharp.dll)_
- fields: NumberOfSamples, Benchmark, SourceFont
- methods: Awake, Start, .ctor

## TMPro.Examples.Benchmark03/BenchmarkType  _(Assembly-CSharp.dll)_
- fields: value__, TMP_SDF_MOBILE, TMP_SDF__MOBILE_SSD, TMP_SDF, TMP_BITMAP_MOBILE, TEXTMESH_BITMAP

## TMPro.Examples.Benchmark04  _(Assembly-CSharp.dll)_
- fields: SpawnType, MinPointSize, MaxPointSize, Steps, m_Transform
- methods: Start, .ctor

## TMPro.Examples.CameraController  _(Assembly-CSharp.dll)_
- fields: cameraTransform, dummyTarget, CameraTarget, FollowDistance, MaxFollowDistance, MinFollowDistance, ElevationAngle, MaxElevationAngle, MinElevationAngle, OrbitalAngle, CameraMode, MovementSmoothing, RotationSmoothing, previousSmoothing, MovementSmoothingValue, RotationSmoothingValue, MoveSensitivity, currentVelocity, desiredPosition, mouseX, mouseY, moveVector, mouseWheel, event_SmoothingValue, event_FollowDistance
- methods: Awake, Start, LateUpdate, GetPlayerInput, .ctor

## TMPro.Examples.CameraController/CameraModes  _(Assembly-CSharp.dll)_
- fields: value__, Follow, Isometric, Free

## TMPro.Examples.ObjectSpin  _(Assembly-CSharp.dll)_
- fields: SpinSpeed, RotationRange, m_transform, m_time, m_prevPOS, m_initial_Rotation, m_initial_Position, m_lightColor, frames, Motion
- methods: Awake, Update, .ctor

## TMPro.Examples.ObjectSpin/MotionType  _(Assembly-CSharp.dll)_
- fields: value__, Rotation, BackAndForth, Translation

## TMPro.Examples.ShaderPropAnimator  _(Assembly-CSharp.dll)_
- fields: m_Renderer, m_Material, GlowCurve, m_frame
- methods: Awake, Start, AnimateProperties, .ctor

## TMPro.Examples.ShaderPropAnimator/<AnimateProperties>d__6  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## TMPro.Examples.SimpleScript  _(Assembly-CSharp.dll)_
- fields: m_textMeshPro, label, m_frame
- methods: Start, Update, .ctor

## TMPro.Examples.SkewTextExample  _(Assembly-CSharp.dll)_
- fields: m_TextComponent, VertexCurve, CurveScale, ShearAmount
- methods: Awake, Start, CopyAnimationCurve, WarpText, .ctor

## TMPro.Examples.SkewTextExample/<WarpText>d__7  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this, <old_CurveScale>5__2, <old_ShearValue>5__3, <old_curve>5__4
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## TMPro.Examples.TMP_ExampleScript_01  _(Assembly-CSharp.dll)_
- fields: ObjectType, isStatic, m_text, k_label, count
- methods: Awake, Update, .ctor

## TMPro.Examples.TMP_ExampleScript_01/objectType  _(Assembly-CSharp.dll)_
- fields: value__, TextMeshPro, TextMeshProUGUI

## TMPro.Examples.TMP_FrameRateCounter  _(Assembly-CSharp.dll)_
- fields: UpdateInterval, m_LastInterval, m_Frames, AnchorPosition, htmlColorTag, fpsLabel, m_TextMeshPro, m_frameCounter_transform, m_camera, last_AnchorPosition
- methods: Awake, Start, Update, Set_FrameCounter_Position, .ctor

## TMPro.Examples.TMP_FrameRateCounter/FpsCounterAnchorPositions  _(Assembly-CSharp.dll)_
- fields: value__, TopLeft, BottomLeft, TopRight, BottomRight

## TMPro.Examples.TMP_TextEventCheck  _(Assembly-CSharp.dll)_
- fields: TextEventHandler, m_TextComponent
- methods: OnEnable, OnDisable, OnCharacterSelection, OnSpriteSelection, OnWordSelection, OnLineSelection, OnLinkSelection, .ctor

## TMPro.Examples.TMP_TextInfoDebugTool  _(Assembly-CSharp.dll)_
- methods: .ctor

## TMPro.Examples.TMP_TextSelector_A  _(Assembly-CSharp.dll)_
- fields: m_TextMeshPro, m_Camera, m_isHoveringObject, m_selectedLink, m_lastCharIndex, m_lastWordIndex
- methods: Awake, LateUpdate, OnPointerEnter, OnPointerExit, .ctor

## TMPro.Examples.TMP_TextSelector_B  _(Assembly-CSharp.dll)_
- fields: TextPopup_Prefab_01, m_TextPopup_RectTransform, m_TextPopup_TMPComponent, k_LinkText, k_WordText, m_TextMeshPro, m_Canvas, m_Camera, isHoveringObject, m_selectedWord, m_selectedLink, m_lastIndex, m_matrix, m_cachedMeshInfoVertexData
- methods: Awake, OnEnable, OnDisable, ON_TEXT_CHANGED, LateUpdate, OnPointerEnter, OnPointerExit, OnPointerClick, OnPointerUp, RestoreCachedVertexAttributes, .ctor

## TMPro.Examples.TMP_UiFrameRateCounter  _(Assembly-CSharp.dll)_
- fields: UpdateInterval, m_LastInterval, m_Frames, AnchorPosition, htmlColorTag, fpsLabel, m_TextMeshPro, m_frameCounter_transform, last_AnchorPosition
- methods: Awake, Start, Update, Set_FrameCounter_Position, .ctor

## TMPro.Examples.TMP_UiFrameRateCounter/FpsCounterAnchorPositions  _(Assembly-CSharp.dll)_
- fields: value__, TopLeft, BottomLeft, TopRight, BottomRight

## TMPro.Examples.TMPro_InstructionOverlay  _(Assembly-CSharp.dll)_
- fields: AnchorPosition, instructions, m_TextMeshPro, m_textContainer, m_frameCounter_transform, m_camera
- methods: Awake, Set_FrameCounter_Position, .ctor

## TMPro.Examples.TMPro_InstructionOverlay/FpsCounterAnchorPositions  _(Assembly-CSharp.dll)_
- fields: value__, TopLeft, BottomLeft, TopRight, BottomRight

## TMPro.Examples.TeleType  _(Assembly-CSharp.dll)_
- fields: label01, label02, m_textMeshPro
- methods: Awake, Start, .ctor

## TMPro.Examples.TeleType/<Start>d__4  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this, <totalVisibleCharacters>5__2, <counter>5__3
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## TMPro.Examples.TextConsoleSimulator  _(Assembly-CSharp.dll)_
- fields: m_TextComponent, hasTextChanged
- methods: Awake, Start, OnEnable, OnDisable, ON_TEXT_CHANGED, RevealCharacters, RevealWords, .ctor

## TMPro.Examples.TextConsoleSimulator/<RevealCharacters>d__7  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, textComponent, <>4__this, <textInfo>5__2, <totalVisibleCharacters>5__3, <visibleCount>5__4
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## TMPro.Examples.TextConsoleSimulator/<RevealWords>d__8  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, textComponent, <totalWordCount>5__2, <totalVisibleCharacters>5__3, <counter>5__4, <visibleCount>5__5
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## TMPro.Examples.TextMeshProFloatingText  _(Assembly-CSharp.dll)_
- fields: TheFont, m_floatingText, m_textMeshPro, m_textMesh, m_transform, m_floatingText_Transform, m_cameraTransform, lastPOS, lastRotation, SpawnType, IsTextObjectScaleStatic, k_WaitForEndOfFrame, k_WaitForSecondsRandom
- methods: Awake, Start, DisplayTextMeshProFloatingText, DisplayTextMeshFloatingText, .ctor, .cctor

## TMPro.Examples.TextMeshProFloatingText/<DisplayTextMeshFloatingText>d__16  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this, <CountDuration>5__2, <starting_Count>5__3, <current_Count>5__4, <start_pos>5__5, <start_color>5__6, <alpha>5__7, <fadeDuration>5__8
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## TMPro.Examples.TextMeshProFloatingText/<DisplayTextMeshProFloatingText>d__15  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this, <CountDuration>5__2, <starting_Count>5__3, <current_Count>5__4, <start_pos>5__5, <start_color>5__6, <alpha>5__7, <fadeDuration>5__8
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## TMPro.Examples.TextMeshSpawner  _(Assembly-CSharp.dll)_
- fields: SpawnType, NumberOfNPC, TheFont, floatingText_Script
- methods: Awake, Start, .ctor

## TMPro.Examples.VertexColorCycler  _(Assembly-CSharp.dll)_
- fields: m_TextComponent
- methods: Awake, Start, AnimateVertexColors, .ctor

## TMPro.Examples.VertexColorCycler/<AnimateVertexColors>d__3  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this, <textInfo>5__2, <currentCharacter>5__3
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## TMPro.Examples.VertexJitter  _(Assembly-CSharp.dll)_
- fields: AngleMultiplier, SpeedMultiplier, CurveScale, m_TextComponent, hasTextChanged
- methods: Awake, OnEnable, OnDisable, Start, ON_TEXT_CHANGED, AnimateVertexColors, .ctor

## TMPro.Examples.VertexJitter/<AnimateVertexColors>d__11  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this, <textInfo>5__2, <loopCount>5__3, <vertexAnim>5__4, <cachedMeshInfo>5__5
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## TMPro.Examples.VertexJitter/VertexAnim  _(Assembly-CSharp.dll)_
- fields: angleRange, angle, speed

## TMPro.Examples.VertexShakeA  _(Assembly-CSharp.dll)_
- fields: AngleMultiplier, SpeedMultiplier, ScaleMultiplier, RotationMultiplier, m_TextComponent, hasTextChanged
- methods: Awake, OnEnable, OnDisable, Start, ON_TEXT_CHANGED, AnimateVertexColors, .ctor

## TMPro.Examples.VertexShakeA/<AnimateVertexColors>d__11  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this, <textInfo>5__2, <copyOfVertices>5__3
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## TMPro.Examples.VertexShakeB  _(Assembly-CSharp.dll)_
- fields: AngleMultiplier, SpeedMultiplier, CurveScale, m_TextComponent, hasTextChanged
- methods: Awake, OnEnable, OnDisable, Start, ON_TEXT_CHANGED, AnimateVertexColors, .ctor

## TMPro.Examples.VertexShakeB/<AnimateVertexColors>d__10  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this, <textInfo>5__2, <copyOfVertices>5__3
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## TMPro.Examples.VertexZoom  _(Assembly-CSharp.dll)_
- fields: AngleMultiplier, SpeedMultiplier, CurveScale, m_TextComponent, hasTextChanged
- methods: Awake, OnEnable, OnDisable, Start, ON_TEXT_CHANGED, AnimateVertexColors, .ctor

## TMPro.Examples.VertexZoom/<>c__DisplayClass10_0  _(Assembly-CSharp.dll)_
- fields: modifiedCharScale, <>9__0
- methods: .ctor

## TMPro.Examples.VertexZoom/<AnimateVertexColors>d__10  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this, <>8__1, <textInfo>5__2, <cachedMeshInfoVertexData>5__3, <scaleSortingOrder>5__4
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

## TMPro.Examples.WarpTextExample  _(Assembly-CSharp.dll)_
- fields: m_TextComponent, VertexCurve, AngleMultiplier, SpeedMultiplier, CurveScale
- methods: Awake, Start, CopyAnimationCurve, WarpText, .ctor

## TMPro.Examples.WarpTextExample/<WarpText>d__8  _(Assembly-CSharp.dll)_
- fields: <>1__state, <>2__current, <>4__this, <old_CurveScale>5__2, <old_curve>5__3
- properties: System.Collections.Generic.IEnumerator<System.Object>.Current, System.Collections.IEnumerator.Current
- methods: .ctor, System.IDisposable.Dispose, MoveNext, System.Collections.Generic.IEnumerator<System.Object>.get_Current, System.Collections.IEnumerator.Reset, System.Collections.IEnumerator.get_Current

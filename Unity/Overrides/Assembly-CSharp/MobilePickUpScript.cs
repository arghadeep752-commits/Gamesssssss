using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

/// <summary>
/// Granny-style hands: look at something within reach and the hand button appears. Tap it to pick up an item (it goes
/// to that item's own hold point in front of the camera), or to open / use what you look at with the item you hold:
/// doors, drawers, the locks on the main door, the lever, the balloon parts. The drop button puts the item down.
/// Only one item at a time; picking up another one drops the first.
/// </summary>
public class MobilePickUpScript : MonoBehaviour
{
    [Header("Pickup Settings")]
    public Transform holdPoint;
    public float pickupRange;
    public Button interactButton;
    public Button dropButton;
    public float throwForce;

    [Header("UI Text Settings")]
    public Text itemNameText;
    public Text lockedAlertText;

    [Header("Center Interact Prompt (Granny Style)")]
    public GameObject interactPrompt;
    public GameObject crosshairDot;
    public bool autoCreatePrompt;
    public float promptSize;
    public int letterSize;
    public string promptLetter;

    private RectTransform promptRect;
    private Text promptLetterText;
    private bool promptVisible;

    [Header("Mobile Look Settings")]
    public bool useOwnTouchLook;
    public float cameraSensitivity;

    [Header("Wall Anti-Clipping Settings")]
    public LayerMask wallLayerMask;
    public float wallBufferOffset;

    [Header("Held Item Rendering (no clipping through walls)")]
    public Camera heldItemCamera;
    public bool pushItemAwayFromWalls;

    private int heldItemLayer = -1;
    private int interactableLayerMask;
    private int originalItemLayer;
    private InteractableItem heldItem;
    private Rigidbody heldRigidbody;
    private GameObject targetedItem;
    private Camera cam;
    private float xRotation;
    private AudioSource playerAudioSource;
    private Coroutine alertCoroutine;
    private PlayerHidingController hidingController;
    private Transform activeHoldDestination;
    private Vector3 initialLocalPosition;
    private Vector3 heldItemOriginalScale;
    private bool isTeleporting;
    public bool IsTeleporting => isTeleporting;

    private Component targetedInteractable;
    private readonly List<Collider> disabledColliders = new List<Collider>();
    private readonly Dictionary<GameObject, int> originalLayers = new Dictionary<GameObject, int>();
    private PlayerInteractionEngine engine;
    private int lastInteractFrame = -1;
    private int lastDropFrame = -1;
    private bool buttonsHooked;

    public static MobilePickUpScript Instance { get; private set; }

    /// <summary>True while the hand button would do something (an item or an interactable is in reach).</summary>
    public bool HasTarget => targetedItem != null || targetedInteractable != null;

    private void Awake()
    {
        Instance = this;
    }

    private void Start()
    {
        foreach (Camera c in GetComponentsInChildren<Camera>(true))
            if (c.CompareTag("MainCamera")) { cam = c; break; }
        if (cam == null) cam = GetComponentInChildren<Camera>(true);
        playerAudioSource = GetComponent<AudioSource>();
        if (playerAudioSource == null)
        {
            playerAudioSource = gameObject.AddComponent<AudioSource>();
            playerAudioSource.playOnAwake = false;
            playerAudioSource.spatialBlend = 0f;
        }
        hidingController = GetComponent<PlayerHidingController>();
        engine = GetComponent<PlayerInteractionEngine>();
        heldItemLayer = LayerMask.NameToLayer("HeldItem");
        int ignore = (1 << gameObject.layer) | (1 << LayerMask.NameToLayer("Ignore Raycast")) | (1 << LayerMask.NameToLayer("UI"));
        if (heldItemLayer >= 0) ignore |= 1 << heldItemLayer;
        interactableLayerMask = ~ignore;
        if (pickupRange <= 0f) pickupRange = 2f;
        if (throwForce <= 0f) throwForce = 3f;
        if (holdPoint == null && cam != null) holdPoint = GameSave.FindDeep(cam.transform, "HoldPoint");
        if (holdPoint != null) initialLocalPosition = holdPoint.localPosition;
        HookButtons();
        if (interactButton != null) interactButton.gameObject.SetActive(false);
        if (dropButton != null) dropButton.gameObject.SetActive(false);
        if (itemNameText != null) itemNameText.text = "";
        if (lockedAlertText != null) lockedAlertText.text = "";
        if (interactPrompt == null && autoCreatePrompt) CreateDefaultPrompt();
        SetInteractPrompt(false);
    }

    private void HookButtons()
    {
        if (buttonsHooked) return;
        buttonsHooked = true;
        if (interactButton != null) interactButton.onClick.AddListener(OnInteractButtonPressed);
        if (dropButton != null) dropButton.onClick.AddListener(DropItem);
    }

    private void Update()
    {
        if (isTeleporting || Time.timeScale == 0f)
        {
            UpdateButtonState(false, "");
            return;
        }
        if (hidingController != null && (hidingController.IsCurrentlyHiding || hidingController.IsExiting))
        {
            targetedItem = null;
            targetedInteractable = null;
            UpdateButtonState(false, "");
            return;
        }
        CheckForInteractables();
        if (!Application.isMobilePlatform)
        {
            if (Input.GetKeyDown(KeyCode.E)) OnInteractButtonPressed();
            if (Input.GetKeyDown(KeyCode.G)) DropItem();
        }
        if (useOwnTouchLook) HandleTouchLook();
        if (pushItemAwayFromWalls) HandleWallClipping();
    }

    public void SetTeleportingState(bool state)
    {
        isTeleporting = state;
        if (state) UpdateButtonState(false, "");
    }

    private void SetInteractPrompt(bool show)
    {
        promptVisible = show;
        if (interactPrompt != null && interactPrompt.activeSelf != show) interactPrompt.SetActive(show);
        if (crosshairDot != null && crosshairDot.activeSelf == show) crosshairDot.SetActive(!show);
    }

    private void ApplyPromptSize()
    {
        if (promptRect != null) promptRect.sizeDelta = new Vector2(promptSize > 0 ? promptSize : 40f, promptSize > 0 ? promptSize : 40f);
        if (promptLetterText != null) promptLetterText.fontSize = letterSize > 0 ? letterSize : 34;
    }

    private void CreateDefaultPrompt()
    {
        Canvas canvas = FindFirstObjectByType<Canvas>();
        if (canvas == null) return;
        var go = new GameObject("InteractPrompt", typeof(RectTransform), typeof(Image));
        go.transform.SetParent(canvas.transform, false);
        promptRect = go.GetComponent<RectTransform>();
        promptRect.anchorMin = promptRect.anchorMax = new Vector2(0.5f, 0.5f);
        go.GetComponent<Image>().color = new Color(0f, 0f, 0f, 0.5f);
        var letter = new GameObject("Letter", typeof(RectTransform), typeof(Text));
        letter.transform.SetParent(go.transform, false);
        promptLetterText = letter.GetComponent<Text>();
        promptLetterText.text = string.IsNullOrEmpty(promptLetter) ? "E" : promptLetter;
        promptLetterText.alignment = TextAnchor.MiddleCenter;
        promptLetterText.font = GetUsableFont();
        var lr = letter.GetComponent<RectTransform>();
        lr.anchorMin = Vector2.zero; lr.anchorMax = Vector2.one; lr.offsetMin = lr.offsetMax = Vector2.zero;
        interactPrompt = go;
        ApplyPromptSize();
    }

    private Font GetUsableFont()
    {
        return Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
    }

    private void HandleTouchLook()
    {
        // turning is done by the FPSController (useOwnTouchLook is off in the game)
    }

    private void HandleWallClipping()
    {
        if (heldItem == null || activeHoldDestination == null || cam == null) return;
        int mask = wallLayerMask.value != 0 ? wallLayerMask.value : interactableLayerMask;
        Vector3 to = activeHoldDestination.position - cam.transform.position;
        if (Physics.Raycast(cam.transform.position, to.normalized, out RaycastHit hit, to.magnitude + wallBufferOffset, mask, QueryTriggerInteraction.Ignore))
            heldItem.transform.position = cam.transform.position + to.normalized * Mathf.Max(0.1f, hit.distance - wallBufferOffset);
        else
            heldItem.transform.localPosition = Vector3.zero;
    }

    private void CheckForInteractables()
    {
        targetedItem = null;
        targetedInteractable = null;
        if (cam == null) { UpdateButtonState(false, ""); return; }
        float range = pickupRange;
        if (engine != null && engine.reachDistance > range) range = engine.reachDistance;
        Ray ray = new Ray(cam.transform.position, cam.transform.forward);
        RaycastHit[] hits = Physics.RaycastAll(ray, range, interactableLayerMask, QueryTriggerInteraction.Collide);
        System.Array.Sort(hits, (a, b) => a.distance.CompareTo(b.distance));
        foreach (RaycastHit hit in hits)
        {
            Collider c = hit.collider;
            if (c == null || c.transform.IsChildOf(transform)) continue;
            InteractableItem item = c.GetComponentInParent<InteractableItem>();
            if (item != null && !item.isHeld && item != heldItem && item.gameObject.activeInHierarchy)
            {
                targetedItem = item.gameObject;
                break;
            }
            Component inter = FindInteractable(c);
            if (inter != null)
            {
                targetedInteractable = inter;
                break;
            }
            if (!c.isTrigger) break;    // a wall or a solid object is in the way
        }
        string label = "";
        if (targetedItem != null)
        {
            var it = targetedItem.GetComponent<InteractableItem>();
            label = it != null ? it.itemName : "";
        }
        UpdateButtonState(targetedItem != null || targetedInteractable != null, label);
    }

    private static T Active<T>(Collider c) where T : Behaviour
    {
        T x = c.GetComponentInParent<T>();
        return x != null && x.isActiveAndEnabled ? x : null;
    }

    private static Component FindInteractable(Collider c)
    {
        Component x;
        if ((x = Active<EscapeLockElement>(c)) != null) return x;
        if ((x = Active<LeverInteractable>(c)) != null) return x;
        if ((x = Active<RopeAnchorInteraction>(c)) != null) return x;
        if ((x = Active<BalloonHoleZone>(c)) != null) return x;
        if ((x = Active<BalloonCylinderSlot>(c)) != null) return x;
        if ((x = Active<BalloonBurnerZone>(c)) != null) return x;
        if ((x = Active<DoorPlankComponent>(c)) != null) return x;
        if ((x = Active<PlankLockedDoorInteractable>(c)) != null) return x;
        if ((x = Active<MainDoorEscape>(c)) != null) return x;
        if ((x = Active<DoorInteractable>(c)) != null) return x;
        if ((x = Active<DrawerInteractable>(c)) != null) return x;
        if ((x = Active<CabinetInteractable>(c)) != null) return x;
        if ((x = Active<GrannyDrawer>(c)) != null) return x;
        if ((x = Active<DrawerPivotAnimation>(c)) != null) return x;
        if ((x = Active<DoorLockComponent>(c)) != null) return x;
        if ((x = Active<HotAirBalloonEscape>(c)) != null) return x;
        return null;
    }

    private void UpdateButtonState(bool showButton, string textMessage)
    {
        if (interactButton != null && interactButton.gameObject.activeSelf != showButton) interactButton.gameObject.SetActive(showButton);
        if (itemNameText != null && itemNameText.text != textMessage) itemNameText.text = textMessage;
        SetInteractPrompt(showButton);
    }

    public void OnInteractButtonPressed()
    {
        if (!GameSave.FirstThisFrame(ref lastInteractFrame)) return;
        if (isTeleporting) return;
        if (hidingController != null && (hidingController.IsCurrentlyHiding || hidingController.IsExiting)) return;
        if (targetedItem == null && targetedInteractable == null) CheckForInteractables();
        if (targetedItem != null)
        {
            PickUp(targetedItem.GetComponent<InteractableItem>());
            return;
        }
        if (targetedInteractable != null)
        {
            Interact(targetedInteractable);
            return;
        }
        if (heldItem != null) UseHeldItem();
    }

    private void Interact(Component c)
    {
        string held = GetHeldItemName();
        switch (c)
        {
            case EscapeLockElement lockElement: lockElement.InteractWithLock(held); break;
            case LeverInteractable lever: lever.InteractWithLever(gameObject); break;
            case RopeAnchorInteraction anchor: anchor.InteractWithAnchor(held); break;
            case BalloonHoleZone hole:
                if (GameSave.SameItem(held, "Duct Tape")) hole.FixHoleWithTape();
                else ShowLockedNotification("I need Duct Tape to fix this rip");
                break;
            case BalloonCylinderSlot slot:
                if (GameSave.SameItem(held, "Cylinder")) slot.InsertCylinderFromPlayer();
                else ShowLockedNotification("I need a Gas Cylinder!");
                break;
            case BalloonBurnerZone burner:
                if (GameSave.SameItem(held, "Lighter")) burner.OnBurnerIgnited();
                else ShowLockedNotification("I need a Lighter to start the burner");
                break;
            case DoorPlankComponent plank: plank.RemovePlank(); break;
            case PlankLockedDoorInteractable plankDoor: plankDoor.Interact(held); break;
            case MainDoorEscape mainDoor: mainDoor.TryMasterKeyEscape(); break;
            case DoorInteractable door: door.Interact(held); break;
            case DrawerInteractable drawer: drawer.Interact(); break;
            case CabinetInteractable cabinet: cabinet.Interact(held); break;
            case GrannyDrawer grannyDrawer: grannyDrawer.ToggleDrawer(); break;
            case DrawerPivotAnimation pivot: pivot.Interact(); break;
            case DoorLockComponent doorLock: doorLock.Interact(held); break;
            case HotAirBalloonEscape balloon: balloon.TriggerLaunchAttempt(); break;
        }
    }

    private Transform FindHoldPoint(string pointName)
    {
        if (string.IsNullOrEmpty(pointName) || cam == null) return null;
        Transform t = GameSave.FindDeep(cam.transform, pointName);
        if (t == null) t = GameSave.FindDeep(transform, pointName);
        return t;
    }

    private void PickUp(InteractableItem item)
    {
        if (item == null) return;
        if (heldItem != null) DropCurrentlyHeldItem();
        heldItem = item;
        heldRigidbody = item.GetComponent<Rigidbody>();
        item.isHeld = true;
        if (heldRigidbody != null)
        {
            heldRigidbody.isKinematic = true;
            heldRigidbody.detectCollisions = false;
            heldRigidbody.interpolation = RigidbodyInterpolation.None;
        }
        disabledColliders.Clear();
        foreach (Collider col in item.GetComponentsInChildren<Collider>())
            if (col.enabled) { col.enabled = false; disabledColliders.Add(col); }
        activeHoldDestination = FindHoldPoint(item.targetHoldPointName);
        if (activeHoldDestination == null) activeHoldDestination = holdPoint;
        if (activeHoldDestination != null && !activeHoldDestination.gameObject.activeSelf) activeHoldDestination.gameObject.SetActive(true);
        heldItemOriginalScale = item.transform.lossyScale;
        if (activeHoldDestination != null)
        {
            item.transform.SetParent(activeHoldDestination, true);
            item.transform.localPosition = Vector3.zero;
            item.transform.localRotation = Quaternion.identity;
        }
        originalItemLayer = item.gameObject.layer;
        originalLayers.Clear();
        foreach (Transform t in item.GetComponentsInChildren<Transform>(true)) originalLayers[t.gameObject] = t.gameObject.layer;
        if (heldItemLayer >= 0) SetLayerRecursively(item.gameObject, heldItemLayer);
        if (item.pickupSound != null && playerAudioSource != null) playerAudioSource.PlayOneShot(item.pickupSound);
        if (dropButton != null) dropButton.gameObject.SetActive(true);
        if (engine != null) engine.currentlyHeldItem = item.itemName;
        targetedItem = null;
        RefreshHeldItemUI();
    }

    public void DropItem()
    {
        if (!GameSave.FirstThisFrame(ref lastDropFrame)) return;
        if (hidingController != null && hidingController.IsCurrentlyHiding) return;
        DropCurrentlyHeldItem();
    }

    public void DropCurrentlyHeldItem()
    {
        if (heldItem == null) return;
        Vector3 origin = cam != null ? cam.transform.position : transform.position + Vector3.up;
        Vector3 forward = cam != null ? cam.transform.forward : transform.forward;
        float distance = 0.6f;
        if (Physics.Raycast(origin, forward, out RaycastHit hit, distance + 0.2f, interactableLayerMask, QueryTriggerInteraction.Ignore))
            distance = Mathf.Max(0.15f, hit.distance - 0.25f);
        Release(origin + forward * distance, forward * throwForce + Vector3.up * 0.5f);
    }

    /// <summary>Granny caught the player: the item falls where he stands.</summary>
    public void DropItemOnDeath()
    {
        if (heldItem == null) return;
        Vector3 p = transform.position + transform.forward * 0.4f;
        if (Physics.Raycast(p + Vector3.up * 0.5f, Vector3.down, out RaycastHit hit, 4f, interactableLayerMask, QueryTriggerInteraction.Ignore))
            p = hit.point + Vector3.up * 0.15f;
        Release(p, Vector3.zero);
    }

    public void DropItemAtPosition(Vector3 customPosition)
    {
        if (heldItem == null) return;
        Release(customPosition, Vector3.zero);
    }

    private void Release(Vector3 position, Vector3 velocity)
    {
        InteractableItem item = heldItem;
        Rigidbody rb = heldRigidbody;
        heldItem = null;
        heldRigidbody = null;
        if (item == null) return;
        item.transform.SetParent(null, true);
        item.transform.position = position;
        foreach (var kv in originalLayers)
            if (kv.Key != null) kv.Key.layer = kv.Value;
        originalLayers.Clear();
        foreach (Collider col in disabledColliders)
            if (col != null) col.enabled = true;
        disabledColliders.Clear();
        if (rb != null)
        {
            rb.isKinematic = false;
            rb.detectCollisions = true;
            rb.interpolation = RigidbodyInterpolation.Interpolate;
            rb.linearVelocity = velocity;
            rb.angularVelocity = Random.insideUnitSphere * 2f;
        }
        item.isHeld = false;
        if (dropButton != null) dropButton.gameObject.SetActive(false);
        if (engine != null) engine.currentlyHeldItem = "";
        RefreshHeldItemUI();
    }

    private void UseHeldItem()
    {
        if (heldItem != null) heldItem.UseItem();
    }

    public void ShowLockedNotification(string explicitMessage)
    {
        if (lockedAlertText == null || string.IsNullOrEmpty(explicitMessage)) return;
        if (alertCoroutine != null) StopCoroutine(alertCoroutine);
        alertCoroutine = StartCoroutine(DisplayAlertRoutine(explicitMessage));
    }

    private IEnumerator DisplayAlertRoutine(string message)
    {
        lockedAlertText.text = message;
        lockedAlertText.gameObject.SetActive(true);
        yield return new WaitForSeconds(2.5f);
        lockedAlertText.text = "";
        alertCoroutine = null;
    }

    /// <summary>The held item was used up (a key turned in its lock, tape stuck on the balloon...).</summary>
    public void ConsumeHeldItem()
    {
        InteractableItem item = heldItem;
        if (item == null) return;
        heldItem = null;
        heldRigidbody = null;
        foreach (var kv in originalLayers)
            if (kv.Key != null) kv.Key.layer = kv.Value;
        originalLayers.Clear();
        disabledColliders.Clear();
        item.isHeld = false;
        item.transform.SetParent(null, true);
        item.gameObject.SetActive(false);
        if (dropButton != null) dropButton.gameObject.SetActive(false);
        if (engine != null) engine.currentlyHeldItem = "";
        RefreshHeldItemUI();
    }

    public string GetHeldItemName()
    {
        return heldItem != null ? heldItem.itemName : "";
    }

    public InteractableItem GetHeldItem()
    {
        return heldItem;
    }

    public void RefreshHeldItemUI()
    {
        if (dropButton != null)
        {
            bool show = heldItem != null && (hidingController == null || !hidingController.IsCurrentlyHiding);
            if (dropButton.gameObject.activeSelf != show) dropButton.gameObject.SetActive(show);
        }
    }

    private void SetLayerRecursively(GameObject obj, int layer)
    {
        if (obj == null) return;
        obj.layer = layer;
        foreach (Transform child in obj.transform) SetLayerRecursively(child.gameObject, layer);
    }

    private void LateUpdate()
    {
        if (heldItemCamera != null && cam != null && heldItemCamera.fieldOfView != cam.fieldOfView)
            heldItemCamera.fieldOfView = cam.fieldOfView;
        if (heldItem != null && activeHoldDestination != null && heldItem.transform.parent != activeHoldDestination)
        {
            heldItem.transform.SetParent(activeHoldDestination, true);
            heldItem.transform.localPosition = Vector3.zero;
            heldItem.transform.localRotation = Quaternion.identity;
        }
    }
}

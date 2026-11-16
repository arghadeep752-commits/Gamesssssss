using UnityEngine;
using UnityEngine.EventSystems;

/// <summary>
/// First-person player: joystick to walk, a finger anywhere else on the screen to look around (Granny style).
/// In the editor WASD and the mouse work too. Gravity keeps him on the floor and on the stairs.
/// </summary>
public class FPSController : MonoBehaviour
{
    public float moveSpeed;
    public float mouseSensitivity;
    public float gravity;

    [Header("Mobile Setup")]
    public MobileJoystick joystick;

    [Header("Mobile Look (touch)")]
    public float touchLookScale;
    public float touchLookSmoothing;

    [Header("Frame Rate (mobile)")]
    public int mobileTargetFrameRate;

    private int lookFingerId = -1;
    private Vector2 smoothedTouchDelta;
    private CharacterController controller;
    private Camera cam;
    private float xRotation;
    private Vector3 velocity;
    private PlayerHidingController hidingController;
    private bool isFirstFrameAfterEnable;

    private void Start()
    {
        controller = GetComponent<CharacterController>();
        cam = GetComponentInChildren<Camera>(true);
        hidingController = GetComponent<PlayerHidingController>();
        if (moveSpeed <= 0f) moveSpeed = 3.5f;
        if (gravity == 0f) gravity = -9.81f;
        if (touchLookScale <= 0f) touchLookScale = 0.2f;
        mouseSensitivity = GameSave.Sensitivity(mouseSensitivity > 0f ? mouseSensitivity : 2f);
        if (Application.isMobilePlatform && mobileTargetFrameRate > 0) Application.targetFrameRate = mobileTargetFrameRate;
        SyncPitchFromCamera();
    }

    private void OnEnable()
    {
        isFirstFrameAfterEnable = true;
        lookFingerId = -1;
        smoothedTouchDelta = Vector2.zero;
        SyncPitchFromCamera();
    }

    private void SyncPitchFromCamera()
    {
        if (cam == null) cam = GetComponentInChildren<Camera>(true);
        if (cam == null) return;
        float x = cam.transform.localEulerAngles.x;
        if (x > 180f) x -= 360f;
        xRotation = Mathf.Clamp(x, -80f, 80f);
    }

    /// <summary>Turns the player to a heading and the camera to a pitch (teleports, cutscene exits, tests).</summary>
    public void SetLook(float yawDegrees, float pitchDegrees)
    {
        if (cam == null) cam = GetComponentInChildren<Camera>(true);
        transform.rotation = Quaternion.Euler(0f, yawDegrees, 0f);
        xRotation = Mathf.Clamp(pitchDegrees, -80f, 80f);
        if (cam != null) cam.transform.localRotation = Quaternion.Euler(xRotation, 0f, 0f);
        smoothedTouchDelta = Vector2.zero;
    }

    public void ResetGravityVelocity()
    {
        velocity = Vector3.zero;
    }

    private bool IsHiding()
    {
        return hidingController != null && (hidingController.IsCurrentlyHiding || hidingController.IsExiting);
    }

    private void Update()
    {
        if (controller == null) controller = GetComponent<CharacterController>();
        if (IsHiding()) return;

        // ---- look ----
        Vector2 look = Vector2.zero;
        bool touching = false;
        for (int i = 0; i < Input.touchCount; i++)
        {
            Touch t = Input.GetTouch(i);
            touching = true;
            if (t.phase == TouchPhase.Began && lookFingerId < 0)
            {
                bool overUi = EventSystem.current != null && EventSystem.current.IsPointerOverGameObject(t.fingerId);
                if (!overUi) lookFingerId = t.fingerId;
            }
            if (t.fingerId == lookFingerId)
            {
                if (t.phase == TouchPhase.Moved) look = t.deltaPosition * touchLookScale * mouseSensitivity;
                if (t.phase == TouchPhase.Ended || t.phase == TouchPhase.Canceled) lookFingerId = -1;
            }
        }
        if (!touching)
        {
            lookFingerId = -1;
            if (!Application.isMobilePlatform && Input.GetMouseButton(1))
                look = new Vector2(Input.GetAxis("Mouse X"), Input.GetAxis("Mouse Y")) * mouseSensitivity * 4f;
        }
        if (isFirstFrameAfterEnable) { look = Vector2.zero; isFirstFrameAfterEnable = false; }
        if (touchLookSmoothing > 0f)
            smoothedTouchDelta = Vector2.Lerp(smoothedTouchDelta, look, 1f - Mathf.Exp(-touchLookSmoothing * Time.unscaledDeltaTime));
        else
            smoothedTouchDelta = look;
        if (Time.timeScale > 0f)
        {
            xRotation = Mathf.Clamp(xRotation - smoothedTouchDelta.y, -80f, 80f);
            if (cam != null) cam.transform.localRotation = Quaternion.Euler(xRotation, 0f, 0f);
            transform.Rotate(Vector3.up * smoothedTouchDelta.x, Space.World);
        }

        // ---- walk ----
        if (controller == null || !controller.enabled) return;
        float h = joystick != null ? joystick.Horizontal : 0f;
        float v = joystick != null ? joystick.Vertical : 0f;
        if (!Application.isMobilePlatform)
        {
            h += Input.GetAxisRaw("Horizontal");
            v += Input.GetAxisRaw("Vertical");
        }
        Vector3 move = transform.right * h + transform.forward * v;
        if (move.sqrMagnitude > 1f) move.Normalize();
        controller.Move(move * moveSpeed * Time.deltaTime);
        if (controller.isGrounded && velocity.y < 0f) velocity.y = -2f;
        velocity.y += gravity * Time.deltaTime;
        controller.Move(velocity * Time.deltaTime);
    }

    public void ResetMovementState()
    {
        velocity = Vector3.zero;
        smoothedTouchDelta = Vector2.zero;
        lookFingerId = -1;
        isFirstFrameAfterEnable = true;
        SyncPitchFromCamera();
    }
}

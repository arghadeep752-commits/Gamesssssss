using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.CompilerServices;
using UnityEngine;
using UnityEngine.UI;

public class MobilePickUpScript : MonoBehaviour
{
	[CompilerGenerated]
	private sealed class _003CDisplayAlertRoutine_003Ed__54 : IEnumerator<object>, IEnumerator, IDisposable
	{
		private int _003C_003E1__state;

		private object _003C_003E2__current;

		public MobilePickUpScript _003C_003E4__this;

		public string message;

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
		public _003CDisplayAlertRoutine_003Ed__54(int _003C_003E1__state)
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

	[Header("Pickup Settings")]
	public Transform holdPoint;

	public float pickupRange;

	public Button interactButton;

	public Button dropButton;

	[Tooltip("How hard the object is pushed forward when dropped")]
	public float throwForce;

	[Header("UI Text Settings")]
	public Text itemNameText;

	[Tooltip("Drag your central red warning/notification text component here")]
	public Text lockedAlertText;

	[Header("Center Interact Prompt (Granny Style)")]
	[Tooltip("UI object placed at the screen center (e.g. a circle with an 'E' in it). Leave empty and tick Auto Create to have one built automatically.")]
	public GameObject interactPrompt;

	[Tooltip("Optional: your normal crosshair dot. It is hidden while the E prompt is showing.")]
	public GameObject crosshairDot;

	[Tooltip("Build a simple E prompt at runtime if none is assigned above")]
	public bool autoCreatePrompt;

	[Tooltip("Width/height (pixels) of the E prompt box")]
	public float promptSize;

	[Tooltip("Font size of the E letter")]
	public int letterSize;

	[Tooltip("Letter shown in the auto-created prompt")]
	public string promptLetter;

	private RectTransform promptRect;

	private Text promptLetterText;

	private bool promptVisible;

	[Header("Mobile Look Settings")]
	[Tooltip("OFF (recommended): the FPSController turns the camera. ON: this script ALSO turns it - that made left/right twice as fast as up/down.")]
	public bool useOwnTouchLook;

	public float cameraSensitivity;

	[Header("Wall Anti-Clipping Settings")]
	[Tooltip("Layer mask for things the item shouldn't clip through (e.g., Default, Environment)")]
	public LayerMask wallLayerMask;

	[Tooltip("Minimum buffer distance to keep the item away from a wall surface")]
	public float wallBufferOffset;

	[Tooltip("The overlay camera that only renders the 'HeldItem' layer. Its field of view is kept in sync with the main camera.")]
	[Header("Held Item Rendering (no clipping through walls)")]
	public Camera heldItemCamera;

	[Tooltip("Old method: pull the item toward your face when a wall is in the way. Not needed once the HeldItem layer + overlay camera are set up.")]
	public bool pushItemAwayFromWalls;

	private int heldItemLayer;

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

	private void Start()
	{
	}

	private void Update()
	{
	}

	public void SetTeleportingState(bool state)
	{
	}

	private void SetInteractPrompt(bool show)
	{
	}

	private void ApplyPromptSize()
	{
	}

	private void CreateDefaultPrompt()
	{
	}

	private Font GetUsableFont()
	{
		return null;
	}

	private void HandleTouchLook()
	{
	}

	private void HandleWallClipping()
	{
	}

	private void CheckForInteractables()
	{
	}

	private void UpdateButtonState(bool showButton, string textMessage)
	{
	}

	public void OnInteractButtonPressed()
	{
	}

	public void DropItem()
	{
	}

	public void DropItemOnDeath()
	{
	}

	public void DropCurrentlyHeldItem()
	{
	}

	private void UseHeldItem()
	{
	}

	public void ShowLockedNotification(string explicitMessage)
	{
	}

	[IteratorStateMachine(typeof(_003CDisplayAlertRoutine_003Ed__54))]
	private IEnumerator DisplayAlertRoutine(string message)
	{
		return null;
	}

	public void ConsumeHeldItem()
	{
	}

	public string GetHeldItemName()
	{
		return null;
	}

	public void RefreshHeldItemUI()
	{
	}

	private void SetLayerRecursively(GameObject obj, int layer)
	{
	}

	private void LateUpdate()
	{
	}

	public void DropItemAtPosition(Vector3 customPosition)
	{
	}
}

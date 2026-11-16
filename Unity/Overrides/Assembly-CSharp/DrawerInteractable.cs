using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// A drawer that slides out along its local Z axis. Items lying inside it are held by the drawer: they stay still
/// and move with it. An item dropped into the open drawer is taken in once it has nearly stopped moving.
/// </summary>
public class DrawerInteractable : MonoBehaviour
{
    private class HeldEntry
    {
        public Rigidbody rb;
        public InteractableItem item;
        public bool wasKinematic;
    }

    [Header("Drawer Movement Settings")]
    public float openDistance;
    public float slideSpeed;

    [Header("Drawer Audio Profiles")]
    public AudioClip openSound;
    public AudioClip closeSound;

    [Header("Items Inside The Drawer")]
    public Vector3 contentsCenter;
    public Vector3 contentsSize;
    public float autoBoxShrink;
    public float settleSpeed;

    private bool isOpen;
    private AudioSource myAudioSource;
    private Vector3 closedLocalPosition;
    private Vector3 openLocalPosition;
    private Vector3 targetLocalPosition;
    private readonly List<HeldEntry> heldItems = new List<HeldEntry>();
    private Vector3 lastWorldPosition;
    private float scanTimer;
    private readonly Collider[] overlapBuffer = new Collider[32];

    private void Start()
    {
        myAudioSource = GetComponent<AudioSource>();
        if (myAudioSource == null)
        {
            myAudioSource = gameObject.AddComponent<AudioSource>();
            myAudioSource.playOnAwake = false;
            myAudioSource.spatialBlend = 1f;
        }
        if (openDistance == 0f) openDistance = 0.3f;
        if (slideSpeed <= 0f) slideSpeed = 4f;
        if (autoBoxShrink <= 0f) autoBoxShrink = 0.9f;
        if (settleSpeed <= 0f) settleSpeed = 0.15f;
        closedLocalPosition = transform.localPosition;
        openLocalPosition = closedLocalPosition + transform.localRotation * new Vector3(0f, 0f, openDistance);
        targetLocalPosition = closedLocalPosition;
        if (contentsSize == Vector3.zero) AutoFitContentsBox();
        lastWorldPosition = transform.position;
        CaptureItemsInside(true);
    }

    private void Update()
    {
        if ((transform.localPosition - targetLocalPosition).sqrMagnitude > 0.000001f)
            transform.localPosition = Vector3.MoveTowards(transform.localPosition, targetLocalPosition, slideSpeed * 0.25f * Time.deltaTime);

        // let go of items the player has picked up
        for (int i = heldItems.Count - 1; i >= 0; i--)
        {
            HeldEntry e = heldItems[i];
            if (e.rb == null || e.item == null || e.item.isHeld || e.rb.transform.parent != transform)
                heldItems.RemoveAt(i);
        }
        if (isOpen)
        {
            scanTimer -= Time.deltaTime;
            if (scanTimer <= 0f)
            {
                scanTimer = 0.25f;
                CaptureItemsInside(false);
            }
        }
        lastWorldPosition = transform.position;
    }

    public void Interact()
    {
        isOpen = !isOpen;
        targetLocalPosition = isOpen ? openLocalPosition : closedLocalPosition;
        CaptureItemsInside(true);
        AudioClip clip = isOpen ? openSound : closeSound;
        if (clip != null && myAudioSource != null) myAudioSource.PlayOneShot(clip);
    }

    private void CaptureItemsInside(bool evenIfMoving)
    {
        Vector3 centre = transform.TransformPoint(contentsCenter);
        Vector3 half = Vector3.Scale(contentsSize, transform.lossyScale) * 0.5f;
        half = new Vector3(Mathf.Abs(half.x), Mathf.Abs(half.y), Mathf.Abs(half.z));
        if (half.sqrMagnitude < 0.00001f) return;
        int n = Physics.OverlapBoxNonAlloc(centre, half, overlapBuffer, transform.rotation, Physics.AllLayers, QueryTriggerInteraction.Ignore);
        for (int i = 0; i < n; i++)
        {
            Collider c = overlapBuffer[i];
            if (c == null) continue;
            InteractableItem item = c.GetComponentInParent<InteractableItem>();
            if (item == null || item.isHeld) continue;
            Rigidbody rb = item.GetComponent<Rigidbody>();
            if (rb == null || IsAlreadyHeld(rb)) continue;
            if (!evenIfMoving && !rb.isKinematic && rb.linearVelocity.magnitude > settleSpeed) continue;
            heldItems.Add(new HeldEntry { rb = rb, item = item, wasKinematic = rb.isKinematic });
            rb.isKinematic = true;
            item.transform.SetParent(transform, true);
        }
    }

    private bool IsAlreadyHeld(Rigidbody rb)
    {
        foreach (HeldEntry e in heldItems)
            if (e.rb == rb) return true;
        return false;
    }

    private void AutoFitContentsBox()
    {
        var mf = GetComponent<MeshFilter>();
        if (mf != null && mf.sharedMesh != null)
        {
            Bounds b = mf.sharedMesh.bounds;
            contentsCenter = b.center;
            contentsSize = b.size * autoBoxShrink;
            return;
        }
        var col = GetComponent<BoxCollider>();
        if (col != null)
        {
            contentsCenter = col.center;
            contentsSize = col.size * autoBoxShrink;
        }
    }

    private void OnDrawGizmosSelected()
    {
        Gizmos.color = Color.yellow;
        Gizmos.matrix = transform.localToWorldMatrix;
        Gizmos.DrawWireCube(contentsCenter, contentsSize);
    }
}

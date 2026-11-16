using UnityEngine;

public class HidingCameraLook : MonoBehaviour
{
	[Header("Sensitivity Settings")]
	public float mobileSensitivity;

	public float pcSensitivity;

	private Transform targetAnchor;

	private float rotationY;

	private const float HORIZONTAL_LIMIT = 90f;

	public void Activate(Transform anchor)
	{
	}

	public void Deactivate()
	{
	}

	private void Update()
	{
	}
}

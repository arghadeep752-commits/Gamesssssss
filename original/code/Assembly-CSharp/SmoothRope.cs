using UnityEngine;

[RequireComponent(typeof(LineRenderer))]
public class SmoothRope : MonoBehaviour
{
	[Header("Rope Connections")]
	public Transform topPoint;

	public Transform bottomPoint;

	[Range(10f, 30f)]
	[Header("Rope Appearance")]
	public int segments;

	public float ropeSag;

	private LineRenderer lineRenderer;

	private void Start()
	{
	}

	private void Update()
	{
	}
}

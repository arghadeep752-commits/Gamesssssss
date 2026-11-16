using UnityEngine;

namespace TMPro.Examples
{
	public class ObjectSpin : MonoBehaviour
	{
		public enum MotionType
		{
			Rotation = 0,
			BackAndForth = 1,
			Translation = 2
		}

		public float SpinSpeed;

		public int RotationRange;

		private Transform m_transform;

		private float m_time;

		private Vector3 m_prevPOS;

		private Vector3 m_initial_Rotation;

		private Vector3 m_initial_Position;

		private Color32 m_lightColor;

		private int frames;

		public MotionType Motion;

		private void Awake()
		{
		}

		private void Update()
		{
		}
	}
}

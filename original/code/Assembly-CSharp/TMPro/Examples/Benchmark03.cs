using UnityEngine;

namespace TMPro.Examples
{
	public class Benchmark03 : MonoBehaviour
	{
		public enum BenchmarkType
		{
			TMP_SDF_MOBILE = 0,
			TMP_SDF__MOBILE_SSD = 1,
			TMP_SDF = 2,
			TMP_BITMAP_MOBILE = 3,
			TEXTMESH_BITMAP = 4
		}

		public int NumberOfSamples;

		public BenchmarkType Benchmark;

		public Font SourceFont;

		private void Awake()
		{
		}

		private void Start()
		{
		}
	}
}

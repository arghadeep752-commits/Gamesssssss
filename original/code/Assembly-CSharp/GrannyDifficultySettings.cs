using System;
using UnityEngine;

[Serializable]
public class GrannyDifficultySettings
{
	[Tooltip("Walking speed while patrolling the house")]
	[Header("Speeds")]
	public float patrolSpeed;

	[Tooltip("Running speed while chasing the player")]
	public float chaseSpeed;

	[Tooltip("Speed when she goes to check a noise (dropped item, creaking floor)")]
	public float investigateSpeed;

	[Header("Vision")]
	[Tooltip("How far she can see the player (meters)")]
	public float viewDistance;

	[Tooltip("Width of her vision cone (degrees). 180 = everything in front of her")]
	[Range(10f, 360f)]
	public float viewAngle;

	[Tooltip("Up close she notices the player in ANY direction within this distance (meters)")]
	public float proximityRange;

	[Header("Chase")]
	[Tooltip("How long she keeps chasing after losing sight of the player (seconds)")]
	public float loseSightGraceTime;

	[Tooltip("How close she must be to hit the player (meters)")]
	public float attackRange;

	[Header("Noise Investigation")]
	[Tooltip("How long she stands and looks around at the noise spot (seconds)")]
	public float soundInvestigateWaitTime;

	[Header("Patrol Pauses")]
	[Tooltip("Shortest pause at a patrol point (seconds)")]
	public float minWaitTime;

	[Tooltip("Longest pause at a patrol point (seconds)")]
	public float maxWaitTime;

	[Header("Hiding Spots")]
	[Tooltip("How long she stands at the bed before the bed kill (seconds). Shorter = harder")]
	public float bedKillWaitTime;

	public GrannyDifficultySettings()
	{
	}

	public GrannyDifficultySettings(float patrol, float chase, float investigate, float view, float angle, float proximity, float loseSight, float attack, float investigateWait, float minWait, float maxWait, float bedWait)
	{
	}
}

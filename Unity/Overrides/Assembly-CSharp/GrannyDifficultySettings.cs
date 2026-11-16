using System;
using UnityEngine;

/// <summary>Granny's numbers for one mode (Easy / Normal / Hard / Extreme), set on her GrannyAI.</summary>
[Serializable]
public class GrannyDifficultySettings
{
    [Header("Speeds")]
    public float patrolSpeed;
    public float chaseSpeed;
    public float investigateSpeed;

    [Header("Vision")]
    public float viewDistance;
    public float viewAngle;
    public float proximityRange;

    [Header("Chase")]
    public float loseSightGraceTime;
    public float attackRange;

    [Header("Noise Investigation")]
    public float soundInvestigateWaitTime;

    [Header("Patrol Pauses")]
    public float minWaitTime;
    public float maxWaitTime;

    [Header("Hiding Spots")]
    public float bedKillWaitTime;

    public GrannyDifficultySettings()
    {
        patrolSpeed = 1.2f; chaseSpeed = 2.8f; investigateSpeed = 2.8f;
        viewDistance = 8f; viewAngle = 120f; proximityRange = 3f;
        loseSightGraceTime = 3f; attackRange = 1.8f; soundInvestigateWaitTime = 4f;
        minWaitTime = 5f; maxWaitTime = 5f; bedKillWaitTime = 2f;
    }

    public GrannyDifficultySettings(float patrol, float chase, float investigate, float view, float angle, float proximity, float loseSight, float attack, float investigateWait, float minWait, float maxWait, float bedWait)
    {
        patrolSpeed = patrol; chaseSpeed = chase; investigateSpeed = investigate;
        viewDistance = view; viewAngle = angle; proximityRange = proximity;
        loseSightGraceTime = loseSight; attackRange = attack; soundInvestigateWaitTime = investigateWait;
        minWaitTime = minWait; maxWaitTime = maxWait; bedKillWaitTime = bedWait;
    }
}

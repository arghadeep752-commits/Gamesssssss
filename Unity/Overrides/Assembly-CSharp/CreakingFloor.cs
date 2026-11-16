using UnityEngine;

/// <summary>
/// A creaky floorboard: stepping on it makes a creak Granny can hear (Easy: silent; Normal: within the hearing radius;
/// Hard and Extreme: anywhere in the house).
/// </summary>
public class CreakingFloor : MonoBehaviour
{
    [Header("Audio Settings")]
    public AudioSource audioSource;
    public AudioClip[] creakSounds;

    [Header("Granny Hearing Range Per Difficulty")]
    public float normalHearingRadius;
    public bool hardHearsFromAnywhere;
    public bool extremeHearsFromAnywhere;

    [Header("Cooldown")]
    public float cooldownTime;

    private bool isCoolingDown;

    private void OnTriggerEnter(Collider other)
    {
        if (isCoolingDown || other.GetComponentInParent<FPSController>() == null) return;
        PlayCreakSoundAndAlert();
    }

    private string GetDifficulty()
    {
        return GameSave.Difficulty;
    }

    private void PlayCreakSoundAndAlert()
    {
        string difficulty = GetDifficulty();
        if (difficulty == "Easy") return;
        if (audioSource == null) audioSource = GetComponent<AudioSource>();
        if (audioSource != null && creakSounds != null && creakSounds.Length > 0)
        {
            AudioClip c = creakSounds[Random.Range(0, creakSounds.Length)];
            if (c != null) audioSource.PlayOneShot(c);
        }
        else if (audioSource != null && audioSource.clip != null) audioSource.Play();
        AlertGranny(transform.position, difficulty);
        isCoolingDown = true;
        Invoke(nameof(ResetCooldown), Mathf.Max(0.5f, cooldownTime));
    }

    private void AlertGranny(Vector3 noisePosition, string difficulty)
    {
        if (difficulty == "Practice") return;
        GrannyAI g = GrannyAI.Instance;
        if (g == null) return;
        bool anywhere = (difficulty == "Hard" && hardHearsFromAnywhere) || (difficulty == "Extreme" && extremeHearsFromAnywhere);
        if (anywhere || Vector3.Distance(g.transform.position, noisePosition) <= (normalHearingRadius > 0f ? normalHearingRadius : 20f))
            g.HearNoise(noisePosition, "creaking floor");
    }

    private void ResetCooldown()
    {
        isCoolingDown = false;
    }

    private void OnDrawGizmosSelected()
    {
        Gizmos.color = new Color(1f, 0.6f, 0f, 0.4f);
        Gizmos.DrawWireSphere(transform.position, normalHearingRadius);
    }
}

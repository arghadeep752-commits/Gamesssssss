using System.Collections;
using System.Collections.Generic;
using UnityEngine;

/// <summary>Crickets and night air outside: fades in when the player is in the outdoor zone, out when he goes in.</summary>
public class OutdoorAmbientZone : MonoBehaviour
{
    [Header("Audio References")]
    public AudioSource ambientAudioSource;

    [Header("Fade Settings")]
    public float fadeDuration;
    public float maxVolume;

    [Header("Player Detection")]
    public Transform player;
    public float feetCheckDepth;

    private static readonly List<OutdoorAmbientZone> allZones = new List<OutdoorAmbientZone>();
    private static bool mutedByDeath;
    private Collider[] zoneColliders;
    private Coroutine fadeCoroutine;
    private bool playerInside;
    private Vector3 lastPlayerPos;
    private bool hasLastPos;

    private void Awake()
    {
        zoneColliders = GetComponentsInChildren<Collider>();
        foreach (Collider c in zoneColliders) c.isTrigger = true;
        if (ambientAudioSource == null) ambientAudioSource = GetComponent<AudioSource>();
        mutedByDeath = false;
    }

    private void OnEnable()
    {
        if (!allZones.Contains(this)) allZones.Add(this);
    }

    private void OnDisable()
    {
        allZones.Remove(this);
    }

    private void Start()
    {
        if (player == null) { GameObject p = GameSave.PlayerObject(); if (p != null) player = p.transform; }
        if (ambientAudioSource != null)
        {
            ambientAudioSource.loop = true;
            ambientAudioSource.volume = 0f;
            if (!ambientAudioSource.isPlaying) ambientAudioSource.Play();
        }
    }

    private void Update()
    {
        if (player == null || ambientAudioSource == null || mutedByDeath) return;
        if (hasLastPos && (player.position - lastPlayerPos).sqrMagnitude < 0.0025f) return;
        lastPlayerPos = player.position;
        hasLastPos = true;
        bool inside = IsPlayerInZone();
        if (inside == playerInside) return;
        playerInside = inside;
        StartFade(inside ? (maxVolume > 0f ? maxVolume : 0.2f) : 0f);
    }

    private bool IsPlayerInZone()
    {
        float depth = feetCheckDepth > 0f ? feetCheckDepth : 2.5f;
        for (float d = 0f; d <= depth; d += 0.5f)
            if (ContainsPoint(player.position + Vector3.down * d)) return true;
        return false;
    }

    private bool ContainsPoint(Vector3 point)
    {
        foreach (Collider c in zoneColliders)
            if (c != null && c.enabled && (c.ClosestPoint(point) - point).sqrMagnitude < 0.0001f) return true;
        return false;
    }

    public static void OnPlayerDied()
    {
        mutedByDeath = true;
        foreach (OutdoorAmbientZone z in allZones) z.StopAmbientSoundImmediate();
    }

    public static void OnNewDay()
    {
        mutedByDeath = false;
        foreach (OutdoorAmbientZone z in allZones) { z.playerInside = false; z.hasLastPos = false; }
    }

    public void StopAmbientSoundImmediate()
    {
        if (fadeCoroutine != null) StopCoroutine(fadeCoroutine);
        if (ambientAudioSource != null) ambientAudioSource.volume = 0f;
        playerInside = false;
    }

    private void StartFade(float targetVolume)
    {
        if (fadeCoroutine != null) StopCoroutine(fadeCoroutine);
        fadeCoroutine = StartCoroutine(FadeAudio(targetVolume));
    }

    private IEnumerator FadeAudio(float targetVolume)
    {
        float startVolume = ambientAudioSource.volume;
        float elapsed = 0f;
        float d = Mathf.Max(0.05f, fadeDuration);
        while (elapsed < d)
        {
            elapsed += Time.deltaTime;
            ambientAudioSource.volume = Mathf.Lerp(startVolume, targetVolume, elapsed / d);
            yield return null;
        }
        ambientAudioSource.volume = targetVolume;
    }
}

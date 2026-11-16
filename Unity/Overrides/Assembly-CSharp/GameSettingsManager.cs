using UnityEngine;
using UnityEngine.UI;

/// <summary>In-game settings: pauses the game, music on/off, look sensitivity, and quitting to the menu with a warning.</summary>
public class GameSettingsManager : MonoBehaviour
{
    [Header("UI Component References")]
    public GameObject settingsPanel;
    public Toggle musicToggle;
    public Slider sensitivitySlider;

    [Header("Pause & Warning UI Additions")]
    public GameObject quitWarningPanel;
    public MonoBehaviour fpsController;

    [Header("Hide These While Settings Are Open")]
    public GameObject[] hideWhileSettingsOpen;

    [Header("Default Safe Settings")]
    public float defaultSensitivity;

    private bool isPaused;
    private bool[] wasShowingBeforeSettings;

    private void Start()
    {
        if (settingsPanel != null) settingsPanel.SetActive(false);
        if (quitWarningPanel != null) quitWarningPanel.SetActive(false);
        if (musicToggle != null)
        {
            musicToggle.SetIsOnWithoutNotify(MusicSettings.IsOn);
            musicToggle.onValueChanged.AddListener(OnMusicToggleChanged);
        }
        float sens = GameSave.Sensitivity(defaultSensitivity > 0f ? defaultSensitivity : 2f);
        if (sensitivitySlider != null)
        {
            sensitivitySlider.SetValueWithoutNotify(Mathf.Clamp(sens, sensitivitySlider.minValue, sensitivitySlider.maxValue));
            sensitivitySlider.onValueChanged.AddListener(OnSensitivitySliderChanged);
        }
        ApplySensitivityState(sens);
    }

    private void LateUpdate()
    {
        if (isPaused && Time.timeScale != 0f) Time.timeScale = 0f;
    }

    private void HideGameplayButtons()
    {
        if (hideWhileSettingsOpen == null) return;
        wasShowingBeforeSettings = new bool[hideWhileSettingsOpen.Length];
        for (int i = 0; i < hideWhileSettingsOpen.Length; i++)
        {
            GameObject g = hideWhileSettingsOpen[i];
            if (g == null) continue;
            wasShowingBeforeSettings[i] = g.activeSelf;
            g.SetActive(false);
        }
    }

    private void ShowGameplayButtons()
    {
        if (hideWhileSettingsOpen == null || wasShowingBeforeSettings == null) return;
        for (int i = 0; i < hideWhileSettingsOpen.Length && i < wasShowingBeforeSettings.Length; i++)
            if (hideWhileSettingsOpen[i] != null && wasShowingBeforeSettings[i]) hideWhileSettingsOpen[i].SetActive(true);
    }

    private void Update()
    {
        if (Input.GetKeyDown(KeyCode.Escape))
        {
            if (isPaused) ResumeGame();
            else OpenSettings();
        }
    }

    public void OpenSettings()
    {
        if (isPaused) return;
        isPaused = true;
        if (settingsPanel != null) settingsPanel.SetActive(true);
        if (quitWarningPanel != null) quitWarningPanel.SetActive(false);
        HideGameplayButtons();
        if (fpsController != null) fpsController.enabled = false;
        Time.timeScale = 0f;
    }

    public void ResumeGame()
    {
        if (!isPaused) return;
        isPaused = false;
        if (settingsPanel != null) settingsPanel.SetActive(false);
        if (quitWarningPanel != null) quitWarningPanel.SetActive(false);
        ShowGameplayButtons();
        Time.timeScale = 1f;
        if (fpsController != null)
        {
            PlayerWakeUp wake = fpsController.GetComponent<PlayerWakeUp>();
            bool locked = (wake != null && wake.IsWakingUp) || (MobilePickUpScript.Instance != null && MobilePickUpScript.Instance.IsTeleporting);
            if (!locked) fpsController.enabled = true;
        }
    }

    public void OnMainMenuButtonClicked()
    {
        if (quitWarningPanel != null) quitWarningPanel.SetActive(true);
        else ConfirmQuitToMainMenu();
    }

    public void CancelQuit()
    {
        if (quitWarningPanel != null) quitWarningPanel.SetActive(false);
    }

    public void ConfirmQuitToMainMenu()
    {
        isPaused = false;
        Time.timeScale = 1f;
        DimnightUtil.LoadScene("MainMenu", null);
    }

    private void OnMusicToggleChanged(bool isMusicOn)
    {
        MusicSettings.SetEnabled(isMusicOn);
    }

    private void OnSensitivitySliderChanged(float newSensitivityValue)
    {
        GameSave.SetSensitivity(newSensitivityValue);
        ApplySensitivityState(newSensitivityValue);
    }

    private void ApplySensitivityState(float sensitivityValue)
    {
        FPSController fps = fpsController as FPSController;
        if (fps == null && fpsController != null) fps = fpsController.GetComponent<FPSController>();
        if (fps == null) fps = FindFirstObjectByType<FPSController>();
        if (fps != null) fps.mouseSensitivity = sensitivityValue;
    }
}

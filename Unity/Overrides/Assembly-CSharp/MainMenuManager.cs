using System.Collections;
using TMPro;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.UI;

/// <summary>
/// Main menu: Play -> choose the mode (Practice / Easy / Normal / Hard / Extreme, darker mode, extra locks)
/// -> "good luck" -> loading screen -> the house. Music and texture quality are saved between sessions.
/// </summary>
public class MainMenuManager : MonoBehaviour
{
    [Header("Scene Settings")]
    public string gameplaySceneName;

    [Header("UI Panels")]
    public GameObject mainMenuPanel;
    public GameObject optionsChoosePanel;
    public GameObject goodLuckPanel;
    public GameObject loadingPanel;

    [Header("UI Toggles")]
    public Toggle darkerModeToggle;
    public Toggle extraLocksToggle;
    public Toggle musicToggle;

    [Header("Menu Music")]
    public AudioSource menuMusicSource;

    [Header("Quality (Texture) Settings")]
    public TMP_Dropdown qualityDropdown;
    public int defaultQualityIndex;
    public int lowTextureLimit;
    public int mediumTextureLimit;
    public int highTextureLimit;
    public bool alsoChangeUnityQualityLevel;
    public int lowUnityQualityLevel;
    public int mediumUnityQualityLevel;
    public int highUnityQualityLevel;

    [Header("Loading UI Elements")]
    public TextMeshProUGUI loadingText;

    [Header("Instruction / Description UI")]
    public TextMeshProUGUI difficultyDescriptionText;

    [Header("Write Your Difficulty Descriptions Here")]
    public string practiceText;
    public string easyText;
    public string normalText;
    public string hardText;
    public string extremeText;

    private string selectedDifficulty;
    private bool isDarkerModeOn;
    private bool isExtraLocksOn;
    private bool isMusicOn;
    private int selectedQualityIndex;
    private bool playerDarkerChoice;
    private bool playerExtraLocksChoice;
    private bool loading;
    private bool ignoreToggleEvents;
    private int lastPlayFrame = -1, lastContinueFrame = -1, lastGoodLuckFrame = -1, lastBackFrame = -1;

    private const string DarkerChoiceKey = "DarkerModeChoice";
    private const string ExtraLocksChoiceKey = "ExtraLocksChoice";

    private void Start()
    {
        Time.timeScale = 1f;
        AudioListener.pause = false;
        Cursor.lockState = CursorLockMode.None;
        Cursor.visible = true;
        if (string.IsNullOrEmpty(gameplaySceneName)) gameplaySceneName = "Main";

        if (mainMenuPanel != null) mainMenuPanel.SetActive(true);
        if (optionsChoosePanel != null) optionsChoosePanel.SetActive(false);
        if (goodLuckPanel != null) goodLuckPanel.SetActive(false);
        if (loadingPanel != null) loadingPanel.SetActive(false);

        LoadSavedPanelPreferences();

        isMusicOn = MusicSettings.IsOn;
        ignoreToggleEvents = true;
        if (musicToggle != null)
        {
            musicToggle.SetIsOnWithoutNotify(isMusicOn);
            musicToggle.onValueChanged.AddListener(SetMusicFromCode);
        }
        if (darkerModeToggle != null) darkerModeToggle.onValueChanged.AddListener(SetDarkerModeFromCode);
        if (extraLocksToggle != null) extraLocksToggle.onValueChanged.AddListener(SetExtraLocksFromCode);
        ignoreToggleEvents = false;
        ApplyMenuMusic(isMusicOn);

        selectedQualityIndex = Mathf.Clamp(PlayerPrefs.GetInt(GameQualityApplier.QualityIndexKey, defaultQualityIndex), 0, 2);
        if (qualityDropdown != null)
        {
            qualityDropdown.SetValueWithoutNotify(selectedQualityIndex);
            qualityDropdown.onValueChanged.AddListener(SetQualityFromCode);
        }
        ApplyAndSaveQuality(selectedQualityIndex);

        SetDifficulty(GameSave.Difficulty);
    }

    private void LoadSavedPanelPreferences()
    {
        playerDarkerChoice = PlayerPrefs.GetInt(DarkerChoiceKey, 0) == 1;
        playerExtraLocksChoice = PlayerPrefs.GetInt(ExtraLocksChoiceKey, 0) == 1;
        isDarkerModeOn = playerDarkerChoice;
        isExtraLocksOn = playerExtraLocksChoice;
        if (darkerModeToggle != null) darkerModeToggle.SetIsOnWithoutNotify(isDarkerModeOn);
        if (extraLocksToggle != null) extraLocksToggle.SetIsOnWithoutNotify(isExtraLocksOn);
    }

    public void OnPlayButtonClicked()
    {
        if (!GameSave.FirstThisFrame(ref lastPlayFrame) || loading) return;
        if (mainMenuPanel != null) mainMenuPanel.SetActive(false);
        if (optionsChoosePanel != null) optionsChoosePanel.SetActive(true);
        UpdateDifficultyInstruction(selectedDifficulty);
        RefreshToggleInteractability();
    }

    public void OnQuitButtonClicked()
    {
        PlayerPrefs.Save();
        Application.Quit();
    }

    public void SetDifficulty(string difficulty)
    {
        if (string.IsNullOrEmpty(difficulty)) difficulty = "Normal";
        selectedDifficulty = char.ToUpperInvariant(difficulty[0]) + difficulty.Substring(1).ToLowerInvariant();
        GameSave.Difficulty = selectedDifficulty;
        RefreshToggleInteractability();
        UpdateDifficultyInstruction(selectedDifficulty);
    }

    private void RefreshToggleInteractability()
    {
        bool extreme = selectedDifficulty == "Extreme";
        ignoreToggleEvents = true;
        if (extreme)
        {
            // Extreme: extra locks and darker mode are always on
            isDarkerModeOn = true;
            isExtraLocksOn = true;
        }
        else
        {
            isDarkerModeOn = playerDarkerChoice;
            isExtraLocksOn = playerExtraLocksChoice;
        }
        if (darkerModeToggle != null)
        {
            darkerModeToggle.SetIsOnWithoutNotify(isDarkerModeOn);
            darkerModeToggle.interactable = !extreme;
        }
        if (extraLocksToggle != null)
        {
            extraLocksToggle.SetIsOnWithoutNotify(isExtraLocksOn);
            extraLocksToggle.interactable = !extreme;
        }
        ignoreToggleEvents = false;
    }

    private void UpdateDifficultyInstruction(string difficulty)
    {
        if (difficultyDescriptionText == null) return;
        string text;
        switch (difficulty)
        {
            case "Practice": text = practiceText; break;
            case "Easy": text = easyText; break;
            case "Hard": text = hardText; break;
            case "Extreme": text = extremeText; break;
            default: text = normalText; break;
        }
        difficultyDescriptionText.text = text ?? "";
    }

    public void SetDarkerMode(bool isOn)
    {
        if (ignoreToggleEvents) return;
        if (selectedDifficulty == "Extreme") { RefreshToggleInteractability(); return; }
        isDarkerModeOn = isOn;
        playerDarkerChoice = isOn;
        PlayerPrefs.SetInt(DarkerChoiceKey, isOn ? 1 : 0);
        PlayerPrefs.Save();
    }

    public void SetExtraLocks(bool isOn)
    {
        if (ignoreToggleEvents) return;
        if (selectedDifficulty == "Extreme") { RefreshToggleInteractability(); return; }
        isExtraLocksOn = isOn;
        playerExtraLocksChoice = isOn;
        PlayerPrefs.SetInt(ExtraLocksChoiceKey, isOn ? 1 : 0);
        PlayerPrefs.Save();
    }

    public void SetMusic(bool isOn)
    {
        if (ignoreToggleEvents) return;
        if (isMusicOn == isOn && MusicSettings.IsOn == isOn) return;
        isMusicOn = isOn;
        MusicSettings.SetEnabled(isOn);
        ApplyMenuMusic(isOn);
    }

    private void SetMusicFromCode(bool isOn) { SetMusic(isOn); }
    private void SetDarkerModeFromCode(bool isOn) { SetDarkerMode(isOn); }
    private void SetExtraLocksFromCode(bool isOn) { SetExtraLocks(isOn); }
    private void SetQualityFromCode(int index) { SetQuality(index); }

    private void ApplyMenuMusic(bool on)
    {
        if (menuMusicSource == null) return;
        if (on)
        {
            menuMusicSource.mute = false;
            if (!menuMusicSource.isPlaying) menuMusicSource.Play();
        }
        else
        {
            menuMusicSource.Stop();
        }
    }

    public void SetQuality(int qualityIndex)
    {
        if (qualityIndex == selectedQualityIndex && PlayerPrefs.HasKey(GameQualityApplier.QualityIndexKey)) return;
        ApplyAndSaveQuality(qualityIndex);
    }

    private void ApplyAndSaveQuality(int index)
    {
        selectedQualityIndex = Mathf.Clamp(index, 0, 2);
        int tex = selectedQualityIndex == 0 ? lowTextureLimit : selectedQualityIndex == 1 ? mediumTextureLimit : highTextureLimit;
        int level = -1;
        if (alsoChangeUnityQualityLevel)
            level = selectedQualityIndex == 0 ? lowUnityQualityLevel : selectedQualityIndex == 1 ? mediumUnityQualityLevel : highUnityQualityLevel;
        PlayerPrefs.SetInt(GameQualityApplier.QualityIndexKey, selectedQualityIndex);
        PlayerPrefs.SetInt(GameQualityApplier.TextureLimitKey, tex);
        PlayerPrefs.SetInt(GameQualityApplier.UnityLevelKey, level);
        PlayerPrefs.Save();
        GameQualityApplier.Apply(tex, level);
    }

    public void OnBackButtonClicked()
    {
        if (!GameSave.FirstThisFrame(ref lastBackFrame) || loading) return;
        if (goodLuckPanel != null && goodLuckPanel.activeSelf)
        {
            goodLuckPanel.SetActive(false);
            if (optionsChoosePanel != null) optionsChoosePanel.SetActive(true);
            return;
        }
        if (optionsChoosePanel != null) optionsChoosePanel.SetActive(false);
        if (mainMenuPanel != null) mainMenuPanel.SetActive(true);
    }

    public void OnOptionsContinueButtonClicked()
    {
        if (!GameSave.FirstThisFrame(ref lastContinueFrame) || loading) return;
        GameSave.Difficulty = selectedDifficulty;
        GameSave.DarkerMode = isDarkerModeOn;
        GameSave.ExtraLocks = isExtraLocksOn;
        if (optionsChoosePanel != null) optionsChoosePanel.SetActive(false);
        if (goodLuckPanel != null) goodLuckPanel.SetActive(true);
        else OnGoodLuckContinueButtonClicked();
    }

    public void OnGoodLuckContinueButtonClicked()
    {
        if (!GameSave.FirstThisFrame(ref lastGoodLuckFrame) || loading) return;
        loading = true;
        if (goodLuckPanel != null) goodLuckPanel.SetActive(false);
        if (optionsChoosePanel != null) optionsChoosePanel.SetActive(false);
        if (mainMenuPanel != null) mainMenuPanel.SetActive(false);
        if (loadingPanel != null) loadingPanel.SetActive(true);
        StartCoroutine(LoadSceneWithMinimumTime());
    }

    private IEnumerator LoadSceneWithMinimumTime()
    {
        AsyncOperation operation = SceneManager.LoadSceneAsync(gameplaySceneName);
        if (operation == null) { loading = false; yield break; }
        operation.allowSceneActivation = false;
        float minimumWaitTime = 2.5f;
        float elapsedTime = 0f;
        float textBlinkTimer = 0f;
        bool isTextVisible = true;
        while (elapsedTime < minimumWaitTime || operation.progress < 0.9f)
        {
            elapsedTime += Time.unscaledDeltaTime;
            textBlinkTimer += Time.unscaledDeltaTime;
            if (loadingText != null && textBlinkTimer >= 0.5f)
            {
                textBlinkTimer = 0f;
                isTextVisible = !isTextVisible;
                loadingText.alpha = isTextVisible ? 1f : 0.25f;
            }
            if (menuMusicSource != null && menuMusicSource.isPlaying)
                menuMusicSource.volume = Mathf.MoveTowards(menuMusicSource.volume, 0f, Time.unscaledDeltaTime * 0.4f);
            yield return null;
        }
        operation.allowSceneActivation = true;
    }
}

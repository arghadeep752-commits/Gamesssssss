using UnityEngine;
using UnityEngine.UI;

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
	[Tooltip("Drag your Joystick, Crouch button, Interact (hand) button, Drop button, etc. here. They are hidden while the settings panel is open and come back when it closes. Press + to add more slots.")]
	public GameObject[] hideWhileSettingsOpen;

	[Header("Default Safe Settings")]
	public float defaultSensitivity;

	private bool isPaused;

	private bool[] wasShowingBeforeSettings;

	private void Start()
	{
	}

	private void LateUpdate()
	{
	}

	private void HideGameplayButtons()
	{
	}

	private void ShowGameplayButtons()
	{
	}

	private void Update()
	{
	}

	public void OpenSettings()
	{
	}

	public void ResumeGame()
	{
	}

	public void OnMainMenuButtonClicked()
	{
	}

	public void CancelQuit()
	{
	}

	public void ConfirmQuitToMainMenu()
	{
	}

	private void OnMusicToggleChanged(bool isMusicOn)
	{
	}

	private void OnSensitivitySliderChanged(float newSensitivityValue)
	{
	}

	private void ApplySensitivityState(float sensitivityValue)
	{
	}
}

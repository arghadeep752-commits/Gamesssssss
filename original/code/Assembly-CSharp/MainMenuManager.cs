using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.CompilerServices;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

public class MainMenuManager : MonoBehaviour
{
	[CompilerGenerated]
	private sealed class _003CLoadSceneWithMinimumTime_003Ed__50 : IEnumerator<object>, IEnumerator, IDisposable
	{
		private int _003C_003E1__state;

		private object _003C_003E2__current;

		public MainMenuManager _003C_003E4__this;

		private AsyncOperation _003Coperation_003E5__2;

		private float _003CminimumWaitTime_003E5__3;

		private float _003CelapsedTime_003E5__4;

		private float _003CtextBlinkTimer_003E5__5;

		private bool _003CisTextVisible_003E5__6;

		object IEnumerator<object>.Current
		{
			[DebuggerHidden]
			get
			{
				return null;
			}
		}

		object IEnumerator.Current
		{
			[DebuggerHidden]
			get
			{
				return null;
			}
		}

		[DebuggerHidden]
		public _003CLoadSceneWithMinimumTime_003Ed__50(int _003C_003E1__state)
		{
		}

		[DebuggerHidden]
		void IDisposable.Dispose()
		{
		}

		private bool MoveNext()
		{
			return false;
		}

		bool IEnumerator.MoveNext()
		{
			//ILSpy generated this explicit interface implementation from .override directive in MoveNext
			return this.MoveNext();
		}

		[DebuggerHidden]
		void IEnumerator.Reset()
		{
		}
	}

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
	[Tooltip("Drag the AudioSource of your MenuBackgroundMusic object here. It turns off/on with the Music toggle.")]
	public AudioSource menuMusicSource;

	[Header("Quality (Texture) Settings")]
	[Tooltip("Drag your Quality Dropdown here. Option 0 = Low, 1 = Medium, 2 = High.")]
	public TMP_Dropdown qualityDropdown;

	[Tooltip("Which option is selected the very first time the game is played (0 = Low, 1 = Medium, 2 = High).")]
	[Range(0f, 2f)]
	public int defaultQualityIndex;

	[Tooltip("Texture resolution for LOW. 0 = full size, 1 = half size, 2 = quarter size, 3 = eighth size.")]
	[Range(0f, 3f)]
	public int lowTextureLimit;

	[Tooltip("Texture resolution for MEDIUM. 0 = full size, 1 = half size, 2 = quarter size, 3 = eighth size.")]
	[Range(0f, 3f)]
	public int mediumTextureLimit;

	[Tooltip("Texture resolution for HIGH. 0 = full size, 1 = half size, 2 = quarter size, 3 = eighth size.")]
	[Range(0f, 3f)]
	public int highTextureLimit;

	[Tooltip("OPTIONAL: also switch the Unity Quality Level (Edit > Project Settings > Quality) for each option. Leave OFF to only change textures.")]
	public bool alsoChangeUnityQualityLevel;

	[Tooltip("Unity Quality Level index used for LOW (0 = top of the list in Project Settings > Quality).")]
	public int lowUnityQualityLevel;

	[Tooltip("Unity Quality Level index used for MEDIUM.")]
	public int mediumUnityQualityLevel;

	[Tooltip("Unity Quality Level index used for HIGH.")]
	public int highUnityQualityLevel;

	[Header("Loading UI Elements")]
	public TextMeshProUGUI loadingText;

	[Header("Instruction / Description UI")]
	public TextMeshProUGUI difficultyDescriptionText;

	[TextArea(3, 10)]
	[Header("Write Your Difficulty Descriptions Here")]
	public string practiceText;

	[TextArea(3, 10)]
	public string easyText;

	[TextArea(3, 10)]
	public string normalText;

	[TextArea(3, 10)]
	public string hardText;

	[TextArea(3, 10)]
	public string extremeText;

	private string selectedDifficulty;

	private bool isDarkerModeOn;

	private bool isExtraLocksOn;

	private bool isMusicOn;

	private int selectedQualityIndex;

	private bool playerDarkerChoice;

	private bool playerExtraLocksChoice;

	private const string DarkerChoiceKey = "DarkerModeChoice";

	private const string ExtraLocksChoiceKey = "ExtraLocksChoice";

	private void Start()
	{
	}

	private void LoadSavedPanelPreferences()
	{
	}

	public void OnPlayButtonClicked()
	{
	}

	public void OnQuitButtonClicked()
	{
	}

	public void SetDifficulty(string difficulty)
	{
	}

	private void RefreshToggleInteractability()
	{
	}

	private void UpdateDifficultyInstruction(string difficulty)
	{
	}

	public void SetDarkerMode(bool isOn)
	{
	}

	public void SetExtraLocks(bool isOn)
	{
	}

	public void SetMusic(bool isOn)
	{
	}

	private void ApplyMenuMusic(bool on)
	{
	}

	public void SetQuality(int qualityIndex)
	{
	}

	private void ApplyAndSaveQuality(int index)
	{
	}

	public void OnBackButtonClicked()
	{
	}

	public void OnOptionsContinueButtonClicked()
	{
	}

	public void OnGoodLuckContinueButtonClicked()
	{
	}

	[IteratorStateMachine(typeof(_003CLoadSceneWithMinimumTime_003Ed__50))]
	private IEnumerator LoadSceneWithMinimumTime()
	{
		return null;
	}
}

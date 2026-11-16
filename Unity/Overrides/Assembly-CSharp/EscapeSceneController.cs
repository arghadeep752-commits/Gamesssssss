using System.Collections;
using UnityEngine;

/// <summary>The balloon escape scene: plays for a while, then back to the main menu.</summary>
public class EscapeSceneController : MonoBehaviour
{
    public float escapeDuration;
    public string mainMenuSceneName;

    private void Start()
    {
        Time.timeScale = 1f;
        Debug.Log("Escaped successfully!");
        StartCoroutine(WaitAndGoToMenu());
    }

    private IEnumerator WaitAndGoToMenu()
    {
        yield return new WaitForSeconds(escapeDuration > 0f ? escapeDuration : 35f);
        LoadMainMenu();
    }

    public void LoadMainMenu()
    {
        DimnightUtil.LoadScene(mainMenuSceneName, "MainMenu");
    }
}

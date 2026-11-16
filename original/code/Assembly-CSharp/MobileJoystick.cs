using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

public class MobileJoystick : MonoBehaviour, IDragHandler, IEventSystemHandler, IPointerUpHandler, IPointerDownHandler
{
	private Image joystickBackground;

	private Image joystickHandle;

	private Vector2 inputVector;

	public float Horizontal => 0f;

	public float Vertical => 0f;

	private void Start()
	{
	}

	public void OnDrag(PointerEventData eventData)
	{
	}

	public void OnPointerDown(PointerEventData eventData)
	{
	}

	public void OnPointerUp(PointerEventData eventData)
	{
	}

	public float GetInputDistance()
	{
		return 0f;
	}

	private void OnDisable()
	{
	}
}

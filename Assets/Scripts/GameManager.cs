using UnityEngine;

namespace ZombieStrike
{
    // Temporary pipeline check: a lit spinning cube. Replaced by the real game.
    public class GameManager : MonoBehaviour
    {
        Transform cube;

        void Start()
        {
            var camGo = new GameObject("Camera");
            var cam = camGo.AddComponent<Camera>();
            cam.clearFlags = CameraClearFlags.SolidColor;
            cam.backgroundColor = new Color(0.07f, 0.09f, 0.11f);
            camGo.transform.position = new Vector3(0, 1, -4);

            var lightGo = new GameObject("Light");
            var light = lightGo.AddComponent<Light>();
            light.type = LightType.Directional;
            lightGo.transform.rotation = Quaternion.Euler(50, -30, 0);

            var go = GameObject.CreatePrimitive(PrimitiveType.Cube);
            var baseMat = Resources.Load<Material>("Materials/Lit");
            if (baseMat != null)
            {
                var m = new Material(baseMat);
                m.color = new Color(0.4f, 0.8f, 0.3f);
                go.GetComponent<Renderer>().sharedMaterial = m;
            }
            go.transform.position = new Vector3(0, 1, 0);
            cube = go.transform;
            Debug.Log("ZS-READY");
            Debug.Log("ZS-LAYOUT w=" + Screen.width + " h=" + Screen.height + " play=" + Screen.width / 2 + "," + Screen.height / 2 +
                      " fire=" + (Screen.width - 200) + ",200 joy=200,200 reload=" + (Screen.width - 400) + ",120");
        }

        void Update()
        {
            if (cube != null) cube.Rotate(20 * Time.deltaTime, 45 * Time.deltaTime, 0);
        }
    }
}

using System.Text;
using UnityEngine;
using UnityEngine.UI;

namespace TradersMadness
{
    /// <summary>Scrolling ticker tape of prices (green up, red down) for the menu's bottom bar.</summary>
    [RequireComponent(typeof(Text))]
    public class Ticker : MonoBehaviour
    {
        public float speed = 70f;
        static readonly string[] Sym = { "EUR/USD", "BTC/USD", "GOLD", "GBP/JPY", "ETH/USD", "USD/INR", "OIL", "NAS100", "TRDR", "S&P500", "SILVER", "AUD/USD" };
        Text text;
        RectTransform rt;
        float x, width;
        readonly System.Random rng = new System.Random();

        void Start()
        {
            text = GetComponent<Text>();
            rt = (RectTransform)transform;
            Build();
        }

        void Build()
        {
            var sb = new StringBuilder();
            foreach (string s in Sym)
            {
                bool up = rng.NextDouble() < 0.35;
                double p = 10 + rng.NextDouble() * 9000;
                double ch = (up ? 1 : -1) * rng.NextDouble() * 9.9;
                sb.Append(s).Append(' ').Append(p.ToString("0.00"));
                sb.Append(up ? "  <color=#22F07F>+" : "  <color=#FA2E3C>").Append(ch.ToString("0.00")).Append("%</color>      ");
            }
            string block = sb.ToString();
            text.text = block + block + block;
            width = text.preferredWidth;
            rt.anchorMin = new Vector2(0f, 0f);
            rt.anchorMax = new Vector2(0f, 1f);
            rt.pivot = new Vector2(0f, 0.5f);
            rt.sizeDelta = new Vector2(width + 40f, 0f);
            x = 0f;
        }

        void Update()
        {
            x -= speed * Time.unscaledDeltaTime;
            float block = width / 3f;
            if (block > 1f && x < -block) x += block;
            rt.anchoredPosition = new Vector2(x, 0f);
        }
    }
}

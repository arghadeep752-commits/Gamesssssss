using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

namespace Danga
{
    /// <summary>
    /// The playing screen in the style of the GTA V fan-made mobile games: see-through round buttons with white icons,
    /// the minimap in the bottom-left corner with health and armour under it, money, stars and the weapon top-right.
    /// </summary>
    public class Hud : MonoBehaviour
    {
        public static Hud I;
        public RectTransform rt;
        Stick stick;
        HoldBtn fire, jump, sprint, enter, gas, brakeB, horn, exitB, up, down, weaponB, pauseB, phoneB, context, camB;
        GameObject foot, drive, heli, ctxGo, toastBox;
        Text money, speed, ammo, toast, zoneT, big, clock, fps, radioT;
        Image healthBar, armorBar, flash, wpnIcon, rupee;
        RawImage map;
        RectTransform mapRt, arrow, blipRoot;
        readonly List<Image> starImgs = new List<Image>();
        readonly List<KeyValuePair<Image, Vector3>> blips = new List<KeyValuePair<Image, Vector3>>();
        readonly List<Image> copBlips = new List<Image>();
        float toastUntil, zoneUntil, bigUntil, flashA, radioUntil;
        string lastZone = "";
        System.Action ctxAction;
        float fpsAcc;
        int fpsN;
        public bool showFps;
        public static bool scripted, sFire, sGas, sBrake, sUp;
        public static Vector2 sMove;
        static readonly Color Glass = new Color(1f, 1f, 1f, 0.62f);
        const float MapW = 340f, MapH = 210f;

        public static Hud Create()
        {
            var r = Ui.Fill(Ui.root, "HUD");
            I = r.gameObject.AddComponent<Hud>();
            I.rt = r;
            I.Build();
            return I;
        }

        /// <summary>A GTA-style button: dark see-through circle, white icon.</summary>
        HoldBtn Btn(Transform parent, string icon, Vector2 anchor, Vector2 pos, float size, System.Action click = null)
        {
            var b = Ui.Round(parent, icon, null, Glass, anchor, pos, size, click);
            if (b.icon != null) b.icon.rectTransform.sizeDelta = new Vector2(size * 0.5f, size * 0.5f);
            return b;
        }

        void Build()
        {
            var lp = Ui.Fill(rt, "look");
            var lpi = lp.gameObject.AddComponent<Image>();
            lpi.color = new Color(0, 0, 0, 0);
            lp.gameObject.AddComponent<LookPad>();

            // joystick: anywhere on the left, above the minimap
            var sz = Ui.Box(rt, "stickzone", Ui.BL, new Vector2(0, 250), new Vector2(760, 620));
            var szi = sz.gameObject.AddComponent<Image>();
            szi.color = new Color(0, 0, 0, 0);
            var baseIm = Ui.Img(sz, "ring", new Color(1, 1, 1, 0.9f), Ui.BL, Vector2.zero, new Vector2(230, 230));
            baseIm.rectTransform.pivot = Ui.C;
            baseIm.rectTransform.anchoredPosition = new Vector2(250, 190);
            var knob = Ui.Img(baseIm.transform, "circle", new Color(1, 1, 1, 0.9f), Ui.C, Vector2.zero, new Vector2(100, 100));
            stick = sz.gameObject.AddComponent<Stick>();
            stick.Setup(baseIm.rectTransform, knob.rectTransform);

            // minimap: bottom-left rectangle, like GTA V
            var frame = Ui.Img(rt, null, new Color(0, 0, 0, 0.75f), Ui.BL, new Vector2(22, 34), new Vector2(MapW + 8, MapH + 8));
            var mm = Ui.Box(frame.transform, "minimap", Ui.C, Vector2.zero, new Vector2(MapW, MapH));
            mm.gameObject.AddComponent<RectMask2D>();
            float big2 = Mathf.Sqrt(MapW * MapW + MapH * MapH) + 4f;
            var mapGo = Ui.Box(mm, "map", Ui.C, Vector2.zero, new Vector2(big2, big2));
            map = mapGo.gameObject.AddComponent<RawImage>();
            map.texture = Resources.Load<Texture2D>("Gen/City/map");
            map.raycastTarget = false;
            mapRt = mapGo;
            blipRoot = Ui.Box(mm, "blips", Ui.C, Vector2.zero, new Vector2(MapW, MapH));
            arrow = Ui.Img(mm, "arrow", Color.white, Ui.C, Vector2.zero, new Vector2(26, 26)).rectTransform;
            arrow.pivot = Ui.C;
            arrow.anchoredPosition = new Vector2(0, -20);
            // health (green) and armour (blue) under the map
            Ui.Img(rt, null, new Color(0, 0, 0, 0.75f), Ui.BL, new Vector2(22, 16), new Vector2(MapW + 8, 16));
            healthBar = Ui.Img(rt, null, new Color(0.34f, 0.69f, 0.31f), Ui.BL, new Vector2(26, 20), new Vector2(MapW * 0.6f - 4, 8));
            armorBar = Ui.Img(rt, null, new Color(0.24f, 0.55f, 0.85f), Ui.BL, new Vector2(26 + MapW * 0.6f, 20), new Vector2(MapW * 0.4f - 4, 8));

            // top-right: weapon, money, stars (GTA layout)
            weaponB = Ui.Round(rt, null, null, new Color(0, 0, 0, 0.01f), Ui.TR, new Vector2(-24, -14), 120, () => { if (Player.I != null) Player.I.NextWeapon(1); });
            wpnIcon = Ui.Img(weaponB.transform, "i_fist", Color.white, Ui.C, new Vector2(0, 6), new Vector2(92, 92));
            ammo = Ui.Txt(rt, "", 34, Color.white, TextAnchor.MiddleRight, Ui.TR, new Vector2(-150, -50), new Vector2(240, 40));
            money = Ui.Txt(rt, "₹0", 64, new Color(0.45f, 0.78f, 0.38f), TextAnchor.MiddleRight, Ui.TR, new Vector2(-26, -132), new Vector2(560, 74), Ui.title);
            for (int i = 0; i < 5; i++)
                starImgs.Add(Ui.Img(rt, "i_star", new Color(1, 1, 1, 0.22f), Ui.TR, new Vector2(-28 - (4 - i) * 50, -206), new Vector2(44, 44)));
            clock = Ui.Txt(rt, "", 28, new Color(1, 1, 1, 0.85f), TextAnchor.MiddleRight, Ui.TR, new Vector2(-28, -252), new Vector2(200, 34));
            pauseB = Btn(rt, "pause", Ui.TL, new Vector2(22, -22), 78, () => Menus.I.Pause());
            camB = Btn(rt, "camera", Ui.TL, new Vector2(110, -22), 78, () => { if (Cam.I != null) Cam.I.dist = Cam.I.dist > 5f ? 3.4f : Cam.I.dist > 4f ? 6.5f : 4.4f; });
            phoneB = Btn(rt, "phone", Ui.BL, new Vector2(MapW + 44, 40), 86, () => Menus.I.Phone());
            fps = Ui.Txt(rt, "", 24, Color.yellow, TextAnchor.MiddleLeft, Ui.TL, new Vector2(200, -34), new Vector2(300, 30));

            // on foot
            foot = Ui.Box(rt, "foot", Ui.BR, Vector2.zero, new Vector2(600, 560)).gameObject;
            fire = Btn(foot.transform, "fist", Ui.BR, new Vector2(-46, 64), 170);
            jump = Btn(foot.transform, "jump", Ui.BR, new Vector2(-246, 46), 116, () => { if (Player.I != null) Player.I.jump = true; });
            sprint = Btn(foot.transform, "sprint", Ui.BR, new Vector2(-56, 262), 116);
            enter = Btn(foot.transform, "car", Ui.BR, new Vector2(-236, 216), 116, () => { if (Player.I != null && Player.I.nearVehicle != null) Player.I.EnterVehicle(Player.I.nearVehicle); });
            // driving
            drive = Ui.Box(rt, "drive", Ui.BR, Vector2.zero, new Vector2(600, 560)).gameObject;
            gas = Btn(drive.transform, "gas", Ui.BR, new Vector2(-46, 64), 170);
            brakeB = Btn(drive.transform, "brake", Ui.BR, new Vector2(-246, 46), 130);
            horn = Btn(drive.transform, "horn", Ui.BR, new Vector2(-56, 262), 106, () => { if (Player.I != null && Player.I.vehicle != null) Player.I.vehicle.Horn(); });
            exitB = Btn(rt, "exit", Ui.BR, new Vector2(-236, 236), 106, () => { if (Player.I != null) Player.I.ExitVehicle(); });
            // helicopter
            heli = Ui.Box(rt, "heli", Ui.BR, Vector2.zero, new Vector2(600, 560)).gameObject;
            up = Btn(heli.transform, "up", Ui.BR, new Vector2(-56, 262), 150);
            down = Btn(heli.transform, "down", Ui.BR, new Vector2(-56, 64), 150);
            speed = Ui.Txt(rt, "", 46, Color.white, TextAnchor.LowerRight, Ui.BR, new Vector2(-330, 30), new Vector2(300, 60), Ui.title);
            radioT = Ui.Txt(rt, "", 34, Color.white, TextAnchor.MiddleCenter, Ui.T, new Vector2(0, -30), new Vector2(900, 50));
            // context action (shops, house, hospital)
            var cb = Ui.Wide(rt, "SHOP", new Color(0, 0, 0, 0.7f), Ui.B, new Vector2(0, 150), new Vector2(360, 86), () => { if (ctxAction != null) ctxAction(); }, 40);
            context = cb;
            ctxGo = cb.gameObject;
            ctxGo.SetActive(false);
            // GTA-style help box (top-left) for messages
            var tb = Ui.Img(rt, null, new Color(0, 0, 0, 0.78f), Ui.TL, new Vector2(22, -112), new Vector2(600, 84));
            toastBox = tb.gameObject;
            toast = Ui.Txt(tb.transform, "", 34, Color.white, TextAnchor.MiddleLeft, Ui.C, Vector2.zero, new Vector2(570, 80), Ui.body, false);
            toastBox.SetActive(false);
            zoneT = Ui.Txt(rt, "", 52, Color.white, TextAnchor.MiddleCenter, Ui.B, new Vector2(0, 40), new Vector2(1000, 70), Ui.title);
            big = Ui.Txt(rt, "", 200, Ui.Red, TextAnchor.MiddleCenter, Ui.C, new Vector2(0, 40), new Vector2(1600, 260), Ui.title);
            flash = Ui.Img(rt, null, new Color(0.8f, 0f, 0f, 0f), Ui.C, Vector2.zero, new Vector2(4000, 3000));
            BuildBlips();
        }

        void BuildBlips()
        {
            if (City.I == null) return;
            foreach (var p in City.I.points)
            {
                string icon = null;
                Color c = Color.white;
                switch (p.kind)
                {
                    case "house": icon = "house"; c = new Color(0.4f, 0.9f, 0.4f); break;
                    case "gunshop": icon = "pistol"; c = new Color(1f, 0.4f, 0.35f); break;
                    case "clothes": icon = "shirt"; c = new Color(0.85f, 0.55f, 1f); break;
                    case "hospital": icon = "cross"; c = new Color(1f, 0.35f, 0.35f); break;
                    case "police": icon = "badge"; c = new Color(0.45f, 0.65f, 1f); break;
                    case "boat": icon = "boat"; c = new Color(0.45f, 0.85f, 1f); break;
                    case "vehicle": if (p.model == "helicopter") { icon = "heli"; c = new Color(1f, 0.85f, 0.3f); } break;
                }
                if (icon == null) continue;
                var bg = Ui.Img(blipRoot, "mask_circle", new Color(0, 0, 0, 0.8f), Ui.C, Vector2.zero, new Vector2(30, 30));
                Ui.Img(bg.transform, "i_" + icon, c, Ui.C, Vector2.zero, new Vector2(21, 21));
                blips.Add(new KeyValuePair<Image, Vector3>(bg, p.p));
            }
            for (int i = 0; i < 14; i++)
            {
                var b = Ui.Img(blipRoot, "mask_circle", new Color(0.3f, 0.5f, 1f), Ui.C, Vector2.zero, new Vector2(12, 12));
                b.gameObject.SetActive(false);
                copBlips.Add(b);
            }
        }

        public static string Rupees(int v)
        {
            // Indian grouping: 12,34,567
            string s = Mathf.Abs(v).ToString();
            if (s.Length > 3)
            {
                string last = s.Substring(s.Length - 3);
                string rest = s.Substring(0, s.Length - 3);
                var parts = new List<string>();
                while (rest.Length > 2) { parts.Insert(0, rest.Substring(rest.Length - 2)); rest = rest.Substring(0, rest.Length - 2); }
                if (rest.Length > 0) parts.Insert(0, rest);
                s = string.Join(",", parts.ToArray()) + "," + last;
            }
            return (v < 0 ? "-" : "") + s;
        }

        public static void Toast(string s, Color c, float time = 2.8f)
        {
            if (I == null) return;
            I.toast.text = s;
            I.toast.color = c == Color.white ? Color.white : Color.Lerp(c, Color.white, 0.25f);
            I.toastUntil = Time.unscaledTime + time;
            I.toastBox.SetActive(true);
        }

        public static void Toast(string s) { Toast(s, Color.white); }

        public static void Big(string s, Color c, float time)
        {
            if (I == null) return;
            I.big.text = s;
            I.big.color = c;
            I.bigUntil = Time.unscaledTime + time;
        }

        public static void Flash() { if (I != null) I.flashA = 0.4f; }

        public static void Stars()
        {
            if (I == null) return;
            for (int i = 0; i < I.starImgs.Count; i++) I.starImgs[i].transform.localScale = Vector3.one * (i < Wanted.stars ? 1.3f : 1f);
        }

        public static void Radio(string s) { if (I != null) { I.radioT.text = s; I.radioUntil = Time.unscaledTime + 3f; } }

        public void SetContext(string label, System.Action a)
        {
            ctxAction = a;
            bool on = label != null;
            if (ctxGo.activeSelf != on) ctxGo.SetActive(on);
            if (on && context.label.text != label) context.label.text = label;
        }

        void Update()
        {
            Player p = Player.I;
            if (p == null) return;
            float dt = Time.unscaledDeltaTime;
            Vehicle v = p.vehicle;
            bool inV = v != null;
            bool isHeli = inV && v.spec.IsHeli;
            foot.SetActive(!inV);
            drive.SetActive(inV && !isHeli);
            heli.SetActive(isHeli);
            exitB.gameObject.SetActive(inV);
            enter.gameObject.SetActive(!inV && p.nearVehicle != null);
            if (enter.gameObject.activeSelf && p.nearVehicle != null)
            {
                string ic = p.nearVehicle.spec.IsHeli ? "i_heli" : p.nearVehicle.spec.IsBoat ? "i_boat" : "i_car";
                if (enter.icon.sprite != Ui.S(ic)) enter.icon.sprite = Ui.S(ic);
            }
            // inputs (the emulator check drives the same inputs through 'scripted')
            Vector2 mv = stick.value;
#if UNITY_EDITOR
            mv += new Vector2(Input.GetAxisRaw("Horizontal"), Input.GetAxisRaw("Vertical"));
            mv = Vector2.ClampMagnitude(mv, 1f);
#endif
            bool fireH = fire.held, sprintH = sprint.held, gasH = gas.held, brakeH = brakeB.held, upH = up.held, downH = down.held;
            if (scripted) { mv = sMove; fireH = sFire; sprintH = false; gasH = sGas; brakeH = sBrake; upH = sUp; downH = false; }
            p.move = mv;
            p.fire = fireH;
            p.sprint = sprintH;
            if (inV)
            {
                v.steer = Mathf.MoveTowards(v.steer, mv.x, dt * (v.spec.IsBike ? 3.5f : 4.5f));
                if (isHeli)
                {
                    v.throttle = mv.y;
                    v.lift = (upH ? 1f : 0f) - (downH ? 1f : 0f);
                }
                else
                {
                    float thr = gasH ? 1f : 0f;
                    if (brakeH) thr = v.ForwardSpeed > 1.5f ? 0f : -1f;
                    if (Mathf.Abs(mv.y) > 0.5f && !gasH && !brakeH) thr = mv.y > 0 ? mv.y : (v.ForwardSpeed > 1.5f ? 0f : mv.y);
                    v.throttle = thr;
                    v.brake = brakeH && v.ForwardSpeed > 1.5f ? 1f : (mv.y < -0.5f && v.ForwardSpeed > 1.5f ? 1f : 0f);
                    v.handbrake = brakeH && gasH;
                }
                int kmh = Mathf.RoundToInt(v.Speed * 3.6f);
                speed.text = isHeli ? kmh + " KM/H  " + Mathf.RoundToInt(v.transform.position.y) + " M" : kmh + " KM/H";
            }
            else speed.text = "";
            if (Time.unscaledTime > radioUntil) radioT.text = "";

            // weapon, money, health
            var def = p.Def;
            if (wpnIcon.sprite != Ui.S("i_" + def.icon)) wpnIcon.sprite = Ui.S("i_" + def.icon);
            ammo.text = def.melee ? "" : p.clip[(int)def.id] + "  " + p.ammo[(int)def.id];
            fire.icon.sprite = Ui.S(def.melee ? "i_" + def.icon : "i_target");
            money.text = "₹" + Rupees(p.money);
            healthBar.rectTransform.sizeDelta = new Vector2((MapW * 0.6f - 4f) * Mathf.Clamp01(p.health / p.maxHealth), 8f);
            healthBar.color = p.health < 30f ? new Color(0.8f, 0.2f, 0.15f) : new Color(0.34f, 0.69f, 0.31f);
            armorBar.rectTransform.sizeDelta = new Vector2((MapW * 0.4f - 4f) * Mathf.Clamp01(p.armor / 100f), 8f);
            clock.text = Env.Clock();
            for (int i = 0; i < starImgs.Count; i++)
            {
                bool on = i < Wanted.stars;
                float blink = Wanted.Escape > 0.5f && on ? (Mathf.Sin(Time.unscaledTime * 10f) > 0 ? 1f : 0.35f) : 1f;
                starImgs[i].color = on ? new Color(1f, 1f, 1f, blink) : new Color(1, 1, 1, 0.2f);
                starImgs[i].transform.localScale = Vector3.Lerp(starImgs[i].transform.localScale, Vector3.one, dt * 4f);
            }
            Minimap(p);
            // messages
            if (Time.unscaledTime > toastUntil && toastBox.activeSelf) toastBox.SetActive(false);
            if (Time.unscaledTime > bigUntil) big.text = "";
            string zone = City.I != null ? City.I.ZoneAt(p.transform.position) : "";
            if (zone != lastZone) { lastZone = zone; zoneT.text = zone; zoneUntil = Time.unscaledTime + 4f; }
            zoneT.color = new Color(1f, 1f, 1f, Mathf.Clamp01(zoneUntil - Time.unscaledTime));
            flashA = Mathf.MoveTowards(flashA, p.health < 25f && !p.dead ? 0.12f + 0.08f * Mathf.Sin(Time.unscaledTime * 6f) : 0f, dt * 0.8f);
            flash.color = new Color(0.7f, 0f, 0f, flashA);
            fpsAcc += dt;
            fpsN++;
            if (fpsAcc > 0.5f) { fps.text = showFps ? Mathf.RoundToInt(fpsN / fpsAcc) + " FPS" : ""; fpsAcc = 0f; fpsN = 0; }
        }

        void Minimap(Player p)
        {
            if (map.texture == null) return;
            float H = City.Half;
            Vector3 pos = p.vehicle != null ? p.vehicle.transform.position : p.transform.position;
            float range = p.vehicle != null ? 260f : 170f;             // metres across the width of the minimap
            float k = MapW / range;                                   // pixels per metre
            float side = mapRt.sizeDelta.x;
            float w = side / k / (2f * H);
            // the player sits a little below the centre (GTA style), so more of the road ahead shows
            Vector2 off = new Vector2(0f, -20f);
            float camYaw = Cam.I != null ? Cam.I.transform.eulerAngles.y : 0f;
            mapRt.localEulerAngles = new Vector3(0, 0, camYaw);
            mapRt.anchoredPosition = off;
            map.uvRect = new Rect((pos.x + H) / (2f * H) - w * 0.5f, (pos.z + H) / (2f * H) - w * 0.5f, w, w);
            float heading = p.vehicle != null ? p.vehicle.transform.eulerAngles.y : p.transform.eulerAngles.y;
            arrow.localEulerAngles = new Vector3(0, 0, camYaw - heading);
            float c = Mathf.Cos(camYaw * Mathf.Deg2Rad), s = Mathf.Sin(camYaw * Mathf.Deg2Rad);
            foreach (var b in blips)
            {
                Vector2 d = new Vector2(b.Value.x - pos.x, b.Value.z - pos.z) * k;
                Vector2 r = new Vector2(d.x * c - d.y * s, d.x * s + d.y * c) + off;
                r.x = Mathf.Clamp(r.x, -MapW / 2 + 14, MapW / 2 - 14);
                r.y = Mathf.Clamp(r.y, -MapH / 2 + 14, MapH / 2 - 14);
                b.Key.rectTransform.anchoredPosition = r;
            }
            int n = 0;
            if (Wanted.stars > 0)
                foreach (var h in Human.all)
                {
                    if (!h.police || h.dead || n >= copBlips.Count) continue;
                    Vector2 d = new Vector2(h.transform.position.x - pos.x, h.transform.position.z - pos.z) * k;
                    Vector2 r = new Vector2(d.x * c - d.y * s, d.x * s + d.y * c) + off;
                    if (Mathf.Abs(r.x) > MapW / 2 || Mathf.Abs(r.y) > MapH / 2) continue;
                    var im = copBlips[n++];
                    im.gameObject.SetActive(true);
                    im.color = Mathf.Sin(Time.unscaledTime * 8f) > 0 ? new Color(0.3f, 0.5f, 1f) : new Color(1f, 0.25f, 0.25f);
                    im.rectTransform.anchoredPosition = r;
                }
            for (int i = n; i < copBlips.Count; i++) if (copBlips[i].gameObject.activeSelf) copBlips[i].gameObject.SetActive(false);
        }
    }
}

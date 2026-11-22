using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

namespace Danga
{
    /// <summary>The playing screen, laid out like Indian Bike Driving 3D: joystick left, big round buttons right, minimap, money, stars.</summary>
    public class Hud : MonoBehaviour
    {
        public static Hud I;
        public RectTransform rt;
        Stick stick;
        HoldBtn fire, jump, sprint, enter, gas, brakeB, horn, exitB, up, down, weaponB, pauseB, phoneB, context, camB;
        GameObject foot, drive, heli, ctxGo;
        Text money, speed, speedUnit, ammo, toast, zoneT, big, clock, fps, radioT;
        Image healthBar, armorBar, flash, wpnIcon;
        RawImage map;
        RectTransform mapRt, arrow, blipRoot;
        readonly List<Image> starImgs = new List<Image>();
        readonly List<KeyValuePair<Image, Vector3>> blips = new List<KeyValuePair<Image, Vector3>>();
        readonly List<Image> copBlips = new List<Image>();
        float toastUntil, zoneUntil, bigUntil, flashA;
        string lastZone = "";
        System.Action ctxAction;
        float fpsAcc;
        int fpsN;
        public bool showFps;
        public static bool scripted, sFire, sGas, sBrake, sUp;
        public static Vector2 sMove;

        public static Hud Create()
        {
            var r = Ui.Fill(Ui.root, "HUD");
            I = r.gameObject.AddComponent<Hud>();
            I.rt = r;
            I.Build();
            return I;
        }

        void Build()
        {
            var lp = Ui.Fill(rt, "look");
            var lpi = lp.gameObject.AddComponent<Image>();
            lpi.color = new Color(0, 0, 0, 0);
            lp.gameObject.AddComponent<LookPad>();

            // joystick zone: the lower-left part of the screen
            var sz = Ui.Box(rt, "stickzone", Ui.BL, Vector2.zero, new Vector2(760, 640));
            var szi = sz.gameObject.AddComponent<Image>();
            szi.color = new Color(0, 0, 0, 0);
            var baseIm = Ui.Img(sz, "ring", new Color(1, 1, 1, 0.85f), Ui.BL, new Vector2(170, 150), new Vector2(260, 260));
            baseIm.rectTransform.pivot = Ui.C;
            baseIm.rectTransform.anchoredPosition = new Vector2(300, 280);
            var knob = Ui.Img(baseIm.transform, "circle", new Color(1, 1, 1, 0.95f), Ui.C, Vector2.zero, new Vector2(120, 120));
            stick = sz.gameObject.AddComponent<Stick>();
            stick.Setup(baseIm.rectTransform, knob.rectTransform);

            // minimap
            var mm = Ui.Box(rt, "minimap", Ui.TL, new Vector2(36, -36), new Vector2(300, 300));
            var mask = mm.gameObject.AddComponent<Image>();
            mask.sprite = Ui.S("mask_circle");
            mm.gameObject.AddComponent<Mask>().showMaskGraphic = true;
            mask.color = new Color(0.15f, 0.2f, 0.18f, 1f);
            var mapGo = Ui.Box(mm, "map", Ui.C, Vector2.zero, new Vector2(300, 300));
            map = mapGo.gameObject.AddComponent<RawImage>();
            map.texture = Resources.Load<Texture2D>("Gen/City/map");
            map.raycastTarget = false;
            mapRt = mapGo;
            blipRoot = Ui.Box(mm, "blips", Ui.C, Vector2.zero, new Vector2(300, 300));
            Ui.Img(rt, "minimap_ring", Color.white, Ui.TL, new Vector2(30, -30), new Vector2(312, 312));
            arrow = Ui.Img(mm, "arrow", new Color(1f, 0.9f, 0.2f), Ui.C, Vector2.zero, new Vector2(34, 34)).rectTransform;
            arrow.pivot = Ui.C;
            arrow.anchoredPosition = Vector2.zero;
            // health and armour
            Ui.Img(rt, "pill", new Color(0, 0, 0, 0.6f), Ui.TL, new Vector2(40, -350), new Vector2(292, 26));
            healthBar = Ui.Img(rt, null, new Color(0.35f, 0.9f, 0.35f), Ui.TL, new Vector2(48, -356), new Vector2(276, 14));
            Ui.Img(rt, "pill", new Color(0, 0, 0, 0.6f), Ui.TL, new Vector2(40, -380), new Vector2(292, 20));
            armorBar = Ui.Img(rt, null, new Color(0.35f, 0.6f, 1f), Ui.TL, new Vector2(48, -385), new Vector2(276, 10));
            clock = Ui.Txt(rt, "", 30, Color.white, TextAnchor.MiddleLeft, Ui.TL, new Vector2(46, -408), new Vector2(200, 36));
            fps = Ui.Txt(rt, "", 24, Color.yellow, TextAnchor.MiddleLeft, Ui.TL, new Vector2(360, -20), new Vector2(300, 30));

            // money and stars
            var mp = Ui.Img(rt, "pill", new Color(0.05f, 0.25f, 0.08f, 0.85f), Ui.TR, new Vector2(-36, -36), new Vector2(380, 84));
            Ui.Img(mp.transform, "i_rupee", new Color(0.55f, 1f, 0.5f), Ui.L, new Vector2(22, 0), new Vector2(56, 56));
            money = Ui.Txt(mp.transform, "0", 60, new Color(0.6f, 1f, 0.55f), TextAnchor.MiddleRight, Ui.R, new Vector2(-26, 2), new Vector2(300, 80));
            for (int i = 0; i < 5; i++)
                starImgs.Add(Ui.Img(rt, "i_star", new Color(1, 1, 1, 0.25f), Ui.TR, new Vector2(-36 - (4 - i) * 66, -132), new Vector2(60, 60)));
            pauseB = Ui.Round(rt, "pause", null, new Color(0.25f, 0.25f, 0.3f), Ui.TR, new Vector2(-440, -40), 84, () => Menus.I.Pause());
            phoneB = Ui.Round(rt, "phone", null, new Color(0.2f, 0.45f, 0.9f), Ui.TR, new Vector2(-536, -40), 84, () => Menus.I.Phone());
            weaponB = Ui.Round(rt, null, null, new Color(0.15f, 0.15f, 0.18f, 0.9f), Ui.TR, new Vector2(-40, -214), 150, () => { if (Player.I != null) Player.I.NextWeapon(1); });
            wpnIcon = Ui.Img(weaponB.transform, "i_fist", Color.white, Ui.C, new Vector2(0, 8), new Vector2(96, 96));
            ammo = Ui.Txt(weaponB.transform, "", 30, Color.white, TextAnchor.MiddleCenter, Ui.B, new Vector2(0, 14), new Vector2(150, 34));
            camB = Ui.Round(rt, "camera", null, new Color(0.25f, 0.25f, 0.3f), Ui.TR, new Vector2(-632, -40), 84, () => { if (Cam.I != null) Cam.I.dist = Cam.I.dist > 5f ? 3.4f : Cam.I.dist > 4f ? 6.5f : 4.4f; });

            // on foot
            foot = Ui.Box(rt, "foot", Ui.BR, Vector2.zero, new Vector2(700, 640)).gameObject;
            fire = Ui.Round(foot.transform, "fist", null, Ui.Red, Ui.BR, new Vector2(-60, 80), 240);
            jump = Ui.Round(foot.transform, "jump", null, Ui.Blue, Ui.BR, new Vector2(-330, 60), 150, () => { if (Player.I != null) Player.I.jump = true; });
            sprint = Ui.Round(foot.transform, "sprint", null, Ui.Saffron, Ui.BR, new Vector2(-90, 350), 150);
            enter = Ui.Round(foot.transform, "car", null, Ui.Yellow, Ui.BR, new Vector2(-330, 260), 160, () => { if (Player.I != null && Player.I.nearVehicle != null) Player.I.EnterVehicle(Player.I.nearVehicle); });
            // driving
            drive = Ui.Box(rt, "drive", Ui.BR, Vector2.zero, new Vector2(700, 640)).gameObject;
            gas = Ui.Round(drive.transform, "gas", null, Ui.Green, Ui.BR, new Vector2(-60, 70), 220);
            brakeB = Ui.Round(drive.transform, "brake", null, Ui.Red, Ui.BR, new Vector2(-310, 50), 180);
            horn = Ui.Round(drive.transform, "horn", null, Ui.Saffron, Ui.BR, new Vector2(-80, 330), 130, () => { if (Player.I != null && Player.I.vehicle != null) Player.I.vehicle.Horn(); });
            exitB = Ui.Round(rt, "exit", null, Ui.Yellow, Ui.BR, new Vector2(-330, 300), 130, () => { if (Player.I != null) Player.I.ExitVehicle(); });
            // helicopter
            heli = Ui.Box(rt, "heli", Ui.BR, Vector2.zero, new Vector2(700, 640)).gameObject;
            up = Ui.Round(heli.transform, "up", null, Ui.Green, Ui.BR, new Vector2(-70, 290), 190);
            down = Ui.Round(heli.transform, "down", null, Ui.Red, Ui.BR, new Vector2(-70, 60), 190);
            speed = Ui.Txt(rt, "", 84, Color.white, TextAnchor.LowerCenter, Ui.B, new Vector2(0, 60), new Vector2(400, 100), Ui.display);
            speedUnit = Ui.Txt(rt, "", 28, Color.white, TextAnchor.UpperCenter, Ui.B, new Vector2(0, 26), new Vector2(300, 40));
            radioT = Ui.Txt(rt, "", 34, Ui.Yellow, TextAnchor.MiddleCenter, Ui.T, new Vector2(0, -100), new Vector2(900, 50));
            // context action (shops, house)
            var cb = Ui.Wide(rt, "SHOP", Ui.Saffron, Ui.B, new Vector2(330, 60), new Vector2(330, 96), () => { if (ctxAction != null) ctxAction(); }, 44);
            context = cb;
            ctxGo = cb.gameObject;
            ctxGo.SetActive(false);
            toast = Ui.Txt(rt, "", 50, Color.white, TextAnchor.MiddleCenter, Ui.T, new Vector2(0, -180), new Vector2(1200, 70));
            zoneT = Ui.Txt(rt, "", 64, new Color(1f, 0.92f, 0.75f), TextAnchor.MiddleRight, Ui.BR, new Vector2(-60, 560), new Vector2(900, 80), Ui.display);
            big = Ui.Txt(rt, "", 190, Ui.Red, TextAnchor.MiddleCenter, Ui.C, new Vector2(0, 40), new Vector2(1600, 260), Ui.display);
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
                    case "house": icon = "house"; c = new Color(0.3f, 0.95f, 0.4f); break;
                    case "gunshop": icon = "pistol"; c = new Color(1f, 0.35f, 0.3f); break;
                    case "clothes": icon = "shirt"; c = new Color(0.85f, 0.5f, 1f); break;
                    case "hospital": icon = "cross"; c = new Color(1f, 0.3f, 0.3f); break;
                    case "police": icon = "badge"; c = new Color(0.4f, 0.6f, 1f); break;
                    case "boat": icon = "boat"; c = new Color(0.4f, 0.85f, 1f); break;
                    case "vehicle": if (p.model == "helicopter") { icon = "heli"; c = new Color(1f, 0.85f, 0.3f); } break;
                }
                if (icon == null) continue;
                var bg = Ui.Img(blipRoot, "mask_circle", new Color(0.05f, 0.05f, 0.05f, 0.85f), Ui.C, Vector2.zero, new Vector2(40, 40));
                Ui.Img(bg.transform, "i_" + icon, c, Ui.C, Vector2.zero, new Vector2(28, 28));
                blips.Add(new KeyValuePair<Image, Vector3>(bg, p.p));
            }
            for (int i = 0; i < 14; i++)
            {
                var b = Ui.Img(blipRoot, "mask_circle", new Color(0.3f, 0.5f, 1f), Ui.C, Vector2.zero, new Vector2(16, 16));
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

        public static void Toast(string s, Color c, float time = 2.5f)
        {
            if (I == null) return;
            I.toast.text = s;
            I.toast.color = c;
            I.toastUntil = Time.unscaledTime + time;
        }

        public static void Toast(string s) { Toast(s, Color.white); }

        public static void Big(string s, Color c, float time)
        {
            if (I == null) return;
            I.big.text = s;
            I.big.color = c;
            I.bigUntil = Time.unscaledTime + time;
        }

        public static void Flash() { if (I != null) I.flashA = 0.45f; }

        public static void Stars()
        {
            if (I == null) return;
            for (int i = 0; i < I.starImgs.Count; i++) I.starImgs[i].transform.localScale = Vector3.one * (i < Wanted.stars ? 1.25f : 1f);
        }

        public static void Radio(string s) { if (I != null) { I.radioT.text = s; I.toastUntil = Mathf.Max(I.toastUntil, 0f); I.radioUntil = Time.unscaledTime + 3f; } }
        float radioUntil;

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
                v.steer = Mathf.MoveTowards(v.steer, mv.x, dt * (v.spec.IsBike ? 4f : 6f));
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
                speed.text = kmh.ToString();
                speedUnit.text = isHeli ? "KM/H  ALT " + Mathf.RoundToInt(v.transform.position.y) + " M" : "KM/H";
            }
            else { speed.text = ""; speedUnit.text = ""; }
            if (Time.unscaledTime > radioUntil) radioT.text = "";

            // weapon, money, health
            var def = p.Def;
            if (wpnIcon.sprite != Ui.S("i_" + def.icon)) wpnIcon.sprite = Ui.S("i_" + def.icon);
            ammo.text = def.melee ? "" : p.clip[(int)def.id] + " / " + p.ammo[(int)def.id];
            fire.icon.sprite = Ui.S(def.melee ? "i_" + def.icon : "i_target");
            money.text = Rupees(p.money);
            healthBar.rectTransform.sizeDelta = new Vector2(276f * Mathf.Clamp01(p.health / p.maxHealth), 14f);
            healthBar.color = p.health < 30f ? Ui.Red : new Color(0.35f, 0.9f, 0.35f);
            armorBar.rectTransform.sizeDelta = new Vector2(276f * Mathf.Clamp01(p.armor / 100f), 10f);
            clock.text = Env.Clock();
            for (int i = 0; i < starImgs.Count; i++)
            {
                bool on = i < Wanted.stars;
                float blink = Wanted.Escape > 0.5f && on ? (Mathf.Sin(Time.unscaledTime * 10f) > 0 ? 1f : 0.3f) : 1f;
                starImgs[i].color = on ? new Color(1f, 0.85f, 0.2f, blink) : new Color(1, 1, 1, 0.22f);
                starImgs[i].transform.localScale = Vector3.Lerp(starImgs[i].transform.localScale, Vector3.one, dt * 4f);
            }
            Minimap(p);
            // messages
            if (Time.unscaledTime > toastUntil) toast.text = "";
            if (Time.unscaledTime > bigUntil) big.text = "";
            string zone = City.I != null ? City.I.ZoneAt(p.transform.position) : "";
            if (zone != lastZone) { lastZone = zone; zoneT.text = zone; zoneUntil = Time.unscaledTime + 4f; }
            zoneT.color = new Color(1f, 0.92f, 0.75f, Mathf.Clamp01(zoneUntil - Time.unscaledTime));
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
            float range = p.vehicle != null ? 300f : 180f;
            float w = range / (2f * H);
            map.uvRect = new Rect((pos.x + H) / (2f * H) - w * 0.5f, (pos.z + H) / (2f * H) - w * 0.5f, w, w);
            float camYaw = Cam.I != null ? Cam.I.transform.eulerAngles.y : 0f;
            mapRt.localEulerAngles = new Vector3(0, 0, camYaw);
            float heading = p.vehicle != null ? p.vehicle.transform.eulerAngles.y : p.transform.eulerAngles.y;
            arrow.localEulerAngles = new Vector3(0, 0, camYaw - heading);
            float k = 300f / range;
            float c = Mathf.Cos(camYaw * Mathf.Deg2Rad), s = Mathf.Sin(camYaw * Mathf.Deg2Rad);
            foreach (var b in blips)
            {
                Vector2 d = new Vector2(b.Value.x - pos.x, b.Value.z - pos.z) * k;
                Vector2 r = new Vector2(d.x * c - d.y * s, d.x * s + d.y * c);
                if (r.magnitude > 132f) r = r.normalized * 132f;
                b.Key.rectTransform.anchoredPosition = r;
            }
            int n = 0;
            if (Wanted.stars > 0)
                foreach (var h in Human.all)
                {
                    if (!h.police || h.dead || n >= copBlips.Count) continue;
                    Vector2 d = new Vector2(h.transform.position.x - pos.x, h.transform.position.z - pos.z) * k;
                    if (d.magnitude > 140f) continue;
                    var im = copBlips[n++];
                    im.gameObject.SetActive(true);
                    im.color = Mathf.Sin(Time.unscaledTime * 8f) > 0 ? new Color(0.3f, 0.5f, 1f) : new Color(1f, 0.25f, 0.25f);
                    im.rectTransform.anchoredPosition = new Vector2(d.x * c - d.y * s, d.x * s + d.y * c);
                }
            for (int i = n; i < copBlips.Count; i++) if (copBlips[i].gameObject.activeSelf) copBlips[i].gameObject.SetActive(false);
        }
    }
}

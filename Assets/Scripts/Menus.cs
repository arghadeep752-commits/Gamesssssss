using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

namespace Danga
{
    /// <summary>Main menu, pause, settings, credits, the gun shop, the clothes shop, the house, the phone and the big map.</summary>
    public class Menus : MonoBehaviour
    {
        public static Menus I;
        RectTransform layer;
        GameObject current;
        public string currentName = "";
        Text dialText;
        string dial = "";
        public bool IsOpen => current != null;

        public static Menus Create()
        {
            var r = Ui.Fill(Ui.root, "Menus");
            I = r.gameObject.AddComponent<Menus>();
            I.layer = r;
            return I;
        }

        public void Close()
        {
            if (current != null) Destroy(current);
            current = null;
            currentName = "";
            if (Game.I != null && Game.I.state == Game.S.Paused) Game.I.Resume();
        }

        RectTransform Window(string name, string title, Vector2 size, bool close = true, bool dim = true)
        {
            if (current != null) Destroy(current);
            currentName = name;
            var bg = Ui.Fill(layer, name);
            var bim = bg.gameObject.AddComponent<Image>();
            bim.color = dim ? new Color(0, 0, 0, 0.55f) : new Color(0, 0, 0, 0f);
            current = bg.gameObject;
            var panel = Ui.Panel(bg, new Color(0.1f, 0.1f, 0.13f, 0.96f), Ui.C, Vector2.zero, size);
            if (title != null)
            {
                var band = Ui.Img(panel.transform, "pill", Ui.Saffron, Ui.T, new Vector2(0, 34), new Vector2(Mathf.Min(size.x - 80, 760), 96));
                Ui.Txt(band.transform, title, 64, Color.white, TextAnchor.MiddleCenter, Ui.C, new Vector2(0, 2), new Vector2(740, 96), Ui.display);
            }
            if (close) Ui.Round(panel.transform, "exit", null, Ui.Red, Ui.TR, new Vector2(40, 40), 100, Close);
            return panel.rectTransform;
        }

        static RectTransform Scroll(Transform parent, Vector2 pos, Vector2 size)
        {
            var view = Ui.Box(parent, "scroll", Ui.T, pos, size);
            var vi = view.gameObject.AddComponent<Image>();
            vi.color = new Color(0, 0, 0, 0.01f);
            view.gameObject.AddComponent<RectMask2D>();
            var content = Ui.Box(view, "content", Ui.T, Vector2.zero, new Vector2(size.x, 0));
            var vl = content.gameObject.AddComponent<VerticalLayoutGroup>();
            vl.spacing = 12;
            vl.childControlHeight = false;
            vl.childControlWidth = false;
            vl.childForceExpandHeight = false;
            vl.childAlignment = TextAnchor.UpperCenter;
            content.gameObject.AddComponent<ContentSizeFitter>().verticalFit = ContentSizeFitter.FitMode.PreferredSize;
            var sr = view.gameObject.AddComponent<ScrollRect>();
            sr.content = content;
            sr.horizontal = false;
            sr.movementType = ScrollRect.MovementType.Clamped;
            sr.scrollSensitivity = 30;
            return content;
        }

        static RectTransform Row(Transform list, float w, float h)
        {
            var r = Ui.Img(list, "panel", new Color(1, 1, 1, 0.08f), Ui.T, Vector2.zero, new Vector2(w, h)).rectTransform;
            r.gameObject.AddComponent<LayoutElement>().preferredHeight = h;
            return r;
        }

        // ------------------------------------------------------------------ main menu
        public void MainMenu()
        {
            var bg = Ui.Fill(layer, "main");
            if (current != null) Destroy(current);
            current = bg.gameObject;
            currentName = "main";
            var im = bg.gameObject.AddComponent<Image>();
            im.color = new Color(0, 0, 0, 0.25f);
            var title = Ui.Img(bg, "title", Color.white, Ui.T, new Vector2(0, -60), new Vector2(980, 330));
            title.preserveAspect = true;
            Ui.Txt(bg, "AGARTALA  •  TRIPURA", 46, new Color(1f, 0.9f, 0.7f), TextAnchor.MiddleCenter, Ui.T, new Vector2(0, -390), new Vector2(1200, 60));
            bool hasSave = Save.Exists;
            float y = -40;
            if (hasSave)
            {
                Ui.Wide(bg, "CONTINUE", Ui.Green, Ui.C, new Vector2(0, y), new Vector2(560, 110), () => Game.I.Play(true));
                y -= 130;
                Ui.Wide(bg, "NEW GAME", Ui.Saffron, Ui.C, new Vector2(0, y), new Vector2(560, 100), () => Game.I.Play(false), 50);
            }
            else Ui.Wide(bg, "PLAY", Ui.Green, Ui.C, new Vector2(0, y), new Vector2(560, 120), () => Game.I.Play(false), 70);
            y -= 120;
            Ui.Wide(bg, "SETTINGS", new Color(0.3f, 0.3f, 0.36f), Ui.C, new Vector2(-150, y - 10), new Vector2(280, 90), () => Settings(MainMenu), 42);
            Ui.Wide(bg, "CREDITS", new Color(0.3f, 0.3f, 0.36f), Ui.C, new Vector2(150, y - 10), new Vector2(280, 90), Credits, 42);
            Ui.Txt(bg, "MXYAN GAMES OFFICIAL", 40, Color.white, TextAnchor.MiddleCenter, Ui.B, new Vector2(0, 40), new Vector2(1000, 60));
            Ui.Txt(bg, "v1." + Game.Build, 26, new Color(1, 1, 1, 0.6f), TextAnchor.MiddleRight, Ui.BR, new Vector2(-30, 30), new Vector2(300, 40));
        }

        public void Credits()
        {
            var w = Window("credits", "CREDITS", new Vector2(1500, 900));
            var list = Scroll(w, new Vector2(0, -110), new Vector2(1400, 760));
            var ta = Resources.Load<TextAsset>("credits");
            string txt = "DANGA\nMade by MXYAN GAMES\n\n" + (ta != null ? ta.text : "");
            // one text block per paragraph keeps each under the text mesh limit
            foreach (string para in txt.Split(new[] { "\n\n" }, StringSplitOptions.RemoveEmptyEntries))
            {
                var t = Ui.Txt(list, para.Trim(), 26, Color.white, TextAnchor.UpperLeft, Ui.T, Vector2.zero, new Vector2(1360, 40), Ui.body, false);
                var fit = t.gameObject.AddComponent<ContentSizeFitter>();
                fit.verticalFit = ContentSizeFitter.FitMode.PreferredSize;
            }
            Ui.Wide(w, "BACK", Ui.Saffron, Ui.B, new Vector2(0, -50), new Vector2(300, 90), () => { if (Game.I.state == Game.S.Menu) MainMenu(); else Pause(); });
        }

        // ------------------------------------------------------------------ pause and settings
        public void Pause()
        {
            if (Game.I.state != Game.S.Play && Game.I.state != Game.S.Paused) return;
            Game.I.PauseGame();
            var w = Window("pause", "PAUSED", new Vector2(760, 800));
            float y = -150;
            Ui.Wide(w, "RESUME", Ui.Green, Ui.T, new Vector2(0, y), new Vector2(520, 110), Close);
            y -= 140;
            Ui.Wide(w, "MAP", Ui.Blue, Ui.T, new Vector2(0, y), new Vector2(520, 100), BigMap);
            y -= 130;
            Ui.Wide(w, "SETTINGS", new Color(0.35f, 0.35f, 0.42f), Ui.T, new Vector2(0, y), new Vector2(520, 100), () => Settings(Pause));
            y -= 130;
            Ui.Wide(w, "CREDITS", new Color(0.35f, 0.35f, 0.42f), Ui.T, new Vector2(0, y), new Vector2(520, 100), Credits);
            y -= 130;
            Ui.Wide(w, "MAIN MENU", Ui.Red, Ui.T, new Vector2(0, y), new Vector2(520, 100), () => { Close(); Game.I.ToMenu(); });
        }

        public void Settings(Action back)
        {
            if (Game.I.state == Game.S.Play) Game.I.PauseGame();
            var w = Window("settings", "SETTINGS", new Vector2(1300, 900), false);
            var st = Game.I.settings;
            var list = Scroll(w, new Vector2(0, -120), new Vector2(1200, 640));
            Option(list, "GRAPHICS", new[] { "LOW", "MEDIUM", "HIGH" }, () => st.quality, v => { st.quality = v; Game.I.ApplySettings(); });
            Option(list, "DRAW DISTANCE", new[] { "NEAR", "NORMAL", "FAR" }, () => st.distance, v => { st.distance = v; Game.I.ApplySettings(); });
            Option(list, "TRAFFIC & PEOPLE", new[] { "FEW", "NORMAL", "MANY" }, () => st.density, v => { st.density = v; Game.I.ApplySettings(); });
            Option(list, "SOUND", Numbers(), () => st.sound, v => { st.sound = v; Game.I.ApplySettings(); });
            Option(list, "MUSIC & RADIO", Numbers(), () => st.music, v => { st.music = v; Game.I.ApplySettings(); });
            Option(list, "CAMERA SPEED", Numbers(), () => st.sens, v => { st.sens = v; Game.I.ApplySettings(); });
            Option(list, "SHOW FPS", new[] { "OFF", "ON" }, () => st.fps, v => { st.fps = v; Game.I.ApplySettings(); });
            Ui.Wide(w, "DONE", Ui.Green, Ui.B, new Vector2(0, -50), new Vector2(340, 100), () => { st.Save(); back(); });
        }

        static string[] Numbers()
        {
            var a = new string[11];
            for (int i = 0; i <= 10; i++) a[i] = i.ToString();
            return a;
        }

        static void Option(Transform list, string label, string[] values, Func<int> get, Action<int> set)
        {
            var r = Row(list, 1160, 110);
            Ui.Txt(r, label, 46, Color.white, TextAnchor.MiddleLeft, Ui.L, new Vector2(30, 0), new Vector2(560, 100));
            var val = Ui.Txt(r, values[Mathf.Clamp(get(), 0, values.Length - 1)], 50, Ui.Yellow, TextAnchor.MiddleCenter, Ui.R, new Vector2(-150, 0), new Vector2(260, 100));
            Action refresh = () => val.text = values[Mathf.Clamp(get(), 0, values.Length - 1)];
            Ui.Round(r, "left", null, Ui.Saffron, Ui.R, new Vector2(-420, 0), 86, () => { set(Mathf.Max(0, get() - 1)); refresh(); });
            Ui.Round(r, "right", null, Ui.Saffron, Ui.R, new Vector2(-30, 0), 86, () => { set(Mathf.Min(values.Length - 1, get() + 1)); refresh(); });
        }

        // ------------------------------------------------------------------ shops and the house
        public void GunShop()
        {
            Game.I.PauseGame();
            var w = Window("gunshop", "DANGA ARMS", new Vector2(1500, 920));
            Fill(w);
        }

        void Fill(RectTransform w)
        {
            Player p = Player.I;
            var old = w.Find("scroll");
            if (old != null) Destroy(old.gameObject);
            var cash = w.Find("cash");
            if (cash != null) Destroy(cash.gameObject);
            var ct = Ui.Txt(w, "₹ " + Hud.Rupees(p.money), 50, new Color(0.6f, 1f, 0.55f), TextAnchor.MiddleLeft, Ui.TL, new Vector2(50, -40), new Vector2(500, 70), Ui.body);
            ct.name = "cash";
            var list = Scroll(w, new Vector2(0, -120), new Vector2(1400, 760));
            foreach (var d in Combat.Defs)
            {
                if (d.id == Wpn.Fist) continue;
                var def = d;
                var r = Row(list, 1360, 130);
                Ui.Img(r, "i_" + d.icon, Color.white, Ui.L, new Vector2(30, 0), new Vector2(100, 100));
                Ui.Txt(r, d.name.ToUpper(), 50, Color.white, TextAnchor.MiddleLeft, Ui.L, new Vector2(160, 18), new Vector2(520, 60));
                string info = d.melee ? "MELEE  •  DAMAGE " + d.damage : "DAMAGE " + d.damage * d.pellets + "  •  MAG " + d.mag + "  •  AMMO " + p.TotalAmmo(d.id);
                Ui.Txt(r, info, 30, new Color(1, 1, 1, 0.7f), TextAnchor.MiddleLeft, Ui.L, new Vector2(160, -30), new Vector2(700, 40));
                bool own = p.owned.Contains(d.id);
                if (!own)
                    Ui.Wide(r, "BUY ₹" + Hud.Rupees(d.price), p.money >= d.price ? Ui.Green : new Color(0.4f, 0.4f, 0.4f), Ui.R, new Vector2(-30, 0), new Vector2(380, 90), () =>
                    {
                        if (p.money < def.price) { Hud.Toast("Not enough money", Ui.Red); return; }
                        p.money -= def.price;
                        p.owned.Add(def.id);
                        if (!def.melee) { p.clip[(int)def.id] = def.mag; p.ammo[(int)def.id] = def.ammoPack; }
                        p.Equip(def.id);
                        GameAudio.Ui("cash", 0.8f);
                        Fill(w);
                    }, 40);
                else if (!d.melee)
                    Ui.Wide(r, "+" + d.ammoPack + " AMMO ₹" + Hud.Rupees(d.ammoPrice), p.money >= d.ammoPrice ? Ui.Blue : new Color(0.4f, 0.4f, 0.4f), Ui.R, new Vector2(-30, 0), new Vector2(440, 90), () =>
                    {
                        if (p.money < def.ammoPrice) { Hud.Toast("Not enough money", Ui.Red); return; }
                        p.money -= def.ammoPrice;
                        p.ammo[(int)def.id] += def.ammoPack;
                        GameAudio.Ui("reload", 0.8f);
                        Fill(w);
                    }, 36);
                else Ui.Txt(r, "OWNED", 46, Ui.Green, TextAnchor.MiddleRight, Ui.R, new Vector2(-40, 0), new Vector2(300, 90));
            }
            var ar = Row(list, 1360, 130);
            Ui.Img(ar, "i_shield", new Color(0.5f, 0.75f, 1f), Ui.L, new Vector2(30, 0), new Vector2(100, 100));
            Ui.Txt(ar, "BODY ARMOUR", 50, Color.white, TextAnchor.MiddleLeft, Ui.L, new Vector2(160, 0), new Vector2(520, 60));
            Ui.Wide(ar, "BUY ₹2,500", p.money >= 2500 ? Ui.Green : new Color(0.4f, 0.4f, 0.4f), Ui.R, new Vector2(-30, 0), new Vector2(380, 90), () =>
            {
                if (p.money < 2500) { Hud.Toast("Not enough money", Ui.Red); return; }
                p.money -= 2500;
                p.armor = 100f;
                GameAudio.Ui("cash", 0.8f);
                Fill(w);
            }, 40);
        }

        public static readonly string[] Outfits = { "player_casual", "player_kurta", "player_jacket" };
        public static readonly string[] OutfitNames = { "CASUAL", "KURTA", "JACKET" };
        public static readonly int[] OutfitPrice = { 0, 3000, 6000 };
        public static readonly Color[] Tints = { Color.white, new Color(1f, 0.78f, 0.75f), new Color(0.75f, 0.85f, 1f), new Color(0.78f, 1f, 0.8f), new Color(1f, 0.95f, 0.7f), new Color(0.62f, 0.62f, 0.66f) };

        public void Clothes(bool wardrobe)
        {
            Game.I.PauseGame();
            var w = Window("clothes", wardrobe ? "WARDROBE" : "FASHION POINT", new Vector2(1500, 900));
            Player p = Player.I;
            var st = Game.I.save;
            float x = -460;
            for (int i = 0; i < Outfits.Length; i++)
            {
                int k = i;
                bool own = st.outfits.Contains(Outfits[i]) || OutfitPrice[i] == 0;
                if (wardrobe && !own) continue;
                var card = Ui.Img(w, "panel", p.Outfit == Outfits[i] ? new Color(1f, 0.6f, 0.1f, 0.35f) : new Color(1, 1, 1, 0.08f), Ui.C, new Vector2(x, 60), new Vector2(400, 460));
                Ui.Img(card.transform, "i_shirt", Color.white, Ui.T, new Vector2(0, -40), new Vector2(200, 200));
                Ui.Txt(card.transform, OutfitNames[i], 58, Color.white, TextAnchor.MiddleCenter, Ui.C, new Vector2(0, -60), new Vector2(380, 80));
                string label = p.Outfit == Outfits[i] ? "WEARING" : own ? "WEAR" : "BUY ₹" + Hud.Rupees(OutfitPrice[i]);
                Ui.Wide(card.transform, label, own ? Ui.Green : Ui.Saffron, Ui.B, new Vector2(0, 30), new Vector2(330, 90), () =>
                {
                    if (!own)
                    {
                        if (p.money < OutfitPrice[k]) { Hud.Toast("Not enough money", Ui.Red); return; }
                        p.money -= OutfitPrice[k];
                        st.outfits.Add(Outfits[k]);
                        GameAudio.Ui("cash", 0.8f);
                    }
                    p.SetOutfit(Outfits[k], p.tint);
                    Clothes(wardrobe);
                }, 40);
                x += 460;
            }
            Ui.Txt(w, "COLOUR", 44, Color.white, TextAnchor.MiddleLeft, Ui.B, new Vector2(-560, 120), new Vector2(300, 60));
            for (int i = 0; i < Tints.Length; i++)
            {
                Color c = Tints[i];
                Ui.Round(w, null, null, c, Ui.B, new Vector2(-330 + i * 130, 120), 100, () => { p.SetOutfit(p.Outfit, c); });
            }
        }

        public void House()
        {
            Game.I.PauseGame();
            var w = Window("house", "YOUR HOUSE", new Vector2(900, 760));
            Ui.Wide(w, "SAVE GAME", Ui.Green, Ui.T, new Vector2(0, -160), new Vector2(560, 110), () => { Game.I.SaveGame(); Hud.Toast("Game saved", Ui.Green); Close(); });
            Ui.Wide(w, "SLEEP 6 HOURS", Ui.Blue, Ui.T, new Vector2(0, -300), new Vector2(560, 110), () =>
            {
                Env.hour = Mathf.Repeat(Env.hour + 6f, 24f);
                Player.I.health = Player.I.maxHealth;
                Wanted.Set(0);
                Game.I.SaveGame();
                Hud.Toast("You slept. It is " + Env.Clock() + " now.", Color.white, 3f);
                Close();
            });
            Ui.Wide(w, "WARDROBE", Ui.Saffron, Ui.T, new Vector2(0, -440), new Vector2(560, 110), () => Clothes(true));
            Ui.Txt(w, "Your motorbike is parked outside.", 30, new Color(1, 1, 1, 0.75f), TextAnchor.MiddleCenter, Ui.B, new Vector2(0, 60), new Vector2(800, 50), Ui.body, false);
        }

        // ------------------------------------------------------------------ the phone
        public void Phone()
        {
            if (Game.I.state != Game.S.Play) return;
            Game.I.PauseGame();
            GameAudio.Ui("phone_ring", 0.25f);
            PhoneHome();
        }

        RectTransform PhoneFrame(string app)
        {
            if (current != null) Destroy(current);
            currentName = "phone";
            var bg = Ui.Fill(layer, "phone");
            var bim = bg.gameObject.AddComponent<Image>();
            bim.color = new Color(0, 0, 0, 0.4f);
            current = bg.gameObject;
            var body = Ui.Panel(bg, new Color(0.05f, 0.05f, 0.06f, 1f), Ui.R, new Vector2(-160, -20), new Vector2(560, 980));
            var screen = Ui.Img(body.transform, "panel", new Color(0.12f, 0.16f, 0.24f, 1f), Ui.C, new Vector2(0, 20), new Vector2(500, 840));
            screen.raycastTarget = true;
            Ui.Txt(screen.transform, Env.Clock(), 34, Color.white, TextAnchor.MiddleLeft, Ui.TL, new Vector2(24, -10), new Vector2(200, 44), Ui.body, false);
            Ui.Txt(screen.transform, app, 34, Color.white, TextAnchor.MiddleRight, Ui.TR, new Vector2(-24, -10), new Vector2(300, 44), Ui.body, false);
            Ui.Round(body.transform, null, null, new Color(0.25f, 0.25f, 0.28f), Ui.B, new Vector2(0, 14), 76, () => { if (app == "DANGA") Close(); else PhoneHome(); });
            return screen.rectTransform;
        }

        void PhoneHome()
        {
            var s = PhoneFrame("DANGA");
            string[] apps = { "dial", "map", "wallet", "radio", "notes", "settings" };
            string[] names = { "CHEATS", "MAP", "WALLET", "RADIO", "NOTES", "SETTINGS" };
            Color[] cols = { Ui.Green, Ui.Blue, new Color(0.2f, 0.6f, 0.3f), Ui.Saffron, Ui.Yellow, new Color(0.45f, 0.45f, 0.5f) };
            for (int i = 0; i < apps.Length; i++)
            {
                int k = i;
                var b = Ui.Round(s, apps[i], null, cols[i], Ui.T, new Vector2(-150 + (i % 3) * 150, -110 - (i / 3) * 210), 120, () => App(apps[k]));
                Ui.Txt(b.transform, names[i], 26, Color.white, TextAnchor.MiddleCenter, Ui.B, new Vector2(0, -44), new Vector2(160, 40));
            }
            Ui.Txt(s, "MXYAN GAMES OFFICIAL", 22, new Color(1, 1, 1, 0.5f), TextAnchor.MiddleCenter, Ui.B, new Vector2(0, 30), new Vector2(460, 40), Ui.body, false);
        }

        void App(string app)
        {
            switch (app)
            {
                case "dial": Dialer(); break;
                case "map": BigMap(); break;
                case "wallet": Wallet(); break;
                case "radio": RadioApp(); break;
                case "notes": Notes(); break;
                case "settings": Settings(Phone2); break;
            }
        }

        void Phone2() { PhoneHome(); }

        void Dialer()
        {
            var s = PhoneFrame("CHEATS");
            dial = "";
            var disp = Ui.Img(s, "pill", new Color(0, 0, 0, 0.5f), Ui.T, new Vector2(0, -70), new Vector2(440, 100));
            dialText = Ui.Txt(disp.transform, "", 60, Color.white, TextAnchor.MiddleCenter, Ui.C, Vector2.zero, new Vector2(420, 90), Ui.body, false);
            string[] keys = { "1", "2", "3", "4", "5", "6", "7", "8", "9", "*", "0", "#" };
            for (int i = 0; i < keys.Length; i++)
            {
                string k = keys[i];
                Ui.Round(s, null, k, new Color(0.25f, 0.28f, 0.36f), Ui.T, new Vector2(-140 + (i % 3) * 140, -200 - (i / 3) * 130), 112, () =>
                {
                    if (dial.Length < 8) dial += k;
                    dialText.text = dial;
                    dialText.color = Color.white;
                });
            }
            Ui.Round(s, "phone", null, Ui.Green, Ui.B, new Vector2(-70, 40), 120, () =>
            {
                string msg = Game.I.Cheat(dial);
                dialText.text = msg ?? "WRONG NUMBER";
                dialText.color = msg != null ? Ui.Green : Ui.Red;
                dialText.fontSize = msg != null ? 34 : 44;
                dial = "";
            });
            Ui.Round(s, "left", null, Ui.Red, Ui.B, new Vector2(80, 40), 100, () => { if (dial.Length > 0) dial = dial.Substring(0, dial.Length - 1); dialText.text = dial; dialText.fontSize = 60; });
        }

        void Wallet()
        {
            var s = PhoneFrame("WALLET");
            Player p = Player.I;
            Ui.Img(s, "i_rupee", new Color(0.6f, 1f, 0.55f), Ui.T, new Vector2(0, -80), new Vector2(110, 110));
            Ui.Txt(s, Hud.Rupees(p.money), 70, new Color(0.6f, 1f, 0.55f), TextAnchor.MiddleCenter, Ui.T, new Vector2(0, -200), new Vector2(480, 90), Ui.display);
            float y = -300;
            foreach (var d in Combat.Defs)
            {
                if (!p.owned.Contains(d.id) || d.id == Wpn.Fist) continue;
                Ui.Img(s, "i_" + d.icon, Color.white, Ui.TL, new Vector2(40, y), new Vector2(64, 64));
                Ui.Txt(s, d.name.ToUpper() + (d.melee ? "" : "   " + p.TotalAmmo(d.id)), 34, Color.white, TextAnchor.MiddleLeft, Ui.TL, new Vector2(120, y - 6), new Vector2(360, 56));
                y -= 76;
            }
        }

        void RadioApp()
        {
            var s = PhoneFrame("RADIO");
            for (int i = 0; i < GameAudio.Stations.Length; i++)
            {
                int k = i;
                bool on = GameAudio.station == i;
                Ui.Wide(s, GameAudio.StationNames[i].ToUpper(), on ? Ui.Saffron : new Color(0.25f, 0.28f, 0.36f), Ui.T, new Vector2(0, -90 - i * 120), new Vector2(450, 100), () =>
                {
                    GameAudio.station = k;
                    Game.I.save.station = k;
                    GameAudio.Radio(Player.I.vehicle != null);
                    RadioApp();
                }, 26);
            }
            Ui.Wide(s, "RADIO OFF", GameAudio.station < 0 ? Ui.Red : new Color(0.25f, 0.28f, 0.36f), Ui.T, new Vector2(0, -90 - GameAudio.Stations.Length * 120), new Vector2(450, 100), () =>
            {
                GameAudio.station = -1;
                Game.I.save.station = -1;
                GameAudio.Radio(false);
                RadioApp();
            }, 30);
            Ui.Txt(s, "The radio plays while you drive.", 26, new Color(1, 1, 1, 0.6f), TextAnchor.MiddleCenter, Ui.B, new Vector2(0, 40), new Vector2(460, 40), Ui.body, false);
        }

        void Notes()
        {
            var s = PhoneFrame("NOTES");
            var list = Scroll(s, new Vector2(0, -60), new Vector2(470, 760));
            var t = Ui.Txt(list, Game.CheatList, 28, Color.white, TextAnchor.UpperLeft, Ui.T, Vector2.zero, new Vector2(440, 40), Ui.body, false);
            t.gameObject.AddComponent<ContentSizeFitter>().verticalFit = ContentSizeFitter.FitMode.PreferredSize;
        }

        // ------------------------------------------------------------------ the big map
        public void BigMap()
        {
            if (Game.I.state == Game.S.Play) Game.I.PauseGame();
            var w = Window("map", null, new Vector2(1900, 1060));
            var tex = Resources.Load<Texture2D>("Gen/City/map");
            var m = Ui.Box(w, "map", Ui.L, new Vector2(30, 0), new Vector2(1000, 1000));
            var ri = m.gameObject.AddComponent<RawImage>();
            ri.texture = tex;
            float H = City.Half, k = 1000f / (2f * H);
            foreach (var p in City.I.points)
            {
                string icon = null;
                Color c = Color.white;
                switch (p.kind)
                {
                    case "house": icon = "house"; c = Ui.Green; break;
                    case "gunshop": icon = "pistol"; c = Ui.Red; break;
                    case "clothes": icon = "shirt"; c = new Color(0.85f, 0.5f, 1f); break;
                    case "hospital": icon = "cross"; c = Ui.Red; break;
                    case "police": icon = "badge"; c = Ui.Blue; break;
                    case "boat": icon = "boat"; c = new Color(0.4f, 0.85f, 1f); break;
                    case "vehicle": if (p.model == "helicopter") { icon = "heli"; c = Ui.Yellow; } break;
                }
                Vector2 pos = new Vector2((p.p.x + H) * k - 500f, (p.p.z + H) * k - 500f);
                if (icon != null)
                {
                    var bg = Ui.Img(m, "mask_circle", new Color(0, 0, 0, 0.8f), Ui.C, pos, new Vector2(44, 44));
                    Ui.Img(bg.transform, "i_" + icon, c, Ui.C, Vector2.zero, new Vector2(30, 30));
                }
                else if (p.kind == "landmark")
                    Ui.Txt(m, p.label, 20, Color.white, TextAnchor.MiddleCenter, Ui.C, pos, new Vector2(260, 30), Ui.body, true);
            }
            Player pl = Player.I;
            Vector3 pp = pl.vehicle != null ? pl.vehicle.transform.position : pl.transform.position;
            var ar = Ui.Img(m, "arrow", Ui.Yellow, Ui.C, new Vector2((pp.x + H) * k - 500f, (pp.z + H) * k - 500f), new Vector2(46, 46));
            ar.rectTransform.localEulerAngles = new Vector3(0, 0, -(pl.vehicle != null ? pl.vehicle.transform.eulerAngles.y : pl.transform.eulerAngles.y));
            Ui.Txt(w, "AGARTALA", 90, Color.white, TextAnchor.MiddleLeft, Ui.TL, new Vector2(1080, -60), new Vector2(760, 120), Ui.display);
            Ui.Txt(w, "You are in " + City.I.ZoneAt(pp), 40, Ui.Yellow, TextAnchor.MiddleLeft, Ui.TL, new Vector2(1080, -170), new Vector2(760, 60), Ui.body);
            string[] leg = { "house|Your house", "pistol|Danga Arms - guns", "shirt|Fashion Point - clothes", "cross|Hospital", "badge|Police station", "boat|Boat jetty", "heli|Helicopter" };
            for (int i = 0; i < leg.Length; i++)
            {
                var parts = leg[i].Split('|');
                Ui.Img(w, "i_" + parts[0], Color.white, Ui.TL, new Vector2(1090, -260 - i * 76), new Vector2(56, 56));
                Ui.Txt(w, parts[1], 36, Color.white, TextAnchor.MiddleLeft, Ui.TL, new Vector2(1170, -262 - i * 76), new Vector2(640, 60), Ui.body);
            }
        }
    }
}

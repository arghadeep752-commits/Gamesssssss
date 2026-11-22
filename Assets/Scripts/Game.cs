using System.Collections;
using System.Collections.Generic;
using System.Text;
using UnityEngine;
using UnityEngine.UI;

namespace Danga
{
    public class Settings
    {
        public int quality = 1, distance = 1, density = 1, sound = 8, music = 6, sens = 5, fps;

        public void Load()
        {
            string gpu = SystemInfo.graphicsDeviceName ?? "";
            bool weak = SystemInfo.systemMemorySize < 4500 || gpu.Contains("Mali-G5") || gpu.Contains("Mali-G3") || gpu.Contains("Mali-T") || gpu.Contains("Adreno (TM) 5")
                        || gpu.Contains("PowerVR");
            quality = PlayerPrefs.GetInt("dg_quality", weak ? 0 : 1);
            distance = PlayerPrefs.GetInt("dg_distance", weak ? 0 : 1);
            density = PlayerPrefs.GetInt("dg_density", 1);
            sound = PlayerPrefs.GetInt("dg_sound", 8);
            music = PlayerPrefs.GetInt("dg_music", 6);
            sens = PlayerPrefs.GetInt("dg_sens", 5);
            fps = PlayerPrefs.GetInt("dg_fps", 0);
        }

        public void Save()
        {
            PlayerPrefs.SetInt("dg_quality", quality);
            PlayerPrefs.SetInt("dg_distance", distance);
            PlayerPrefs.SetInt("dg_density", density);
            PlayerPrefs.SetInt("dg_sound", sound);
            PlayerPrefs.SetInt("dg_music", music);
            PlayerPrefs.SetInt("dg_sens", sens);
            PlayerPrefs.SetInt("dg_fps", fps);
            PlayerPrefs.Save();
        }
    }

    /// <summary>The saved game (PlayerPrefs): money, weapons, clothes, time of day, radio.</summary>
    public class Save
    {
        public int money = 25000, station;
        public string outfit = "player_casual";
        public Color tint = Color.white;
        public List<string> outfits = new List<string> { "player_casual" };
        public int[] ammo = new int[7], clip = new int[7];
        public List<int> owned = new List<int> { 0, 1, 2, 3 };
        public float hour = 9.5f, armor;
        const string Key = "danga_save_v1";

        public static bool Exists => PlayerPrefs.HasKey(Key);

        public void Write()
        {
            var sb = new StringBuilder();
            sb.Append("{\"money\":").Append(money).Append(",\"station\":").Append(station).Append(",\"hour\":").Append(hour.ToString(System.Globalization.CultureInfo.InvariantCulture));
            sb.Append(",\"armor\":").Append(Mathf.RoundToInt(armor));
            sb.Append(",\"outfit\":\"").Append(outfit).Append("\",\"tint\":[").Append(F(tint.r)).Append(',').Append(F(tint.g)).Append(',').Append(F(tint.b)).Append(']');
            sb.Append(",\"outfits\":[");
            for (int i = 0; i < outfits.Count; i++) sb.Append(i > 0 ? "," : "").Append('"').Append(outfits[i]).Append('"');
            sb.Append("],\"owned\":[").Append(string.Join(",", owned.ConvertAll(x => x.ToString()).ToArray())).Append(']');
            sb.Append(",\"ammo\":[").Append(string.Join(",", System.Array.ConvertAll(ammo, x => x.ToString()))).Append(']');
            sb.Append(",\"clip\":[").Append(string.Join(",", System.Array.ConvertAll(clip, x => x.ToString()))).Append("]}");
            PlayerPrefs.SetString(Key, sb.ToString());
            PlayerPrefs.Save();
        }

        static string F(float v) { return v.ToString("0.###", System.Globalization.CultureInfo.InvariantCulture); }

        public static Save Read()
        {
            var s = new Save();
            if (!Exists) return s;
            try
            {
                object o = Json.Parse(PlayerPrefs.GetString(Key));
                s.money = Json.I(o, "money", 25000);
                s.station = Json.I(o, "station", 0);
                s.hour = Json.F(o, "hour", 9.5f);
                s.armor = Json.F(o, "armor", 0f);
                s.outfit = Json.S(o, "outfit", "player_casual");
                var t = Json.A(o, "tint");
                if (t != null && t.Count >= 3) s.tint = new Color(Json.F(t[0]), Json.F(t[1]), Json.F(t[2]));
                var of = Json.A(o, "outfits");
                if (of != null) { s.outfits.Clear(); foreach (object x in of) s.outfits.Add(x as string); }
                var ow = Json.A(o, "owned");
                if (ow != null) { s.owned.Clear(); foreach (object x in ow) s.owned.Add((int)Json.F(x)); }
                var am = Json.A(o, "ammo");
                if (am != null) for (int i = 0; i < Mathf.Min(7, am.Count); i++) s.ammo[i] = (int)Json.F(am[i]);
                var cl = Json.A(o, "clip");
                if (cl != null) for (int i = 0; i < Mathf.Min(7, cl.Count); i++) s.clip[i] = (int)Json.F(cl[i]);
            }
            catch (System.Exception e) { Debug.LogWarning("[DG] save unreadable: " + e.Message); }
            return s;
        }
    }

    /// <summary>Starts everything, runs the game's states, cheats and saving.</summary>
    public class Game : MonoBehaviour
    {
        public static Game I;
        public enum S { Loading, Menu, Play, Paused, Dead }
        public S state = S.Loading;
        public static string Build = "0";
        public Settings settings = new Settings();
        public Save save = new Save();
        public bool godMode;
        Hud hud;
        Text loadText;
        GameObject loading;
        Vector3 orbitCentre;
        readonly Dictionary<City.MapPoint, Vehicle> pointVehicles = new Dictionary<City.MapPoint, Vehicle>();
        readonly List<GameObject> markers = new List<GameObject>();
        float nextPointCheck;

        public Vector3 Focus
        {
            get
            {
                if (state == S.Menu || Player.I == null) return orbitCentre;
                return Player.I.vehicle != null ? Player.I.vehicle.transform.position : Player.I.transform.position;
            }
        }

        public const string CheatList =
            "CHEAT CODES\nDial them in the Cheats app.\n\n" +
            "1999  Full health and armour\n4545  Get ₹1,00,000\n1122  All weapons and ammo\n0000  Clear wanted level\n7777  Five stars\n" +
            "4321  Never wanted (on / off)\n1100  God mode (on / off)\n1001  Super run (on / off)\n1234  Moon gravity (on / off)\n" +
            "8080  Sports car\n2323  Motorbike\n6060  Auto rickshaw\n1515  Bus\n3030  Police jeep\n9090  Helicopter\n5050  Speedboat\n" +
            "6000  Skip 6 hours\n2222  Blow up nearby vehicles\n3131  Go home\n";

        void Awake()
        {
            I = this;
            Application.targetFrameRate = 30;
            Screen.sleepTimeout = SleepTimeout.NeverSleep;
            QualitySettings.vSyncCount = 0;
            Input.multiTouchEnabled = true;
            var ver = Application.version.Split('.');
            Build = ver.Length > 0 ? ver[ver.Length - 1] : "0";
        }

        IEnumerator Start()
        {
            settings.Load();
            Ui.Init();
            ShowLoading();
            yield return null;
            Step("Loading Agartala...");
            yield return null;
            Models.Init();
            var cityGo = new GameObject("City");
            var city = cityGo.AddComponent<City>();
            city.Init();
            Env.Init();
            Fx.Init(transform);
            GameAudio.Init(transform);
            var cam = Cam.Create();
            var palace = city.points.Find(p => p.name.Contains("Ujjayanta"));
            orbitCentre = palace != null ? palace.p : Vector3.zero;
            Step("Building the streets...");
            yield return null;
            city.StreamNow(orbitCentre);
            var spawn = city.Point("spawn");
            Vector3 sp = spawn != null ? spawn.p : Vector3.zero;
            city.StreamNow(sp);
            Step("People of Agartala are waking up...");
            yield return null;
            var tr = new GameObject("Traffic").AddComponent<Traffic>();
            tr.Init();
            save = Save.Read();
            var pl = Player.Create(sp + Vector3.up * 0.1f, spawn != null ? spawn.yaw : 0f);
            pl.gameObject.SetActive(false);
            SpawnPointVehicles();
            MakeMarkers();
            hud = Hud.Create();
            Menus.Create();
            ApplySettings();
            Env.hour = save.hour;
            Destroy(loading);
            ToMenu();
#if DG_AUTOTEST
            gameObject.AddComponent<AutoTest>();
#endif
        }

        void ShowLoading()
        {
            var r = Ui.Fill(Ui.root, "loading");
            loading = r.gameObject;
            r.SetAsLastSibling();
            var bg = r.gameObject.AddComponent<Image>();
            bg.color = new Color(0.04f, 0.03f, 0.03f, 1f);
            var t = Ui.Img(r, "title", Color.white, Ui.C, new Vector2(0, 120), new Vector2(900, 300));
            t.preserveAspect = true;
            loadText = Ui.Txt(r, "", 44, Color.white, TextAnchor.MiddleCenter, Ui.C, new Vector2(0, -120), new Vector2(1400, 60));
            Ui.Txt(r, "MXYAN GAMES OFFICIAL", 34, new Color(1, 1, 1, 0.7f), TextAnchor.MiddleCenter, Ui.B, new Vector2(0, 40), new Vector2(1000, 50));
        }

        void Step(string s)
        {
            if (loadText != null) loadText.text = s.ToUpper();
            Debug.Log("[DG] " + s);
        }

        // ------------------------------------------------------------------ states
        public void ToMenu()
        {
            state = S.Menu;
            Time.timeScale = 1f;
            if (Player.I != null)
            {
                if (Player.I.vehicle != null) Player.I.ExitVehicle(true);
                Player.I.gameObject.SetActive(false);
            }
            Cam.I.menuOrbit = true;
            Cam.I.orbitCentre = orbitCentre;
            hud.gameObject.SetActive(false);
            GameAudio.Radio(false);
            GameAudio.Menu(true);
            Menus.I.MainMenu();
        }

        public void Play(bool cont)
        {
            if (!cont) { save = new Save(); PlayerPrefs.DeleteKey("danga_save_v1"); }
            else save = Save.Read();
            Player p = Player.I;
            p.gameObject.SetActive(true);
            p.money = save.money;
            p.owned.Clear();
            foreach (int w in save.owned) p.owned.Add((Wpn)w);
            if (!cont) { p.clip[(int)Wpn.Revolver] = 6; p.ammo[(int)Wpn.Revolver] = 36; }
            else { System.Array.Copy(save.ammo, p.ammo, 7); System.Array.Copy(save.clip, p.clip, 7); }
            p.armor = save.armor;
            p.tint = save.tint;
            p.SetOutfit(save.outfit, save.tint);
            p.Revive();
            p.Equip(Wpn.Fist);
            Env.hour = cont ? save.hour : 9.5f;
            GameAudio.station = save.station;
            Wanted.Set(0);
            Wanted.never = false;
            godMode = false;
            p.speedMul = 1f;
            p.gravity = -20f;
            var spawn = City.I.Point("spawn");
            Vector3 sp = SpawnPoint();
            City.I.StreamNow(sp);
            p.Teleport(sp, spawn != null ? spawn.yaw : 0f);
            Menus.I.Close();
            GameAudio.Menu(false);
            Cam.I.menuOrbit = false;
            Cam.I.yaw = p.transform.eulerAngles.y;
            Cam.I.pitch = 12f;
            hud.gameObject.SetActive(true);
            state = S.Play;
            Hud.Toast(cont ? "Welcome back to Agartala" : "Welcome to Agartala", Color.white, 3f);
        }

        public Vector3 SpawnPoint()
        {
            var spawn = City.I != null ? City.I.Point("spawn") : null;
            return spawn != null ? spawn.p + Vector3.up * 0.1f : Vector3.up;
        }

        public void PauseGame()
        {
            if (state == S.Play) { state = S.Paused; Time.timeScale = 0f; }
        }

        public void Resume()
        {
            if (state == S.Paused) { state = S.Play; Time.timeScale = 1f; }
        }

        public void SaveGame()
        {
            Player p = Player.I;
            save.money = p.money;
            save.owned.Clear();
            foreach (var w in p.owned) save.owned.Add((int)w);
            System.Array.Copy(p.ammo, save.ammo, 7);
            System.Array.Copy(p.clip, save.clip, 7);
            save.outfit = p.Outfit;
            save.tint = p.tint;
            save.hour = Env.hour;
            save.armor = p.armor;
            save.station = GameAudio.station;
            save.Write();
        }

        public void Wasted()
        {
            if (state != S.Play) return;
            state = S.Dead;
            Hud.Big("WASTED", Ui.Red, 3.5f);
            StartCoroutine(Respawn("hospital", 0.1f, "Hospital bill"));
        }

        public void Busted()
        {
            if (state != S.Play) return;
            state = S.Dead;
            if (Player.I.vehicle != null) Player.I.ExitVehicle(true);
            if (Player.I.rig != null) Player.I.rig.Play("cower", 0.1f);
            Hud.Big("BUSTED", Ui.Blue, 3.5f);
            StartCoroutine(Respawn("police", 0.1f, "Fine"));
        }

        IEnumerator Respawn(string where, float fee, string what)
        {
            yield return new WaitForSeconds(3.5f);
            var pt = City.I.Point(where);
            Vector3 pos = pt != null ? pt.p + Quaternion.Euler(0, pt.yaw, 0) * new Vector3(0, 0, 4f) : SpawnPoint();
            City.I.StreamNow(pos);
            Player p = Player.I;
            p.Revive();
            p.Teleport(pos + Vector3.up * 0.2f, pt != null ? pt.yaw : 0f);
            int cost = Mathf.Min(5000, Mathf.RoundToInt(p.money * fee));
            p.money -= cost;
            Wanted.Set(0);
            state = S.Play;
            Hud.Toast(what + ": ₹" + Hud.Rupees(cost), Color.white, 3f);
        }

        public void OnEnterVehicle(Vehicle v)
        {
            GameAudio.Radio(GameAudio.station >= 0);
            if (GameAudio.station >= 0) Hud.Radio(GameAudio.StationNames[GameAudio.station % GameAudio.StationNames.Length]);
        }

        public void OnExitVehicle(Vehicle v) { GameAudio.Radio(false); }

        public void ApplySettings()
        {
            var s = settings;
            float scale = s.quality == 0 ? 0.62f : s.quality == 1 ? 0.78f : 0.92f;
            int nh = Display.main.systemHeight, nw = Display.main.systemWidth;
            if (nh > nw) { int t = nh; nh = nw; nw = t; }
            int h = Mathf.Min(1080, Mathf.RoundToInt(nh * scale)), w = Mathf.RoundToInt(h * (float)nw / Mathf.Max(1, nh));
#if !UNITY_EDITOR
            if (h > 200 && (Screen.height != h)) Screen.SetResolution(w, h, true);
#endif
            QualitySettings.antiAliasing = s.quality == 0 ? 0 : s.quality == 1 ? 2 : 4;
            Application.targetFrameRate = s.quality == 2 ? 45 : 30;
            if (City.I != null)
            {
                City.I.renderDist = s.distance == 0 ? 300f : s.distance == 1 ? 420f : 580f;
                City.I.SetNormalMaps(s.quality == 2);
            }
            Env.fogEnd = s.distance == 0 ? 560f : s.distance == 1 ? 800f : 1050f;
            Env.fogStart = s.distance == 0 ? 90f : 150f;
            if (Cam.I != null) { Cam.I.cam.farClipPlane = s.distance == 0 ? 900f : 1500f; Cam.I.sensitivity = 0.45f + s.sens * 0.12f; }
            if (Traffic.I != null)
            {
                Traffic.I.maxCars = s.density == 0 ? 7 : s.density == 1 ? 12 : 18;
                Traffic.I.maxPeds = s.density == 0 ? 9 : s.density == 1 ? 15 : 22;
            }
            AudioListener.volume = s.sound / 10f;
            GameAudio.music = s.music / 10f;
            if (Hud.I != null) Hud.I.showFps = s.fps == 1;
        }

        // ------------------------------------------------------------------ the world's fixed vehicles and markers
        void SpawnPointVehicles()
        {
            foreach (var p in City.I.points)
            {
                if (p.kind != "vehicle" && p.kind != "boat") continue;
                Vehicle v;
                if (pointVehicles.TryGetValue(p, out v) && v != null) continue;
                string model = p.kind == "boat" ? "speedboat" : p.model;
                if (string.IsNullOrEmpty(model) || !Models.vehicles.ContainsKey(model)) continue;
                Vector3 pos = p.p;
                if (p.kind == "boat")
                {
                    float wl = City.I.WaterLevel(pos.x, pos.z);
                    pos.y = float.IsNaN(wl) ? pos.y : wl - 0.2f;
                }
                v = Vehicle.Spawn(model, pos + Vector3.up * 0.15f, p.yaw, false, Color.white);
                if (v == null) continue;
                v.owned = p.owned;
                pointVehicles[p] = v;
            }
        }

        void MakeMarkers()
        {
            Shader ms = Shader.Find("Danga/Marker");
            foreach (var p in City.I.points)
            {
                Color c;
                switch (p.kind)
                {
                    case "gunshop": c = new Color(1f, 0.3f, 0.2f, 0.35f); break;
                    case "clothes": c = new Color(0.8f, 0.4f, 1f, 0.35f); break;
                    case "house": c = new Color(0.3f, 1f, 0.4f, 0.35f); break;
                    case "hospital": c = new Color(1f, 1f, 1f, 0.3f); break;
                    default: continue;
                }
                var go = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
                Destroy(go.GetComponent<Collider>());
                go.name = "marker_" + p.kind;
                go.transform.position = p.p + Vector3.up * 0.75f;
                go.transform.localScale = new Vector3(2.2f, 0.75f, 2.2f);
                var r = go.GetComponent<MeshRenderer>();
                r.sharedMaterial = new Material(ms);
                r.sharedMaterial.SetColor("_Color", new Color(c.r, c.g, c.b, 0.8f));
                r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
                markers.Add(go);
            }
        }

        void Update()
        {
            if (state == S.Loading) return;
            float dt = Time.deltaTime;
            if (City.I != null) City.I.Stream(Focus, 2);
            if (state != S.Paused) Env.Tick(state == S.Menu ? dt * 0.3f : dt);
            if (Input.GetKeyDown(KeyCode.Escape))
            {
                if (Menus.I.IsOpen && state != S.Menu) Menus.I.Close();
                else if (state == S.Play) Menus.I.Pause();
            }
            if (state != S.Play) { if (hud != null) hud.SetContext(null, null); return; }
            Wanted.Tick();
            Player p = Player.I;
            // shops, house and hospital
            string label = null;
            System.Action act = null;
            if (p.vehicle == null && !p.dead)
                foreach (var pt in City.I.points)
                {
                    if ((pt.p - p.transform.position).sqrMagnitude > 2.4f * 2.4f) continue;
                    switch (pt.kind)
                    {
                        case "gunshop": label = "GUN SHOP"; act = Menus.I.GunShop; break;
                        case "clothes": label = "CLOTHES"; act = () => Menus.I.Clothes(false); break;
                        case "house": label = "HOUSE"; act = Menus.I.House; break;
                        case "hospital": label = "HEAL ₹500"; act = Heal; break;
                    }
                }
            hud.SetContext(label, act);
            foreach (var m in markers) m.transform.localScale = new Vector3(2.2f + Mathf.Sin(Time.time * 3f) * 0.1f, 0.75f, 2.2f + Mathf.Sin(Time.time * 3f) * 0.1f);
            if (Time.time > nextPointCheck)
            {
                nextPointCheck = Time.time + 5f;
                RespawnPointVehicles(p.transform.position);
            }
        }

        void Heal()
        {
            Player p = Player.I;
            if (p.health >= p.maxHealth) { Hud.Toast("You are healthy"); return; }
            if (p.money < 500) { Hud.Toast("Not enough money", Ui.Red); return; }
            p.money -= 500;
            p.health = p.maxHealth;
            GameAudio.Ui("cash", 0.6f);
            Hud.Toast("Healed", Ui.Green);
        }

        void RespawnPointVehicles(Vector3 pp)
        {
            var keys = new List<City.MapPoint>(pointVehicles.Keys);
            foreach (var pt in keys)
            {
                Vehicle v = pointVehicles[pt];
                bool gone = v == null || v.wrecked || (v.transform.position - pt.p).sqrMagnitude > 40f * 40f;
                if (!gone || (pt.p - pp).sqrMagnitude < 160f * 160f) continue;
                if (v != null && v.driver != null && v.driver.isPlayer) continue;
                pointVehicles.Remove(pt);
            }
            SpawnPointVehicles();
        }

        // ------------------------------------------------------------------ cheats
        public string Cheat(string code)
        {
            Player p = Player.I;
            string msg = null;
            switch (code)
            {
                case "1999": p.health = p.maxHealth; p.armor = 100f; msg = "HEALTH & ARMOUR FULL"; break;
                case "4545": p.AddMoney(100000); msg = "₹1,00,000 ADDED"; break;
                case "1122":
                    foreach (var d in Combat.Defs) { p.owned.Add(d.id); if (!d.melee) { p.clip[(int)d.id] = d.mag; p.ammo[(int)d.id] += d.ammoPack * 3; } }
                    msg = "ALL WEAPONS";
                    break;
                case "0000": Wanted.Set(0); msg = "WANTED LEVEL CLEARED"; break;
                case "7777": Wanted.Set(5); msg = "FIVE STARS!"; break;
                case "4321": Wanted.never = !Wanted.never; if (Wanted.never) Wanted.Set(0); msg = "NEVER WANTED " + (Wanted.never ? "ON" : "OFF"); break;
                case "1100": godMode = !godMode; msg = "GOD MODE " + (godMode ? "ON" : "OFF"); break;
                case "1001": p.speedMul = p.speedMul > 1f ? 1f : 2.2f; msg = "SUPER RUN " + (p.speedMul > 1f ? "ON" : "OFF"); break;
                case "1234": p.gravity = p.gravity < -10f ? -4.5f : -20f; msg = "MOON GRAVITY " + (p.gravity > -10f ? "ON" : "OFF"); break;
                case "8080": msg = SpawnNear("sports_car"); break;
                case "2323": msg = SpawnNear("motorbike"); break;
                case "6060": msg = SpawnNear("auto_rickshaw"); break;
                case "1515": msg = SpawnNear("bus"); break;
                case "3030": msg = SpawnNear("police_jeep"); break;
                case "9090": msg = SpawnNear("helicopter"); break;
                case "5050": msg = SpawnBoat(); break;
                case "6000": Env.hour = Mathf.Repeat(Env.hour + 6f, 24f); msg = "TIME " + Env.Clock(); break;
                case "2222":
                    foreach (var v in Vehicle.all.ToArray())
                        if (v != p.vehicle && (v.transform.position - p.transform.position).sqrMagnitude < 60f * 60f) { v.Damage(99999f, null); v.burning = 4.6f; }
                    msg = "BOOM!";
                    break;
                case "3131":
                    p.Teleport(SpawnPoint(), 0f);
                    City.I.StreamNow(SpawnPoint());
                    msg = "WELCOME HOME";
                    break;
            }
            if (msg != null) { GameAudio.Ui("cash", 0.4f); Hud.Toast("CHEAT: " + msg, Ui.Yellow, 3f); }
            return msg;
        }

        string SpawnNear(string model)
        {
            Player p = Player.I;
            Vector3 at = p.transform.position + p.transform.forward * (model == "bus" ? 9f : model == "helicopter" ? 12f : 5f);
            if (p.vehicle != null) at = p.vehicle.transform.position + p.vehicle.transform.right * 6f;
            at.y = GroundNear(at, p.transform.position.y) + 0.4f;
            var v = Vehicle.Spawn(model, at, p.transform.eulerAngles.y + 90f, false, Color.white);
            if (v == null) return null;
            v.parked = false;
            return model.Replace('_', ' ').ToUpper() + " READY";
        }

        /// <summary>The ground just under a point near the player's height (not the roof of a house above it).</summary>
        static float GroundNear(Vector3 at, float fromY)
        {
            RaycastHit h;
            if (Physics.Raycast(new Vector3(at.x, fromY + 2.5f, at.z), Vector3.down, out h, 12f, 1 << City.LayerWorld, QueryTriggerInteraction.Ignore)) return h.point.y;
            return fromY;
        }

        string SpawnBoat()
        {
            Player p = Player.I;
            City.MapPoint best = null;
            float bd = 1e12f;
            foreach (var pt in City.I.points)
                if (pt.kind == "boat" && (pt.p - p.transform.position).sqrMagnitude < bd) { bd = (pt.p - p.transform.position).sqrMagnitude; best = pt; }
            Vector3 ahead = p.transform.position + p.transform.forward * 8f;
            float wl = City.I.WaterLevel(ahead.x, ahead.z);
            if (!float.IsNaN(wl))
            {
                var v = Vehicle.Spawn("speedboat", new Vector3(ahead.x, wl, ahead.z), p.transform.eulerAngles.y, false, Color.white);
                if (v != null) v.parked = false;
                return "SPEEDBOAT READY";
            }
            if (best == null) return null;
            float bw = City.I.WaterLevel(best.p.x, best.p.z);
            var b = Vehicle.Spawn("speedboat", new Vector3(best.p.x, float.IsNaN(bw) ? best.p.y : bw, best.p.z), best.yaw, false, Color.white);
            if (b != null) b.parked = false;
            p.Teleport(best.p + Quaternion.Euler(0, best.yaw, 0) * new Vector3(3f, 1.5f, 0f), best.yaw);
            City.I.StreamNow(best.p);
            return "BOAT AT " + best.name.ToUpper();
        }

        // ------------------------------------------------------------------ for the emulator check
        public void TestTeleport(Vector3 p, float yaw) { City.I.StreamNow(p); Player.I.Teleport(p, yaw); }
    }
}

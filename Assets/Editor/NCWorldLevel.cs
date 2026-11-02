using System.Collections.Generic;
using UnityEngine;
using UnityEngine.AI;

namespace NightClass.EditorTools
{
    /// <summary>
    /// The school: one floor plus a basement. Corridor along X (z -2..2); classrooms, lounge and
    /// toilets to the north; cafeteria, janitor's room, entrance hall and gym to the south; the
    /// principal's office and library past the fire in the west; the garage behind a roller door in
    /// the east; the basement and boiler room under the janitor's room.
    /// </summary>
    public static partial class NCWorld
    {
        const float H = 3.2f, T = 0.2f, GymH = 4.5f, BY = -3.6f, BH = 3.3f;

        static Material mFloorWood, mFloorTile, mFloorTileSmall, mFloorConcrete, mFloorGym, mWall, mWallLower, mWallTile, mWallBrick, mWallOffice, mCeiling;
        static Material mWood, mWoodDark, mMetalGreen, mMetalGrey, mMetalDark, mRust, mFabric, mChalkboard, mPaper, mWindow, mLampTube, mLampOff, mBrass;
        static Material mRubber, mCeramic, mMirror, mCake, mRock, mGold, mCarPaint, mTire, mGround, mBark, mNote, mMap, mClock, mKeypad, mLed, mRed, mGlassDark;
        static Material mShaft, mShaftWarm, mFire, mSmoke, mWater, mSpark, mDust, mBug, mChalkDraw, mCrate, mMat, mBook1, mBook2, mBook3, mRuler;
        static Material[] mPosters;

        static Transform playerSpawn, introCam;
        static readonly List<Transform> menuCam = new List<Transform>();
        static readonly List<Transform> endingCam = new List<Transform>();
        static readonly List<Transform> patrol = new List<Transform>();

        struct Op
        {
            public float c, w, b, t;
            public Op(float c, float w, float b, float t) { this.c = c; this.w = w; this.b = b; this.t = t; }
        }
        static Op Dr(float c, float w = 1.1f) { return new Op(c, w, 0f, 2.2f); }
        static Op Wn(float c, float w = 1.6f) { return new Op(c, w, 1.0f, 2.4f); }

        static void CreateMaterials()
        {
            mFloorWood = NCMats.Lit("floor_wood", "wood_floor", new Color(0.78f, 0.7f, 0.62f), 0.45f, 0f, 0.45f);
            mFloorTile = NCMats.Lit("floor_tile", "tiles_floor", new Color(0.82f, 0.82f, 0.8f), 0.55f, 0f, 0.5f);
            mFloorTileSmall = NCMats.Lit("floor_tile_small", "tiles_small", new Color(0.86f, 0.9f, 0.9f), 0.6f, 0f, 1f);
            mFloorConcrete = NCMats.Lit("floor_concrete", "concrete", new Color(0.7f, 0.7f, 0.7f), 0.25f, 0f, 0.4f);
            mFloorGym = NCMats.Lit("floor_gym", "wood_floor", new Color(0.95f, 0.8f, 0.6f), 0.6f, 0f, 0.6f);
            mWall = NCMats.Lit("wall_paint", "plaster", new Color(0.74f, 0.75f, 0.66f), 0.15f, 0f, 0.35f);
            mWallLower = NCMats.Lit("wall_lower", "plaster", new Color(0.26f, 0.36f, 0.33f), 0.3f, 0f, 0.35f);
            mWallTile = NCMats.Lit("wall_tile", "tiles_small", new Color(0.78f, 0.86f, 0.84f), 0.65f, 0f, 1f);
            mWallBrick = NCMats.Lit("wall_brick", "brick", new Color(0.62f, 0.55f, 0.52f), 0.2f, 0f, 0.5f);
            mWallOffice = NCMats.Lit("wall_office", "plaster", new Color(0.55f, 0.42f, 0.36f), 0.15f, 0f, 0.35f);
            mCeiling = NCMats.Lit("ceiling", "plaster", new Color(0.62f, 0.62f, 0.6f), 0.1f, 0f, 0.3f);
            mWood = NCMats.Lit("wood", "wood_furniture", new Color(0.85f, 0.72f, 0.58f), 0.4f, 0f, 1f);
            mWoodDark = NCMats.Lit("wood_dark", "wood_furniture", new Color(0.42f, 0.3f, 0.22f), 0.45f, 0f, 1f);
            mMetalGreen = NCMats.Lit("metal_green", "metal_painted", new Color(0.32f, 0.45f, 0.4f), 0.45f, 0.3f, 1f);
            mMetalGrey = NCMats.Lit("metal_grey", "metal_painted", new Color(0.6f, 0.6f, 0.62f), 0.4f, 0.4f, 1f);
            mMetalDark = NCMats.Lit("metal_dark", null, new Color(0.12f, 0.12f, 0.13f), 0.55f, 0.8f);
            mRust = NCMats.Lit("rust", "rust", new Color(0.8f, 0.7f, 0.65f), 0.3f, 0.2f, 1f);
            mFabric = NCMats.Lit("fabric", "fabric", new Color(0.55f, 0.2f, 0.18f), 0.1f, 0f, 1.5f);
            mChalkboard = NCMats.Picture("chalkboard", "chalkboard", Color.white, 0.25f);
            mPaper = NCMats.Lit("paper", null, new Color(0.85f, 0.83f, 0.76f), 0.1f);
            mWindow = NCMats.Custom("window", "NightClass/Window", m =>
            {
                Texture2D g = NCMats.Tex(NCMats.FxDir + "grime");
                if (g != null) m.SetTexture("_Grime", g);
            });
            mLampTube = NCMats.Lit("lamp_tube", null, new Color(0.9f, 0.9f, 0.85f), 0.5f, 0f, 1f, new Color(1.6f, 1.5f, 1.3f));
            mLampOff = NCMats.Lit("lamp_off", null, new Color(0.5f, 0.5f, 0.48f), 0.5f);
            mBrass = NCMats.Lit("brass", null, new Color(0.75f, 0.58f, 0.25f), 0.7f, 1f);
            mRubber = NCMats.Lit("rubber", null, new Color(0.05f, 0.05f, 0.05f), 0.2f);
            mCeramic = NCMats.Lit("ceramic", null, new Color(0.85f, 0.87f, 0.86f), 0.8f);
            mMirror = NCMats.Lit("mirror", null, new Color(0.12f, 0.14f, 0.16f), 0.95f, 1f);
            mCake = NCMats.Picture("cake", "cake", Color.white, 0.3f);
            mRock = NCMats.Lit("rock", "concrete", new Color(0.55f, 0.52f, 0.5f), 0.15f, 0f, 1.2f);
            mGold = NCMats.Lit("gold", null, new Color(0.9f, 0.7f, 0.25f), 0.85f, 1f, 1f, new Color(0.15f, 0.1f, 0.02f));
            mCarPaint = NCMats.Lit("car_paint", null, new Color(0.25f, 0.05f, 0.04f), 0.75f, 0.4f);
            mTire = NCMats.Lit("tire", null, new Color(0.04f, 0.04f, 0.04f), 0.25f);
            mGround = NCMats.Lit("ground", "concrete", new Color(0.3f, 0.32f, 0.28f), 0.1f, 0f, 0.25f);
            mBark = NCMats.Lit("bark", "wood_furniture", new Color(0.18f, 0.15f, 0.13f), 0.1f, 0f, 1f);
            mNote = NCMats.Picture("note", "note", Color.white, 0.1f);
            mMap = NCMats.Picture("map", "map", Color.white, 0.25f);
            mClock = NCMats.Picture("clock", "clock", Color.white, 0.4f);
            mKeypad = NCMats.Picture("keypad", "keypad", Color.white, 0.4f);
            mLed = NCMats.Lit("led", null, new Color(0.3f, 0.05f, 0.05f), 0.6f, 0f, 1f, new Color(2.2f, 0.15f, 0.1f));
            mRed = NCMats.Lit("red_paint", null, new Color(0.55f, 0.06f, 0.05f), 0.4f);
            mGlassDark = NCMats.Lit("glass_dark", null, new Color(0.04f, 0.05f, 0.06f), 0.96f, 0.6f);
            mCrate = NCMats.Lit("crate", "wood_floor", new Color(0.7f, 0.58f, 0.42f), 0.2f, 0f, 1.2f);
            mMat = NCMats.Lit("gym_mat", "fabric", new Color(0.12f, 0.2f, 0.42f), 0.15f, 0f, 1.5f);
            mBook1 = NCMats.Lit("book1", null, new Color(0.35f, 0.08f, 0.07f), 0.3f);
            mBook2 = NCMats.Lit("book2", null, new Color(0.08f, 0.18f, 0.3f), 0.3f);
            mBook3 = NCMats.Lit("book3", null, new Color(0.2f, 0.26f, 0.1f), 0.3f);
            mRuler = NCMats.Lit("ruler", "wood_furniture", new Color(0.9f, 0.78f, 0.55f), 0.3f, 0f, 2f);
            mPosters = new[]
            {
                NCMats.Picture("poster0", "poster0", Color.white, 0.2f),
                NCMats.Picture("poster1", "poster1", Color.white, 0.2f),
                NCMats.Picture("poster2", "poster2", Color.white, 0.2f),
                NCMats.Picture("poster3", "poster3", Color.white, 0.2f),
            };
            mChalkDraw = NCMats.Picture("chalk_drawing", "drawing", Color.white, 0.2f, new Color(0f, 0f, 0f));
            mShaft = NCMats.Custom("shaft_moon", "NightClass/LightShaft", m =>
            {
                m.SetColor("_Color", new Color(0.4f, 0.52f, 0.78f, 0.16f));
                m.SetFloat("_Fade", 1.4f);
                m.SetFloat("_Edge", 2.2f);
            });
            mShaftWarm = NCMats.Custom("shaft_lamp", "NightClass/LightShaft", m =>
            {
                m.SetColor("_Color", new Color(0.9f, 0.8f, 0.6f, 0.08f));
                m.SetFloat("_Fade", 1.2f);
                m.SetFloat("_Edge", 2.5f);
            });
            NCMats.SetUV(mShaftWarm, 1f / 2.4f);
            mFire = NCMats.Particle("fx_fire", "flame", new Color(1f, 0.85f, 0.7f, 1f), true);
            mSpark = NCMats.Particle("fx_spark", "spark", new Color(1f, 0.8f, 0.5f, 1f), true);
            mSmoke = NCMats.Particle("fx_smoke", "smoke", new Color(0.5f, 0.5f, 0.5f, 1f), false);
            mDust = NCMats.Particle("fx_dust", "smoke", new Color(0.6f, 0.56f, 0.5f, 1f), false);
            mWater = NCMats.Particle("fx_water", "drop", new Color(0.6f, 0.7f, 0.85f, 0.8f), false);
            mBug = NCMats.Custom("bug", "NightClass/ParticleAlpha", m =>
            {
                Texture2D t = NCMats.Tex(NCMats.FxDir + "bug");
                if (t != null) m.SetTexture("_BaseMap", t);
                m.SetColor("_BaseColor", Color.white);
            });
        }

        // ------------------------------------------------------------------ spatial chunks
        /// <summary>Static geometry is grouped in 8 m cells so each mesh only needs the few lamps around it.</summary>
        static string Cell(Vector3 p)
        {
            int lvl = p.y < -0.5f ? 1 : 0;
            return "L" + lvl + "_" + Mathf.FloorToInt(p.x / 8f) + "_" + Mathf.FloorToInt(p.z / 8f);
        }

        static void SBox(Material mat, Vector3 center, Vector3 size, bool collider = true, Surface? surface = null)
        {
            Box(Cell(center), mat, center, size, collider, surface);
        }

        /// <summary>Horizontal slab split into 8 m tiles (floors, ceilings), with optional rectangular holes.</summary>
        static void Slab(Material mat, float x0, float z0, float x1, float z1, float yBottom, float yTop, Surface? surface, bool collider = true, Rect? hole = null)
        {
            for (float x = x0; x < x1 - 0.001f; x += 8f)
                for (float z = z0; z < z1 - 0.001f; z += 8f)
                {
                    float xa = x, xb = Mathf.Min(x + 8f, x1), za = z, zb = Mathf.Min(z + 8f, z1);
                    if (hole.HasValue)
                    {
                        Rect h = hole.Value;
                        if (h.xMin < xb && h.xMax > xa && h.yMin < zb && h.yMax > za)
                        {
                            // split this tile into up to four pieces around the hole
                            SlabPiece(mat, xa, za, xb, Mathf.Max(za, h.yMin), yBottom, yTop, surface, collider);
                            SlabPiece(mat, xa, Mathf.Min(zb, h.yMax), xb, zb, yBottom, yTop, surface, collider);
                            SlabPiece(mat, xa, Mathf.Max(za, h.yMin), Mathf.Max(xa, h.xMin), Mathf.Min(zb, h.yMax), yBottom, yTop, surface, collider);
                            SlabPiece(mat, Mathf.Min(xb, h.xMax), Mathf.Max(za, h.yMin), xb, Mathf.Min(zb, h.yMax), yBottom, yTop, surface, collider);
                            continue;
                        }
                    }
                    SlabPiece(mat, xa, za, xb, zb, yBottom, yTop, surface, collider);
                }
        }

        static void SlabPiece(Material mat, float xa, float za, float xb, float zb, float y0, float y1, Surface? surface, bool collider)
        {
            if (xb - xa < 0.01f || zb - za < 0.01f) return;
            SBox(mat, new Vector3((xa + xb) * 0.5f, (y0 + y1) * 0.5f, (za + zb) * 0.5f), new Vector3(xb - xa, y1 - y0, zb - za), collider, surface);
        }

        static void Room(Material floor, Surface s, float x0, float z0, float x1, float z1, float ceilingH = H, Material ceiling = null, float y0 = 0f, Rect? hole = null)
        {
            Slab(floor, x0, z0, x1, z1, y0 - 0.3f, y0, s, true, hole);
            Slab(ceiling ?? mCeiling, x0, z0, x1, z1, y0 + ceilingH, y0 + ceilingH + 0.25f, null, false);
        }

        // ------------------------------------------------------------------ walls
        static void WallX(Material up, Material low, float z, float x0, float x1, float y0, float h, params Op[] ops)
        {
            var list = new List<Op>(ops);
            list.Sort((a, b) => a.c.CompareTo(b.c));
            float cur = x0 - T * 0.5f, end = x1 + T * 0.5f;
            foreach (Op o in list)
            {
                float a = o.c - o.w * 0.5f, b = o.c + o.w * 0.5f;
                if (a > cur + 0.001f) Solid(true, up, low, z, cur, a, y0, 0f, h);
                if (o.b > 0.001f) Solid(true, up, low, z, a, b, y0, 0f, o.b);
                if (o.t < h - 0.001f) Solid(true, up, low, z, a, b, y0, o.t, h);
                cur = b;
            }
            if (end > cur + 0.001f) Solid(true, up, low, z, cur, end, y0, 0f, h);
        }

        static void WallZ(Material up, Material low, float x, float z0, float z1, float y0, float h, params Op[] ops)
        {
            var list = new List<Op>(ops);
            list.Sort((a, b) => a.c.CompareTo(b.c));
            float cur = z0 + T * 0.5f, end = z1 - T * 0.5f;
            foreach (Op o in list)
            {
                float a = o.c - o.w * 0.5f, b = o.c + o.w * 0.5f;
                if (a > cur + 0.001f) Solid(false, up, low, x, cur, a, y0, 0f, h);
                if (o.b > 0.001f) Solid(false, up, low, x, a, b, y0, 0f, o.b);
                if (o.t < h - 0.001f) Solid(false, up, low, x, a, b, y0, o.t, h);
                cur = b;
            }
            if (end > cur + 0.001f) Solid(false, up, low, x, cur, end, y0, 0f, h);
        }

        /// <summary>A solid run of wall (split into 6 m pieces), dark lower paint up to 1.1 m.</summary>
        static void Solid(bool alongX, Material up, Material low, float fixedCoord, float a, float b, float y0, float ya, float yb)
        {
            const float split = 1.1f;
            float len = b - a;
            int pieces = Mathf.Max(1, Mathf.CeilToInt(len / 6f));
            for (int i = 0; i < pieces; i++)
            {
                float pa = a + len * i / pieces, pb = a + len * (i + 1) / pieces;
                float c = (pa + pb) * 0.5f, l = pb - pa;
                System.Func<float, float, Vector3> center = (yA, yB) => alongX ? new Vector3(c, y0 + (yA + yB) * 0.5f, fixedCoord) : new Vector3(fixedCoord, y0 + (yA + yB) * 0.5f, c);
                System.Func<float, Vector3> size = hh => alongX ? new Vector3(l, hh, T) : new Vector3(T, hh, l);
                if (low != null && ya < split && yb > split)
                {
                    SBox(low, center(ya, split), size(split - ya), false);
                    SBox(up, center(split, yb), size(yb - split), false);
                }
                else SBox(low != null && yb <= split + 0.001f ? low : up, center(ya, yb), size(yb - ya), false);
                Collider(center(ya, yb), size(yb - ya));
            }
        }

        // ------------------------------------------------------------------ the building
        static void BuildLevel()
        {
            // ---------------- floors and ceilings
            Room(mFloorTile, Surface.Tile, -36f, -2f, 26f, 2f);                  // corridor
            Room(mFloorWood, Surface.Wood, -24f, 2f, -14f, 12f);                 // class A
            Room(mFloorWood, Surface.Wood, -14f, 2f, -4f, 12f);                  // class B (start)
            Room(mFloorWood, Surface.Wood, -4f, 2f, 4f, 12f);                    // teachers' lounge
            Room(mFloorWood, Surface.Wood, 4f, 2f, 14f, 12f);                    // class C
            Room(mFloorTileSmall, Surface.Tile, 14f, 2f, 24f, 12f);              // toilets
            Room(mFloorWood, Surface.Wood, -36f, 2f, -24f, 10f);                 // principal's office
            Room(mFloorWood, Surface.Wood, -36f, -10f, -24f, -2f);               // library
            Room(mFloorTile, Surface.Tile, -24f, -12f, -14f, -2f);               // cafeteria
            Room(mFloorConcrete, Surface.Concrete, -14f, -12f, -8f, -2f, H, null, 0f, new Rect(-12.2f, -6.1f, 1.4f, 2.8f)); // janitor (stairwell hole)
            Room(mFloorTile, Surface.Tile, -8f, -14f, 4f, -2f);                  // entrance hall
            Room(mFloorGym, Surface.Wood, 4f, -16f, 24f, -2f, GymH);             // gym
            Slab(mCeiling, 18f, -16f, 24f, -11f, 3.0f, 3.2f, null, false);       // gym storage roof
            Room(mFloorConcrete, Surface.Concrete, 26f, -6f, 36f, 6f);           // garage
            Room(mFloorWood, Surface.Wood, -12f, 12f, -6f, 15f);                 // secret room

            // ---------------- ground-floor walls
            WallX(mWall, null, 12f, -24f, 24f, 0f, H, Wn(-21f), Wn(-17f), Wn(-12f), Dr(-9f), Wn(-6f), Wn(0f), Wn(7f), Wn(11f), new Op(19f, 1.2f, 1.9f, 2.6f));
            WallX(mWall, mWallLower, 2f, -36f, 26f, 0f, H, Dr(-28f), Dr(-16f), Dr(-6f), Dr(0f), Dr(6f), Dr(16f));
            WallX(mWallOffice, null, 10f, -36f, -24f, 0f, H, Wn(-30f));
            WallX(mWall, mWallLower, -2f, -36f, 4f, 0f, H, Dr(-28f), Dr(-17f), Dr(-10f), new Op(-3f, 4f, 0f, 2.8f));
            WallX(mWall, mWallLower, -2f, 4f, 26f, 0f, GymH, new Op(9f, 2.2f, 0f, 2.6f));
            WallX(mWall, null, -10f, -36f, -24f, 0f, H, Wn(-30f));
            WallX(mWall, null, -12f, -24f, -8f, 0f, H, Wn(-21f), Wn(-17f));
            WallX(mWall, mWallLower, -14f, -8f, 4f, 0f, H, new Op(-2f, 2.2f, 0f, 2.7f));
            WallX(mWall, mWallLower, -16f, 4f, 24f, 0f, GymH, new Op(8f, 2.4f, 2.6f, 3.9f), new Op(14f, 2.4f, 2.6f, 3.9f), new Op(20f, 2.4f, 2.6f, 3.9f));
            WallX(mWall, null, -11f, 18f, 24f, 0f, 3.0f, Dr(20f));
            WallX(mWallBrick, null, 6f, 26f, 36f, 0f, H);
            WallX(mWallBrick, null, -6f, 26f, 36f, 0f, H);
            WallX(mWall, null, 15f, -12f, -6f, 0f, H);

            WallZ(mWall, null, -36f, -10f, 10f, 0f, H, Wn(-6f), Wn(0f), Wn(6f));
            WallZ(mWall, null, -24f, 2f, 12f, 0f, H);
            WallZ(mWall, null, -24f, -12f, -2f, 0f, H);
            WallZ(mWall, null, -14f, 2f, 12f, 0f, H);
            WallZ(mWall, null, -14f, -12f, -2f, 0f, H, new Op(-10f, 0.9f, 0f, 1.0f));
            WallZ(mWall, null, -4f, 2f, 12f, 0f, H);
            WallZ(mWall, null, 4f, 2f, 12f, 0f, H);
            WallZ(mWall, mWallLower, 4f, -16f, -2f, 0f, GymH);
            WallZ(mWallTile, null, 14f, 2f, 12f, 0f, H);
            WallZ(mWallTile, null, 24f, 2f, 12f, 0f, H);
            WallZ(mWall, mWallLower, 24f, -16f, -2f, 0f, GymH, new Op(-9f, 2.4f, 2.6f, 3.9f));
            WallZ(mWall, mWallLower, -8f, -14f, -2f, 0f, H);
            WallZ(mWall, null, 18f, -16f, -11f, 0f, 3.0f);
            WallZ(mWallBrick, null, 26f, -6f, 6f, 0f, H, new Op(0f, 3.2f, 0f, 2.6f));
            WallZ(mWallBrick, null, 36f, -6f, 6f, 0f, H);
            WallZ(mWall, null, -12f, 12f, 15f, 0f, H);
            WallZ(mWall, null, -6f, 12f, 15f, 0f, H);
            // toilet tiles on the inner faces
            SBox(mWallTile, new Vector3(19f, 1.6f, 11.88f), new Vector3(9.8f, 3.2f, 0.04f), false);
            SBox(mWallTile, new Vector3(19f, 0.8f, 2.12f), new Vector3(9.8f, 1.6f, 0.04f), false);

            // ---------------- basement
            Slab(mFloorConcrete, -14f, -12f, -4f, -3f, BY - 0.3f, BY, Surface.Concrete);
            Slab(mFloorConcrete, -4f, -12f, 6f, -4f, BY - 0.3f, BY, Surface.Concrete);
            Slab(mFloorConcrete, -14f, -12f, -4f, -3f, -0.33f, -0.3f, null, false, new Rect(-12.2f, -6.1f, 1.4f, 2.8f));
            Slab(mFloorConcrete, -4f, -12f, 6f, -4f, -0.33f, -0.3f, null, false);
            WallX(mWallBrick, null, -3f, -14f, -4f, BY, BH);
            WallX(mWallBrick, null, -12f, -14f, 6f, BY, BH);
            WallX(mWallBrick, null, -4f, -4f, 6f, BY, BH);
            WallZ(mWallBrick, null, -14f, -12f, -3f, BY, BH);
            WallZ(mWallBrick, null, -4f, -12f, -3f, BY, BH, new Op(-8f, 1.8f, 0f, 2.4f));
            WallZ(mWallBrick, null, 6f, -12f, -4f, BY, BH);
            Stairs();

            // ---------------- outside (seen in the escape ending)
            Slab(mGround, -40f, -45f, 40f, -16.1f, -0.35f, -0.05f, Surface.Concrete);
            Slab(mGround, -8f, -16.1f, 4f, -14.1f, -0.35f, -0.05f, Surface.Concrete);
            Outside();

            BuildLights();
            BuildWindows();
        }

        static void Stairs()
        {
            // 15 solid steps from the janitor's floor (z -3.3) down to the basement (z -7.8)
            for (int k = 0; k < 15; k++)
            {
                float top = -0.24f * (k + 1);
                float za = -3.3f - 0.3f * (k + 1), zb = -3.3f - 0.3f * k;
                SBox(mFloorConcrete, new Vector3(-11.5f, (top + BY) * 0.5f, (za + zb) * 0.5f), new Vector3(1.4f, top - BY, zb - za), false);
            }
            // one smooth ramp collider for walking and for the teacher's navmesh
            float len = Mathf.Sqrt(4.5f * 4.5f + 3.6f * 3.6f);
            float ang = Mathf.Atan2(3.6f, 4.5f) * Mathf.Rad2Deg;
            var go = new GameObject("StairRamp");
            go.transform.SetParent(colRoot, false);
            Vector3 n = Quaternion.Euler(-ang, 0f, 0f) * Vector3.up;
            go.transform.position = new Vector3(-11.5f, -1.8f, -5.55f) - n * 0.05f;
            go.transform.rotation = Quaternion.Euler(-ang, 0f, 0f);
            go.isStatic = true;
            var bc = go.AddComponent<BoxCollider>();
            bc.size = new Vector3(1.4f, 0.1f, len);
            go.AddComponent<SurfaceTag>().surface = Surface.Concrete;
            // side walls of the stairwell under the floor
            SBox(mWallBrick, new Vector3(-12.3f, -1.95f, -5.55f), new Vector3(0.2f, 3.3f, 4.5f));
            SBox(mWallBrick, new Vector3(-10.7f, -1.95f, -5.55f), new Vector3(0.2f, 3.3f, 4.5f));
            patrol.Add(Point("Patrol_basement", new Vector3(-9f, BY, -8f)));
            patrol.Add(Point("Patrol_boiler", new Vector3(1f, BY, -7f)));
        }

        static void Outside()
        {
            var rnd = new System.Random(7);
            for (int i = 0; i < 9; i++)
            {
                float x = -26f + i * 6.5f + (float)rnd.NextDouble() * 3f;
                float z = -24f - (float)rnd.NextDouble() * 14f;
                if (Mathf.Abs(x + 2f) < 4f) x += 8f;
                float h = 4f + (float)rnd.NextDouble() * 3f;
                Vector3 b = new Vector3(x, -0.05f, z);
                Draw(Cell(b), mBark, Matrix4x4.identity, mb =>
                {
                    mb.Cylinder(b, b + Vector3.up * h, 0.22f, 0.08f, 8);
                    for (int k = 0; k < 5; k++)
                    {
                        float a = k * 1.3f + (float)rnd.NextDouble();
                        Vector3 s = b + Vector3.up * (h * (0.45f + 0.1f * k));
                        Vector3 e = s + new Vector3(Mathf.Cos(a), 0.6f, Mathf.Sin(a)) * (1.2f + (float)rnd.NextDouble());
                        mb.Cylinder(s, e, 0.07f, 0.02f, 5, false);
                    }
                });
            }
            // fence and a street lamp
            for (int i = 0; i < 26; i++)
            {
                float x = -30f + i * 2.4f;
                SBox(mMetalDark, new Vector3(x, 0.9f, -40f), new Vector3(0.06f, 1.9f, 0.06f), false);
            }
            SBox(mMetalDark, new Vector3(0f, 1.6f, -40f), new Vector3(62f, 0.06f, 0.05f), false);
            SBox(mMetalDark, new Vector3(0f, 0.4f, -40f), new Vector3(62f, 0.06f, 0.05f), false);
            SBox(mMetalDark, new Vector3(6f, 2.2f, -22f), new Vector3(0.12f, 4.5f, 0.12f), false);
            Light l = PointLight(null, new Vector3(6f, 4.3f, -22f), new Color(1f, 0.62f, 0.3f), 2.5f, 12f, "StreetLamp");
            l.gameObject.name = "StreetLamp";
            SBox(mLampTube, new Vector3(6f, 4.45f, -22f), new Vector3(0.4f, 0.12f, 0.4f), false);
            endingCam.Add(Point("End_0", new Vector3(-2f, 1.65f, -11.5f), 180f, 2f));
            endingCam.Add(Point("End_1", new Vector3(-2f, 1.6f, -14.6f), 180f, 0f));
            endingCam.Add(Point("End_2", new Vector3(-2f, 1.8f, -21f), 175f, -6f));
            endingCam.Add(Point("End_3", new Vector3(-1f, 4.5f, -30f), 0f, 8f));
        }

        // ------------------------------------------------------------------ lamps
        static void Lamp(Vector3 ceilingPos, Color color, float intensity, float range, bool flicker = false, bool broken = false, bool off = false, float yaw = 0f)
        {
            GameObject go = Obj("Lamp", lightRoot, ceilingPos, Quaternion.Euler(0f, yaw, 0f));
            Part(go.transform, "Housing", mMetalGrey, b => b.Box(new Vector3(0f, -0.04f, 0f), new Vector3(1.3f, 0.07f, 0.3f)));
            MeshRenderer tube = Part(go.transform, "Tube", off ? mLampOff : mLampTube, b =>
            {
                b.Cylinder(new Vector3(-0.6f, -0.1f, 0.06f), new Vector3(0.6f, -0.1f, 0.06f), 0.025f, 0.025f, 8);
                b.Cylinder(new Vector3(-0.6f, -0.1f, -0.06f), new Vector3(0.6f, -0.1f, -0.06f), 0.025f, 0.025f, 8);
            });
            if (off) return;
            Light l = PointLight(go.transform, ceilingPos + Vector3.down * 0.35f, color, intensity, range);
            if (flicker || broken)
            {
                FlickerLight f = go.AddComponent<FlickerLight>();
                f.lamp = l;
                f.tube = tube;
                f.broken = broken;
            }
            // soft glow cone under the lamp
            Draw(Cell(ceilingPos), mShaftWarm, Matrix4x4.identity, b => b.Cylinder(ceilingPos + Vector3.down * 0.12f, ceilingPos + Vector3.down * 2.4f, 0.35f, 1.3f, 12, false));
        }

        static readonly Color Cool = new Color(0.82f, 0.9f, 1f), Warm = new Color(1f, 0.82f, 0.6f), Sickly = new Color(0.8f, 1f, 0.82f);

        static void BuildLights()
        {
            float cy = H - 0.02f;
            float[] corridor = { -32f, -24f, -16f, -8f, 0f, 8f, 16f, 23f };
            for (int i = 0; i < corridor.Length; i++)
            {
                float x = corridor[i];
                bool flick = x == -8f || x == 8f, broken = x == 16f, off = x == -24f;
                Lamp(new Vector3(x, cy, 0f), Cool, 1.5f, 5.5f, flick, broken, off);
            }
            Lamp(new Vector3(-19f, cy, 8f), Cool, 1.6f, 5.5f, false, false, true);       // class A
            Lamp(new Vector3(-19f, cy, 5f), Cool, 1.3f, 5f, true);
            Lamp(new Vector3(-9f, cy, 8.5f), Cool, 1.5f, 5.5f);                          // class B
            Lamp(new Vector3(-9f, cy, 4.5f), Cool, 1.2f, 5f, true);
            Lamp(new Vector3(0f, cy, 7f), Warm, 1.6f, 6f);                               // lounge
            Lamp(new Vector3(9f, cy, 8f), Cool, 1.5f, 5.5f);                             // class C
            Lamp(new Vector3(9f, cy, 4.5f), Cool, 1.2f, 5f, false, false, true);
            Lamp(new Vector3(19f, cy, 7f), Sickly, 1.4f, 6f, false, true);               // toilets
            Lamp(new Vector3(-30f, cy, -6f), Warm, 1.1f, 5.5f, true);                    // library
            Lamp(new Vector3(-19f, cy, -5.5f), Cool, 1.4f, 5f);                          // cafeteria
            Lamp(new Vector3(-19f, cy, -9.5f), Cool, 1.2f, 5f, true);
            Lamp(new Vector3(-2f, cy, -5.5f), Cool, 1.5f, 5.5f);                         // entrance
            Lamp(new Vector3(-2f, cy, -10.5f), Cool, 1.3f, 5.5f, true);
            Lamp(new Vector3(9f, GymH - 0.05f, -6f), Cool, 2.2f, 7f);                    // gym
            Lamp(new Vector3(14f, GymH - 0.05f, -11f), Cool, 2f, 7f, false, true);
            Lamp(new Vector3(19f, GymH - 0.05f, -6f), Cool, 2f, 7f, false, false, true);
            Lamp(new Vector3(31f, cy, 0f), Cool, 1.6f, 6.5f, true);                      // garage
            // bare bulbs
            Bulb(new Vector3(-11f, 2.9f, -9.5f), Warm, 1.1f, 5f, true);                  // janitor
            Bulb(new Vector3(21f, 2.75f, -13.5f), Warm, 0.9f, 4.5f, false);              // gym storage
            Bulb(new Vector3(-8f, -0.6f, -7.5f), Warm, 1.2f, 6f, true);                  // basement
            Bulb(new Vector3(2f, -0.6f, -9f), Warm, 0.9f, 5f, false);                    // boiler room
            Bulb(new Vector3(-9f, 2.85f, 13.5f), Warm, 1.2f, 4f, false);                 // secret room
            PointLight(null, new Vector3(1f, BY + 0.7f, -10.6f), new Color(1f, 0.45f, 0.15f), 1.8f, 5f, "BoilerGlow");
            // office desk lamp
            PointLight(null, new Vector3(-30.5f, 1.25f, 6.6f), new Color(1f, 0.72f, 0.45f), 1.3f, 4.5f, "DeskLamp");
        }

        static void Bulb(Vector3 pos, Color color, float intensity, float range, bool flicker)
        {
            GameObject go = Obj("Bulb", lightRoot, pos, Quaternion.identity);
            Part(go.transform, "Cord", mMetalDark, b => b.Cylinder(new Vector3(0f, 0.05f, 0f), new Vector3(0f, 0.35f, 0f), 0.006f, 0.006f, 5, false));
            MeshRenderer glass = Part(go.transform, "Glass", mLampTube, b => b.Sphere(Vector3.zero, new Vector3(0.05f, 0.065f, 0.05f), 10, 8));
            Light l = PointLight(go.transform, pos + Vector3.down * 0.1f, color, intensity, range);
            if (flicker)
            {
                FlickerLight f = go.AddComponent<FlickerLight>();
                f.lamp = l;
                f.tube = glass;
            }
        }

        // ------------------------------------------------------------------ windows + moonlight
        static void BuildWindows()
        {
            // north wall (z = 12), looking in = -Z
            foreach (float x in new[] { -21f, -17f, -12f, -6f, 0f, 7f, 11f }) Window(new Vector3(x, 1.7f, 12f), 0f, 1.6f, 1.4f, x == -21f || x == 7f || x == -6f);
            Window(new Vector3(19f, 2.25f, 12f), 0f, 1.2f, 0.7f, false);
            Window(new Vector3(-30f, 1.7f, 10f), 0f, 1.6f, 1.4f, true);
            // south walls, looking in = +Z
            foreach (float x in new[] { -21f, -17f }) Window(new Vector3(x, 1.7f, -12f), 180f, 1.6f, 1.4f, x == -21f);
            Window(new Vector3(-30f, 1.7f, -10f), 180f, 1.6f, 1.4f, true);
            foreach (float x in new[] { 8f, 14f, 20f }) Window(new Vector3(x, 3.25f, -16f), 180f, 2.4f, 1.3f, x != 20f);
            // west wall (x = -36), looking in = +X
            foreach (float z in new[] { -6f, 0f, 6f }) Window(new Vector3(-36f, 1.7f, z), -90f, 1.6f, 1.4f, z == 0f);
            Window(new Vector3(24f, 3.25f, -9f), 90f, 2.4f, 1.3f, true);
        }

        /// <summary>yaw: 0 = window in a wall facing -Z inside (north wall), 180 = south wall, -90 = west wall, 90 = east wall.</summary>
        static void Window(Vector3 c, float yaw, float w, float h, bool moon)
        {
            Quaternion r = Quaternion.Euler(0f, yaw, 0f);
            Vector3 inward = r * Vector3.back;
            Vector3 right = r * Vector3.right;
            string g = Cell(c + inward * 0.5f);
            // glass (faces into the room), a little behind the wall centre
            Draw(g, mWindow, Matrix4x4.TRS(c - inward * 0.02f, r, Vector3.one), b => b.Panel(Vector3.zero, new Vector3(w, h, 0.01f)));
            // frame + cross bars
            Draw(g, mWood, Matrix4x4.TRS(c, r, Vector3.one), b =>
            {
                b.Box(new Vector3(0f, h * 0.5f + 0.03f, -0.02f), new Vector3(w + 0.12f, 0.06f, 0.14f));
                b.Box(new Vector3(0f, -h * 0.5f - 0.03f, -0.06f), new Vector3(w + 0.16f, 0.06f, 0.26f));
                b.Box(new Vector3(-w * 0.5f - 0.03f, 0f, -0.02f), new Vector3(0.06f, h, 0.14f));
                b.Box(new Vector3(w * 0.5f + 0.03f, 0f, -0.02f), new Vector3(0.06f, h, 0.14f));
                b.Box(new Vector3(0f, 0f, -0.03f), new Vector3(0.04f, h, 0.05f));
                b.Box(new Vector3(0f, h * 0.15f, -0.03f), new Vector3(w, 0.04f, 0.05f));
            });
            if (!moon) return;
            Vector3 dir = (inward * 1f + Vector3.down * 0.8f).normalized;
            SpotLight(null, c + inward * 0.3f, Quaternion.LookRotation(dir), new Color(0.55f, 0.68f, 1f), 1.6f, 9f, 75f);
            // light shaft: frustum from the window into the room
            Vector3 far = dir * 4.2f;
            Draw(g, mShaft, Matrix4x4.identity, b =>
            {
                Vector3 hx = right * w * 0.5f, hy = Vector3.up * h * 0.5f;
                Vector3[] near = { c - hx - hy, c + hx - hy, c + hx + hy, c - hx + hy };
                float grow = 1.35f;
                Vector3[] fr = { c + far + (-hx - hy) * grow, c + far + (hx - hy) * grow, c + far + (hx + hy) * grow, c + far + (-hx + hy) * grow };
                for (int i = 0; i < 4; i++)
                {
                    int j = (i + 1) % 4;
                    Vector3 mid = (near[i] + near[j] + fr[i] + fr[j]) * 0.25f;
                    Vector3 nrm = (mid - (c + far * 0.5f)).normalized;
                    b.Quad(near[i], near[j], fr[j], fr[i], nrm, new Vector2(0, 0), new Vector2(1, 0), new Vector2(1, 1), new Vector2(0, 1), Color.white);
                }
            });
        }
    }
}

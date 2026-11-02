using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;
using UnityEngine.AI;
using UnityEngine.Rendering;

namespace NightClass.EditorTools
{
    /// <summary>
    /// The teacher: a gaunt old woman in a long dark dress, grey bun, cracked round glasses and a
    /// wooden ruler. Built as a jointed hierarchy that TeacherRig animates procedurally. The lower
    /// face is a separate jaw so she can open her mouth wide for the jumpscare.
    /// </summary>
    public static partial class NCWorld
    {
        static Material tSkin, tFace, tDress, tCollar, tHair, tEye, tPupil, tShoe, tStocking, tTeeth, tMouth, tLensCrack, tLensClean;

        static void TeacherMaterials()
        {
            tFace = NCMats.Picture("teacher_face", "face", new Color(0.92f, 0.88f, 0.85f), 0.32f);
            tSkin = NCMats.Lit("teacher_skin", null, new Color(0.66f, 0.58f, 0.54f), 0.3f);
            tDress = NCMats.Lit("teacher_dress", "fabric", new Color(0.16f, 0.15f, 0.17f), 0.12f, 0f, 3f);
            tCollar = NCMats.Lit("teacher_collar", "fabric", new Color(0.78f, 0.75f, 0.68f), 0.2f, 0f, 6f);
            tHair = NCMats.Lit("teacher_hair", null, new Color(0.56f, 0.56f, 0.55f), 0.42f);
            tEye = NCMats.Lit("teacher_eye", null, new Color(0.78f, 0.74f, 0.62f), 0.85f, 0f, 1f, new Color(0.28f, 0.05f, 0.03f));
            tPupil = NCMats.Lit("teacher_pupil", null, new Color(0.01f, 0.01f, 0.01f), 0.9f);
            tShoe = NCMats.Lit("teacher_shoe", null, new Color(0.03f, 0.025f, 0.02f), 0.65f);
            tStocking = NCMats.Lit("teacher_stocking", null, new Color(0.07f, 0.065f, 0.07f), 0.3f);
            tTeeth = NCMats.Lit("teacher_teeth", null, new Color(0.72f, 0.66f, 0.48f), 0.55f);
            tMouth = NCMats.Lit("teacher_mouth", null, new Color(0.1f, 0.015f, 0.015f), 0.5f);
            tLensCrack = Lens("teacher_lens_crack", "lens_crack");
            tLensClean = Lens("teacher_lens_clean", "lens_clean");
        }

        static Material Lens(string key, string file)
        {
            Material m = NCMats.Picture(key, file, new Color(1f, 1f, 1f, 1f), 0.92f);
            m.SetFloat("_Surface", 1f);
            m.SetFloat("_Blend", 0f);
            m.SetFloat("_SrcBlend", (float)BlendMode.SrcAlpha);
            m.SetFloat("_DstBlend", (float)BlendMode.OneMinusSrcAlpha);
            m.SetFloat("_SrcBlendAlpha", (float)BlendMode.One);
            m.SetFloat("_DstBlendAlpha", (float)BlendMode.OneMinusSrcAlpha);
            m.SetFloat("_ZWrite", 0f);
            m.SetOverrideTag("RenderType", "Transparent");
            m.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
            m.renderQueue = (int)RenderQueue.Transparent;
            EditorUtility.SetDirty(m);
            return m;
        }

        // ------------------------------------------------------------------ face shape
        const float MouthLat = -0.4668f;           // asin(-0.45): the line between the lips
        const float JawLon = 35f * Mathf.Deg2Rad;  // the jaw piece spans +-35 degrees around the front

        static float G2(float x, float y, float sx, float sy) { x /= sx; y /= sy; return Mathf.Exp(-(x * x + y * y)); }

        /// <summary>Radial displacement of the head ellipsoid: a gaunt old face.</summary>
        static float FaceShape(Vector3 d)
        {
            float front = Mathf.Clamp01(d.z * 2.2f);
            if (front <= 0f) return 1f;
            float k = 0f;
            k += 0.2f * G2(d.x, 0f, 0.1f, 1f) * G2(0f, d.y + 0.1f, 1f, 0.17f);          // long nose
            k += 0.05f * G2(d.x, d.y + 0.17f, 0.07f, 0.05f);                           // nose tip
            k -= 0.095f * (G2(d.x - 0.36f, d.y - 0.14f, 0.15f, 0.1f) + G2(d.x + 0.36f, d.y - 0.14f, 0.15f, 0.1f));  // sunken eyes
            k += 0.035f * G2(0f, d.y - 0.3f, 1f, 0.07f) * Mathf.Clamp01(1.2f - Mathf.Abs(d.x) * 1.6f);              // brow ridge
            k += 0.045f * (G2(d.x - 0.5f, d.y, 0.14f, 0.1f) + G2(d.x + 0.5f, d.y, 0.14f, 0.1f));                    // cheekbones
            k -= 0.085f * (G2(d.x - 0.52f, d.y + 0.3f, 0.18f, 0.16f) + G2(d.x + 0.52f, d.y + 0.3f, 0.18f, 0.16f));  // hollow cheeks
            k -= 0.05f * (G2(d.x - 0.74f, d.y - 0.35f, 0.12f, 0.15f) + G2(d.x + 0.74f, d.y - 0.35f, 0.12f, 0.15f)); // temples
            k -= 0.03f * G2(d.x, d.y + 0.45f, 0.26f, 0.025f);                          // lip line
            k += 0.025f * G2(d.x, d.y + 0.39f, 0.2f, 0.035f);                          // thin upper lip
            k += 0.07f * G2(d.x, d.y + 0.8f, 0.24f, 0.15f);                            // pointed chin
            return 1f + k * front;
        }

        static Vector3 SphereDir(float lat, float lon)
        {
            return new Vector3(Mathf.Cos(lat) * Mathf.Sin(lon), Mathf.Sin(lat), Mathf.Cos(lat) * Mathf.Cos(lon));
        }

        /// <summary>A lat/lon patch of the displaced head, with finite-difference normals and front-projected UVs.</summary>
        static void FacePatch(MeshBuilder b, Vector3 center, Vector3 radii, float lat0, float lat1, float lon0, float lon1, int rings, int segs, Vector3 offset)
        {
            Func<float, float, Vector3> P = (la, lo) => { Vector3 dd = SphereDir(la, lo); return center + Vector3.Scale(dd, radii) * FaceShape(dd); };
            const float e = 0.004f;
            int start = b.v.Count;
            for (int r = 0; r <= rings; r++)
            {
                float lat = Mathf.Lerp(lat0, lat1, r / (float)rings);
                for (int s = 0; s <= segs; s++)
                {
                    float lon = Mathf.Lerp(lon0, lon1, s / (float)segs);
                    Vector3 d = SphereDir(lat, lon);
                    Vector3 p = P(lat, lon);
                    Vector3 tLon = P(lat, lon + e) - P(lat, lon - e);
                    Vector3 tLat = P(lat + e, lon) - P(lat - e, lon);
                    Vector3 nn = Vector3.Cross(tLon, tLat);
                    if (nn.sqrMagnitude < 1e-12f || Mathf.Abs(lat) > 1.55f)
                        nn = Vector3.Scale(d, new Vector3(1f / radii.x, 1f / radii.y, 1f / radii.z));
                    b.v.Add(p - offset);
                    b.n.Add(nn.normalized);
                    b.uv.Add(new Vector2(0.5f + d.x * 0.5f, 0.5f + d.y * 0.5f));
                    b.col.Add(Color.white);
                }
            }
            int row = segs + 1;
            for (int r = 0; r < rings; r++)
                for (int s = 0; s < segs; s++)
                {
                    int a = start + r * row + s, c = a + row;
                    b.t.Add(a); b.t.Add(a + 1); b.t.Add(c);
                    b.t.Add(a + 1); b.t.Add(c + 1); b.t.Add(c);
                }
        }

        /// <summary>Flared skirt with soft vertical folds (smooth normals).</summary>
        static void Flare(MeshBuilder b, Vector3 top, float rTop, float rBot, float len, float zScale, int segs, int rings, float folds, float foldAmp)
        {
            int start = b.v.Count;
            for (int r = 0; r <= rings; r++)
            {
                float t = r / (float)rings;
                float rad = Mathf.Lerp(rTop, rBot, Mathf.Pow(t, 0.75f));
                for (int s = 0; s <= segs; s++)
                {
                    float a = s / (float)segs * Mathf.PI * 2f;
                    float fold = 1f + foldAmp * t * Mathf.Sin(a * folds) + foldAmp * 0.4f * t * Mathf.Sin(a * folds * 2.3f + 1f);
                    Vector3 d = new Vector3(Mathf.Sin(a), 0f, Mathf.Cos(a) * zScale);
                    b.v.Add(top + new Vector3(d.x * rad * fold, -len * t, d.z * rad * fold));
                    float dFold = foldAmp * t * folds * Mathf.Cos(a * folds);
                    Vector3 tangent = new Vector3(Mathf.Cos(a), 0f, -Mathf.Sin(a) * zScale) * fold + d * dFold;
                    Vector3 nn = Vector3.Cross(tangent, Vector3.up).normalized;
                    nn.y = (rBot - rTop) / len * 0.6f;
                    b.n.Add(nn.normalized);
                    b.uv.Add(new Vector2(s / (float)segs * 2.2f, -len * t * 3f));
                    b.col.Add(Color.white);
                }
            }
            int row = segs + 1;
            for (int r = 0; r < rings; r++)
                for (int s = 0; s < segs; s++)
                {
                    int i0 = start + r * row + s, i1 = i0 + row;
                    Vector3 wn = Vector3.Cross(b.v[i0 + 1] - b.v[i0], b.v[i1] - b.v[i0]);
                    if (Vector3.Dot(wn, b.n[i0]) >= 0f) { b.t.Add(i0); b.t.Add(i0 + 1); b.t.Add(i1); b.t.Add(i0 + 1); b.t.Add(i1 + 1); b.t.Add(i1); }
                    else { b.t.Add(i0); b.t.Add(i1); b.t.Add(i0 + 1); b.t.Add(i0 + 1); b.t.Add(i1); b.t.Add(i1 + 1); }
                }
        }

        static void Ellipse(MeshBuilder b, Vector3 center, Vector3 radii, int seg = 14, int rings = 10) { b.Sphere(center, radii, seg, rings); }

        static void Scaled(MeshBuilder b, Vector3 pos, Quaternion rot, Vector3 scale, Action<MeshBuilder> draw)
        {
            b.m = Matrix4x4.TRS(pos, rot, scale);
            draw(b);
            b.m = Matrix4x4.identity;
        }

        // ------------------------------------------------------------------ body parts
        static Transform Joint(Transform parent, string name, Vector3 localPos)
        {
            Transform t = Child(parent, name);
            t.localPosition = localPos;
            t.gameObject.layer = LayerTeacher;
            return t;
        }

        static void Arm(Transform chest, bool left, out Transform shoulder, out Transform elbow, out Transform hand, List<Renderer> rends)
        {
            float sx = left ? -1f : 1f;
            shoulder = Joint(chest, left ? "ShoulderL" : "ShoulderR", new Vector3(0.17f * sx, 0.19f, -0.005f));
            rends.Add(Part(shoulder, "Sleeve", tDress, b =>
            {
                Ellipse(b, new Vector3(0f, -0.015f, 0f), new Vector3(0.058f, 0.055f, 0.058f));
                b.Cylinder(new Vector3(0f, -0.02f, 0f), new Vector3(0f, -0.29f, 0f), 0.046f, 0.036f, 12);
            }));
            elbow = Joint(shoulder, "Elbow", new Vector3(0f, -0.29f, 0f));
            rends.Add(Part(elbow, "Forearm", tDress, b =>
            {
                Ellipse(b, Vector3.zero, new Vector3(0.037f, 0.037f, 0.037f), 10, 8);
                b.Cylinder(Vector3.zero, new Vector3(0f, -0.22f, 0f), 0.036f, 0.03f, 12);
            }));
            rends.Add(Part(elbow, "Cuff", tCollar, b => b.Cylinder(new Vector3(0f, -0.2f, 0f), new Vector3(0f, -0.25f, 0f), 0.033f, 0.036f, 12)));
            hand = Joint(elbow, "Hand", new Vector3(0f, -0.262f, 0f));
            rends.Add(Part(hand, "Skin", tSkin, b =>
            {
                b.Cylinder(new Vector3(0f, 0.015f, 0f), new Vector3(0f, -0.015f, 0f), 0.02f, 0.021f, 10);
                b.m = Matrix4x4.TRS(new Vector3(0f, -0.05f, 0.002f), Quaternion.identity, Vector3.one);
                b.Box(Vector3.zero, new Vector3(0.052f, 0.075f, 0.022f));
                b.m = Matrix4x4.identity;
                // long bony fingers, curled a little
                for (int f = 0; f < 4; f++)
                {
                    float fx = (-0.019f + f * 0.0127f) * sx;
                    float flen = f == 1 || f == 2 ? 0.085f : 0.072f;
                    Vector3 k0 = new Vector3(fx, -0.086f, 0.002f);
                    Vector3 k1 = k0 + new Vector3(0f, -flen * 0.55f, 0.012f);
                    Vector3 k2 = k1 + new Vector3(0f, -flen * 0.45f, 0.022f);
                    b.Cylinder(k0, k1, 0.0068f, 0.0058f, 6);
                    b.Cylinder(k1, k2, 0.0058f, 0.0045f, 6);
                    Ellipse(b, k1, new Vector3(0.0068f, 0.0068f, 0.0068f), 6, 4);
                }
                b.Cylinder(new Vector3(0.024f * sx, -0.035f, 0.01f), new Vector3(0.03f * sx, -0.075f, 0.03f), 0.008f, 0.006f, 6);
            }));
        }

        static void Leg(Transform hips, bool left, out Transform leg, out Transform shin, out Transform foot, List<Renderer> rends)
        {
            float sx = left ? -1f : 1f;
            leg = Joint(hips, left ? "LegL" : "LegR", new Vector3(0.085f * sx, -0.06f, 0f));
            rends.Add(Part(leg, "Thigh", tStocking, b => b.Cylinder(Vector3.zero, new Vector3(0f, -0.43f, 0f), 0.068f, 0.05f, 10)));
            shin = Joint(leg, "Shin", new Vector3(0f, -0.43f, 0f));
            rends.Add(Part(shin, "Calf", tStocking, b =>
            {
                Ellipse(b, Vector3.zero, new Vector3(0.05f, 0.05f, 0.05f), 8, 6);
                b.Cylinder(Vector3.zero, new Vector3(0f, -0.4f, 0f), 0.047f, 0.028f, 10);
            }));
            foot = Joint(shin, "Foot", new Vector3(0f, -0.4f, 0f));
            rends.Add(Part(foot, "Shoe", tShoe, b =>
            {
                b.Box(new Vector3(0f, -0.045f, 0.045f), new Vector3(0.074f, 0.07f, 0.17f));
                b.Cylinder(new Vector3(0f, -0.05f, 0.125f), new Vector3(0f, -0.065f, 0.2f), 0.036f, 0.01f, 10);
                b.Box(new Vector3(0f, -0.065f, -0.03f), new Vector3(0.05f, 0.05f, 0.045f));
                b.Cylinder(new Vector3(0f, 0.02f, 0f), new Vector3(0f, -0.03f, 0f), 0.032f, 0.036f, 10);
            }));
        }

        // ------------------------------------------------------------------ the teacher
        static void BuildTeacher()
        {
            TeacherMaterials();
            if (BuildRocketboxTeacher()) return;
            Vector3 spawnPos = teacherSpawn != null ? teacherSpawn.position : new Vector3(0.5f, 0f, 8.5f);
            var go = new GameObject("Teacher");
            go.transform.position = spawnPos;
            go.transform.rotation = Quaternion.Euler(0f, 180f, 0f);
            go.layer = LayerTeacher;
            var rends = new List<Renderer>();

            Transform body = Joint(go.transform, "Body", Vector3.zero);
            Transform hips = Joint(body, "Hips", new Vector3(0f, 0.98f, 0f));
            rends.Add(Part(hips, "Pelvis", tDress, b => Ellipse(b, new Vector3(0f, 0.02f, 0f), new Vector3(0.168f, 0.12f, 0.13f))));
            Transform skirt = Joint(hips, "Skirt", new Vector3(0f, 0.04f, 0f));
            rends.Add(Part(skirt, "Dress", tDress, b => Flare(b, Vector3.zero, 0.158f, 0.31f, 0.9f, 0.82f, 40, 12, 9f, 0.07f)));
            rends.Add(Part(skirt, "Hem", tShoe, b =>
            {
                b.m = Matrix4x4.TRS(new Vector3(0f, -0.885f, 0f), Quaternion.identity, new Vector3(1f, 1f, 0.82f));
                b.Cylinder(Vector3.zero, new Vector3(0f, -0.018f, 0f), 0.322f, 0.324f, 40, false);
                b.m = Matrix4x4.identity;
            }));

            Transform legL, shinL, footL, legR, shinR, footR;
            Leg(hips, true, out legL, out shinL, out footL, rends);
            Leg(hips, false, out legR, out shinR, out footR, rends);

            Transform spine = Joint(hips, "Spine", new Vector3(0f, 0.1f, 0f));
            rends.Add(Part(spine, "Waist", tDress, b => Scaled(b, Vector3.zero, Quaternion.identity, new Vector3(1f, 1f, 0.72f),
                bb => bb.Cylinder(new Vector3(0f, -0.07f, 0f), new Vector3(0f, 0.22f, 0f), 0.122f, 0.138f, 18))));
            rends.Add(Part(spine, "Belt", tShoe, b => Scaled(b, Vector3.zero, Quaternion.identity, new Vector3(1f, 1f, 0.72f),
                bb => bb.Cylinder(new Vector3(0f, -0.005f, 0f), new Vector3(0f, 0.035f, 0f), 0.127f, 0.128f, 18))));
            Transform chest = Joint(spine, "Chest", new Vector3(0f, 0.22f, 0f));
            rends.Add(Part(chest, "Torso", tDress, b =>
            {
                Ellipse(b, new Vector3(0f, 0.08f, 0f), new Vector3(0.158f, 0.17f, 0.108f), 18, 12);
                Ellipse(b, new Vector3(0f, 0.17f, -0.01f), new Vector3(0.19f, 0.06f, 0.09f), 16, 8);   // shoulder line
            }));
            rends.Add(Part(chest, "Collar", tCollar, b =>
            {
                b.Cylinder(new Vector3(0f, 0.19f, 0f), new Vector3(0f, 0.275f, 0f), 0.06f, 0.05f, 16);
                b.Torus(new Vector3(0f, 0.2f, 0f), Vector3.up, 0.07f, 0.012f, 18, 5);
            }));
            rends.Add(Part(chest, "Buttons", mBrass, b =>
            {
                for (int i = 0; i < 6; i++)
                {
                    float y = 0.17f - i * 0.045f;
                    float dy = (y - 0.08f) / 0.17f;
                    float z = 0.108f * Mathf.Sqrt(Mathf.Max(0f, 1f - dy * dy)) + 0.003f;
                    Ellipse(b, new Vector3(0f, y, z), new Vector3(0.007f, 0.007f, 0.004f), 8, 5);
                }
                Ellipse(b, new Vector3(0f, 0.21f, 0.062f), new Vector3(0.013f, 0.016f, 0.006f), 10, 6);   // brooch
            }));

            Transform neck = Joint(chest, "Neck", new Vector3(0f, 0.2f, 0f));
            rends.Add(Part(neck, "Neck", tSkin, b => b.Cylinder(Vector3.zero, new Vector3(0f, 0.115f, 0.006f), 0.034f, 0.03f, 12)));
            Transform head = Joint(neck, "Head", new Vector3(0f, 0.1f, 0.006f));

            // face: upper head + sides on the head, the chin piece on the jaw
            Vector3 fc = new Vector3(0f, 0.075f, 0.01f), fr = new Vector3(0.08f, 0.112f, 0.097f);
            Vector3 jawPivot = new Vector3(0f, 0.045f, -0.01f);
            rends.Add(Part(head, "Face", tFace, b =>
            {
                FacePatch(b, fc, fr, MouthLat, Mathf.PI * 0.5f, 0f, Mathf.PI * 2f, 18, 36, Vector3.zero);
                FacePatch(b, fc, fr, -Mathf.PI * 0.5f, MouthLat, JawLon, Mathf.PI * 2f - JawLon, 8, 30, Vector3.zero);
            }));
            Transform jaw = Joint(head, "Jaw", jawPivot);
            rends.Add(Part(jaw, "Chin", tFace, b => FacePatch(b, fc, fr, -Mathf.PI * 0.5f, MouthLat, -JawLon, JawLon, 8, 8, jawPivot)));
            rends.Add(Part(head, "MouthInside", tMouth, b => Ellipse(b, new Vector3(0f, 0.022f, 0.045f), new Vector3(0.042f, 0.034f, 0.045f), 12, 8)));
            rends.Add(Part(head, "TeethTop", tTeeth, b =>
            {
                for (int i = 0; i < 7; i++)
                {
                    float a = (i - 3) * 0.2f;
                    b.Box(new Vector3(Mathf.Sin(a) * 0.026f, 0.021f, 0.062f + Mathf.Cos(a) * 0.024f), new Vector3(0.0062f, 0.009f, 0.004f));
                }
            }));
            rends.Add(Part(jaw, "TeethBottom", tTeeth, b =>
            {
                for (int i = 0; i < 6; i++)
                {
                    float a = (i - 2.5f) * 0.2f;
                    b.Box(new Vector3(Mathf.Sin(a) * 0.024f, 0.015f - jawPivot.y, 0.058f + Mathf.Cos(a) * 0.022f - jawPivot.z), new Vector3(0.0058f, 0.008f, 0.004f));
                }
            }));

            // hair pulled back into a tight bun
            rends.Add(Part(head, "Hair", tHair, b =>
            {
                b.Sphere(new Vector3(0f, 0.095f, -0.013f), new Vector3(0.0875f, 0.104f, 0.098f), 24, 16,
                    d => d.y < 0.05f && d.z > -0.3f ? 1f - 0.3f * Mathf.Clamp01((0.05f - d.y) * 2.2f) * Mathf.Clamp01((d.z + 0.3f) * 1.5f) : 1f);
                b.Sphere(new Vector3(0f, 0.148f, -0.098f), new Vector3(0.052f, 0.048f, 0.046f), 14, 10, d => 1f + 0.05f * Mathf.Sin(d.x * 18f + d.y * 9f));
                b.Torus(new Vector3(0f, 0.148f, -0.098f), new Vector3(0f, 0.35f, -1f), 0.04f, 0.012f, 14, 5);
            }));
            rends.Add(Part(head, "HairPins", mMetalDark, b =>
            {
                b.Cylinder(new Vector3(-0.05f, 0.17f, -0.09f), new Vector3(0.04f, 0.19f, -0.12f), 0.0025f, 0.0025f, 4, false);
                b.Cylinder(new Vector3(-0.04f, 0.12f, -0.12f), new Vector3(0.05f, 0.15f, -0.09f), 0.0025f, 0.0025f, 4, false);
            }));

            // sunken pale eyes
            Vector3 eyeL = new Vector3(-0.0272f, 0.0893f, 0.084f), eyeR = new Vector3(0.0272f, 0.0893f, 0.084f);
            rends.Add(Part(head, "Eyes", tEye, b => { Ellipse(b, eyeL, Vector3.one * 0.0122f, 12, 8); Ellipse(b, eyeR, Vector3.one * 0.0122f, 12, 8); }));
            rends.Add(Part(head, "Pupils", tPupil, b =>
            {
                Ellipse(b, eyeL + new Vector3(0.001f, 0f, 0.011f), new Vector3(0.0042f, 0.0042f, 0.0022f), 8, 6);
                Ellipse(b, eyeR + new Vector3(-0.001f, 0f, 0.011f), new Vector3(0.0042f, 0.0042f, 0.0022f), 8, 6);
            }));

            // round glasses, one lens cracked
            Vector3 lensL = new Vector3(-0.031f, 0.09f, 0.112f), lensR = new Vector3(0.031f, 0.09f, 0.112f);
            Part(head, "GlassesFrame", mMetalDark, b =>
            {
                b.Torus(lensL, Vector3.forward, 0.021f, 0.0022f, 18, 5);
                b.Torus(lensR, Vector3.forward, 0.021f, 0.0022f, 18, 5);
                b.Cylinder(new Vector3(-0.0105f, 0.093f, 0.118f), new Vector3(0.0105f, 0.093f, 0.118f), 0.0018f, 0.0018f, 5, false);
                b.Cylinder(new Vector3(-0.052f, 0.09f, 0.111f), new Vector3(-0.083f, 0.088f, 0.0f), 0.0016f, 0.0016f, 5, false);
                b.Cylinder(new Vector3(0.052f, 0.09f, 0.111f), new Vector3(0.083f, 0.088f, 0.0f), 0.0016f, 0.0016f, 5, false);
            });
            Part(head, "LensL", tLensCrack, b => Scaled(b, lensL, Quaternion.Euler(0f, 180f, 0f), Vector3.one, bb => bb.Panel(Vector3.zero, new Vector3(0.042f, 0.042f, 0.001f))));
            Part(head, "LensR", tLensClean, b => Scaled(b, lensR, Quaternion.Euler(0f, 180f, 0f), Vector3.one, bb => bb.Panel(Vector3.zero, new Vector3(0.042f, 0.042f, 0.001f))));

            Transform shL, elL, haL, shR, elR, haR;
            Arm(chest, true, out shL, out elL, out haL, rends);
            Arm(chest, false, out shR, out elR, out haR, rends);
            // the wooden ruler in her right hand
            Part(haR, "Ruler", mRuler, b =>
            {
                Vector3 dir = new Vector3(0f, -Mathf.Cos(50f * Mathf.Deg2Rad), Mathf.Sin(50f * Mathf.Deg2Rad));
                Vector3 grip = new Vector3(0f, -0.075f, 0.018f);
                Scaled(b, grip + dir * 0.27f, Quaternion.Euler(-50f, 0f, 0f), Vector3.one, bb => bb.Box(Vector3.zero, new Vector3(0.036f, 0.6f, 0.006f)));
            });
            Part(haR, "RulerMarks", mMetalDark, b =>
            {
                Vector3 dir = new Vector3(0f, -Mathf.Cos(50f * Mathf.Deg2Rad), Mathf.Sin(50f * Mathf.Deg2Rad));
                Vector3 grip = new Vector3(0f, -0.075f, 0.018f);
                for (int i = 0; i < 20; i++)
                {
                    Vector3 c = grip + dir * (0.03f + i * 0.027f);
                    float len = i % 5 == 0 ? 0.014f : 0.007f;
                    Scaled(b, c, Quaternion.Euler(-50f, 0f, 0f), Vector3.one, bb => bb.Box(new Vector3(0.018f - len * 0.5f, 0f, -0.0032f), new Vector3(len, 0.0012f, 0.0006f)));
                }
            });

            // rig
            TeacherRig rig = go.AddComponent<TeacherRig>();
            rig.hips = hips; rig.spine = spine; rig.chest = chest; rig.neck = neck; rig.head = head; rig.jaw = jaw; rig.skirt = skirt;
            rig.legL = legL; rig.shinL = shinL; rig.footL = footL; rig.legR = legR; rig.shinR = shinR; rig.footR = footR;
            rig.shoulderL = shL; rig.elbowL = elL; rig.handL = haL; rig.shoulderR = shR; rig.elbowR = elR; rig.handR = haR;
            rig.tintable = rends.ToArray();
            var glowGo = new GameObject("EyeGlow");
            glowGo.transform.SetParent(head, false);
            glowGo.transform.localPosition = new Vector3(0f, 0.09f, 0.16f);
            Light glow = glowGo.AddComponent<Light>();
            glow.type = LightType.Point; glow.color = new Color(1f, 0.16f, 0.08f); glow.range = 0.9f; glow.intensity = 0.15f; glow.shadows = LightShadows.None;
            rig.eyeGlow = glow;

            // AI + navigation
            NavMeshAgent agent = go.AddComponent<NavMeshAgent>();
            agent.radius = 0.3f;
            agent.height = 1.75f;
            agent.baseOffset = 0f;
            agent.speed = 1.45f;
            agent.angularSpeed = 420f;
            agent.acceleration = 9f;
            agent.stoppingDistance = 0.25f;
            agent.obstacleAvoidanceType = ObstacleAvoidanceType.LowQualityObstacleAvoidance;
            agent.enabled = false;   // TeacherAI enables it once the runtime navmesh exists
            var cap = go.AddComponent<CapsuleCollider>();
            cap.isTrigger = true;
            cap.radius = 0.35f;
            cap.height = 1.75f;
            cap.center = new Vector3(0f, 0.875f, 0f);
            var rb = go.AddComponent<Rigidbody>();
            rb.isKinematic = true;
            rb.useGravity = false;

            TeacherAI ai = go.AddComponent<TeacherAI>();
            ai.rig = rig;
            ai.spawn = teacherSpawn;
            ai.patrolPoints = patrol.ToArray();
            ai.eye = Point("Eye", Vector3.zero, 0f, 0f, head);
            ai.eye.localPosition = new Vector3(0f, 0.09f, 0.1f);
            ai.eye.localRotation = Quaternion.identity;
            // jumpscare camera: in front of her face, looking back at it (on the chest so the head jitter shows)
            Transform js = Child(chest, "JumpscareCam");
            js.localPosition = new Vector3(0f, 0.37f, 0.37f);
            js.localRotation = Quaternion.Euler(4f, 180f, 0f);
            ai.jumpscareCam = js;
            var flGo = new GameObject("FaceLight");
            flGo.transform.SetParent(js, false);
            flGo.transform.localPosition = new Vector3(0.05f, -0.16f, 0.02f);
            Light fl = flGo.AddComponent<Light>();
            fl.type = LightType.Point; fl.color = new Color(0.75f, 0.85f, 1f); fl.range = 1.1f; fl.intensity = 1.6f; fl.shadows = LightShadows.None;
            fl.enabled = false;
            ai.faceLight = fl;
            ai.burnFire = Fire(chest, new Vector3(0f, 0.05f, 0f), 0.9f, false);
            ai.burnSmoke = Smoke(head, new Vector3(0f, 0.25f, 0f), 0.8f, false);

            SetLayer(go, LayerTeacher);
            teacherAI = ai;
            Log("teacher built: " + rends.Count + " parts");
        }
    }
}

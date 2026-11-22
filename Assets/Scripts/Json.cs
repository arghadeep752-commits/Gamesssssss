using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;
using UnityEngine;

namespace Danga
{
    /// <summary>
    /// Small JSON reader for house_meta.json (objects become Dictionary&lt;string, object&gt;, arrays List&lt;object&gt;,
    /// numbers double, plus string, bool and null), with helpers that read the values the game needs.
    /// </summary>
    public static class Json
    {
        public static object Parse(string text)
        {
            int i = 0;
            object v = Value(text, ref i);
            return v;
        }

        static void Skip(string s, ref int i)
        {
            while (i < s.Length && char.IsWhiteSpace(s[i])) i++;
        }

        static object Value(string s, ref int i)
        {
            Skip(s, ref i);
            if (i >= s.Length) return null;
            char c = s[i];
            if (c == '{') return Obj(s, ref i);
            if (c == '[') return Arr(s, ref i);
            if (c == '"') return Str(s, ref i);
            if (c == 't' && string.CompareOrdinal(s, i, "true", 0, 4) == 0) { i += 4; return true; }
            if (c == 'f' && string.CompareOrdinal(s, i, "false", 0, 5) == 0) { i += 5; return false; }
            if (c == 'n' && string.CompareOrdinal(s, i, "null", 0, 4) == 0) { i += 4; return null; }
            return Num(s, ref i);
        }

        static Dictionary<string, object> Obj(string s, ref int i)
        {
            var d = new Dictionary<string, object>();
            i++;
            while (true)
            {
                Skip(s, ref i);
                if (i >= s.Length) break;
                if (s[i] == '}') { i++; break; }
                if (s[i] == ',') { i++; continue; }
                string k = Str(s, ref i);
                Skip(s, ref i);
                if (i < s.Length && s[i] == ':') i++;
                d[k] = Value(s, ref i);
            }
            return d;
        }

        static List<object> Arr(string s, ref int i)
        {
            var a = new List<object>();
            i++;
            while (true)
            {
                Skip(s, ref i);
                if (i >= s.Length) break;
                if (s[i] == ']') { i++; break; }
                if (s[i] == ',') { i++; continue; }
                a.Add(Value(s, ref i));
            }
            return a;
        }

        static string Str(string s, ref int i)
        {
            var sb = new StringBuilder();
            i++;
            while (i < s.Length)
            {
                char c = s[i++];
                if (c == '"') break;
                if (c == '\\' && i < s.Length)
                {
                    char e = s[i++];
                    switch (e)
                    {
                        case 'n': sb.Append('\n'); break;
                        case 't': sb.Append('\t'); break;
                        case 'r': sb.Append('\r'); break;
                        case 'b': sb.Append('\b'); break;
                        case 'f': sb.Append('\f'); break;
                        case 'u':
                            if (i + 4 <= s.Length)
                            {
                                sb.Append((char)Convert.ToInt32(s.Substring(i, 4), 16));
                                i += 4;
                            }
                            break;
                        default: sb.Append(e); break;
                    }
                }
                else sb.Append(c);
            }
            return sb.ToString();
        }

        static object Num(string s, ref int i)
        {
            int st = i;
            while (i < s.Length && "+-0123456789.eE".IndexOf(s[i]) >= 0) i++;
            double d;
            double.TryParse(s.Substring(st, i - st), NumberStyles.Float, CultureInfo.InvariantCulture, out d);
            return d;
        }

        // ------------------------------------------------------------------ helpers
        public static Dictionary<string, object> O(object o, string key)
        {
            var d = o as Dictionary<string, object>;
            object v;
            if (d != null && d.TryGetValue(key, out v)) return v as Dictionary<string, object>;
            return null;
        }

        public static List<object> A(object o, string key)
        {
            var d = o as Dictionary<string, object>;
            object v;
            if (d != null && d.TryGetValue(key, out v)) return v as List<object>;
            return null;
        }

        public static object Get(object o, string key)
        {
            var d = o as Dictionary<string, object>;
            object v;
            if (d != null && d.TryGetValue(key, out v)) return v;
            return null;
        }

        public static bool Has(object o, string key)
        {
            var d = o as Dictionary<string, object>;
            return d != null && d.ContainsKey(key);
        }

        public static float F(object v, float fallback = 0f)
        {
            if (v is double) return (float)(double)v;
            if (v is bool) return (bool)v ? 1f : 0f;
            if (v is string)
            {
                float f;
                if (float.TryParse((string)v, NumberStyles.Float, CultureInfo.InvariantCulture, out f)) return f;
            }
            return fallback;
        }

        public static float F(object o, string key, float fallback = 0f)
        {
            return F(Get(o, key), fallback);
        }

        public static int I(object o, string key, int fallback = 0)
        {
            object v = Get(o, key);
            return v is double ? (int)Math.Round((double)v) : fallback;
        }

        public static string S(object o, string key, string fallback = "")
        {
            object v = Get(o, key);
            if (v == null) return fallback;
            if (v is string) return (string)v;
            if (v is bool) return (bool)v ? "true" : "false";
            if (v is double) return ((double)v).ToString(CultureInfo.InvariantCulture);
            return fallback;
        }

        /// <summary>A [x, y, z] array (house_meta.json is written in Unity space already).</summary>
        public static Vector3 V3(object arr)
        {
            var a = arr as List<object>;
            if (a == null || a.Count < 3) return Vector3.zero;
            return new Vector3(F(a[0]), F(a[1]), F(a[2]));
        }

        public static Vector3 V3(object o, string key)
        {
            return V3(Get(o, key));
        }

        public static float At(object arr, int i, float fallback = 0f)
        {
            var a = arr as List<object>;
            return a != null && i < a.Count ? F(a[i], fallback) : fallback;
        }
    }
}

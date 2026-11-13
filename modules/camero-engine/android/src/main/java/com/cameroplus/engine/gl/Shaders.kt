package com.cameroplus.engine.gl

/**
 * The single grading shader used everywhere (live camera, editor canvas, photo export and the
 * Media3 video effect). Only the sampler type differs between camera/video (OES) and bitmaps (2D).
 */
object Shaders {
  const val VERTEX = """
attribute vec4 aPos;
uniform mat4 uTexMatrix;
uniform mat4 uPosMatrix;
varying vec2 vTex;
varying vec2 vPos;
void main() {
  gl_Position = aPos;
  vec4 uv = vec4(aPos.x * 0.5 + 0.5, aPos.y * 0.5 + 0.5, 0.0, 1.0);
  vTex = (uTexMatrix * uv).xy;
  vPos = (uPosMatrix * uv).xy;
}
"""

  private const val FRAGMENT_BODY = """
#ifdef GL_FRAGMENT_PRECISION_HIGH
precision highp float;
#else
precision mediump float;
#endif
varying vec2 vTex;
varying vec2 vPos;
uniform SAMPLER_TYPE uTex;
uniform sampler2D uLut;
uniform vec2 uLutParams;   // size, mix
uniform vec4 uTone;        // exposure, brightness, contrast, saturation
uniform vec4 uTone2;       // vibrance, highlights, shadows, whites
uniform vec4 uTone3;       // blacks, fade, vignette, grain
uniform vec4 uDetail;      // sharpness, clarity, dehaze, detail scale
uniform vec3 uWb;          // linear white balance gains
uniform vec4 uFrame;       // output width, output height, source long edge, grain seed
uniform vec2 uTexel;       // input texel size in texture units
uniform vec4 uOverlay;     // peaking, zebra, bypass, unused
uniform vec3 uPeakColor;

#define uExposure uTone.x
#define uBrightness uTone.y
#define uContrast uTone.z
#define uSaturation uTone.w
#define uVibrance uTone2.x
#define uHighlights uTone2.y
#define uShadows uTone2.z
#define uWhites uTone2.w
#define uBlacks uTone3.x
#define uFade uTone3.y
#define uVignette uTone3.z
#define uGrain uTone3.w
#define uSharpness uDetail.x
#define uClarity uDetail.y
#define uDehaze uDetail.z
#define uDetailScale uDetail.w

const vec3 LUMA = vec3(0.2126, 0.7152, 0.0722);

vec3 src(vec2 uv) { return texture2D(uTex, uv).rgb; }

vec3 lut3d(vec3 c) {
  float n = uLutParams.x;
  vec3 k = clamp(c, 0.0, 1.0) * (n - 1.0);
  float b0 = floor(k.b);
  float b1 = min(b0 + 1.0, n - 1.0);
  float x = (k.r + 0.5) / (n * n);
  float y = (k.g + 0.5) / n;
  vec3 s0 = texture2D(uLut, vec2(x + b0 / n, y)).rgb;
  vec3 s1 = texture2D(uLut, vec2(x + b1 / n, y)).rgb;
  return mix(s0, s1, k.b - b0);
}

float hash12(vec2 p) {
  vec3 p3 = fract(vec3(p.xyx) * 0.1031);
  p3 += dot(p3, p3.yzx + 33.33);
  return fract((p3.x + p3.y) * p3.z);
}

float filmic(float x, float g) {
  float a = pow(clamp(x, 0.0, 1.0), g);
  float b = pow(clamp(1.0 - x, 0.0, 1.0), g);
  return a / max(a + b, 1e-5);
}

vec3 softClip(vec3 v) {
  vec3 t = max(v - vec3(0.8), vec3(0.0));
  return min(v, vec3(0.8) + 0.2 * (vec3(1.0) - exp(-t / 0.2)));
}

vec3 ringBlur(vec2 uv, float r) {
  vec2 d = uTexel * r;
  vec2 e = d * 0.7071;
  vec3 s = src(uv) * 0.2;
  s += src(uv + vec2(d.x, 0.0)) * 0.1;
  s += src(uv - vec2(d.x, 0.0)) * 0.1;
  s += src(uv + vec2(0.0, d.y)) * 0.1;
  s += src(uv - vec2(0.0, d.y)) * 0.1;
  s += src(uv + e) * 0.1;
  s += src(uv - e) * 0.1;
  s += src(uv + vec2(e.x, -e.y)) * 0.1;
  s += src(uv + vec2(-e.x, e.y)) * 0.1;
  return s;
}

void main() {
  vec3 orig = src(vTex);
  vec3 c = orig;

  if (uOverlay.z < 0.5) {
    if (uSharpness > 0.001) {
      vec3 b = ringBlur(vTex, 1.3 * uDetailScale);
      c += (c - b) * uSharpness * 1.6;
    }
    if (abs(uClarity) > 0.001 || abs(uDehaze) > 0.001) {
      float r = max(uFrame.z * 0.004, 2.0) * uDetailScale;
      vec3 b = ringBlur(vTex, r);
      if (abs(uClarity) > 0.001) {
        float l = dot(c, LUMA);
        float lb = dot(b, LUMA);
        float mid = 1.0 - pow(abs(l * 2.0 - 1.0), 2.0);
        c += vec3((l - lb) * uClarity * 1.4 * mid);
      }
      if (uDehaze > 0.001) {
        float veil = min(min(b.r, min(b.g, b.b)), 0.85) * uDehaze * 0.9;
        c = (c - vec3(veil)) / max(1.0 - veil, 0.15);
        float ld = dot(c, LUMA);
        c = mix(vec3(ld), c, 1.0 + uDehaze * 0.25);
      } else if (uDehaze < -0.001) {
        c = mix(c, vec3(0.82, 0.84, 0.86), -uDehaze * 0.35);
      }
    }

    vec3 lin = pow(clamp(c, 0.0, 1.0), vec3(2.2));
    lin *= exp2(uExposure) * uWb;
    c = pow(max(lin, vec3(0.0)), vec3(1.0 / 2.2));
    if (uExposure > 0.001 || max(uWb.r, max(uWb.g, uWb.b)) > 1.001) c = softClip(c);

    if (abs(uBrightness) > 0.001) {
      c = pow(clamp(c, 0.0, 1.0), vec3(exp2(-uBrightness * 0.9)));
    }

    if (abs(uShadows) + abs(uHighlights) + abs(uWhites) + abs(uBlacks) > 0.001) {
      float L = clamp(dot(c, LUMA), 0.0, 1.0);
      float sh = 1.0 - smoothstep(0.0, 0.55, L);
      float hi = smoothstep(0.45, 1.0, L);
      float bl = 1.0 - smoothstep(0.0, 0.25, L);
      float wh = smoothstep(0.75, 1.0, L);
      float dl = uShadows * 0.32 * sh + uHighlights * 0.32 * hi + uBlacks * 0.14 * bl + uWhites * 0.14 * wh;
      vec3 added = c + vec3(dl);
      vec3 scaled = c * ((L + dl) / max(L, 0.001));
      c = mix(added, scaled, smoothstep(0.05, 0.3, L));
    }

    if (abs(uContrast) > 0.001) {
      float g = exp(uContrast * 0.85);
      c = vec3(filmic(c.r, g), filmic(c.g, g), filmic(c.b, g));
    }

    float L2 = dot(c, LUMA);
    if (abs(uSaturation) > 0.001) {
      c = mix(vec3(L2), c, 1.0 + uSaturation);
    }
    if (abs(uVibrance) > 0.001) {
      float mx = max(c.r, max(c.g, c.b));
      float mn = min(c.r, min(c.g, c.b));
      float sat = mx - mn;
      float skin = smoothstep(0.0, 0.08, c.r - c.g) * smoothstep(0.0, 0.08, c.g - c.b) * (1.0 - smoothstep(0.35, 0.6, sat));
      float amt = uVibrance * (1.0 - smoothstep(0.0, 0.7, sat)) * (1.0 - 0.6 * skin);
      c = mix(vec3(L2), c, 1.0 + amt * 1.4);
    }

    if (uLutParams.y > 0.001) {
      c = mix(c, lut3d(c), uLutParams.y);
    }

    if (uFade > 0.001) {
      c = vec3(uFade * 0.16) + clamp(c, 0.0, 1.0) * (1.0 - uFade * 0.22);
    }

    if (abs(uVignette) > 0.001) {
      vec2 d = (vPos - 0.5) * 2.0;
      float r = length(d) * 0.7071;
      float v = smoothstep(0.25, 1.0, r);
      v *= v;
      if (uVignette > 0.0) {
        c *= 1.0 - uVignette * 0.75 * v;
      } else {
        c = mix(c, vec3(1.0), -uVignette * 0.45 * v);
      }
    }

    if (uGrain > 0.001) {
      vec2 px = floor(vPos * uFrame.xy / 1.6);
      float n = hash12(px + uFrame.w) + hash12(px * 1.37 + uFrame.w * 1.91) - 1.0;
      float lg = clamp(dot(c, LUMA), 0.0, 1.0);
      float w = 0.35 + 0.65 * (1.0 - abs(lg * 2.0 - 1.0));
      c += vec3(n * uGrain * 0.14 * w);
    }
    c = clamp(c, 0.0, 1.0);
  }

  if (uOverlay.y > 0.5) {
    float lz = dot(c, LUMA);
    if (lz > 0.96) {
      float stripe = step(0.5, fract((gl_FragCoord.x + gl_FragCoord.y) / 14.0));
      c = mix(c, vec3(stripe), 0.55);
    }
  }

  if (uOverlay.x > 0.5) {
    vec2 t = uTexel;
    float tl = dot(src(vTex + vec2(-t.x, t.y)), LUMA);
    float tc = dot(src(vTex + vec2(0.0, t.y)), LUMA);
    float tr = dot(src(vTex + vec2(t.x, t.y)), LUMA);
    float ml = dot(src(vTex + vec2(-t.x, 0.0)), LUMA);
    float mr = dot(src(vTex + vec2(t.x, 0.0)), LUMA);
    float bl = dot(src(vTex + vec2(-t.x, -t.y)), LUMA);
    float bc = dot(src(vTex + vec2(0.0, -t.y)), LUMA);
    float br = dot(src(vTex + vec2(t.x, -t.y)), LUMA);
    float gx = (tr + 2.0 * mr + br) - (tl + 2.0 * ml + bl);
    float gy = (tl + 2.0 * tc + tr) - (bl + 2.0 * bc + br);
    float g = sqrt(gx * gx + gy * gy);
    c = mix(c, uPeakColor, smoothstep(0.22, 0.4, g));
  }

  gl_FragColor = vec4(c, 1.0);
}
"""

  val FRAGMENT_OES: String =
    "#extension GL_OES_EGL_image_external : require\n#define SAMPLER_TYPE samplerExternalOES\n$FRAGMENT_BODY"

  val FRAGMENT_2D: String = "#define SAMPLER_TYPE sampler2D\n$FRAGMENT_BODY"
}

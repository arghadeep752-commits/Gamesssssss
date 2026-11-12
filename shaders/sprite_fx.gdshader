shader_type canvas_item;
// Lightweight sprite effect shader shared by player, enemies and bosses:
// - cloth palette swap of the artist's purple ninja cloth (CC0 sprite)
// - armour tint, global hue/saturation grade
// - hit flash and dissolve for deaths

uniform float cloth_hue = -1.0;      // -1 keeps original cloth colour
uniform float cloth_sat = 1.0;
uniform float cloth_val = 1.0;
uniform vec4 armor_tint : source_color = vec4(1.0);
uniform float global_hue_shift = 0.0;
uniform float global_sat = 1.0;
uniform vec4 flash_color : source_color = vec4(1.0, 1.0, 1.0, 1.0);
uniform float flash_amount : hint_range(0.0, 1.0) = 0.0;
uniform float dissolve : hint_range(0.0, 1.0) = 0.0;

vec3 rgb2hsv(vec3 c) {
	vec4 K = vec4(0.0, -1.0 / 3.0, 2.0 / 3.0, -1.0);
	vec4 p = mix(vec4(c.bg, K.wz), vec4(c.gb, K.xy), step(c.b, c.g));
	vec4 q = mix(vec4(p.xyw, c.r), vec4(c.r, p.yzx), step(p.x, c.r));
	float d = q.x - min(q.w, q.y);
	float e = 1.0e-10;
	return vec3(abs(q.z + (q.w - q.y) / (6.0 * d + e)), d / (q.x + e), q.x);
}

vec3 hsv2rgb(vec3 c) {
	vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
	vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
	return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
}

varying vec4 vmod;

void vertex() {
	vmod = COLOR;
}

float hash(vec2 p) {
	return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453);
}

void fragment() {
	vec4 col = texture(TEXTURE, UV);
	vec3 hsv = rgb2hsv(col.rgb);
	float cloth = step(0.68, hsv.x) * step(hsv.x, 0.96) * step(0.14, hsv.y);
	if (cloth > 0.5) {
		if (cloth_hue >= 0.0) {
			hsv.x = cloth_hue;
		}
		hsv.y = clamp(hsv.y * cloth_sat, 0.0, 1.0);
		hsv.z = clamp(hsv.z * cloth_val, 0.0, 1.0);
	}
	float armor = (1.0 - step(0.16, hsv.y)) * step(0.10, hsv.z) * (1.0 - step(0.80, hsv.z));
	hsv.x = fract(hsv.x + global_hue_shift);
	hsv.y = clamp(hsv.y * global_sat, 0.0, 1.0);
	vec3 rgb = hsv2rgb(hsv);
	rgb = mix(rgb, rgb * armor_tint.rgb, armor);
	rgb = mix(rgb, flash_color.rgb, flash_amount);
	float a = col.a;
	if (dissolve > 0.0) {
		float n = hash(floor(UV * 64.0));
		a *= step(dissolve, n);
	}
	COLOR = vec4(rgb, a) * vmod;
}

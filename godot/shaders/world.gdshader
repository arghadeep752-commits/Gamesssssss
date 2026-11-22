// Town geometry: one texture array for every surface (layer index per vertex), tint, baked ambient occlusion,
// windows / signs / lamps that light up at night. Lit by Godot (sun, shadows, sky light, fog).
shader_type spatial;
render_mode cull_back, diffuse_burley, specular_schlick_ggx;

uniform sampler2DArray layers : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2DArray layers_n : hint_normal, filter_linear_mipmap, repeat_enable;
uniform bool normal_maps = true;
uniform float night = 0.0;

varying float v_layer;
varying float v_ao;

void vertex() {
	v_layer = mod(UV2.x, 256.0);
	v_ao = floor(UV2.y / 256.0) / 255.0;
	vec3 n = NORMAL;
	vec3 t = abs(n.y) > 0.7 ? cross(n, vec3(0.0, 0.0, 1.0)) : cross(vec3(0.0, 1.0, 0.0), n);
	TANGENT = normalize(t);
	BINORMAL = cross(n, TANGENT);
}

void fragment() {
	vec4 t = texture(layers, vec3(UV, v_layer));
	vec3 base = t.rgb * COLOR.rgb;
	float ao = max(v_ao, 0.25);
	ALBEDO = base * mix(1.0, ao, 0.75);
	AO = ao;
	ROUGHNESS = 0.86;
	SPECULAR = 0.35;
	if (normal_maps) {
		NORMAL_MAP = texture(layers_n, vec3(UV, v_layer)).rgb;
		NORMAL_MAP_DEPTH = 0.7;
	}
	EMISSION = base * COLOR.a * (0.12 + 1.9 * night) * night;
}

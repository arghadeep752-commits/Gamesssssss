// Leaves and grass: alpha-tested, both sides, swaying in the wind.
shader_type spatial;
render_mode cull_disabled, diffuse_lambert_wrap, specular_disabled;

uniform sampler2DArray layers : source_color, filter_linear_mipmap, repeat_enable;
uniform float cutoff = 0.45;

varying float v_layer;

void vertex() {
	v_layer = mod(UV2.x, 256.0);
	vec3 w = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	float sway = sin(TIME * 1.7 + w.x * 0.21 + w.z * 0.17) * 0.06 + sin(TIME * 3.1 + w.x * 0.9) * 0.025;
	VERTEX.xz += sway * clamp(UV.y, 0.0, 1.0) * 1.5;
}

void fragment() {
	vec4 t = texture(layers, vec3(UV, v_layer));
	ALBEDO = t.rgb * COLOR.rgb;
	ALPHA = t.a;
	ALPHA_SCISSOR_THRESHOLD = cutoff;
	if (!FRONT_FACING) {
		NORMAL = -NORMAL;
	}
	ROUGHNESS = 0.9;
}

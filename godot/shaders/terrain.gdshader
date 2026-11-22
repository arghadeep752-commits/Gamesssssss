// Ground: two texture layers per vertex blended with a little height-like contrast, so the edges look natural.
shader_type spatial;
render_mode cull_back, diffuse_burley, specular_schlick_ggx;

uniform sampler2DArray layers : source_color, filter_linear_mipmap_anisotropic, repeat_enable;

varying vec3 v_lay;

void vertex() {
	v_lay = vec3(mod(UV2.x, 256.0), floor(UV2.x / 256.0), mod(UV2.y, 256.0) / 255.0);
}

void fragment() {
	vec3 a = texture(layers, vec3(UV, v_lay.x)).rgb;
	vec3 b = texture(layers, vec3(UV * 0.73, v_lay.y)).rgb;
	float t = clamp((v_lay.z - 0.5) * 1.6 + 0.5 + (dot(b, vec3(0.3)) - 0.2) * 0.4, 0.0, 1.0);
	ALBEDO = mix(a, b, t) * COLOR.rgb * 0.82;
	ROUGHNESS = 0.95;
	SPECULAR = 0.2;
}

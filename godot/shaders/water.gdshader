// River, ponds and the sea: travelling ripples, fresnel reflection of the sky, sun glints. COLOR.r = depth (0..1).
shader_type spatial;
render_mode blend_mix, cull_back, depth_draw_opaque, specular_schlick_ggx;

uniform float waves = 1.0;
uniform vec3 deep : source_color = vec3(0.05, 0.16, 0.20);
uniform vec3 shallow : source_color = vec3(0.16, 0.34, 0.33);
uniform vec3 sky : source_color = vec3(0.55, 0.68, 0.82);
uniform float alpha = 0.82;
uniform float night = 0.0;

varying vec3 v_world;

void vertex() {
	vec3 w = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	VERTEX.y += (sin(w.x * 0.05 + TIME * 0.9) * 0.18 + sin(w.z * 0.07 + TIME * 1.3) * 0.12) * waves * COLOR.r;
	v_world = w;
}

void fragment() {
	vec2 p = v_world.xz;
	vec2 g = vec2(0.0);
	g += cos(dot(p, vec2(0.31, 0.17)) + TIME * 1.9) * vec2(0.31, 0.17) * 0.6;
	g += cos(dot(p, vec2(-0.21, 0.37)) + TIME * 2.3) * vec2(-0.21, 0.37) * 0.5;
	g += cos(dot(p, vec2(0.93, -0.61)) + TIME * 3.7) * vec2(0.93, -0.61) * 0.12;
	g += cos(dot(p, vec2(-1.4, -1.1)) + TIME * 4.4) * vec2(-1.4, -1.1) * 0.06;
	vec3 nw = normalize(vec3(-g.x * 0.35 * waves, 1.0, -g.y * 0.35 * waves));
	NORMAL = normalize((VIEW_MATRIX * vec4(nw, 0.0)).xyz);
	float fres = pow(1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0), 4.0) * 0.85 + 0.08;
	float depth = clamp(COLOR.r, 0.0, 1.0);
	ALBEDO = mix(shallow, deep, depth) * (1.0 - fres * 0.6);
	EMISSION = sky * fres * (1.0 - night * 0.9) * 0.55;
	ROUGHNESS = 0.06;
	SPECULAR = 0.6;
	ALPHA = mix(alpha, 1.0, fres * 0.5);
}

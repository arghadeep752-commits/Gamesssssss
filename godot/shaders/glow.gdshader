// Street-lamp glows: camera-facing quads (corner in UV, size in UV2.x) that only show at night.
shader_type spatial;
render_mode unshaded, blend_add, depth_draw_never, cull_disabled, fog_disabled;

uniform sampler2D tex : source_color, filter_linear;
uniform float night = 0.0;
uniform float boost = 1.0;

void vertex() {
	vec2 c = UV * 2.0 - 1.0;
	float s = UV2.x;
	vec3 right = vec3(INV_VIEW_MATRIX[0].xyz);
	vec3 up = vec3(INV_VIEW_MATRIX[1].xyz);
	vec3 w = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz + (right * c.x + up * c.y) * s;
	POSITION = PROJECTION_MATRIX * VIEW_MATRIX * vec4(w, 1.0);
}

void fragment() {
	vec4 t = texture(tex, UV);
	ALBEDO = COLOR.rgb * t.rgb * t.a * COLOR.a * night * boost;
}

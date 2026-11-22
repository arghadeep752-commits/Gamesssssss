// Glowing cylinder markers (shops, house) that pulse gently.
shader_type spatial;
render_mode unshaded, blend_add, depth_draw_never, cull_disabled, shadows_disabled, fog_disabled;

uniform vec4 color : source_color = vec4(0.2, 1.0, 0.4, 1.0);

void fragment() {
	float fade = pow(1.0 - clamp(UV.y, 0.0, 1.0), 1.6);
	float pulse = 0.75 + 0.25 * sin(TIME * 3.0);
	ALBEDO = color.rgb * fade * pulse * color.a;
}

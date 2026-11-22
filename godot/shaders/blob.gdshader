// The soft dark patch under people and vehicles that sits them on the ground (far from the sun shadows).
shader_type spatial;
render_mode unshaded, blend_mix, depth_draw_never, cull_disabled, shadows_disabled;

uniform sampler2D tex : source_color, filter_linear;
uniform float strength = 0.5;

void fragment() {
	ALBEDO = vec3(0.0);
	ALPHA = texture(tex, UV).a * strength;
}

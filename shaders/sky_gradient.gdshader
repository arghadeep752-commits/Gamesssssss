shader_type canvas_item;
// Vertical colour grade for the sky behind the parallax layers.

uniform vec4 top_color : source_color = vec4(0.4, 0.7, 0.95, 1.0);
uniform vec4 bottom_color : source_color = vec4(0.8, 0.9, 1.0, 1.0);

void fragment() {
	COLOR = mix(top_color, bottom_color, smoothstep(0.0, 1.0, UV.y));
}

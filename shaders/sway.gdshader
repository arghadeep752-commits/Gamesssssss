shader_type canvas_item;
// Animated foliage: bends the top of a sprite with the wind. Cheap vertex shader.

uniform float strength = 6.0;
uniform float speed = 1.6;
uniform float phase = 0.0;

void vertex() {
	float top = 1.0 - UV.y;
	VERTEX.x += sin(TIME * speed + phase + VERTEX.y * 0.01) * strength * top * top;
}

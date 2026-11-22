// Day and night panoramas (real HDR skies, tone mapped) blended with the time of day, plus the sun disc.
shader_type sky;

uniform sampler2D day : source_color, filter_linear, repeat_enable;
uniform sampler2D night_tex : source_color, filter_linear, repeat_enable;
uniform float night = 0.0;
uniform float energy = 1.0;
uniform vec3 tint : source_color = vec3(1.0);
uniform float spin = 0.0;

void sky() {
	vec3 d = EYEDIR;
	float u = atan(d.x, -d.z) / (2.0 * PI) + 0.5 + spin;
	float v = acos(clamp(d.y, -1.0, 1.0)) / PI;
	vec2 uv = vec2(u, v);
	vec3 c = mix(texture(day, uv).rgb * tint, texture(night_tex, uv).rgb, night);
	if (d.y < 0.0) {
		c = mix(c, c * 0.55, clamp(-d.y * 4.0, 0.0, 1.0));
	}
	float sd = dot(d, LIGHT0_DIRECTION);
	if (LIGHT0_ENABLED && night < 0.5) {
		c += LIGHT0_COLOR * smoothstep(0.9993, 0.9998, sd) * 8.0 * (1.0 - night * 2.0);
		c += LIGHT0_COLOR * pow(max(sd, 0.0), 300.0) * 0.6 * (1.0 - night * 2.0);
	}
	COLOR = c * energy;
}

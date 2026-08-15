shader_type canvas_item;

// Rayon d'arrondi des coins, en pixels.
uniform float radius : hint_range(0.0, 200.0) = 20.0;

float rounded_box_sdf(vec2 pixel_pos, vec2 half_size, float r) {
	vec2 d = abs(pixel_pos) - half_size + vec2(r);
	return length(max(d, vec2(0.0))) - r;
}

void fragment() {
	vec2 size = 1.0 / TEXTURE_PIXEL_SIZE;
	vec2 pixel_pos = (UV - 0.5) * size;
	float dist = rounded_box_sdf(pixel_pos, size * 0.5, radius);
	float alpha = 1.0 - smoothstep(-1.5, 1.5, dist);
	COLOR = texture(TEXTURE, UV);
	COLOR.a *= alpha;
}

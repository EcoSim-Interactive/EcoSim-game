## Affiche une ressource alimentaire avec son rendu visuel et sa jauge restante.
extends Node2D

@export var default_color: Color = Color(0.2, 0.8, 0.2, 1.0)
@export var default_texture: Texture2D
@export var texture_scale: float = 1.0 
@export var bar_size: Vector2 = Vector2(28, 4)
@export var bar_offset: Vector2 = Vector2(0, -18)
@export var fallback_radius: float = 10.0
@export var target_size: Vector2 = Vector2(32, 32)

@export var use_sprite_sheet: bool = true 
@export var frame_size: Vector2 = Vector2(16, 16) 
@export var grid_columns: int = 38  ## 608px / 16px = 38 colonnes
@export var grid_rows: int = 6  ## 96px / 16px = 6 lignes

var _remaining := 1.0
var _maximum := 1.0
var _texture_override: Texture2D
var _color_override: Color
var _random_frame: Vector2i = Vector2i(-1, -1)  ## -1 = pas encore choisi

func _pick_random_frame() -> void:
	var tex := _texture_override if _texture_override else default_texture
	if tex == null or not use_sprite_sheet:
		return
	
	var tex_size = tex.get_size()
	var cols = grid_columns if grid_columns > 0 else int(tex_size.x / frame_size.x)
	var rows = grid_rows if grid_rows > 0 else int(tex_size.y / frame_size.y)
	
	if cols > 0 and rows > 0:
		_random_frame = Vector2i(randi() % cols, randi() % rows)

func update_state(data: Dictionary, icon: Texture2D = null, color: Color = default_color) -> void:
	_texture_override = icon
	_color_override = color
	_remaining = float(data.get("remaining_nutrition", 1.0))
	_maximum = max(0.001, float(data.get("max_nutrition", _remaining)))
	position = Vector2(float(data.get("x", position.x)), float(data.get("y", position.y)))
	
	# Choisir un frame aléatoire au premier update
	if _random_frame.x < 0:
		_pick_random_frame()
	
	queue_redraw()

func _draw() -> void:
	var draw_color := _color_override if _color_override.a > 0 else default_color
	var tex := _texture_override if _texture_override else default_texture
	if tex:
		if use_sprite_sheet and _random_frame.x >= 0:
			var src_rect = Rect2(
				Vector2(_random_frame) * frame_size,
				frame_size
			)
			var scaled_size = frame_size * texture_scale
			var dest_rect = Rect2(-scaled_size / 2, scaled_size)
			draw_texture_rect_region(tex, dest_rect, src_rect)
		else:
			var original_size = tex.get_size()
			var scale_factor = min(target_size.x / original_size.x, target_size.y / original_size.y)
			var scaled_size = original_size * scale_factor * texture_scale
			var dest_rect = Rect2(-scaled_size / 2, scaled_size)
			draw_texture_rect(tex, dest_rect, false)
	else:
		draw_circle(Vector2.ZERO, fallback_radius, draw_color)
	_draw_bar(draw_color)

func _draw_bar(color: Color) -> void:
	var width = bar_size.x
	var height = bar_size.y
	var top_left = Vector2(-width / 2, bar_offset.y)
	draw_rect(Rect2(top_left, Vector2(width, height)), Color(0, 0, 0, 0.8))
	var ratio = clamp(_remaining / _maximum, 0.0, 1.0)
	var fill_width = (width - 2) * ratio
	draw_rect(
		Rect2(top_left + Vector2(1, 1), Vector2(fill_width, height - 2)),
		Color(color.r, max(color.g, 0.2), color.b, 0.9)
	)

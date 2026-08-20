## Displays a food resource with its visual rendering and remaining gauge.
extends Node2D

@export var default_color: Color = Color(0.2, 0.8, 0.2, 1.0)
@export var default_texture: Texture2D
@export var texture_scale: float = 0.75
@export var bar_size: Vector2 = Vector2(24, 4)
@export var bar_offset: Vector2 = Vector2(0, -14)
@export var fallback_radius: float = 7.5
@export var target_size: Vector2 = Vector2(24, 24)

@export var use_sprite_sheet: bool = true 
@export var frame_size: Vector2 = Vector2(16, 16) 
@export var grid_columns: int = 38  ## 608px / 16px = 38 columns
@export var grid_rows: int = 6  ## 96px / 16px = 6 rows

var _remaining := 1.0
var _maximum := 1.0
var _texture_override: Texture2D
var _color_override: Color
var _random_frame: Vector2i = Vector2i(-1, -1)  ## -1 = not yet chosen
var is_hovered: bool = false

## Randomly picks a cell in the sprite sheet to vary the appearance.
func _pick_random_frame() -> void:
	var tex := _texture_override if _texture_override else default_texture
	if tex == null or not use_sprite_sheet:
		return
	
	var tex_size = tex.get_size()
	var cols = grid_columns if grid_columns > 0 else int(tex_size.x / frame_size.x)
	var rows = grid_rows if grid_rows > 0 else int(tex_size.y / frame_size.y)
	
	if cols > 0 and rows > 0:
		_random_frame = Vector2i(randi() % cols, randi() % rows)

## Updates the position and remaining nutrition from the backend data, then redraws.
func update_state(data: Dictionary, icon: Texture2D = null, color: Color = default_color) -> void:
	_texture_override = icon
	_color_override = color
	_remaining = float(data.get("remaining_nutrition", 1.0))
	_maximum = max(0.001, float(data.get("max_nutrition", _remaining)))
	position = Vector2(float(data.get("x", position.x)), float(data.get("y", position.y)))
	
	# Pick a random frame on the first update
	if _random_frame.x < 0:
		_pick_random_frame()
	
	queue_redraw()

## Draws the resource's texture or fallback circle, and the nutrition bar on hover.
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
		
	# Show the nutrition bar ONLY when the mouse is hovering
	if is_hovered:
		_draw_bar(draw_color)

## Draws the remaining nutrition bar above the resource.
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

## Detects mouse hover over the resource to display the nutrition bar.
func _input(event: InputEvent) -> void:
	if event is InputEventMouseMotion:
		var local_mouse_pos = to_local(get_global_mouse_position())
		var distance = local_mouse_pos.length()

		var hit_limit = target_size.x / 2.0 if target_size.x > 0 else fallback_radius

		var currently_hovered = (distance <= hit_limit)
		if currently_hovered != is_hovered:
			is_hovered = currently_hovered
			queue_redraw()

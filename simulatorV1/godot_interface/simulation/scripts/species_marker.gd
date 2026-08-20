## Draws a minimalist marker to represent a species on the map and handles its interaction.
extends Node2D

signal clicked(marker)

@export var radius: float = 4.5
@export var color: Color = Color(1, 0, 0, 1)
@onready var tooltip_label = $Label

@export var texture_scale: float = 0.75
@export var target_size: Vector2 = Vector2(24, 24)
var icon: Texture2D = null

var vision: float = 100.0
var smell_range: float = 50.0
var is_hovered: bool = false
var is_selected: bool = false

var vitality: float = 100.0
var thirst: float = 0.0
var hunger: float = 0.0
var fatigue: float = 0.0

var species_data: Dictionary = {}
var pos_data: Dictionary = {}
var species_id: String = ""
var clean_species_name: String = ""

var _press_pos: Vector2 = Vector2.ZERO
var _pressed_on_marker: bool = false

## Initializes the tooltip (hidden by default) and extracts the species name from the node's name.
func _ready() -> void:
	tooltip_label.visible = false
	if tooltip_label:
		tooltip_label.position = Vector2(-40, -52)
	queue_redraw()
	
	clean_species_name = name.trim_prefix("SpeciesMarker_").split("_")[0]
	if tooltip_label:
		tooltip_label.text = clean_species_name

## Updates the represented animal's data (entry, position, id, name) and refreshes the tooltip.
func update_data(p_entry: Dictionary, p_pos_data: Dictionary, p_id: String, p_clean_name: String) -> void:
	species_data = p_entry.duplicate(true)
	pos_data = p_pos_data.duplicate(true)
	species_id = p_id
	clean_species_name = p_clean_name
	
	for k in pos_data.keys():
		species_data[k] = pos_data[k]
	species_data["id"] = p_id
	species_data["clean_name"] = p_clean_name
	species_data["position_world"] = global_position
	
	if tooltip_label:
		tooltip_label.text = clean_species_name

## Assembles and returns a complete dictionary of the animal's current data (identity, vitals, position).
func get_full_data() -> Dictionary:
	var result = species_data.duplicate(true)
	result["id"] = species_id
	result["clean_name"] = clean_species_name
	result["vitality"] = vitality
	result["thirst"] = thirst
	result["hunger"] = hunger
	result["fatigue"] = fatigue
	result["vision"] = vision
	result["smell_range"] = smell_range
	result["x"] = global_position.x
	result["y"] = global_position.y
	result["position_world"] = global_position
	return result

## Changes the marker's selection state, adjusts its display order and forces a redraw.
func set_selected(selected: bool) -> void:
	if is_selected != selected:
		is_selected = selected
		z_index = 110 if is_selected else (100 if is_hovered else 5)
		queue_redraw()

## Draws the marker: selection reticle, sprite or base circle, vision/smell circles and status bars on hover.
func _draw() -> void:
	# Selection reticle when the animal is selected
	if is_selected:
		var sel_radius = max(radius, target_size.x / 2.0) + 7.0
		# Outer halo
		draw_circle(Vector2.ZERO, sel_radius + 3.0, Color(0.06, 0.72, 0.51, 0.25))
		# Main selection ring (bright cyan / emerald)
		draw_arc(Vector2.ZERO, sel_radius, 0.0, TAU, 36, Color(0.1, 0.95, 0.65, 0.95), 2.5, true)
		# 4 corners / modern reticles
		var bracket_size = sel_radius + 4.0
		var b_len = 5.0
		draw_line(Vector2(-bracket_size, -bracket_size), Vector2(-bracket_size + b_len, -bracket_size), Color(1, 1, 1, 0.9), 2.0)
		draw_line(Vector2(-bracket_size, -bracket_size), Vector2(-bracket_size, -bracket_size + b_len), Color(1, 1, 1, 0.9), 2.0)
		draw_line(Vector2(bracket_size, -bracket_size), Vector2(bracket_size - b_len, -bracket_size), Color(1, 1, 1, 0.9), 2.0)
		draw_line(Vector2(bracket_size, -bracket_size), Vector2(bracket_size, -bracket_size + b_len), Color(1, 1, 1, 0.9), 2.0)
		draw_line(Vector2(-bracket_size, bracket_size), Vector2(-bracket_size + b_len, bracket_size), Color(1, 1, 1, 0.9), 2.0)
		draw_line(Vector2(-bracket_size, bracket_size), Vector2(-bracket_size, bracket_size - b_len), Color(1, 1, 1, 0.9), 2.0)
		draw_line(Vector2(bracket_size, bracket_size), Vector2(bracket_size - b_len, bracket_size), Color(1, 1, 1, 0.9), 2.0)
		draw_line(Vector2(bracket_size, bracket_size), Vector2(bracket_size, bracket_size - b_len), Color(1, 1, 1, 0.9), 2.0)

	# Draw the sprite or base circle
	if icon:
		var size = icon.get_size()
		var scale_factor = min(target_size.x / size.x, target_size.y / size.y)
		var scaled_size = size * scale_factor * texture_scale
		var dest_rect = Rect2(-scaled_size / 2, scaled_size)
		draw_texture_rect(icon, dest_rect, false)
	else:
		draw_circle(Vector2.ZERO, radius, color)

	# Display on hover or selection
	if is_hovered or is_selected:
		# Vision circle (bright blue)
		draw_arc(Vector2.ZERO, vision, 0.0, TAU, 64, Color(0.1, 0.55, 1.0, 0.7), 2.0, true)
		# Smell circle (bright green)
		draw_arc(Vector2.ZERO, smell_range, 0.0, TAU, 64, Color(0.2, 0.85, 0.3, 0.65), 2.0, true)

		# Status bars above the marker
		_draw_status_bars()

## Draws the three status bars (vitality, thirst, hunger) above the marker.
func _draw_status_bars() -> void:
	var bar_w: float = 36.0
	var bar_h: float = 4.0
	var start_x: float = -bar_w / 2.0
	var start_y: float = -16.0

	# 1. Vitality (green)
	var vita_ratio: float = clamp(vitality / 100.0, 0.0, 1.0)
	_draw_single_bar(Vector2(start_x, start_y - 12.0), bar_w, bar_h, vita_ratio, Color(0.2, 0.85, 0.3, 0.95))

	# 2. Thirst / Hydration (blue)
	var thirst_ratio: float = clamp((100.0 - thirst) / 100.0, 0.0, 1.0)
	_draw_single_bar(Vector2(start_x, start_y - 6.0), bar_w, bar_h, thirst_ratio, Color(0.2, 0.6, 1.0, 0.95))

	# 3. Hunger / Satiety (orange)
	var hunger_ratio: float = clamp((100.0 - hunger) / 100.0, 0.0, 1.0)
	_draw_single_bar(Vector2(start_x, start_y), bar_w, bar_h, hunger_ratio, Color(1.0, 0.6, 0.1, 0.95))

## Draws a single status bar with a black background and a fill proportional to the ratio.
func _draw_single_bar(pos: Vector2, width: float, height: float, ratio: float, fill_color: Color) -> void:
	draw_rect(Rect2(pos, Vector2(width, height)), Color(0.0, 0.0, 0.0, 0.8))
	var fill_w: float = max(0.0, (width - 2.0) * ratio)
	draw_rect(Rect2(pos + Vector2(1.0, 1.0), Vector2(fill_w, height - 2.0)), fill_color)

## Handles mouse hover (updating the tooltip and z-index) and click detection on the marker.
func _input(event: InputEvent) -> void:
	if event is InputEventMouseMotion:
		var local_mouse_pos = to_local(get_global_mouse_position())
		var distance = local_mouse_pos.length()

		var hit_limit = radius
		if icon:
			hit_limit = max(radius, target_size.x / 2.0)
		hit_limit = max(hit_limit, 18.0)

		var currently_hovered = (distance <= hit_limit)
		if currently_hovered != is_hovered:
			is_hovered = currently_hovered
			tooltip_label.visible = is_hovered or is_selected
			if is_hovered:
				z_index = 110 if is_selected else 100
				var clean_name = clean_species_name if clean_species_name != "" else name.trim_prefix("SpeciesMarker_").split("_")[0]
				tooltip_label.text = clean_name
			else:
				z_index = 110 if is_selected else 5
			queue_redraw()

	elif event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT:
		var local_mouse_pos = to_local(get_global_mouse_position())
		var distance = local_mouse_pos.length()
		var hit_limit = max(radius, target_size.x / 2.0) if icon else radius
		hit_limit = max(hit_limit, 20.0)

		if event.pressed:
			if distance <= hit_limit:
				_pressed_on_marker = true
				_press_pos = event.position
		else:
			if _pressed_on_marker:
				_pressed_on_marker = false
				var dist_moved = event.position.distance_to(_press_pos)
				if dist_moved < 12.0 and distance <= hit_limit:
					_on_marker_clicked()

## Emits the click signal and notifies the parent to select this marker.
func _on_marker_clicked() -> void:
	emit_signal("clicked", self)
	var parent = get_parent()
	if parent and parent.has_method("select_species_marker"):
		parent.select_species_marker(self)

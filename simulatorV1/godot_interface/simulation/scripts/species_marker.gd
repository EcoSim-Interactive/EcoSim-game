## Dessine un marqueur minimaliste pour representer une espece sur la carte.
extends Node2D

@export var radius: float = 6.0
@export var color: Color = Color(1, 0, 0, 1)
@onready var tooltip_label = $Label


@export var texture_scale: float = 1.0
@export var target_size: Vector2 = Vector2(32, 32)
var icon: Texture2D = null

var vision: float = 100.0
var smell_range: float = 50.0
var is_hovered: bool = false

func _ready() -> void:
	tooltip_label.visible = false
	queue_redraw()
	
	var species_name = name.trim_prefix("SpeciesMarker_").split("_")[0]
	tooltip_label.text = species_name

func _draw() -> void:
	if icon:
		var size = icon.get_size()
		var scale_factor = min(target_size.x / size.x, target_size.y / size.y)
		var scaled_size = size * scale_factor * texture_scale
		var dest_rect = Rect2(-scaled_size / 2, scaled_size)
		draw_texture_rect(icon, dest_rect, false)
	else:
		draw_circle(Vector2.ZERO, radius, color)

	if is_hovered:
		# Cercle de vision (Bleu vif et bien visible)
		draw_arc(Vector2.ZERO, vision, 0.0, TAU, 64, Color(0.1, 0.55, 1.0, 0.8), 3.0, true)
		# Cercle d'odeur (Vert vif et bien visible)
		draw_arc(Vector2.ZERO, smell_range, 0.0, TAU, 64, Color(0.2, 0.85, 0.3, 0.75), 3.0, true)

func _input(event):
	if event is InputEventMouseMotion:
		var local_mouse_pos = to_local(get_global_mouse_position())
		var distance = local_mouse_pos.length()

		var hit_limit = radius
		if icon:
			hit_limit = max(radius, target_size.x / 2.0)

		var currently_hovered = (distance <= hit_limit)
		if currently_hovered != is_hovered:
			is_hovered = currently_hovered
			tooltip_label.visible = is_hovered
			if is_hovered:
				z_index = 100 # Met le marqueur au premier plan pour garantir que les cercles soient visibles
				var clean_name = name.trim_prefix("SpeciesMarker_").split("_")[0]
				tooltip_label.text = clean_name
			else:
				z_index = 5 # Remet le z-index normal
			queue_redraw()

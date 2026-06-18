## Dessine un marqueur minimaliste pour representer une espece sur la carte.
extends Node2D

@export var radius: float = 6.0
@export var color: Color = Color(1, 0, 0, 1)
@onready var tooltip_label = $Label


@export var texture_scale: float = 1.0
@export var target_size: Vector2 = Vector2(32, 32)
var icon: Texture2D = null

func _ready() -> void:
	tooltip_label.visible = false
	queue_redraw()
	
	var species_name = name.trim_prefix("SpeciesMarker_")
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

func _input(event):
	if event is InputEventMouseMotion:
		var local_mouse_pos = to_local(get_global_mouse_position())
		var distance = local_mouse_pos.length()

		if distance <= radius:
			tooltip_label.visible = true
		else:
			tooltip_label.visible = false

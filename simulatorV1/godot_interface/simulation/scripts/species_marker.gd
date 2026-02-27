extends Node2D

@export var radius: float = 6.0
@export var color: Color = Color(1, 0, 0, 1)
@onready var tooltip_label = $Label


func _ready() -> void:
	tooltip_label.visible = false
	queue_redraw()
	
	var species_name = name.trim_prefix("SpeciesMarker_")
	tooltip_label.text = species_name

func _draw() -> void:
	draw_circle(Vector2.ZERO, radius, color)

func _input(event):
	if event is InputEventMouseMotion:
		var local_mouse_pos = to_local(get_global_mouse_position())
		var distance = local_mouse_pos.length()

		if distance <= radius:
			tooltip_label.visible = true
		else:
			tooltip_label.visible = false

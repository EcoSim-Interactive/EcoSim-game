## Enables or disables the scene's day/night tinting.
extends CheckButton

## Path to the World node that contains world_lighting
@export var world_path: NodePath

var world_lighting: CanvasModulate = null

## Retrieves world_lighting, enables the day/night cycle by default and connects the toggled signal.
func _ready():
	# Get the reference to world_lighting via World
	var world = get_node_or_null(world_path)
	if world:
		world_lighting = world.get_node_or_null("world_lighting")
	
	if world_lighting == null:
		push_warning("world_lighting non trouvé, le bouton jour/nuit sera inactif")
	
	# Enabled by default (button checked = day/night cycle active)
	button_pressed = true
	toggled.connect(_on_toggled)

## Applies the button state to world_lighting's day/night mode.
func _on_toggled(button_state: bool):
	if world_lighting and world_lighting.has_method("set_day_night_mode"):
		world_lighting.set_day_night_mode(button_state)

## Active ou desactive l'habillage jour/nuit de la scene.
extends CheckButton

## Chemin vers le node World qui contient world_lighting
@export var world_path: NodePath

var world_lighting: CanvasModulate = null

func _ready():
	# Obtenir la référence au world_lighting via World
	var world = get_node_or_null(world_path)
	if world:
		world_lighting = world.get_node_or_null("world_lighting")
	
	if world_lighting == null:
		push_warning("world_lighting non trouvé, le bouton jour/nuit sera inactif")
	
	# Par défaut activé (bouton coché = cycle jour/nuit actif)
	button_pressed = true
	toggled.connect(_on_toggled)

func _on_toggled(button_state: bool):
	if world_lighting and world_lighting.has_method("set_day_night_mode"):
		world_lighting.set_day_night_mode(button_state)

## Synchronise l'etat du bouton avec le lancement ou la pause de la simulation.
extends CheckButton

@export var world_path: NodePath
var world: Node = null

func _ready() -> void:
	if world_path != NodePath():
		world = get_node(world_path)

	toggled.connect(_on_toggled)

func _on_toggled(pressed_state: bool) -> void:
	if world == null:
		return

	if pressed_state:
		world.start_simulation()
		if world.has_method("is_running") and not world.is_running():
			set_pressed_no_signal(false)
			text = "Marche/Arrêt"
			return
		text = "Start"
	else:
		world.pause_simulation()
		text = "Pause"

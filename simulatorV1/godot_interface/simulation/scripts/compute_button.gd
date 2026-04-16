## Bouton de lancement du pre-calcul de simulation via le manager reseau.
extends Button

@export var socket_path: NodePath
var socket_node: Node = null

func _ready():
	if socket_path != NodePath():
		socket_node = get_node_or_null(socket_path)
	pressed.connect(_on_pressed)

func _on_pressed() -> void:
	if socket_node == null:
		return
	if socket_node.has_method("compute_simulation"):
		socket_node.compute_simulation()

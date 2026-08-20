## Button that triggers the simulation pre-computation via the network manager.
extends Button

@export var socket_path: NodePath
var socket_node: Node = null

## Resolves the socket node from the exported path and connects the pressed signal.
func _ready():
	if socket_path != NodePath():
		socket_node = get_node_or_null(socket_path)
	pressed.connect(_on_pressed)

## Triggers the simulation pre-computation on the socket node if available.
func _on_pressed() -> void:
	if socket_node == null:
		return
	if socket_node.has_method("compute_simulation"):
		socket_node.compute_simulation()

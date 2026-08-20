## Opens the file selection window to import a simulation.
extends Button

@export var dialog_path: NodePath
var dialog: FileDialog

## Retrieves the import dialog node and connects the pressed signal.
func _ready():
	dialog = get_node(dialog_path)
	pressed.connect(_on_press)

## Shows the import dialog window, or reports an error if it cannot be found.
func _on_press():
	if dialog:
		dialog.popup_centered()
	else:
		push_error("Dialog non défini ou introuvable")

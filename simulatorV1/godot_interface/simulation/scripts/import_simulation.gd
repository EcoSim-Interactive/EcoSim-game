extends Button

@export var dialog_path: NodePath
var dialog: FileDialog

func _ready():
	dialog = get_node(dialog_path)
	pressed.connect(_on_press)

func _on_press():
	if dialog:
		dialog.popup_centered()
	else:
		push_error("Dialog non défini ou introuvable")

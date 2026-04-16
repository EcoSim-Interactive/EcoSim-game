## Dialogue d'import permettant de recharger une simulation JSON existante.
extends FileDialog

@export var simulation_manager_path: NodePath
var manager: SimulationManager

func _ready():
	manager = get_node_or_null(simulation_manager_path)
	file_selected.connect(_on_file_selected)
	access = FileDialog.ACCESS_FILESYSTEM


func _on_file_selected(path: String):
	var file := FileAccess.open(path, FileAccess.READ)
	var text := file.get_as_text()
	file.close()

	var json: Dictionary = JSON.parse_string(text)
	if json == null:
		push_error("Fichier simulation invalide : JSON incorrect")
		return

	if typeof(json) != TYPE_DICTIONARY:
		push_error("Fichier simulation invalide : pas un dictionnaire")
		return

	if manager == null:
		push_error("SimulationManager introuvable")
		return
	if not manager.has_method("rerun_simulation"):
		push_error("SimulationManager ne supporte pas le rerun")
		return

	manager.rerun_simulation(json)
	print("[IMPORT] Fichier importé :", path)

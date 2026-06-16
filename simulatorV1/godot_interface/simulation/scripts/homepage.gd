## Controle l'ecran d'accueil et l'affichage progressif des journaux de simulation.
extends Control

# --- Références aux nodes ---
@onready var export_button = $Boutton/VBoxContainer/ExportLog
@onready var settings_btn = $Header/SettingsBtn
@onready var quit_btn = $Header/QuitBtn
@onready var settings_panel = $SettingsPanel
@onready var mode_option = $SettingsPanel/VBoxContainer/ModeOption
@onready var loading_overlay = $Simulateur/Panel/LoadingOverlay
@onready var world = $Simulateur/Panel/SubViewportContainer/SubViewport/World

# --- Variables principales ---
var simulation_logs = []          # Données chargées depuis summary.json
var current_step_data = {}
var simulation_data = {}          # Données du fichier simulation.json (actions, motivations)

# --- Configuration ---
@export var logs_folder: String = ""
@export var poll_interval := 0.5
var last_step_file_index := 0

# --- Ready ---
func _ready():
	if export_button:
		export_button.pressed.connect(_on_export_log_pressed)
	if settings_btn:
		settings_btn.pressed.connect(_on_settings_pressed)
	if quit_btn:
		quit_btn.pressed.connect(_on_quit_pressed)
	if mode_option:
		var popup = mode_option.get_popup()
		popup.add_theme_font_size_override("font_size", 35)
		
		mode_option.item_selected.connect(_on_mode_selected)
		mode_option.add_item("Plein écran", 0)
		mode_option.add_item("Fenêtré", 1)
		mode_option.add_item("Maximisé", 2)
		var current_mode = DisplayServer.window_get_mode()
		if current_mode == DisplayServer.WINDOW_MODE_FULLSCREEN or current_mode == DisplayServer.WINDOW_MODE_EXCLUSIVE_FULLSCREEN:
			mode_option.select(0)
		elif current_mode == DisplayServer.WINDOW_MODE_MAXIMIZED:
			mode_option.select(2)
		else:
			mode_option.select(1)
			
	if world:
		world.world_loading.connect(_on_world_loading)
		world.world_loaded.connect(_on_world_loaded)
		if world.has_signal("simulation_computing"):
			world.simulation_computing.connect(_on_simulation_computing)
		if world.has_signal("simulation_computed"):
			world.simulation_computed.connect(_on_simulation_computed)
		if not world.world_ready:
			loading_overlay.visible = true

	if logs_folder == "":
		if OS.has_feature("editor"):
			# --- MODE DÉVELOPPEMENT (Éditeur Godot) ---
			# On remonte de deux crans pour trouver le dossier python_backend
			logs_folder = ProjectSettings.globalize_path("res://../../python_backend/logs")
		else:
			# --- MODE BUILD (Jeu exporté .exe) ---
			var base_dir = OS.get_executable_path().get_base_dir()
			logs_folder = base_dir.path_join("server/logs")

	print("📂 Dossier de logs utilisé:", logs_folder)
	load_all_logs()

# --- Charger tous les logs existants ---
func load_all_logs():
	if logs_folder == "":
		push_warning("Le dossier de logs n'est pas défini")
		return

	var dir = DirAccess.open(logs_folder)
	if dir == null:
		push_error("Impossible d'ouvrir le dossier: %s" % logs_folder)
		return

	print("Chargement des logs depuis:", logs_folder)

	dir.list_dir_begin()
	var entry = dir.get_next()
	while entry != "":
		if dir.current_is_dir() and entry != "." and entry != "..":
			var subfolder = "%s/%s" % [logs_folder, entry]
			print("  ➜ Lecture du sous-dossier:", subfolder)
			load_summary_in_folder(subfolder)
		entry = dir.get_next()
	dir.list_dir_end()

	if simulation_logs.is_empty():
		push_warning("Aucun log trouvé dans le dossier: %s" % logs_folder)
	else:
		print("%d logs chargés depuis %s" % [simulation_logs.size(), logs_folder])


# --- Charger le summary.json et simulation.json dans un sous-dossier ---
func load_summary_in_folder(folder_path: String):
	var summary_path = "%s/summary.json" % folder_path
	if FileAccess.file_exists(summary_path):
		print("  Summary trouvé:", summary_path)
		load_simulation_json(summary_path)
		load_simulation_file(folder_path)  # Chargement du simulation.json
	else:
		print("  Aucun summary.json trouvé dans:", folder_path)

# --- Charger simulation.json ---
func load_simulation_file(folder_path: String):
	var sim_path = "%s/simulation.json" % folder_path
	if FileAccess.file_exists(sim_path):
		print("  Simulation.json trouvé:", sim_path)
		var file = FileAccess.open(sim_path, FileAccess.READ)
		if file:
			var content = file.get_as_text()
			file.close()
			var data = JSON.parse_string(content)
			if data is Dictionary:
				simulation_data = data
				print("  ➜ Simulation data chargée (%d entrées)" % data.size())
			else:
				push_warning("Format inattendu dans simulation.json")
	else:
		print("  Aucun simulation.json trouvé dans:", folder_path)

# --- Charger un fichier JSON individuel (summary.json) ---
func load_simulation_json(json_path: String):
	var file = FileAccess.open(json_path, FileAccess.READ)
	if file == null:
		push_error("Impossible d'ouvrir le fichier: " + json_path)
		return

	var json_string = file.get_as_text()
	file.close()

	var data = JSON.parse_string(json_string)
	if data == null:
		push_error("Erreur JSON dans: %s" % json_path)
		return

	if data is Array:
		for step_data in data:
			add_step_log(step_data)
	elif data is Dictionary:
		add_step_log(data)
	else:
		push_warning("Format JSON inattendu dans: %s" % json_path)

# --- Ajouter un step log ---
func add_step_log(step_data: Dictionary):
	simulation_logs.append(step_data)
	current_step_data = step_data

# --- Générer un résumé global pour le fichier TXT ---
func generate_summary_text() -> String:
	var summary_text = "=== ECOSIM SUMMARY REPORT ===\n"
	summary_text += "Export: %s\n" % Time.get_datetime_string_from_system()
	summary_text += "==================================================\n\n"

	if simulation_logs.is_empty():
		summary_text += "Aucune donnée de simulation disponible.\n"
		return summary_text

	var species_seen = {}
	var total_species = 0
	var alive_count = 0
	var dead_count = 0

	# On parcourt tous les steps pour prendre le dernier état de chaque espèce
	for step in simulation_logs:
		if step.has("species"):
			for s in step["species"]:
				var name = s.get("name", "Inconnu")
				species_seen[name] = s  # Dernière version remplace l’ancienne

	# Générer le résumé
	for name in species_seen.keys():
		var s = species_seen[name]
		total_species += 1
		var vitality = s.get("vitality", 0.0)
		var status = "Vivant" if vitality > 0 else "Mort"
		if vitality > 0:
			alive_count += 1
		else:
			dead_count += 1

		var pos = s.get("position", [0, 0])
		var action = s.get("action", "N/A")
		var motivation = s.get("motivation", "N/A")

		# Si action ou motivation manquante → chercher dans simulation.json
		if (action == "N/A" or motivation == "N/A") and simulation_data.has(name):
			var sim_entry = simulation_data[name]
			action = sim_entry.get("action", action)
			motivation = sim_entry.get("motivation", motivation)

		summary_text += "%s\n" % name
		summary_text += "  Type : %s | Sexe : %s | Âge : %.2f ans (%s)\n" % [
			s.get("species_type", "N/A"),
			s.get("sex", "N/A"),
			s.get("age_years", 0.0),
			s.get("age_stage", "N/A")
		]
		summary_text += "  Position : (%.0f, %.0f)\n" % [pos[0], pos[1]]
		summary_text += "  Action : %s\n" % action
		summary_text += "  Motivation : %s\n" % motivation
		summary_text += "  Vitalité : %.1f | Faim : %.1f | Soif : %.1f | Fatigue : %.1f\n" % [
			vitality,
			s.get("hunger", 0.0),
			s.get("thirst", 0.0),
			s.get("fatigue", 0.0)
		]
		summary_text += "  Statut : %s\n\n" % status

	summary_text += "==================================================\n"
	summary_text += "Espèces totales : %d\n" % total_species
	summary_text += "Vivantes : %d | Mortes : %d\n" % [alive_count, dead_count]
	summary_text += "==================================================\n"

	return summary_text

# --- Exporter en TXT ---
func _on_export_log_pressed():
	if simulation_logs.is_empty():
		push_warning("Aucun log à exporter")
		return

	var timestamp = Time.get_datetime_string_from_system().replace(":", "-")
	var file_path = "%s/simulation_summary_%s.txt" % [logs_folder, timestamp]
	print("Export path: ", file_path)

	var file = FileAccess.open(file_path, FileAccess.WRITE)
	if file == null:
		push_error("Impossible de créer le fichier d'export")
		return

	file.store_string(generate_summary_text())
	file.close()

	print("✓ Résumé exporté dans: %s" % file_path)

# --- Fonctions utilitaires ---
func log_simulation_step(step_data: Dictionary):
	add_step_log(step_data)

func clear_logs():
	simulation_logs.clear()

# --- Gestion du Header ---
func _on_settings_pressed():
	if settings_panel:
		settings_panel.visible = !settings_panel.visible

func _on_quit_pressed():
	get_tree().quit()

func _on_mode_selected(index: int):
	var id = mode_option.get_item_id(index)
	match id:
		0:
			DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_FULLSCREEN)
		1:
			DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_WINDOWED)
			var screen_idx = DisplayServer.window_get_current_screen()
			var screen_size = DisplayServer.screen_get_size(screen_idx)
			# Reduce size slightly so the title bar isn't off-screen on 1080p
			var target_size = Vector2i(screen_size.x - 100, screen_size.y - 100)
			if target_size.x > 1600: target_size = Vector2i(1600, 900)
			DisplayServer.window_set_size(target_size)
			DisplayServer.window_set_position((screen_size - target_size) / 2)
		2:
			DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_MAXIMIZED)

func _on_world_loading():
	if loading_overlay:
		if loading_overlay.has_node("Label"):
			loading_overlay.get_node("Label").text = "Génération du monde en cours..."
		loading_overlay.visible = true

func _on_world_loaded():
	if loading_overlay:
		loading_overlay.visible = false

func _on_simulation_computing():
	if loading_overlay:
		if loading_overlay.has_node("Label"):
			loading_overlay.get_node("Label").text = "Génération de la simulation en cours..."
		loading_overlay.visible = true

func _on_simulation_computed():
	if loading_overlay:
		loading_overlay.visible = false

## Controle l'ecran d'accueil et l'affichage progressif des journaux de simulation.
extends Control

# --- Références aux nodes ---
@onready var export_button = $MainVBox/TopBar/Margin/HBox/ExportLogBtn
@onready var settings_btn = $MainVBox/TopBar/Margin/HBox/SettingsBtn
@onready var quit_btn = $MainVBox/TopBar/Margin/HBox/QuitBtn
@onready var settings_panel = $SettingsPanel
@onready var mode_option = $SettingsPanel/VBoxContainer/ModeOption
@onready var loading_overlay = $MainVBox/MainHBox/MainArea/LoadingOverlay
@onready var world = $MainVBox/MainHBox/MainArea/SubViewportContainer/SubViewport/World
@onready var camera = $MainVBox/MainHBox/MainArea/SubViewportContainer/SubViewport/World/Camera2D
const BASE_SPEED_MS: float = 50.0

@onready var zoom_in_btn = $MainVBox/MainHBox/MainArea/FloatingControls/Margin/HBox/ZoomInBtn
@onready var zoom_out_btn = $MainVBox/MainHBox/MainArea/FloatingControls/Margin/HBox/ZoomOutBtn
@onready var speed_05x_btn = get_node_or_null("MainVBox/MainHBox/MainArea/FloatingControls/Margin/HBox/Speed05x")
@onready var speed_1x_btn = get_node_or_null("MainVBox/MainHBox/MainArea/FloatingControls/Margin/HBox/Speed1x")
@onready var speed_2x_btn = get_node_or_null("MainVBox/MainHBox/MainArea/FloatingControls/Margin/HBox/Speed2x")
@onready var speed_3x_btn = get_node_or_null("MainVBox/MainHBox/MainArea/FloatingControls/Margin/HBox/Speed3x")
@onready var speed_custom_spin = get_node_or_null("MainVBox/MainHBox/MainArea/FloatingControls/Margin/HBox/SpeedCustomSpin")
@onready var world_config_btn = $MainVBox/TopBar/Margin/HBox/WorldConfigBtn
@onready var world_configurator = $WorldConfigurator
@onready var species_card = get_node_or_null("MainVBox/MainHBox/LeftSidebar/Margin/VBox/SpeciesCard")

@onready var graph_population = $MainVBox/MainHBox/LeftSidebar/Margin/VBox/GraphPopulation
@onready var graph_food = $MainVBox/MainHBox/LeftSidebar/Margin/VBox/GraphFood
@onready var graph_death = get_node_or_null("MainVBox/MainHBox/RightSidebar/Margin/VBox/GraphDeath")
@onready var graph_energy = get_node_or_null("MainVBox/MainHBox/RightSidebar/Margin/VBox/GraphEnergy")

@onready var sim_status_label = $MainVBox/MainHBox/LeftSidebar/Margin/VBox/SimulationInfoBox/SimStatusLabel
@onready var sim_cycle_label = $MainVBox/MainHBox/LeftSidebar/Margin/VBox/SimulationInfoBox/SimCycleLabel
@onready var sim_population_label = $MainVBox/MainHBox/LeftSidebar/Margin/VBox/SimulationInfoBox/SimPopulationLabel
@onready var sim_time_label = $MainVBox/MainHBox/LeftSidebar/Margin/VBox/SimulationInfoBox/SimTimeLabel
@onready var sim_daynight_label = $MainVBox/MainHBox/LeftSidebar/Margin/VBox/SimulationInfoBox/SimDayNightLabel
@onready var sim_speed_label = $MainVBox/MainHBox/LeftSidebar/Margin/VBox/SimulationInfoBox/SimSpeedLabel
@onready var sim_zoom_label = $MainVBox/MainHBox/LeftSidebar/Margin/VBox/SimulationInfoBox/SimZoomLabel
@onready var action_log_label = get_node_or_null("MainVBox/MainHBox/RightSidebar/Margin/VBox/ActionLogPanel/ActionLogMargin/ActionLogLabel")
@onready var death_log_label = $MainVBox/MainHBox/RightSidebar/Margin/VBox/DeathLogPanel/DeathLogMargin/DeathLogLabel

# --- Variables principales ---
var simulation_logs = []          # Données chargées depuis summary.json
var current_step_data = {}
var simulation_data = {}          # Données du fichier simulation.json (actions, motivations)
var current_speed_text = "1x"
var previous_alive_states = {}
var death_logs: Array = []
var action_logs: Array = []
var last_animal_actions: Dictionary = {}


# --- Variables Audio & SFX ---
const SETTINGS_FILE_PATH = "user://audio_settings.cfg"
var sfx_volume: float = 0.25
var is_sfx_muted: bool = false
var sfx_player_ui: AudioStreamPlayer
var sfx_player_open_close: AudioStreamPlayer

var sfx_click_stream: AudioStream = null
var sfx_hover_stream: AudioStream = null
var sfx_open_stream: AudioStream = null
var sfx_close_stream: AudioStream = null

func _load_audio_settings() -> void:
	var config = ConfigFile.new()
	var err = config.load(SETTINGS_FILE_PATH)
	if err == OK:
		sfx_volume = float(config.get_value("audio", "sfx_volume", 0.25))
		is_sfx_muted = bool(config.get_value("audio", "is_sfx_muted", false))
	else:
		sfx_volume = 0.25
		is_sfx_muted = false

func _save_audio_settings() -> void:
	var config = ConfigFile.new()
	config.load(SETTINGS_FILE_PATH)
	config.set_value("audio", "sfx_volume", sfx_volume)
	config.set_value("audio", "is_sfx_muted", is_sfx_muted)
	config.save(SETTINGS_FILE_PATH)



# --- Configuration ---
@export var logs_folder: String = ""
@export var poll_interval := 0.5
var last_step_file_index := 0

# --- Ready ---
func _ready():
	_setup_settings_ui_and_audio()

	if export_button:

		export_button.pressed.connect(_on_export_log_pressed)
	if settings_btn:
		settings_btn.pressed.connect(_on_settings_pressed)
	if quit_btn:
		quit_btn.pressed.connect(_on_quit_pressed)
	if world_config_btn:
		world_config_btn.pressed.connect(_on_world_config_pressed)
	if zoom_in_btn:
		zoom_in_btn.pressed.connect(_on_zoom_in_pressed)
	if zoom_out_btn:
		zoom_out_btn.pressed.connect(_on_zoom_out_pressed)
	var floating_hbox = get_node_or_null("MainVBox/MainHBox/MainArea/FloatingControls/Margin/HBox")
	if floating_hbox:
		if not speed_05x_btn and speed_1x_btn:
			speed_05x_btn = Button.new()
			speed_05x_btn.name = "Speed05x"
			speed_05x_btn.text = "0.5x"
			if speed_1x_btn.has_theme_stylebox_override("normal"):
				speed_05x_btn.add_theme_stylebox_override("normal", speed_1x_btn.get_theme_stylebox("normal"))
			floating_hbox.add_child(speed_05x_btn)
			floating_hbox.move_child(speed_05x_btn, 0)
			
		if not speed_custom_spin:
			speed_custom_spin = SpinBox.new()
			speed_custom_spin.name = "SpeedCustomSpin"
			speed_custom_spin.min_value = 0.1
			speed_custom_spin.max_value = 5.0
			speed_custom_spin.step = 0.1
			speed_custom_spin.value = 1.0
			speed_custom_spin.suffix = "x"
			speed_custom_spin.custom_arrow_step = 0.1
			floating_hbox.add_child(speed_custom_spin)

	if speed_05x_btn:
		speed_05x_btn.pressed.connect(func(): set_speed_multiplier(0.5))
	if speed_1x_btn:
		speed_1x_btn.pressed.connect(func(): set_speed_multiplier(1.0))
	if speed_2x_btn:
		speed_2x_btn.pressed.connect(func(): set_speed_multiplier(2.0))
	if speed_3x_btn:
		speed_3x_btn.pressed.connect(func(): set_speed_multiplier(3.0))
	if speed_custom_spin:
		speed_custom_spin.value_changed.connect(func(val: float): set_speed_multiplier(val, false))
		var line_edit = speed_custom_spin.get_line_edit()
		if line_edit:
			line_edit.text_submitted.connect(func(new_text: String):
				var sanitized = new_text.replace(",", ".").replace("x", "").strip_edges()
				if sanitized.is_valid_float():
					set_speed_multiplier(float(sanitized), true)
			)
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
		if world.has_signal("step_received"):
			world.step_received.connect(log_simulation_step)
		if world.has_signal("species_selected"):
			world.species_selected.connect(_on_species_selected)
		if world.has_signal("species_deselected"):
			world.species_deselected.connect(_on_species_deselected)
		if not world.world_ready:
			if loading_overlay.has_node("Label"):
				loading_overlay.get_node("Label").text = "En attente du serveur..."
			loading_overlay.visible = true

	if species_card:
		if species_card.has_signal("close_requested"):
			species_card.close_requested.connect(_on_species_card_closed)
		if species_card.has_signal("center_requested"):
			species_card.center_requested.connect(_on_species_card_center)

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

var _was_connected := false

func _process(_delta: float) -> void:
	if world and "connected" in world:
		if sim_status_label:
			if not world.connected:
				sim_status_label.text = "Simulation : Arrêt (Déconnecté)"
				sim_status_label.add_theme_color_override("font_color", Color(0.8, 0.3, 0.3))
			elif world.get("run_completed"):
				sim_status_label.text = "Simulation : Arrêt (Terminé)"
				sim_status_label.add_theme_color_override("font_color", Color(0.2, 0.6, 0.9))
			elif world.get("running"):
				sim_status_label.text = "Simulation : Marche"
				sim_status_label.add_theme_color_override("font_color", Color(0.2, 0.9, 0.4))
			else:
				sim_status_label.text = "Simulation : Arrêt (Pause)"
				sim_status_label.add_theme_color_override("font_color", Color(0.9, 0.7, 0.2))

		if sim_speed_label:
			sim_speed_label.text = "Vitesse : " + current_speed_text
			sim_speed_label.add_theme_color_override("font_color", Color(0.9, 0.6, 0.3))
			
		if sim_zoom_label and camera:
			sim_zoom_label.text = "Zoom : %.1fx" % camera.zoom.x
			sim_zoom_label.add_theme_color_override("font_color", Color(0.7, 0.8, 0.9))

		if world.connected and not _was_connected:
			_was_connected = true
			# Le serveur vient de se connecter, on cache l'ecran d'attente s'il ne charge pas deja le monde
			if loading_overlay and loading_overlay.visible:
				if loading_overlay.has_node("Label"):
					var text = loading_overlay.get_node("Label").text
					if text == "En attente du serveur...":
						loading_overlay.visible = false
		elif not world.connected and _was_connected:
			_was_connected = false
			# Deconnexion detectee, on remet l'ecran d'attente
			if loading_overlay:
				if loading_overlay.has_node("Label"):
					loading_overlay.get_node("Label").text = "En attente du serveur..."
				loading_overlay.visible = true

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


# --- Charger le summary.json d'un sous-dossier ---
# Le simulation.json complet n'est plus charge ici : ces fichiers peuvent
# peser plusieurs Go (donnees par pas + animaux qui survivent longtemps),
# et etaient parses en entier pour CHAQUE run passe au demarrage, bloquant
# le lancement pendant plusieurs minutes. Le chargement complet d'un run se
# fait desormais uniquement via l'import manuel explicite (FileDialog).
func load_summary_in_folder(folder_path: String):
	var summary_path = "%s/summary.json" % folder_path
	if FileAccess.file_exists(summary_path):
		print("  Summary trouvé:", summary_path)
		load_simulation_json(summary_path)
	else:
		print("  Aucun summary.json trouvé dans:", folder_path)

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
	
	_update_graphs(step_data)

func _extract_species_list(step_data: Dictionary) -> Array:
	if not step_data.has("species"):
		return []
	var raw = step_data["species"]
	if typeof(raw) == TYPE_ARRAY:
		return raw
	elif typeof(raw) == TYPE_DICTIONARY:
		var arr: Array = []
		for key in raw.keys():
			var val = raw[key]
			if typeof(val) == TYPE_DICTIONARY:
				arr.append(val)
		return arr
	return []

func _get_vitality(entry: Dictionary) -> float:
	if entry.has("after") and typeof(entry["after"]) == TYPE_DICTIONARY:
		return float(entry["after"].get("vitality", 0.0))
	if entry.has("before") and typeof(entry["before"]) == TYPE_DICTIONARY:
		return float(entry["before"].get("vitality", 0.0))
	return float(entry.get("vitality", 0.0))

func _get_animal_unique_id(entry: Dictionary, index: int) -> String:
	var base_name := String(entry.get("name", entry.get("display_name", "Inconnu")))
	var animal_id = entry.get("animal_id")
	if animal_id != null and str(animal_id) != "":
		return base_name + "_" + str(animal_id)
	return base_name + "_" + str(index)

func _is_alive(entry: Dictionary) -> bool:
	if entry.has("after") and typeof(entry["after"]) == TYPE_DICTIONARY:
		var after = entry["after"]
		if after.has("alive"):
			return bool(after["alive"])
		return float(after.get("vitality", 0.0)) > 0.0
	if entry.has("before") and typeof(entry["before"]) == TYPE_DICTIONARY:
		return bool(entry["before"].get("alive", true))
	if entry.has("vitality"):
		return float(entry["vitality"]) > 0.0
	return true

func _update_graphs(step_data: Dictionary):
	var pop = 0
	var food = 0
	var dead = 0
	var total_energy = 0.0
	
	var species_counts = {}
	var newly_dead = []
	
	var species_list = _extract_species_list(step_data)
	for i in range(species_list.size()):
		var s = species_list[i]
		if typeof(s) != TYPE_DICTIONARY:
			continue

		var is_alive = _is_alive(s)
		var s_name = String(s.get("name", s.get("display_name", "Inconnu")))
		var unique_id = _get_animal_unique_id(s, i)
		if previous_alive_states.has(unique_id) and previous_alive_states[unique_id] and not is_alive:
			newly_dead.append(s)
		previous_alive_states[unique_id] = is_alive

		if is_alive:
			pop += 1
			total_energy += _get_vitality(s)
			var cap_name = _format_species_name(s_name)
			species_counts[cap_name] = species_counts.get(cap_name, 0) + 1
		else:
			dead += 1

	for dead_entry in newly_dead:
		_add_death_log(dead_entry, step_data)

	_update_action_log(step_data)

	if step_data.has("world_state") and step_data["world_state"].has("food_available"):
		food = step_data["world_state"]["food_available"]
	
	var avg_energy = 0.0
	if pop > 0:
		avg_energy = total_energy / float(pop)
		
	var species_colors = {}
	for s_name in species_counts.keys():
		var h = float(s_name.hash() % 1000) / 1000.0
		var c = Color.from_hsv(h, 0.8, 0.9)
		species_colors[s_name] = c

	if graph_population:
		if graph_population.has_method("set_title"):
			graph_population.set_title("Population par espèce")
		if graph_population.has_method("set_bar_data") and not species_counts.is_empty():
			graph_population.set_bar_data(species_counts, species_colors)
		elif graph_population.has_method("add_value"):
			graph_population.add_value(pop)

	if graph_food and graph_food.has_method("add_value"):
		graph_food.add_value(food)
	if graph_death and graph_death.has_method("add_value"):
		graph_death.add_value(dead)
	if graph_energy and graph_energy.has_method("add_value"):
		graph_energy.add_value(avg_energy)

	if sim_population_label:
		sim_population_label.text = "Population Totale : " + str(pop)
		sim_population_label.add_theme_color_override("font_color", Color(1.0, 0.85, 0.4))
		
	if sim_cycle_label:
		sim_cycle_label.add_theme_color_override("font_color", Color(0.4, 0.9, 0.7))
		if step_data.has("step"):
			sim_cycle_label.text = "Cycle : " + str(step_data["step"])
		elif step_data.has("cycle"):
			sim_cycle_label.text = "Cycle : " + str(step_data["cycle"])
			
	if sim_time_label and step_data.has("hour") and step_data.has("minute"):
		var h = int(step_data["hour"])
		var m = int(step_data["minute"])
		sim_time_label.text = "Heure : %02d:%02d" % [h, m]
		sim_time_label.add_theme_color_override("font_color", Color(0.4, 0.8, 0.9))
		if sim_daynight_label:
			if h >= 6 and h < 18:
				sim_daynight_label.text = "Période : Jour"
				sim_daynight_label.add_theme_color_override("font_color", Color(1.0, 0.9, 0.3))
			else:
				sim_daynight_label.text = "Période : Nuit"
				sim_daynight_label.add_theme_color_override("font_color", Color(0.5, 0.5, 0.9))



func _format_species_name(raw_name: String) -> String:
	if raw_name.is_empty():
		return raw_name
	var cleaned = raw_name.replace("_", " ").strip_edges()
	var words = cleaned.split(" ")
	var formatted_words = []
	for word in words:
		if word.length() > 0:
			var first_char = word.left(1).to_upper()
			var rest_chars = word.substr(1).to_lower()
			formatted_words.append(first_char + rest_chars)
	return " ".join(formatted_words)

func _get_action_log_label() -> RichTextLabel:
	if action_log_label and is_instance_valid(action_log_label):
		return action_log_label
	action_log_label = get_node_or_null("MainVBox/MainHBox/RightSidebar/Margin/VBox/ActionLogPanel/ActionLogMargin/ActionLogLabel")
	return action_log_label

func _get_death_log_label() -> RichTextLabel:
	if death_log_label and is_instance_valid(death_log_label):
		return death_log_label
	death_log_label = get_node_or_null("MainVBox/MainHBox/RightSidebar/Margin/VBox/DeathLogPanel/DeathLogMargin/DeathLogLabel")
	return death_log_label


func _add_death_log(entry: Dictionary, step_data: Dictionary):
	var animal_name = String(entry.get("name", entry.get("display_name", "")))
	var time_str = "--:--"
	if step_data.has("hour"):
		var h = int(step_data["hour"])
		var m = int(step_data.get("minute", 0))
		time_str = "%02dh%02d" % [h, m]

	var cause: String = String(entry.get("death_cause", ""))
	if cause.is_empty() or cause == "null":
		var after_dict = entry.get("after", {})
		if typeof(after_dict) == TYPE_DICTIONARY:
			cause = String(after_dict.get("death_cause", ""))
		if cause.is_empty() or cause == "null":
			var before_dict = entry.get("before", {})
			if typeof(before_dict) == TYPE_DICTIONARY:
				var thirst = float(before_dict.get("thirst", 0.0))
				var hunger = float(before_dict.get("hunger", 0.0))
				var fatigue = float(before_dict.get("fatigue", 0.0))
				if thirst >= 80.0:
					cause = "Mort de soif"
				elif hunger >= 80.0:
					cause = "Mort de faim"
				elif fatigue >= 90.0:
					cause = "Épuisement"
				else:
					cause = "Chassé par un prédateur"

	if cause.is_empty() or cause == "null":
		cause = "Mort de cause inconnue"

	var formatted_name = _format_species_name(animal_name)
	var log_str = "[color=#e06c75][%s] 💀 [b]%s[/b]\n   ➜ %s[/color]" % [time_str, formatted_name, cause]
	death_logs.push_front(log_str)
	if death_logs.size() > 50:
		death_logs.pop_back()
		
	var target_label = _get_death_log_label()
	if target_label:
		target_label.text = "\n\n".join(death_logs)

func _update_action_log(step_data: Dictionary):
	var target_label = _get_action_log_label()
	if not target_label:
		return

	var species_list = _extract_species_list(step_data)
	if species_list.is_empty():
		return

	var h = int(step_data.get("hour", 0))
	var m = int(step_data.get("minute", 0))
	var time_str = "%02dh%02d" % [h, m]

	var new_entries_added = false

	for i in range(species_list.size()):
		var entry = species_list[i]
		if typeof(entry) != TYPE_DICTIONARY:
			continue

		if not _is_alive(entry):
			continue

		var animal_name = String(entry.get("name", entry.get("display_name", "")))
		if animal_name.is_empty():
			continue

		var unique_id = _get_animal_unique_id(entry, i)
		var action = String(entry.get("action", "")).strip_edges()
		var motivation = String(entry.get("motivation", "")).strip_edges()
		var food_evt = entry.get("food_event")

		var action_text = _format_action_text(action, motivation, entry, food_evt)
		if action_text.is_empty():
			continue

		var formatted_name = _format_species_name(animal_name)
		var last_action = last_animal_actions.get(unique_id, "")
		if last_action != action_text:
			last_animal_actions[unique_id] = action_text
			var log_str = "[color=#61afef][%s][/color] [b]%s[/b]\n   ➜ %s" % [time_str, formatted_name, action_text]
			action_logs.push_front(log_str)
			if action_logs.size() > 80:
				action_logs.pop_back()
			new_entries_added = true

	if new_entries_added and target_label:
		target_label.text = "\n\n".join(action_logs)



func _format_action_text(action: String, motivation: String, entry: Dictionary = {}, food_evt: Variant = null) -> String:
	if food_evt is Dictionary:
		var evt_type = String(food_evt.get("type", "")).to_lower()
		if evt_type.contains("drink"):
			return "💧 Boit de l'eau à la rivière"
		elif evt_type.contains("carcass") or evt_type.contains("meat"):
			return "🍖 Dévore une carcasse"
		elif evt_type.contains("plant") or evt_type.contains("eat"):
			return "🌿 Mange de la nourriture"
		elif evt_type.contains("kill"):
			return "⚔️ A abattu une proie !"

	var act_lower = action.to_lower()
	var mot_lower = motivation.to_lower()

	# 1. Prédation / Attaque
	if act_lower.contains("kill") or mot_lower.contains("tue"):
		return "⚔️ A abattu une proie !"
	elif act_lower.contains("hunt") or act_lower.contains("predat") or act_lower.contains("pack_attack") or mot_lower.contains("chasse"):
		return "🐾 Traque et chasse une proie"

	# 2. Fuite
	elif act_lower.contains("flee") or mot_lower.contains("fuite") or mot_lower.contains("attaque"):
		return "🏃 Fuit un prédateur !"

	# 3. Boire / Soif
	elif act_lower.contains("drink"):
		return "💧 Boit de l'eau à la rivière"
	elif act_lower.contains("seek_water") or (act_lower.contains("water") and not act_lower.contains("explore")):
		return "💧 Cherche un point d'eau"

	# 4. Manger / Faim
	elif act_lower.contains("eat") or act_lower.contains("gorge") or act_lower.contains("consume"):
		return "🌿 Mange de la nourriture"
	elif act_lower.contains("seen_food") or act_lower.contains("move_to_food"):
		return "🌿 Se dirige vers de la nourriture (vue)"
	elif act_lower.contains("seek_food"):
		return "🌿 Cherche de la nourriture"

	# 5. Repos / Sommeil
	elif act_lower.contains("rest") or act_lower.contains("sleep") or act_lower.contains("guard") or mot_lower.contains("repos") or mot_lower.contains("fatigue"):
		return "😴 Se repose"

	# 6. Groupe / Cohésion
	elif act_lower.contains("cohesion") or act_lower.contains("herd") or mot_lower.contains("groupe"):
		return "🐄 Se déplace en groupe"

	# 7. Exploration / Vadrouille
	elif act_lower.contains("explore_for_food") or mot_lower.contains("faim"):
		return "🌿 Cherche de la nourriture"
	elif act_lower.contains("explore") or act_lower.contains("wander") or act_lower.contains("idle") or mot_lower.contains("exploration") or mot_lower.contains("errance"):
		return "🌍 Vadrouille dans la savane"

	elif not action.is_empty():
		return action
	elif not motivation.is_empty():
		return motivation

	var after_dict = entry.get("after", {})
	if typeof(after_dict) == TYPE_DICTIONARY:
		if bool(after_dict.get("resting", false)):
			return "😴 Se repose"
		var hunger = float(after_dict.get("hunger", 0.0))
		var thirst = float(after_dict.get("thirst", 0.0))
		if thirst > 70.0:
			return "💧 Cherche un point d'eau"
		elif hunger > 70.0:
			return "🌿 Cherche de la nourriture"

	return "🌍 Vadrouille dans la savane"

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
		var sp_list = _extract_species_list(step)
		for s in sp_list:
			if typeof(s) != TYPE_DICTIONARY:
				continue
			var sname = String(s.get("name", s.get("display_name", "Inconnu")))
			species_seen[sname] = s  # Dernière version remplace l'ancienne

	# Générer le résumé
	for sname in species_seen.keys():
		var s = species_seen[sname]
		total_species += 1
		var vitality = _get_vitality(s)
		var is_alive = _is_alive(s)
		var status = "Vivant" if is_alive else "Mort"
		if is_alive:
			alive_count += 1
		else:
			dead_count += 1

		# Lire la position depuis after ou before
		var after_d = s.get("after", {})
		var before_d = s.get("before", {})
		var pos_x = 0.0
		var pos_y = 0.0
		var hunger_v = 0.0
		var thirst_v = 0.0
		var fatigue_v = 0.0
		if typeof(after_d) == TYPE_DICTIONARY:
			pos_x = float(after_d.get("x", 0.0))
			pos_y = float(after_d.get("y", 0.0))
			hunger_v = float(after_d.get("hunger", 0.0))
			thirst_v = float(after_d.get("thirst", 0.0))
			fatigue_v = float(after_d.get("fatigue", 0.0))
		elif typeof(before_d) == TYPE_DICTIONARY:
			pos_x = float(before_d.get("x", 0.0))
			pos_y = float(before_d.get("y", 0.0))
			hunger_v = float(before_d.get("hunger", 0.0))
			thirst_v = float(before_d.get("thirst", 0.0))
			fatigue_v = float(before_d.get("fatigue", 0.0))

		var action = String(s.get("action", "N/A"))
		var motivation = String(s.get("motivation", "N/A"))

		# Si action ou motivation manquante → chercher dans simulation.json
		if (action == "N/A" or motivation == "N/A") and simulation_data.has(sname):
			var sim_entry = simulation_data[sname]
			action = sim_entry.get("action", action)
			motivation = sim_entry.get("motivation", motivation)

		summary_text += "%s\n" % sname
		summary_text += "  Type : %s | Sexe : %s | Âge : %.2f ans (%s)\n" % [
			s.get("species_type", "N/A"),
			s.get("sex", "N/A"),
			float(s.get("age_years", 0.0)),
			String(s.get("age_stage", "N/A"))
		]
		summary_text += "  Position : (%.0f, %.0f)\n" % [pos_x, pos_y]
		summary_text += "  Action : %s\n" % action
		summary_text += "  Motivation : %s\n" % motivation
		summary_text += "  Vitalité : %.1f | Faim : %.1f | Soif : %.1f | Fatigue : %.1f\n" % [
			vitality, hunger_v, thirst_v, fatigue_v
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
	previous_alive_states.clear()
	death_logs.clear()
	action_logs.clear()
	last_animal_actions.clear()
	if death_log_label:
		death_log_label.text = "Aucun décès pour le moment."
	if action_log_label:
		action_log_label.text = "Aucune action récente."
	if graph_population and graph_population.has_method("clear_data"):
		graph_population.clear_data()
	if graph_food and graph_food.has_method("clear_data"):
		graph_food.clear_data()
	if graph_death and graph_death.has_method("clear_data"):
		graph_death.clear_data()
	if graph_energy and graph_energy.has_method("clear_data"):
		graph_energy.clear_data()
	if species_card:
		species_card.visible = false

func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("ui_cancel"):
		if settings_panel and settings_panel.visible:
			_close_settings_panel()
			get_viewport().set_input_as_handled()

# --- Gestion du Header & Paramètres ---
func _on_settings_pressed():
	if settings_panel:
		if settings_panel.visible:
			_close_settings_panel()
		else:
			_open_settings_panel()

func _open_settings_panel():
	if settings_panel:
		settings_panel.visible = true
		play_open_close_sfx(sfx_open_stream)

func _close_settings_panel():
	if settings_panel and settings_panel.visible:
		settings_panel.visible = false
		play_open_close_sfx(sfx_close_stream)

func play_ui_sfx(stream: AudioStream):
	if is_sfx_muted or not stream or not sfx_player_ui:
		return
	sfx_player_ui.stream = stream
	sfx_player_ui.play()

func play_open_close_sfx(stream: AudioStream):
	if is_sfx_muted or not stream or not sfx_player_open_close:
		return
	sfx_player_open_close.stream = stream
	sfx_player_open_close.play()

func _bind_ui_sounds(node: Node):
	if not node or not (node is Control):
		return
	if node is SubViewportContainer:
		return
	if node is Button:
		if not node.is_connected("pressed", Callable(self, "_on_generic_button_pressed")):
			node.pressed.connect(_on_generic_button_pressed)
		if not node.is_connected("mouse_entered", Callable(self, "_on_generic_button_hover")):
			node.mouse_entered.connect(_on_generic_button_hover)
	for child in node.get_children():
		_bind_ui_sounds(child)

func _on_generic_button_pressed():
	play_ui_sfx(sfx_click_stream)

func _on_generic_button_hover():
	play_ui_sfx(sfx_hover_stream)

func _apply_custom_style_to_button(btn: Button, border_col: Color = Color(0.16, 0.65, 0.58, 0.8)):
	if not btn or not is_instance_valid(btn):
		return
	if btn.name == "CloseBtn":
		return

	var sb_normal = StyleBoxFlat.new()
	sb_normal.bg_color = Color(0.12, 0.22, 0.28, 0.95)
	sb_normal.set_border_width_all(1)
	sb_normal.border_color = border_col
	sb_normal.set_corner_radius_all(8)
	sb_normal.content_margin_left = 14
	sb_normal.content_margin_right = 14
	sb_normal.content_margin_top = 6
	sb_normal.content_margin_bottom = 6
	btn.add_theme_stylebox_override("normal", sb_normal)

	var sb_hover = StyleBoxFlat.new()
	sb_hover.bg_color = Color(0.16, 0.32, 0.40, 1.0)
	sb_hover.set_border_width_all(1)
	sb_hover.border_color = Color(min(1.0, border_col.r * 1.3), min(1.0, border_col.g * 1.3), min(1.0, border_col.b * 1.3), 1.0)
	sb_hover.set_corner_radius_all(8)
	sb_hover.content_margin_left = 14
	sb_hover.content_margin_right = 14
	sb_hover.content_margin_top = 6
	sb_hover.content_margin_bottom = 6
	btn.add_theme_stylebox_override("hover", sb_hover)

	var sb_press = StyleBoxFlat.new()
	sb_press.bg_color = Color(0.08, 0.16, 0.22, 1.0)
	sb_press.set_border_width_all(1)
	sb_press.border_color = border_col
	sb_press.set_corner_radius_all(8)
	sb_press.content_margin_left = 14
	sb_press.content_margin_right = 14
	sb_press.content_margin_top = 6
	sb_press.content_margin_bottom = 6
	btn.add_theme_stylebox_override("pressed", sb_press)

func _style_all_ui_buttons(node: Node):
	if not node or not (node is Control) or node is SubViewportContainer:
		return
	if node is Button:
		var btn = node as Button
		if btn.name == "QuitBtn" or btn.name == "QuitButton" or btn.text.to_lower().contains("quitter"):
			_apply_custom_style_to_button(btn, Color(0.85, 0.3, 0.35, 0.8))
		elif btn.name == "StartBtn" or btn.name == "StartPauseBtn" or btn.text.to_lower().contains("start"):
			_apply_custom_style_to_button(btn, Color(0.2, 0.8, 0.5, 0.9))
		else:
			_apply_custom_style_to_button(btn, Color(0.16, 0.65, 0.58, 0.8))
	for child in node.get_children():
		_style_all_ui_buttons(child)

func _setup_settings_ui_and_audio():
	_load_audio_settings()

	# 1. Styliser tous les boutons UI avec le thème sombre + bordures réactives
	_style_all_ui_buttons(self)
	if settings_btn:
		settings_btn.text = "⚙️ Paramètres"


	# 2. Styliser le SettingsPanel & Ajuster sa taille/marges
	if settings_panel:
		settings_panel.z_index = 100
		settings_panel.offset_left = -270.0
		settings_panel.offset_top = -210.0
		settings_panel.offset_right = 270.0
		settings_panel.offset_bottom = 210.0

		var sb_panel = StyleBoxFlat.new()
		sb_panel.bg_color = Color(0.09, 0.13, 0.19, 0.98)
		sb_panel.set_border_width_all(2)
		sb_panel.border_color = Color(0.16, 0.65, 0.58, 0.7)
		sb_panel.set_corner_radius_all(16)
		sb_panel.shadow_color = Color(0, 0, 0, 0.6)
		sb_panel.shadow_size = 20
		settings_panel.add_theme_stylebox_override("panel", sb_panel)

		# Bouton Croix '✕' de fermeture en haut à droite
		var close_btn = settings_panel.get_node_or_null("CloseBtn")
		if not close_btn:
			close_btn = Button.new()
			close_btn.name = "CloseBtn"
			close_btn.text = "✕"
			close_btn.focus_mode = Control.FOCUS_NONE
			close_btn.custom_minimum_size = Vector2(32, 32)
			close_btn.size = Vector2(32, 32)
			close_btn.position = Vector2(494, 14)
			close_btn.add_theme_font_size_override("font_size", 16)
			close_btn.add_theme_color_override("font_color", Color(1, 1, 1, 0.95))

			var sb_empty = StyleBoxEmpty.new()
			close_btn.add_theme_stylebox_override("focus", sb_empty)

			var sb_c_norm = StyleBoxFlat.new()
			sb_c_norm.bg_color = Color(0.85, 0.25, 0.3, 0.25)
			sb_c_norm.set_border_width_all(0)
			sb_c_norm.set_corner_radius_all(16)
			sb_c_norm.content_margin_left = 0
			sb_c_norm.content_margin_top = 0
			sb_c_norm.content_margin_right = 0
			sb_c_norm.content_margin_bottom = 0
			close_btn.add_theme_stylebox_override("normal", sb_c_norm)

			var sb_c_hov = StyleBoxFlat.new()
			sb_c_hov.bg_color = Color(0.95, 0.25, 0.3, 0.95)
			sb_c_hov.set_border_width_all(0)
			sb_c_hov.set_corner_radius_all(16)
			sb_c_hov.content_margin_left = 0
			sb_c_hov.content_margin_top = 0
			sb_c_hov.content_margin_right = 0
			sb_c_hov.content_margin_bottom = 0
			close_btn.add_theme_stylebox_override("hover", sb_c_hov)

			var sb_c_press = StyleBoxFlat.new()
			sb_c_press.bg_color = Color(0.7, 0.15, 0.2, 1.0)
			sb_c_press.set_border_width_all(0)
			sb_c_press.set_corner_radius_all(16)
			sb_c_press.content_margin_left = 0
			sb_c_press.content_margin_top = 0
			sb_c_press.content_margin_right = 0
			sb_c_press.content_margin_bottom = 0
			close_btn.add_theme_stylebox_override("pressed", sb_c_press)

			settings_panel.add_child(close_btn)


		if not close_btn.is_connected("pressed", Callable(self, "_close_settings_panel")):
			close_btn.pressed.connect(_close_settings_panel)

		# Réorganisation et réduction des marges du VBoxContainer
		var vbox = settings_panel.get_node_or_null("VBoxContainer")
		if vbox:
			vbox.offset_left = 28.0
			vbox.offset_top = 24.0
			vbox.offset_right = -28.0
			vbox.offset_bottom = -24.0
			vbox.add_theme_constant_override("separation", 14)

			# Redimensionner le Label existant "Mode d'affichage"
			var display_label = vbox.get_node_or_null("Label")
			if display_label:
				display_label.text = "🖥️ Mode d'affichage"
				display_label.add_theme_font_size_override("font_size", 20)
				display_label.add_theme_color_override("font_color", Color(0.2, 0.8, 0.7, 1.0))

			# Redimensionner l'OptionButton existant
			if mode_option:
				mode_option.custom_minimum_size = Vector2(0, 44)
				mode_option.add_theme_font_size_override("font_size", 16)

			# Conteneur Audio
			if not vbox.has_node("AudioContainer"):
				var audio_box = VBoxContainer.new()
				audio_box.name = "AudioContainer"
				audio_box.add_theme_constant_override("separation", 10)

				var audio_title = Label.new()
				audio_title.text = "🔊 Effets Sonores (SFX)"
				audio_title.add_theme_color_override("font_color", Color(0.2, 0.8, 0.7, 1.0))
				audio_title.add_theme_font_size_override("font_size", 20)
				audio_box.add_child(audio_title)

				var slider_hbox = HBoxContainer.new()
				slider_hbox.add_theme_constant_override("separation", 12)

				var slider = HSlider.new()
				slider.min_value = 0.0
				slider.max_value = 100.0
				slider.step = 5.0
				slider.value = sfx_volume * 100.0
				slider.size_flags_horizontal = Control.SIZE_EXPAND_FILL
				slider.custom_minimum_size = Vector2(0, 28)

				var val_label = Label.new()
				val_label.text = str(int(sfx_volume * 100.0)) + "%"
				val_label.custom_minimum_size = Vector2(45, 0)
				val_label.add_theme_font_size_override("font_size", 15)

				var mute_cb = CheckBox.new()
				mute_cb.text = "Muet"
				mute_cb.focus_mode = Control.FOCUS_NONE
				mute_cb.button_pressed = is_sfx_muted
				mute_cb.add_theme_constant_override("h_separation", 10)
				mute_cb.add_theme_font_size_override("font_size", 15)
				mute_cb.custom_minimum_size = Vector2(85, 30)

				slider_hbox.add_child(slider)
				slider_hbox.add_child(val_label)
				slider_hbox.add_child(mute_cb)
				audio_box.add_child(slider_hbox)

				var test_btn = Button.new()
				test_btn.text = "🎵 Tester le son"
				test_btn.add_theme_font_size_override("font_size", 15)
				test_btn.custom_minimum_size = Vector2(0, 38)
				audio_box.add_child(test_btn)

				vbox.add_child(audio_box)

				var get_db_volume = func(vol: float, muted: bool) -> float:
					if muted or vol <= 0.001:
						return -80.0
					return linear_to_db(vol) - 10.0

				slider.value_changed.connect(func(v: float):
					sfx_volume = v / 100.0
					val_label.text = str(int(v)) + "%"
					var db_v = get_db_volume.call(sfx_volume, is_sfx_muted)
					if sfx_player_ui: sfx_player_ui.volume_db = db_v
					if sfx_player_open_close: sfx_player_open_close.volume_db = db_v
					_save_audio_settings()
				)

				mute_cb.toggled.connect(func(m: bool):
					is_sfx_muted = m
					var db_v = get_db_volume.call(sfx_volume, is_sfx_muted)
					if sfx_player_ui: sfx_player_ui.volume_db = db_v
					if sfx_player_open_close: sfx_player_open_close.volume_db = db_v
					_save_audio_settings()
				)

				test_btn.pressed.connect(func(): play_ui_sfx(sfx_click_stream))

	# 3. Initialiser les joueurs AudioStreamPlayer
	var init_db = -80.0 if is_sfx_muted else (linear_to_db(sfx_volume) - 10.0 if sfx_volume > 0.001 else -80.0)

	sfx_player_ui = AudioStreamPlayer.new()
	sfx_player_ui.name = "SFXPlayerUI"
	sfx_player_ui.volume_db = init_db
	add_child(sfx_player_ui)

	sfx_player_open_close = AudioStreamPlayer.new()
	sfx_player_open_close.name = "SFXPlayerOpenClose"
	sfx_player_open_close.volume_db = init_db
	add_child(sfx_player_open_close)


	# 4. Charger les sons si disponibles
	if ResourceLoader.exists("res://audio/sfx_click.wav"):
		sfx_click_stream = load("res://audio/sfx_click.wav")
	if ResourceLoader.exists("res://audio/sfx_hover.wav"):
		sfx_hover_stream = load("res://audio/sfx_hover.wav")
	if ResourceLoader.exists("res://audio/sfx_open.wav"):
		sfx_open_stream = load("res://audio/sfx_open.wav")
	if ResourceLoader.exists("res://audio/sfx_close.wav"):
		sfx_close_stream = load("res://audio/sfx_close.wav")

	_bind_ui_sounds(self)



func _on_world_config_pressed():
	if world_configurator and world_configurator.has_method("open_modal"):
		world_configurator.open_modal()

func _on_world_config_ready(config):
	pass # Handle logic when world config is ready

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
	clear_logs()
	set_speed_multiplier(1.0)
	if loading_overlay:
		if loading_overlay.has_node("Label"):
			loading_overlay.get_node("Label").text = "Génération du monde en cours..."
		loading_overlay.visible = true

func _on_world_loaded():
	if world and "precompute_pending" in world and world.precompute_pending:
		# La simulation est deja en train d'etre generee derriere, on ne cache pas l'overlay !
		return
	if loading_overlay:
		loading_overlay.visible = false

func _on_simulation_computing():
	set_speed_multiplier(1.0)
	if loading_overlay:
		if loading_overlay.has_node("Label"):
			loading_overlay.get_node("Label").text = "Génération de la simulation en cours..."
		loading_overlay.visible = true

func _on_simulation_computed():
	if loading_overlay:
		loading_overlay.visible = false

# --- Gestion du Zoom ---
func _on_zoom_in_pressed():
	if camera and camera.has_method("zoom_in"):
		camera.zoom_in()

func _on_zoom_out_pressed():
	if camera and camera.has_method("zoom_out"):
		camera.zoom_out()

func set_speed_multiplier(multiplier: float, update_spinbox: bool = true) -> void:
	var clamped_mult: float = clamp(multiplier, 0.1, 5.0)
	var delay_ms: float = max(1.0, BASE_SPEED_MS / clamped_mult)
	
	if world and world.has_method("set_speed"):
		world.set_speed(delay_ms)
		
	if abs(clamped_mult - 0.5) < 0.01:
		current_speed_text = "0.5x"
	elif abs(clamped_mult - 1.0) < 0.01:
		current_speed_text = "1x"
	elif abs(clamped_mult - 2.0) < 0.01:
		current_speed_text = "2x"
	elif abs(clamped_mult - 3.0) < 0.01:
		current_speed_text = "3x"
	else:
		var formatted = "%.1fx" % clamped_mult
		if formatted.ends_with(".0x"):
			formatted = formatted.replace(".0x", "x")
		current_speed_text = formatted
		
	if update_spinbox and speed_custom_spin:
		if speed_custom_spin.has_method("set_value_no_signal"):
			speed_custom_spin.set_value_no_signal(clamped_mult)
		else:
			speed_custom_spin.value = clamped_mult

# --- Gestion de la sélection d'espèce ---
func _on_species_selected(data: Dictionary) -> void:
	if species_card and species_card.has_method("display_species"):
		species_card.display_species(data)

func _on_species_deselected() -> void:
	if species_card:
		species_card.visible = false

func _on_species_card_closed() -> void:
	if world and world.has_method("deselect_species"):
		world.deselect_species()

func _on_species_card_center(target_pos: Vector2) -> void:
	if camera and camera.has_method("center_on_target"):
		camera.center_on_target(target_pos)

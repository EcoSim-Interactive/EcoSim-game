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
		if not world.world_ready:
			if loading_overlay.has_node("Label"):
				loading_overlay.get_node("Label").text = "En attente du serveur..."
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
	
	_update_graphs(step_data)

func _update_graphs(step_data: Dictionary):
	var pop = 0
	var food = 0
	var dead = 0
	var total_energy = 0.0
	
	var species_counts = {}
	var newly_dead = []
	
	if step_data.has("species"):
		for s in step_data["species"]:
			var is_alive = false
			if s.has("vitality"):
				is_alive = s.get("vitality", 0) > 0
			elif s.has("after") and s["after"] is Dictionary:
				is_alive = s["after"].get("alive", false)
			elif s.has("before") and s["before"] is Dictionary:
				is_alive = s["before"].get("alive", false)
			else:
				is_alive = true # Fallback au cas où

			var s_name = s.get("name", "Inconnu")
			if previous_alive_states.has(s_name) and previous_alive_states[s_name] and not is_alive:
				newly_dead.append(s_name)
			previous_alive_states[s_name] = is_alive

			if is_alive:
				pop += 1
				total_energy += s.get("vitality", 0)
				var cap_name = s_name.capitalize()
				species_counts[cap_name] = species_counts.get(cap_name, 0) + 1
			else:
				dead += 1
				
	for dead_name in newly_dead:
		_add_death_log(dead_name, step_data)

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

func _add_death_log(animal_name: String, step_data: Dictionary):
	var cycle = step_data.get("step", step_data.get("cycle", 0))
	var time_str = "--:--"
	if step_data.has("hour"):
		var h = int(step_data["hour"])
		var m = int(step_data.get("minute", 0))
		time_str = "%02dh%02d" % [h, m]

	var cause: String = ""
	if step_data.has("species") and typeof(step_data["species"]) == TYPE_ARRAY:
		for entry in step_data["species"]:
			if typeof(entry) == TYPE_DICTIONARY:
				var name_val = String(entry.get("name", entry.get("display_name", "")))
				if name_val == animal_name or String(entry.get("animal_id", "")) == animal_name:
					cause = String(entry.get("death_cause", ""))
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
					break

	if cause.is_empty() or cause == "null":
		cause = "Mort de cause inconnue"

	var log_str = "[color=#e06c75][%s] 💀 [b]%s[/b]\n   ➜ %s[/color]" % [time_str, animal_name, cause]
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
	if not step_data.has("species") or typeof(step_data["species"]) != TYPE_ARRAY:
		return

	var h = int(step_data.get("hour", 0))
	var m = int(step_data.get("minute", 0))
	var time_str = "%02dh%02d" % [h, m]

	var new_entries_added = false

	for entry in step_data["species"]:
		if typeof(entry) != TYPE_DICTIONARY:
			continue

		var is_alive := true
		if entry.has("after") and typeof(entry["after"]) == TYPE_DICTIONARY:
			is_alive = bool(entry["after"].get("alive", true))
			if entry["after"].has("vitality"):
				is_alive = is_alive and (float(entry["after"].get("vitality", 0.0)) > 0.0)
		elif entry.has("vitality"):
			is_alive = float(entry.get("vitality", 0.0)) > 0.0

		if not is_alive:
			continue

		var animal_name = String(entry.get("name", entry.get("display_name", "")))
		if animal_name.is_empty():
			continue

		var action = String(entry.get("action", "")).strip_edges()
		var motivation = String(entry.get("motivation", "")).strip_edges()
		var food_evt = entry.get("food_event")

		var action_text = _format_action_text(action, motivation, entry, food_evt)
		if action_text.is_empty():
			continue

		var last_action = last_animal_actions.get(animal_name, "")
		if last_action != action_text:
			last_animal_actions[animal_name] = action_text
			var log_str = "[color=#61afef][%s][/color] [b]%s[/b]\n   ➜ %s" % [time_str, animal_name, action_text]
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

# --- Gestion du Header ---
func _on_settings_pressed():
	if settings_panel:
		settings_panel.visible = not settings_panel.visible

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

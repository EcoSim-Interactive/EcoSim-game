## Controle le cadre d'affichage des statistiques détaillées d'une espèce sélectionnée.
extends PanelContainer

signal close_requested
signal center_requested(target_pos: Vector2)

# --- References UI ---
@onready var icon_rect = $Margin/VBox/Header/IconContainer/IconRect
@onready var name_label = $Margin/VBox/Header/InfoVBox/NameLabel
@onready var subtitle_label = $Margin/VBox/Header/InfoVBox/SubtitleLabel
@onready var close_btn = $Margin/VBox/Header/CloseBtn

@onready var diet_chip = $Margin/VBox/Badges/DietChip
@onready var diet_label = $Margin/VBox/Badges/DietChip/DietLabel
@onready var temp_chip = $Margin/VBox/Badges/TempChip
@onready var temp_label = $Margin/VBox/Badges/TempChip/TempLabel
@onready var status_chip = $Margin/VBox/Badges/StatusChip
@onready var status_label = $Margin/VBox/Badges/StatusChip/StatusLabel

@onready var vitality_bar = $Margin/VBox/Vitals/VitalityRow/VitalityBar
@onready var vitality_val = $Margin/VBox/Vitals/VitalityRow/VitalityVal
@onready var thirst_bar = $Margin/VBox/Vitals/ThirstRow/ThirstBar
@onready var thirst_val = $Margin/VBox/Vitals/ThirstRow/ThirstVal
@onready var hunger_bar = $Margin/VBox/Vitals/HungerRow/HungerBar
@onready var hunger_val = $Margin/VBox/Vitals/HungerRow/HungerVal
@onready var fatigue_bar = $Margin/VBox/Vitals/FatigueRow/FatigueBar
@onready var fatigue_val = $Margin/VBox/Vitals/FatigueRow/FatigueVal

@onready var action_label = $Margin/VBox/BehaviorBox/ActionLabel
@onready var motivation_label = $Margin/VBox/BehaviorBox/MotivationLabel

@onready var speed_label = $Margin/VBox/Grid/SpeedLabel
@onready var vision_label = $Margin/VBox/Grid/VisionLabel
@onready var smell_label = $Margin/VBox/Grid/SmellLabel
@onready var mass_label = $Margin/VBox/Grid/MassLabel
@onready var pos_label = $Margin/VBox/Grid/PosLabel

@onready var center_btn = $Margin/VBox/Footer/CenterBtn

var current_species_data: Dictionary = {}
var current_target_pos: Vector2 = Vector2.ZERO
var _texture_cache: Dictionary = {}

func _ready() -> void:
	if close_btn:
		close_btn.pressed.connect(_on_close_pressed)
	if center_btn:
		center_btn.pressed.connect(_on_center_pressed)

func _on_close_pressed() -> void:
	visible = false
	emit_signal("close_requested")

func _on_center_pressed() -> void:
	if current_target_pos != Vector2.ZERO:
		emit_signal("center_requested", current_target_pos)
	elif current_species_data.has("position_world"):
		emit_signal("center_requested", current_species_data["position_world"])
	elif current_species_data.has("x") and current_species_data.has("y"):
		emit_signal("center_requested", Vector2(float(current_species_data["x"]), float(current_species_data["y"])))

func display_species(data: Dictionary) -> void:
	current_species_data = data
	visible = true

	# Position
	if data.has("position_world") and data["position_world"] is Vector2:
		current_target_pos = data["position_world"]
	elif data.has("x") and data.has("y"):
		current_target_pos = Vector2(float(data["x"]), float(data["y"]))
	elif data.has("after") and data["after"] is Dictionary:
		current_target_pos = Vector2(float(data["after"].get("x", 0)), float(data["after"].get("y", 0)))
	elif data.has("before") and data["before"] is Dictionary:
		current_target_pos = Vector2(float(data["before"].get("x", 0)), float(data["before"].get("y", 0)))

	# --- 1. En-tête (Nom, ID, Sexe, Âge) ---
	var base_name: String = String(data.get("display_name", data.get("name", "Espèce"))).capitalize()
	var animal_id = data.get("animal_id", "")
	var id_str = (" #" + str(animal_id)) if animal_id != null and str(animal_id) != "" and str(animal_id) != "null" else ""
	if name_label:
		name_label.text = base_name + id_str

	# Sexe et Âge
	var sex_str = String(data.get("sex", "unknown")).to_lower()
	var sex_symbol = "⚪"
	if sex_str == "male" or sex_str == "mâle":
		sex_symbol = "♂ Mâle"
	elif sex_str == "female" or sex_str == "femelle":
		sex_symbol = "♀ Femelle"
	else:
		sex_symbol = "⚧ Indéfini"

	var age_stage_str = String(data.get("age_stage", "")).capitalize()
	var age_years = float(data.get("age_years", 0.0))
	var sub_text = "%s • %s (%.1f ans)" % [sex_symbol, age_stage_str if age_stage_str != "" else "Adulte", age_years]
	if subtitle_label:
		subtitle_label.text = sub_text

	# Icône
	var species_type = String(data.get("species_type", data.get("name", ""))).to_lower()
	if icon_rect:
		var tex = _get_dynamic_texture(species_type)
		icon_rect.texture = tex

	# --- 2. Badges (Régime, Tempérament, Statut) ---
	var diet = String(data.get("diet", "herbivore")).to_lower()
	if diet_label:
		if diet.contains("carn"):
			diet_label.text = "🍖 Carnivore"
		elif diet.contains("omni"):
			diet_label.text = "🌾 Omnivore"
		else:
			diet_label.text = "🌿 Herbivore"

	var temp = String(data.get("temperament", "neutre")).capitalize()
	if temp_label:
		if temp.to_lower().contains("prudent"):
			temp_label.text = "🛡️ Prudent"
		elif temp.to_lower().contains("agress"):
			temp_label.text = "⚔️ Agressif"
		else:
			temp_label.text = "✨ " + temp

	var is_alive = true
	if data.has("alive"):
		is_alive = bool(data["alive"])
	elif data.has("vitality"):
		is_alive = float(data["vitality"]) > 0.0

	if status_label:
		if is_alive:
			status_label.text = "💚 Vivant"
			if status_chip:
				status_chip.self_modulate = Color(0.1, 0.8, 0.4, 1.0)
		else:
			var cause = String(data.get("death_cause", "Mort"))
			if cause.is_empty() or cause == "null": cause = "Mort"
			status_label.text = "💀 " + cause
			if status_chip:
				status_chip.self_modulate = Color(0.9, 0.25, 0.25, 1.0)

	# --- 3. Barres de statut (Vitals) ---
	var vit = float(data.get("vitality", 100.0))
	var th = float(data.get("thirst", 0.0))
	var hu = float(data.get("hunger", 0.0))
	var fat = float(data.get("fatigue", 0.0))

	# Si dans after/before
	if data.has("after") and data["after"] is Dictionary:
		var aft = data["after"]
		vit = float(aft.get("vitality", vit))
		th = float(aft.get("thirst", th))
		hu = float(aft.get("hunger", hu))
		fat = float(aft.get("fatigue", fat))

	# Progression Vitalité
	if vitality_bar:
		vitality_bar.value = clamp(vit, 0.0, 100.0)
	if vitality_val:
		vitality_val.text = "%d%%" % int(clamp(vit, 0.0, 100.0))

	# Progression Hydratation (100 - Soif)
	var hydro = clamp(100.0 - th, 0.0, 100.0)
	if thirst_bar:
		thirst_bar.value = hydro
	if thirst_val:
		thirst_val.text = "%d%%" % int(hydro)

	# Progression Satiété (100 - Faim)
	var sat = clamp(100.0 - hu, 0.0, 100.0)
	if hunger_bar:
		hunger_bar.value = sat
	if hunger_val:
		hunger_val.text = "%d%%" % int(sat)

	# Progression Énergie (100 - Fatigue)
	var ener = clamp(100.0 - fat, 0.0, 100.0)
	if fatigue_bar:
		fatigue_bar.value = ener
	if fatigue_val:
		fatigue_val.text = "%d%%" % int(ener)

	# --- 4. Action et Motivation ---
	var action_str = _format_action_text(data)
	if action_label:
		action_label.text = "🎯 Action : " + action_str

	var mot_str = String(data.get("motivation", "")).strip_edges()
	if mot_str.is_empty() and data.has("after") and data["after"] is Dictionary:
		mot_str = String(data["after"].get("motivation", "")).strip_edges()
	if mot_str.is_empty():
		if th > 70.0: mot_str = "Soif critique"
		elif hu > 70.0: mot_str = "Faim urgente"
		elif fat > 80.0: mot_str = "Besoin de repos"
		else: mot_str = "Recherche d'opportunités"

	if motivation_label:
		motivation_label.text = "💭 Motivation : " + mot_str

	# --- 5. Caractéristiques physiques ---
	var speed_val = float(data.get("speed", 20.0))
	var vision_val = float(data.get("vision", 100.0))
	var smell_val = float(data.get("smell_range", 50.0))

	# Masse corporelle
	var mass_val = 0.0
	if data.has("traits") and data["traits"] is Dictionary:
		var traits = data["traits"]
		if traits.has("metabolism") and traits["metabolism"] is Dictionary:
			mass_val = float(traits["metabolism"].get("body_mass_kg", 0.0))

	if speed_label:
		speed_label.text = "🏃 Vitesse : %.0f px/s" % speed_val
	if vision_label:
		vision_label.text = "👁️ Vision : %.0f px" % vision_val
	if smell_label:
		smell_label.text = "👃 Odorat : %.0f px" % smell_val
	if mass_label:
		if mass_val > 0.0:
			mass_label.text = "⚖️ Masse : %.1f kg" % mass_val
		else:
			mass_label.text = "⚖️ Masse : N/A"
	if pos_label:
		pos_label.text = "📍 Pos : (%.0f, %.0f)" % [current_target_pos.x, current_target_pos.y]

func _format_action_text(entry: Dictionary) -> String:
	var food_evt = entry.get("food_event")
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

	var action = String(entry.get("action", "")).strip_edges()
	var motivation = String(entry.get("motivation", "")).strip_edges()
	var act_lower = action.to_lower()
	var mot_lower = motivation.to_lower()

	if act_lower.contains("kill") or mot_lower.contains("tue"):
		return "⚔️ A abattu une proie !"
	elif act_lower.contains("hunt") or act_lower.contains("predat") or act_lower.contains("pack_attack") or mot_lower.contains("chasse"):
		return "🐾 Traque et chasse une proie"
	elif act_lower.contains("flee") or mot_lower.contains("fuite") or mot_lower.contains("attaque"):
		return "🏃 Fuit un prédateur !"
	elif act_lower.contains("drink"):
		return "💧 Boit de l'eau à la rivière"
	elif act_lower.contains("seek_water") or (act_lower.contains("water") and not act_lower.contains("explore")):
		return "💧 Cherche un point d'eau"
	elif act_lower.contains("eat") or act_lower.contains("gorge") or act_lower.contains("consume"):
		return "🌿 Mange de la nourriture"
	elif act_lower.contains("seen_food") or act_lower.contains("move_to_food"):
		return "🌿 Se dirige vers la nourriture"
	elif act_lower.contains("seek_food"):
		return "🌿 Cherche de la nourriture"
	elif act_lower.contains("rest") or act_lower.contains("sleep") or act_lower.contains("guard") or mot_lower.contains("repos") or mot_lower.contains("fatigue"):
		return "😴 Se repose"
	elif act_lower.contains("cohesion") or act_lower.contains("herd") or mot_lower.contains("groupe"):
		return "🐄 Se déplace en groupe"
	elif act_lower.contains("explore") or act_lower.contains("wander") or act_lower.contains("idle") or mot_lower.contains("exploration"):
		return "🌍 Vadrouille dans la savane"
	elif not action.is_empty():
		return action
	elif not motivation.is_empty():
		return motivation
	return "🌍 Actif"

func _get_dynamic_texture(sprite_name: String) -> Texture2D:
	if _texture_cache.has(sprite_name):
		return _texture_cache[sprite_name]

	var path = "res://sprites/" + sprite_name + ".png"
	var icon: Texture2D = null

	var global_path = ProjectSettings.globalize_path(path)
	if FileAccess.file_exists(global_path):
		var img = Image.load_from_file(global_path)
		if img != null and not img.is_empty():
			icon = ImageTexture.create_from_image(img)
			
	if icon == null and ResourceLoader.exists(path):
		icon = load(path)

	_texture_cache[sprite_name] = icon
	return icon

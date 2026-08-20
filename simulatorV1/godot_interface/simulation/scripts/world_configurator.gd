## Species configuration modal shown before starting the simulation.
extends CanvasLayer

@export var world_path: NodePath

var world: Node = null
var dialog: AcceptDialog
var status_label: Label
var species_list: ItemList
var template_picker: OptionButton

var count_input: SpinBox
var males_input: SpinBox
var females_input: SpinBox
var vision_input: SpinBox
var smell_input: SpinBox
var speed_input: SpinBox
var nutrition_min_input: SpinBox
var nutrition_max_input: SpinBox
var diurnal_input: CheckBox
var temperament_input: LineEdit
var position_x_input: SpinBox
var position_y_input: SpinBox
var diet_input: OptionButton

var save_button: Button
var save_start_button: Button
var map_preview: Control
var map_marker: ColorRect

var current_world_config: Dictionary = {}
var water_qty_input: SpinBox
var river_segments_input: SpinBox
var stagnant_count_input: SpinBox
var oasis_count_input: SpinBox
var lake_count_input: SpinBox
var herbs_input: SpinBox
var berries_input: SpinBox
var tree_input: SpinBox
var steps_input: SpinBox

var templates_by_id: Dictionary = {}
var base_selection: Array = []
var selection: Array = []
var selected_index: int = -1
var has_opened_once: bool = false
var is_populating_form: bool = false
var map_width: float = 1000.0
var map_height: float = 1000.0
var rng := RandomNumberGenerator.new()

## Initializes the random number generator, retrieves the world reference, builds the dialog box and connects the necessary signals.
func _ready() -> void:
	rng.randomize()
	if world_path != NodePath():
		world = get_node_or_null(world_path)
	if world == null:
		# Defensive fallback in case the exported NodePath is incorrect.
		world = get_node_or_null("../Simulateur/Panel/SubViewportContainer/SubViewport/World")
	_build_dialog()

	if world:
		world.species_configuration_required.connect(_on_species_configuration_required)
		world.species_catalog_ready.connect(_on_species_catalog_ready)
		world.species_configuration_saved.connect(_on_species_configuration_saved)
		if world.has_signal("world_loaded"):
			world.world_loaded.connect(_on_world_loaded)
		if world.has_signal("world_config_ready"):
			world.world_config_ready.connect(_on_world_config_ready)
		world.request_species_catalog()
		if world.has_method("request_world_config"):
			world.request_world_config()
	else:
		push_warning("SpeciesConfigurator: World introuvable, la modal de configuration ne sera pas affichee.")

## Dynamically builds the complete dialog box UI (species/water/food/simulation tabs, fields and buttons).
func _build_dialog() -> void:
	dialog = AcceptDialog.new()
	dialog.title = "Configuration des especes"
	dialog.dialog_text = ""
	dialog.exclusive = true
	dialog.unresizable = false
	dialog.size = Vector2i(1000, 700)
	# An AcceptDialog is a Window: it does not automatically inherit the
	# theme of its ancestors in the scene tree the way a regular Control
	# would. Without this it displayed with the default Godot theme,
	# inconsistent with the rest of the app.
	dialog.theme = load("res://background/theme_dark.tres")
	add_child(dialog)

	var scroll = ScrollContainer.new()
	scroll.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	scroll.vertical_scroll_mode = ScrollContainer.SCROLL_MODE_AUTO
	dialog.add_child(scroll)

	var root = VBoxContainer.new()
	root.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	# Minimum height explicitly forced (instead of relying on the automatic
	# cascading calculation GridContainer -> VBoxContainer -> TabContainer,
	# which did not propagate correctly up to the ScrollContainer). The
	# dialog is 700px tall: with 1000px here, overflow is guaranteed and
	# the scroll (both wheel AND side bar) always has a non-zero range to
	# work with.
	root.custom_minimum_size = Vector2(0, 1000)
	scroll.add_child(root)

	var header_label = Label.new()
	header_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	header_label.text = "Choisissez les especes et personnalisez leurs caracteristiques avant de lancer la simulation."
	header_label.add_theme_color_override("font_color", Color(0.6, 0.65, 0.75, 1))
	root.add_child(header_label)

	status_label = Label.new()
	status_label.text = "Chargement du catalogue..."
	status_label.add_theme_color_override("font_color", Color(0.2, 0.8, 0.5, 1))
	root.add_child(status_label)

	var tab_container = TabContainer.new()
	tab_container.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	tab_container.custom_minimum_size = Vector2(0, 850)
	root.add_child(tab_container)

	# --- TAB 1: SPECIES ---
	var species_tab = VBoxContainer.new()
	species_tab.name = "Especes"
	species_tab.add_theme_constant_override("separation", 12)
	tab_container.add_child(species_tab)

	var top_row = HBoxContainer.new()
	top_row.add_theme_constant_override("separation", 8)
	species_tab.add_child(top_row)

	template_picker = OptionButton.new()
	template_picker.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	top_row.add_child(template_picker)

	var add_button = Button.new()
	add_button.text = "Ajouter"
	add_button.pressed.connect(_on_add_pressed)
	top_row.add_child(add_button)

	var remove_button = Button.new()
	remove_button.text = "Retirer"
	remove_button.pressed.connect(_on_remove_pressed)
	top_row.add_child(remove_button)

	species_list = ItemList.new()
	species_list.custom_minimum_size = Vector2(0, 180)
	species_list.item_selected.connect(_on_species_selected)
	species_tab.add_child(species_list)

	var map_section = VBoxContainer.new()
	map_section.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	species_tab.add_child(map_section)

	var map_label = Label.new()
	map_label.text = "Carte miniature"
	map_label.add_theme_font_size_override("font_size", 18)
	map_section.add_child(map_label)

	var map_hint = Label.new()
	map_hint.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	map_hint.text = "Mini-apercu: cliquez pour definir la position du groupe."
	map_hint.add_theme_color_override("font_color", Color(0.580392, 0.639216, 0.721569, 1))
	map_hint.add_theme_font_size_override("font_size", 14)
	map_section.add_child(map_hint)

	var map_center = CenterContainer.new()
	map_center.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	map_section.add_child(map_center)

	var map_frame = PanelContainer.new()
	map_frame.custom_minimum_size = Vector2(180, 180)
	map_frame.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	map_frame.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	map_center.add_child(map_frame)

	var preview_script = load("res://scripts/mini_world_preview.gd")
	map_preview = preview_script.new()
	map_preview.custom_minimum_size = Vector2(180, 180)
	map_preview.position_selected.connect(_on_map_position_selected)
	map_frame.add_child(map_preview)

	var form = GridContainer.new()
	form.columns = 4
	form.add_theme_constant_override("h_separation", 16)
	form.add_theme_constant_override("v_separation", 10)
	form.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	species_tab.add_child(form)

	count_input = _add_spin_field(form, "Nombre Total", 0, 200, 1)
	males_input = _add_spin_field(form, "Mâles", 0, 200, 1)
	females_input = _add_spin_field(form, "Femelles", 0, 200, 1)
	
	count_input.value_changed.connect(func(v: float):
		if not is_populating_form:
			is_populating_form = true
			var total = int(v)
			var m = int(ceil(total / 2.0))
			var f = total - m
			if males_input.has_method("set_value_no_signal"):
				males_input.set_value_no_signal(m)
				females_input.set_value_no_signal(f)
			else:
				males_input.value = float(m)
				females_input.value = float(f)
			is_populating_form = false
			_on_fields_changed(v)
	)
	males_input.value_changed.connect(func(v: float):
		if not is_populating_form:
			is_populating_form = true
			var m = int(v)
			var total = int(count_input.value)
			if m > total:
				total = m
				count_input.value = float(total)
			var f = max(0, total - m)
			if females_input.has_method("set_value_no_signal"):
				females_input.set_value_no_signal(f)
			else:
				females_input.value = float(f)
			is_populating_form = false
			_on_fields_changed(v)
	)
	females_input.value_changed.connect(func(v: float):
		if not is_populating_form:
			is_populating_form = true
			var f = int(v)
			var total = int(count_input.value)
			if f > total:
				total = f
				count_input.value = float(total)
			var m = max(0, total - f)
			if males_input.has_method("set_value_no_signal"):
				males_input.set_value_no_signal(m)
			else:
				males_input.value = float(m)
			is_populating_form = false
			_on_fields_changed(v)
	)
	
	vision_input = _add_spin_field(form, "Vision", 1, 500, 1)
	smell_input = _add_spin_field(form, "Odorat", 1, 700, 1)
	speed_input = _add_spin_field(form, "Vitesse", 1, 80, 0.1)
	nutrition_min_input = _add_spin_field(form, "Nutrition min", 1, 5000000, 100)
	nutrition_max_input = _add_spin_field(form, "Nutrition max", 1, 5000000, 100)
	position_x_input = _add_spin_field(form, "Position X", 0, map_width, 1)
	position_y_input = _add_spin_field(form, "Position Y", 0, map_height, 1)

	var diurnal_label = Label.new()
	diurnal_label.text = "Diurne"
	form.add_child(diurnal_label)
	diurnal_input = CheckBox.new()
	diurnal_input.button_pressed = true
	form.add_child(diurnal_input)

	var temperament_label = Label.new()
	temperament_label.text = "Temperament"
	form.add_child(temperament_label)
	temperament_input = LineEdit.new()
	form.add_child(temperament_input)

	var diet_label = Label.new()
	diet_label.text = "Regime"
	form.add_child(diet_label)
	diet_input = OptionButton.new()
	diet_input.add_item("herbivore")
	diet_input.add_item("omnivore")
	diet_input.add_item("carnivore")
	form.add_child(diet_input)

	# --- TAB 2: WATER ---
	var water_tab = GridContainer.new()
	water_tab.name = "Points d'eau"
	water_tab.columns = 4
	water_tab.add_theme_constant_override("h_separation", 16)
	water_tab.add_theme_constant_override("v_separation", 10)
	tab_container.add_child(water_tab)
	
	water_qty_input = _add_spin_field(water_tab, "Quantite Globale", 0, 100, 1)
	river_segments_input = _add_spin_field(water_tab, "Segments de Riviere", 0, 200, 1)
	stagnant_count_input = _add_spin_field(water_tab, "Points d'eau stagnante", 0, 50, 1)
	oasis_count_input = _add_spin_field(water_tab, "Oasis", 0, 50, 1)
	lake_count_input = _add_spin_field(water_tab, "Lacs", 0, 20, 1)

	# --- TAB 3: FOOD ---
	var food_tab = GridContainer.new()
	food_tab.name = "Nourriture (Distribution)"
	food_tab.columns = 4
	food_tab.add_theme_constant_override("h_separation", 16)
	food_tab.add_theme_constant_override("v_separation", 10)
	tab_container.add_child(food_tab)
	
	herbs_input = _add_spin_field(food_tab, "Herbes", 0, 1000, 1)
	berries_input = _add_spin_field(food_tab, "Buissons (baies)", 0, 1000, 1)
	tree_input = _add_spin_field(food_tab, "Arbres fruitiers", 0, 1000, 1)

	# --- TAB 4: SIMULATION ---
	var sim_tab = GridContainer.new()
	sim_tab.name = "Simulation"
	sim_tab.columns = 2
	tab_container.add_child(sim_tab)
	
	steps_input = _add_spin_field(sim_tab, "Nombre d'etapes (Steps)", 10, 100000, 10)

	var actions = HBoxContainer.new()
	actions.add_theme_constant_override("separation", 12)
	root.add_child(actions)

	var refresh_button = Button.new()
	refresh_button.text = "Rafraichir"
	refresh_button.pressed.connect(_on_refresh_pressed)
	actions.add_child(refresh_button)

	var reset_button = Button.new()
	reset_button.text = "Base"
	reset_button.pressed.connect(_on_reset_base_pressed)
	actions.add_child(reset_button)

	save_button = Button.new()
	save_button.text = "Enregistrer"
	save_button.pressed.connect(_on_save_pressed)
	actions.add_child(save_button)

	save_start_button = Button.new()
	save_start_button.text = "Enregistrer et lancer"
	save_start_button.pressed.connect(_on_save_and_start_pressed)
	var accent_normal = StyleBoxFlat.new()
	accent_normal.bg_color = Color(0.2, 0.8, 0.5, 0.9)
	accent_normal.content_margin_left = 16.0
	accent_normal.content_margin_top = 8.0
	accent_normal.content_margin_right = 16.0
	accent_normal.content_margin_bottom = 8.0
	accent_normal.set_corner_radius_all(8)
	var accent_hover = StyleBoxFlat.new()
	accent_hover.bg_color = Color(0.25, 0.95, 0.6, 1.0)
	accent_hover.content_margin_left = 16.0
	accent_hover.content_margin_top = 8.0
	accent_hover.content_margin_right = 16.0
	accent_hover.content_margin_bottom = 8.0
	accent_hover.set_corner_radius_all(8)
	save_start_button.add_theme_stylebox_override("normal", accent_normal)
	save_start_button.add_theme_stylebox_override("hover", accent_hover)
	save_start_button.add_theme_color_override("font_color", Color(0.059, 0.09, 0.165, 1))
	actions.add_child(save_start_button)

	for input in [count_input, vision_input, smell_input, speed_input, nutrition_min_input, nutrition_max_input, position_x_input, position_y_input]:
		input.value_changed.connect(_on_fields_changed)
	diurnal_input.toggled.connect(_on_fields_changed)
	temperament_input.text_changed.connect(_on_fields_changed_text)
	diet_input.item_selected.connect(_on_fields_changed)

	var ok_button = dialog.get_ok_button()
	if ok_button:
		ok_button.text = "Fermer"

## Adds a label and a configured SpinBox (min/max/step) to the given container and returns the created SpinBox.
func _add_spin_field(parent: GridContainer, title: String, min_value: float, max_value: float, step_value: float) -> SpinBox:
	var label = Label.new()
	label.text = title
	parent.add_child(label)
	var spin = SpinBox.new()
	spin.min_value = min_value
	spin.max_value = max_value
	spin.step = step_value
	spin.allow_greater = false
	spin.allow_lesser = false
	parent.add_child(spin)
	return spin

## Handler for the signal requesting species configuration: opens the dialog box.
func _on_species_configuration_required() -> void:
	open_modal()

## Refreshes the data from the server if needed, then shows the dialog box centered on screen.
func open_modal() -> void:
	if world:
		if world.get("connected") == false:
			status_label.text = "Serveur Python déconnecté ! Lancez le backend."
		elif world.has_method("request_species_catalog"):
			status_label.text = "Chargement des configs..."
			world.request_species_catalog()
			if world.has_method("request_world_config"):
				world.request_world_config()
	dialog.reset_size()
	dialog.min_size = Vector2i(1000, 700)
	dialog.popup_centered(Vector2i(1000, 700))

## Processes the species catalog received from the server: fills the template picker, the map size and the current selection.
func _on_species_catalog_ready(payload) -> void:
	if typeof(payload) != TYPE_DICTIONARY:
		status_label.text = "Catalogue invalide recu"
		return

	templates_by_id.clear()
	template_picker.clear()
	var templates = payload.get("templates", [])
	map_width = float(payload.get("world_width", 1000.0))
	map_height = float(payload.get("world_height", 1000.0))
	position_x_input.min_value = 0
	position_x_input.max_value = map_width
	position_y_input.min_value = 0
	position_y_input.max_value = map_height
	if map_preview and map_preview.has_method("set_world_size"):
		map_preview.call("set_world_size", map_width, map_height)
	if map_preview and map_preview.has_method("set_world_node"):
		map_preview.call("set_world_node", world)
	if map_preview and map_preview.has_method("refresh_from_world"):
		map_preview.call("refresh_from_world")
	for tpl in templates:
		if typeof(tpl) != TYPE_DICTIONARY:
			continue
		var id_value = String(tpl.get("id", "")).strip_edges()
		if id_value.is_empty():
			continue
		templates_by_id[id_value] = tpl
		var display_name = String(tpl.get("display_name", id_value))
		template_picker.add_item(display_name)
		template_picker.set_item_metadata(template_picker.item_count - 1, id_value)

	base_selection = []
	for row in payload.get("selection", []):
		if typeof(row) == TYPE_DICTIONARY:
			base_selection.append(row.duplicate(true))

	selection = []
	for row in base_selection:
		selection.append(row.duplicate(true))

	_refresh_species_list()
	status_label.text = "Configurez l'environnement et les especes puis enregistrez."

## Fills the water/food/simulation fields from the world configuration received from the server.
func _on_world_config_ready(payload) -> void:
	if typeof(payload) != TYPE_DICTIONARY:
		return
	current_world_config = payload.duplicate(true)
	var water = current_world_config.get("water", {})
	water_qty_input.value = float(water.get("quantity", 12))
	river_segments_input.value = float(water.get("river_segments", 35))
	stagnant_count_input.value = float(water.get("stagnant_count", 3))
	oasis_count_input.value = float(water.get("oasis_count", 2))
	lake_count_input.value = float(water.get("lake_count", 1))

	var food = current_world_config.get("food", {})
	var dist = food.get("distribution", {})
	herbs_input.value = float(dist.get("herbs", 140))
	berries_input.value = float(dist.get("berries", 60))
	tree_input.value = float(dist.get("fruit_tree", 35))

	var sim_cfg = current_world_config.get("simulation", {})
	var steps_val = float(sim_cfg.get("steps", current_world_config.get("steps", 1000)))
	if steps_input:
		steps_input.value = steps_val

## Rebuilds the displayed list of selected species and reloads the editor for the selected entry.
func _refresh_species_list() -> void:
	species_list.clear()
	for idx in range(selection.size()):
		var row = selection[idx]
		var title = String(row.get("display_name", row.get("name", row.get("template_id", "Espece"))))
		var count = int(row.get("count", 0))
		species_list.add_item("%s x%d" % [title, count])

	if selection.is_empty():
		selected_index = -1
		_clear_editor()
		return

	if selected_index < 0 or selected_index >= selection.size():
		selected_index = 0
	species_list.select(selected_index)
	_load_entry_into_editor(selection[selected_index])

## Resets the edit form's fields to their default values (no species selected).
func _clear_editor() -> void:
	is_populating_form = true
	count_input.value = 0
	vision_input.value = 0
	smell_input.value = 0
	speed_input.value = 0
	nutrition_min_input.value = 0
	nutrition_max_input.value = 0
	_set_position_inputs(_random_default_position())
	temperament_input.text = ""
	diurnal_input.button_pressed = true
	diet_input.select(1)
	_update_map_marker()
	is_populating_form = false

## Fills the form fields with a species entry's values, falling back to the template if needed.
func _load_entry_into_editor(entry: Dictionary) -> void:
	is_populating_form = true
	var total_count = int(entry.get("count", 0))
	count_input.value = float(total_count)
	
	var default_males = int(ceil(total_count / 2.0))
	var default_females = total_count - default_males
	males_input.value = float(entry.get("males", default_males))
	females_input.value = float(entry.get("females", default_females))

	var tpl_id = String(entry.get("template_id", entry.get("id", entry.get("species_type", ""))))
	var tpl = templates_by_id.get(tpl_id, {})

	var v = float(entry.get("vision", 0))
	if v <= 0 and typeof(tpl) == TYPE_DICTIONARY:
		v = float(tpl.get("vision", 110.0))
	vision_input.value = v

	var s = float(entry.get("smell_range", 0))
	if s <= 0 and typeof(tpl) == TYPE_DICTIONARY:
		s = float(tpl.get("smell_range", 220.0))
	smell_input.value = s

	var sp = float(entry.get("speed", 0))
	if sp <= 0 and typeof(tpl) == TYPE_DICTIONARY:
		sp = float(tpl.get("speed", 12.0))
	speed_input.value = sp

	var nr = entry.get("nutrition_range", {})
	nutrition_min_input.value = float(nr.get("min", 80.0))
	nutrition_max_input.value = float(nr.get("max", 80.0))
	var pos = entry.get("position", [map_width * 0.5, map_height * 0.5])
	if typeof(pos) == TYPE_ARRAY and pos.size() >= 2:
		_set_position_inputs(Vector2(float(pos[0]), float(pos[1])))
	else:
		_set_position_inputs(_random_default_position())
	temperament_input.text = String(entry.get("temperament", "neutre"))
	diurnal_input.button_pressed = bool(entry.get("diurnal", true))
	var diet = String(entry.get("diet", "omnivore"))
	for i in range(diet_input.item_count):
		if diet_input.get_item_text(i) == diet:
			diet_input.select(i)
			break
	is_populating_form = false

## Copies the form's current values back into the selected species entry, then refreshes the display.
func _sync_editor_to_entry() -> void:
	if selected_index < 0 or selected_index >= selection.size():
		return
	var entry: Dictionary = selection[selected_index]
	entry["count"] = int(count_input.value)
	entry["males"] = int(males_input.value)
	entry["females"] = int(females_input.value)
	entry["vision"] = float(vision_input.value)
	entry["smell_range"] = float(smell_input.value)
	entry["speed"] = float(speed_input.value)
	entry["diurnal"] = bool(diurnal_input.button_pressed)
	entry["temperament"] = temperament_input.text.strip_edges()
	entry["diet"] = diet_input.get_item_text(diet_input.selected)
	entry["nutrition_range"] = {
		"min": float(min(nutrition_min_input.value, nutrition_max_input.value)),
		"max": float(max(nutrition_min_input.value, nutrition_max_input.value)),
	}
	entry["position"] = [
		max(0.0, min(map_width, float(position_x_input.value))),
		max(0.0, min(map_height, float(position_y_input.value))),
	]
	selection[selected_index] = entry
	_refresh_species_list()
	_update_map_marker()

## Handler for selection in the species list: loads the corresponding entry into the editor.
func _on_species_selected(index: int) -> void:
	selected_index = index
	if index >= 0 and index < selection.size():
		_load_entry_into_editor(selection[index])

## Adds a new species to the selection from the chosen template, with a random position.
func _on_add_pressed() -> void:
	if template_picker.item_count == 0:
		return
	var template_id = template_picker.get_item_metadata(template_picker.selected)
	if typeof(template_id) != TYPE_STRING:
		return
	if not templates_by_id.has(template_id):
		return
	var base: Dictionary = templates_by_id[template_id].duplicate(true)
	base["template_id"] = template_id
	base["count"] = 1
	var random_position = _random_default_position()
	base["position"] = [random_position.x, random_position.y]
	selection.append(base)
	selected_index = selection.size() - 1
	_refresh_species_list()

## Removes the currently selected species from the list.
func _on_remove_pressed() -> void:
	if selected_index < 0 or selected_index >= selection.size():
		return
	selection.remove_at(selected_index)
	selected_index = min(selected_index, selection.size() - 1)
	_refresh_species_list()

## Resets the current selection to the base configuration received from the server.
func _on_reset_base_pressed() -> void:
	selection.clear()
	for row in base_selection:
		selection.append(row.duplicate(true))
	selected_index = -1
	_refresh_species_list()

## Syncs the entry with the form when a numeric field changes (ignores internal changes).
func _on_fields_changed(_value = null) -> void:
	if is_populating_form:
		return
	_sync_editor_to_entry()

## Syncs the entry with the form when a text field changes (ignores internal changes).
func _on_fields_changed_text(_value: String) -> void:
	if is_populating_form:
		return
	_sync_editor_to_entry()

## Re-requests the species catalog from the server.
func _on_refresh_pressed() -> void:
	if world and world.has_method("request_species_catalog"):
		world.request_species_catalog()

## Builds the final configuration (filtered species, water, food, simulation) and sends it to the server, with an option to start immediately.
func _save(start_after: bool) -> void:
	_sync_editor_to_entry()
	if selection.is_empty():
		status_label.text = "Ajoutez au moins une espece."
		return
	var filtered_selection: Array = []
	for row in selection:
		if typeof(row) != TYPE_DICTIONARY:
			continue
		var count_value = int(row.get("count", 0))
		if count_value > 0:
			filtered_selection.append(row)
	if not current_world_config.is_empty():
		if not current_world_config.has("water"):
			current_world_config["water"] = {}
		current_world_config["water"]["quantity"] = int(water_qty_input.value)
		current_world_config["water"]["river_segments"] = int(river_segments_input.value)
		current_world_config["water"]["stagnant_count"] = int(stagnant_count_input.value)
		current_world_config["water"]["oasis_count"] = int(oasis_count_input.value)
		current_world_config["water"]["lake_count"] = int(lake_count_input.value)
		
		if not current_world_config.has("food"):
			current_world_config["food"] = {}
		if not current_world_config["food"].has("distribution"):
			current_world_config["food"]["distribution"] = {}
			
		current_world_config["food"]["distribution"]["herbs"] = int(herbs_input.value)
		current_world_config["food"]["distribution"]["berries"] = int(berries_input.value)
		current_world_config["food"]["distribution"]["fruit_tree"] = int(tree_input.value)

		if not current_world_config.has("simulation"):
			current_world_config["simulation"] = {}
		current_world_config["simulation"]["steps"] = int(steps_input.value)
		current_world_config["steps"] = int(steps_input.value)
		
		if world and world.has_method("apply_world_configuration"):
			world.apply_world_configuration(current_world_config, false)

	if world and world.has_method("apply_species_configuration"):
		if filtered_selection.is_empty():
			status_label.text = "Aucune espece active: sauvegarde d'une simulation vide..."
		else:
			status_label.text = "Enregistrement en cours..."
		world.apply_species_configuration(filtered_selection, start_after)

## Handler for the Save button: saves the configuration without starting the simulation.
func _on_save_pressed() -> void:
	_save(false)

## Handler for the Save and Start button: saves the configuration then starts the simulation.
func _on_save_and_start_pressed() -> void:
	_save(true)

## Handler for the save confirmation signal: updates the status and closes the dialog box on success.
func _on_species_configuration_saved(ok, payload) -> void:
	if ok:
		var count = int(payload.get("species_count", 0))
		status_label.text = "Configuration enregistree (%d especes)." % count
		dialog.hide()
	else:
		status_label.text = "Erreur lors de l'enregistrement de la configuration. Voir logs Godot/serveur."

## Refreshes the mini-map preview once the world has loaded.
func _on_world_loaded() -> void:
	if map_preview and map_preview.has_method("refresh_from_world"):
		map_preview.call("refresh_from_world")
		map_preview.queue_redraw()

## Handler for clicking on the mini-map: updates the chosen position and syncs the entry.
func _on_map_position_selected(position_value: Vector2) -> void:
	_set_position_inputs(position_value)
	_sync_editor_to_entry()
	_update_map_marker()

## Applies a position (clamped to the map's dimensions) to the Position X/Y fields.
func _set_position_inputs(position_value: Vector2) -> void:
	position_x_input.value = max(0.0, min(map_width, position_value.x))
	position_y_input.value = max(0.0, min(map_height, position_value.y))

## Computes a random default position near the center of the map.
func _random_default_position() -> Vector2:
	var center_x = map_width * 0.5
	var center_y = map_height * 0.5
	var spread_x = max(24.0, map_width * 0.18)
	var spread_y = max(24.0, map_height * 0.18)
	return Vector2(
		max(0.0, min(map_width, center_x + rng.randf_range(-spread_x, spread_x))),
		max(0.0, min(map_height, center_y + rng.randf_range(-spread_y, spread_y)))
	)

## Updates the marker position displayed on the mini-map from the position fields.
func _update_map_marker() -> void:
	if map_preview == null:
		return
	var world_x = max(0.0, min(map_width, float(position_x_input.value)))
	var world_y = max(0.0, min(map_height, float(position_y_input.value)))
	if map_preview.has_method("set_marker_position"):
		map_preview.call("set_marker_position", Vector2(world_x, world_y))

## Synchronise l'etat du bouton avec le lancement ou la pause de la simulation.
extends Button

@export var world_path: NodePath
var world: Node = null

func _ready() -> void:
	toggle_mode = true
	if world_path != NodePath():
		world = get_node(world_path)

	toggled.connect(_on_toggled)
	_update_visuals(button_pressed)

func _process(_delta: float) -> void:
	if world == null or not world.has_method("is_running"):
		return
		
	var is_generating = false
	if "start_after_world_ready" in world and "precompute_pending" in world:
		is_generating = world.start_after_world_ready or world.precompute_pending
		
	if disabled != is_generating:
		disabled = is_generating
		_update_visuals(world.is_running())

	var actually_running = world.is_running()
	if button_pressed != actually_running:
		set_pressed_no_signal(actually_running)
		_update_visuals(actually_running)

func _on_toggled(pressed_state: bool) -> void:
	if world == null:
		return

	if pressed_state:
		world.start_simulation()
	else:
		world.pause_simulation()

func _update_visuals(is_playing: bool):
	var normal_style = StyleBoxFlat.new()
	var hover_style = StyleBoxFlat.new()
	var pressed_style = StyleBoxFlat.new()
	var disabled_style = StyleBoxFlat.new()
	
	for style in [normal_style, hover_style, pressed_style, disabled_style]:
		style.corner_radius_top_left = 8
		style.corner_radius_top_right = 8
		style.corner_radius_bottom_right = 8
		style.corner_radius_bottom_left = 8
		style.content_margin_left = 20
		style.content_margin_right = 20
		style.content_margin_top = 8
		style.content_margin_bottom = 8

	var base_color: Color
	if disabled:
		base_color = Color("#6B7280") # Gray 500
	elif is_playing:
		text = "Pause"
		base_color = Color("#EF4444") # Red 500
	else:
		text = "Start"
		base_color = Color("#10B981") # Emerald 500
		
	normal_style.bg_color = base_color
	hover_style.bg_color = base_color.lightened(0.1)
	pressed_style.bg_color = base_color.darkened(0.1)
	disabled_style.bg_color = base_color

	add_theme_color_override("font_color", Color(1.0, 1.0, 1.0))
	add_theme_color_override("font_hover_color", Color(1.0, 1.0, 1.0))
	add_theme_color_override("font_pressed_color", Color(0.9, 0.9, 0.9))
	add_theme_color_override("font_disabled_color", Color(0.8, 0.8, 0.8))
	add_theme_font_size_override("font_size", 18)
	
	add_theme_stylebox_override("normal", normal_style)
	add_theme_stylebox_override("hover", hover_style)
	add_theme_stylebox_override("pressed", pressed_style)
	add_theme_stylebox_override("disabled", disabled_style)

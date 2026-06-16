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
	
	# Forme rectangulaire avec bords légèrement arrondis comme dans le dashboard
	for style in [normal_style, hover_style, pressed_style]:
		style.bg_color = Color("#1a202c") # Fond sombre comme les panels
		style.corner_radius_top_left = 6
		style.corner_radius_top_right = 6
		style.corner_radius_bottom_right = 6
		style.corner_radius_bottom_left = 6
		style.border_width_left = 1
		style.border_width_right = 1
		style.border_width_top = 1
		style.border_width_bottom = 1
		style.content_margin_left = 15
		style.content_margin_right = 15
		style.content_margin_top = 10
		style.content_margin_bottom = 10

	var border_color: Color
	if is_playing:
		text = "Pause"
		border_color = Color("#e53e3e") # Bordure rouge subtile
	else:
		text = "Start"
		border_color = Color("#3182ce") # Bordure bleue subtile
		
	normal_style.border_color = border_color
	
	hover_style.border_color = border_color.lightened(0.2)
	hover_style.bg_color = Color("#2d3748") # Fond un peu plus clair au survol
	
	pressed_style.border_color = border_color.darkened(0.2)
	pressed_style.bg_color = Color("#11151c") # Fond plus sombre au clic

	add_theme_color_override("font_color", Color(1.0, 1.0, 1.0))
	add_theme_color_override("font_hover_color", Color(1.0, 1.0, 1.0))
	add_theme_color_override("font_pressed_color", Color(0.8, 0.8, 0.8))
	add_theme_font_size_override("font_size", 32) # Texte très grand comme demandé
	
	add_theme_stylebox_override("normal", normal_style)
	add_theme_stylebox_override("hover", hover_style)
	add_theme_stylebox_override("pressed", pressed_style)

## Gere la teinte globale du monde et l'affichage de l'heure simulee.
extends CanvasModulate

var sky_gradient: Gradient
var display_label: Label = null

@export var day_night_enabled: bool = true

func _ready():
	sky_gradient = Gradient.new()
	var night_color = Color("556688") # Nuit plus claire
	var dawn_color = Color("8ea1cc")
	var day_color = Color("ffffff")
	var sunset_color = Color("e09c7a")
	
	sky_gradient.set_color(0, night_color)  # Point 0 par défaut
	sky_gradient.set_offset(0, 0.0)
	sky_gradient.set_color(1, night_color)  # Point 1 par défaut
	sky_gradient.set_offset(1, 1.0)

	sky_gradient.add_point(0.25, night_color)
	sky_gradient.add_point(0.30, dawn_color)
	sky_gradient.add_point(0.40, day_color)
	sky_gradient.add_point(0.70, day_color)
	sky_gradient.add_point(0.80, sunset_color)
	sky_gradient.add_point(0.90, night_color)
	
	sky_gradient.interpolation_mode = Gradient.GRADIENT_INTERPOLATE_LINEAR
	
	var labels = get_tree().get_nodes_in_group("time_display")
	if labels.size() > 0:
		display_label = labels[0] as Label

func update_time(hour: int, minute: int):
	var target_color: Color
	if day_night_enabled:
		var total_minutes = (hour * 60) + minute
		var day_progress = float(total_minutes) / 1440.0
		target_color = sky_gradient.sample(day_progress)
	else:
		# Mode désactivé: teinte de base (blanc, pas de modification de couleur)
		target_color = Color("ffffff")
	
	var tween = create_tween()
	tween.tween_property(self, "color", target_color, 0.5)
	
	# 2. Gestion du texte
	if display_label:
		var time_str = str(hour).pad_zeros(2) + ":" + str(minute).pad_zeros(2)
		display_label.text = "Heure : " + time_str

func set_day_night_mode(enabled: bool):
	day_night_enabled = enabled
	if not enabled:
		var tween = create_tween()
		tween.tween_property(self, "color", Color("ffffff"), 0.5)

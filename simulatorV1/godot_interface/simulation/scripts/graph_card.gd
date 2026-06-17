extends PanelContainer

@export var title: String = "Graphique"
@export var line_color: Color = Color(0.1, 0.7, 0.5, 1)
@export var max_points: int = 50

@onready var title_label = $Margin/VBox/Header/Title
@onready var value_label = $Margin/VBox/Header/Value
@onready var graph_area = $Margin/VBox/GraphArea

var history: Array[float] = []

func _ready() -> void:
	if title_label:
		title_label.text = title
	if graph_area:
		graph_area.draw.connect(_on_graph_draw)

func add_value(val: float) -> void:
	history.append(val)
	if history.size() > max_points:
		history.pop_front()
	
	if value_label:
		# Format pour eviter trop de decimales
		value_label.text = str(snapped(val, 0.1))
	if graph_area:
		graph_area.queue_redraw()

func set_title(new_title: String) -> void:
	title = new_title
	if title_label:
		title_label.text = title

func set_color(new_color: Color) -> void:
	line_color = new_color
	if graph_area:
		graph_area.queue_redraw()

func _on_graph_draw() -> void:
	if history.size() < 2:
		return
		
	var w = graph_area.size.x
	var h = graph_area.size.y
	
	var min_val = history[0]
	var max_val = history[0]
	for v in history:
		min_val = min(min_val, v)
		max_val = max(max_val, v)
		
	if max_val == min_val:
		max_val = min_val + 1.0
		
	var range_val = max_val - min_val
	
	var points = PackedVector2Array()
	var step_x = w / float(max_points - 1)
	
	var start_idx = max_points - history.size()
	
	for i in range(history.size()):
		var x = (start_idx + i) * step_x
		var normalized_y = (history[i] - min_val) / range_val
		# Inverser Y car 0 est en haut dans Godot
		var y = h - (normalized_y * h)
		# Ajouter un petit padding pour ne pas toucher les bords
		y = clamp(y, 2.0, h - 2.0)
		points.append(Vector2(x, y))
		
	# Tracer la ligne
	graph_area.draw_polyline(points, line_color, 2.0, true)
	
	# Tracer le polygone de fond semi-transparent
	var poly_points = points.duplicate()
	poly_points.append(Vector2(points[points.size()-1].x, h))
	poly_points.append(Vector2(points[0].x, h))
	var fill_color = line_color
	fill_color.a = 0.15
	
	# Godot 4 attend un PackedColorArray de la même taille que poly_points OU de taille 1
	var colors = PackedColorArray()
	for i in range(poly_points.size()):
		colors.append(fill_color)
		
	graph_area.draw_polygon(poly_points, colors)

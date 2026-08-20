## UI card displaying a chart (single line, multi-line or bars) from numeric data series.
extends PanelContainer

@export var title: String = "Graphique"
@export var line_color: Color = Color(0.1, 0.7, 0.5, 1)
@export var max_points: int = 50

@onready var title_label = $Margin/VBox/Header/Title
@onready var value_label = $Margin/VBox/Header/Value
@onready var graph_area = $Margin/VBox/GraphArea

var history: Array[float] = []

var multi_history: Dictionary = {}
var multi_colors: Dictionary = {}

var graph_mode: String = "line"
var bar_data: Dictionary = {}
var bar_colors: Dictionary = {}
var species_max: Dictionary = {}

## Initializes the displayed title and connects the graph area's drawing to _on_graph_draw.
func _ready() -> void:
	if title_label:
		title_label.text = title
	if graph_area:
		graph_area.draw.connect(_on_graph_draw)

## Resets all data series (single line, multi-line, bars) and forces a redraw.
func clear_data() -> void:
	history.clear()
	multi_history.clear()
	multi_colors.clear()
	bar_data.clear()
	bar_colors.clear()
	species_max.clear()
	if graph_area:
		graph_area.queue_redraw()

## Appends a value to the single line's history (respecting the max_points limit) and updates the display.
func add_value(val: float) -> void:
	history.append(val)
	if history.size() > max_points:
		history.pop_front()
	
	if value_label and graph_mode == "line":
		value_label.text = str(snapped(val, 0.1))
	if graph_area:
		graph_area.queue_redraw()

## Switches the graph to bar mode and stores the values, colors and observed maximums per species.
func set_bar_data(values: Dictionary, colors: Dictionary) -> void:
	graph_mode = "bar"
	bar_data = values
	bar_colors = colors
	
	for k in values:
		if not species_max.has(k):
			species_max[k] = values[k]
		else:
			species_max[k] = max(species_max[k], values[k])
	
	if value_label:
		value_label.visible = false # hide the total population
		
	if graph_area:
		graph_area.queue_redraw()

## Appends a value per key to each multi-line history and displays the total of the values.
func add_multi_values(values: Dictionary, colors: Dictionary) -> void:
	for key in values.keys():
		if not multi_history.has(key):
			multi_history[key] = []
		if colors.has(key):
			multi_colors[key] = colors[key]
			
		var arr = multi_history[key]
		arr.append(values[key])
		if arr.size() > max_points:
			arr.pop_front()
	
	if value_label:
		var total = 0.0
		for k in values:
			total += values[k]
		value_label.text = str(snapped(total, 0.1))
		
	if graph_area:
		graph_area.queue_redraw()


## Changes the card's title and updates the corresponding label.
func set_title(new_title: String) -> void:
	title = new_title
	if title_label:
		title_label.text = title

## Changes the main line's color and forces a redraw.
func set_color(new_color: Color) -> void:
	line_color = new_color
	if graph_area:
		graph_area.queue_redraw()

## Draws the graph in line mode: plots the single line with fill and any multi-lines, or delegates to bar mode.
func _on_graph_draw() -> void:
	if graph_mode == "bar":
		_draw_bar_chart()
		return

	var has_single = history.size() >= 2
	var has_multi = false
	for k in multi_history:
		if multi_history[k].size() >= 2:
			has_multi = true
			break
			
	if not has_single and not has_multi:
		return
		
	var w = graph_area.size.x
	var h = graph_area.size.y
	
	var min_val = 0.0
	var max_val = 0.0
	var first = true
	
	if has_single:
		for v in history:
			if first:
				min_val = v
				max_val = v
				first = false
			else:
				min_val = min(min_val, v)
				max_val = max(max_val, v)
				
	if has_multi:
		for k in multi_history:
			for v in multi_history[k]:
				if first:
					min_val = v
					max_val = v
					first = false
				else:
					min_val = min(min_val, v)
					max_val = max(max_val, v)
		
	if max_val == min_val:
		max_val = min_val + 1.0
		
	var range_val = max_val - min_val

	
	# Plot the main line
	if history.size() >= 2:
		var points = PackedVector2Array()
		var step_x = w / float(max_points - 1)
		var start_idx = max_points - history.size()
		
		for i in range(history.size()):
			var x = (start_idx + i) * step_x
			var normalized_y = 0.0
			if range_val > 0:
				normalized_y = (history[i] - min_val) / range_val
			var y = h - (normalized_y * h)
			y = clamp(y, 2.0, h - 2.0)
			points.append(Vector2(x, y))
			
		graph_area.draw_polyline(points, line_color, 2.0, true)
		
		var poly_points = points.duplicate()
		poly_points.append(Vector2(points[points.size()-1].x, h))
		poly_points.append(Vector2(points[0].x, h))
		var fill_color = line_color
		fill_color.a = 0.15
		var colors = PackedColorArray()
		for i in range(poly_points.size()):
			colors.append(fill_color)
		graph_area.draw_polygon(poly_points, colors)
	
	# Plot the multi-lines if any exist
	if not multi_history.is_empty():
		for key in multi_history:
			var arr = multi_history[key]
			if arr.size() < 2:
				continue
				
			var points = PackedVector2Array()
			var step_x = w / float(max_points - 1)
			var start_idx = max_points - arr.size()
			
			for i in range(arr.size()):
				var x = (start_idx + i) * step_x
				var normalized_y = 0.0
				if range_val > 0:
					normalized_y = (arr[i] - min_val) / range_val
				var y = h - (normalized_y * h)
				y = clamp(y, 2.0, h - 2.0)
				points.append(Vector2(x, y))
				
			var c = multi_colors.get(key, Color.WHITE)
			graph_area.draw_polyline(points, c, 2.0, true)

## Draws a horizontal bar chart with name, value and maximum for each species.
func _draw_bar_chart() -> void:
	var w = graph_area.size.x
	var h = graph_area.size.y
	
	if bar_data.is_empty():
		return
		
	var total_val = 0.0
	for k in bar_data:
		total_val += bar_data[k]
	var max_val = max(1.0, total_val)
		
	var species_list = bar_data.keys()
	var num_bars = species_list.size()
	
	var bar_height = h / float(num_bars)
	var spacing = min(bar_height * 0.2, 10.0)
	var actual_bar_height = bar_height - spacing
	
	var text_margin = 80.0
	var graph_w = w - text_margin - 60.0 # extra space for numbers at the end
	
	var font = ThemeDB.fallback_font
	var font_size = 12
	
	for i in range(num_bars):
		var species_name = species_list[i]
		var val = bar_data[species_name]
		
		var c = bar_colors.get(species_name, Color.WHITE)
		var y_pos = i * bar_height + spacing / 2.0
		
		graph_area.draw_string(font, Vector2(5, y_pos + actual_bar_height/2.0 + font_size/3.0), species_name.left(10), HORIZONTAL_ALIGNMENT_LEFT, text_margin, font_size)
		
		var bar_len = (val / max_val) * graph_w
		if bar_len < 2.0 and val > 0:
			bar_len = 2.0 # minimum visible width
			
		var rect = Rect2(text_margin, y_pos, bar_len, actual_bar_height)
		graph_area.draw_rect(rect, c)
		
		var max_s = species_max.get(species_name, val)
		var label_text = "%d / %d" % [int(val), int(max_s)]
		graph_area.draw_string(font, Vector2(text_margin + bar_len + 5, y_pos + actual_bar_height/2.0 + font_size/3.0), label_text, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size, Color.WHITE)

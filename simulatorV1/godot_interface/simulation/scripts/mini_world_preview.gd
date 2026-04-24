extends Control

signal position_selected(position: Vector2)

@export var world_width: float = 1000.0
@export var world_height: float = 1000.0

var marker_position: Vector2 = Vector2.ZERO
var terrain_cells: Array = []
var world_node: Node = null
var sample_step_x: int = 1
var sample_step_y: int = 1
var sample_columns: int = 1
var sample_rows: int = 1

func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_STOP
	_refresh_world_reference()
	queue_redraw()

func set_world_node(node: Node) -> void:
	world_node = node
	_refresh_world_reference()
	refresh_from_world()
	queue_redraw()

func set_world_path(path: NodePath) -> void:
	world_node = get_node_or_null(path)
	_refresh_world_reference()
	queue_redraw()

func set_world_size(width: float, height: float) -> void:
	world_width = max(1.0, width)
	world_height = max(1.0, height)
	queue_redraw()

func set_marker_position(position_value: Vector2) -> void:
	marker_position = Vector2(
		clamp(position_value.x, 0.0, world_width),
		clamp(position_value.y, 0.0, world_height)
	)
	queue_redraw()

func refresh_from_world() -> void:
	_refresh_world_reference()
	terrain_cells.clear()
	if world_node == null:
		queue_redraw()
		return

	var target_columns := 72
	var target_rows := 44
	sample_step_x = max(1, ceili(world_width / float(target_columns)))
	sample_step_y = max(1, ceili(world_height / float(target_rows)))
	sample_columns = max(1, ceili(world_width / float(sample_step_x)))
	sample_rows = max(1, ceili(world_height / float(sample_step_y)))

	var grass_layer = world_node.get_node_or_null("Grass")
	if grass_layer and grass_layer.has_method("get_used_cells"):
		var coarse_cells: Dictionary = {}
		for cell in grass_layer.call("get_used_cells"):
			if typeof(cell) != TYPE_VECTOR2I:
				continue
			var source_id := -1
			if grass_layer.has_method("get_cell_source_id"):
				source_id = int(grass_layer.call("get_cell_source_id", cell))
			var block = Vector2i(cell.x / sample_step_x, cell.y / sample_step_y)
			if not coarse_cells.has(block):
				coarse_cells[block] = source_id
			elif int(coarse_cells[block]) != 1 and source_id == 1:
				coarse_cells[block] = 1
		for block in coarse_cells.keys():
			terrain_cells.append({"cell": block, "source_id": int(coarse_cells[block])})
	queue_redraw()

func _refresh_world_reference() -> void:
	if world_node != null and is_instance_valid(world_node):
		return
	world_node = null

func _gui_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT and event.pressed:
		var selected = _screen_to_world((event as InputEventMouseButton).position)
		set_marker_position(selected)
		emit_signal("position_selected", marker_position)
		queue_redraw()

func _draw() -> void:
	var preview_size = size
	if preview_size.x <= 1.0 or preview_size.y <= 1.0:
		preview_size = custom_minimum_size
	if preview_size.x <= 1.0 or preview_size.y <= 1.0:
		return

	draw_rect(Rect2(Vector2.ZERO, preview_size), Color(0.10, 0.13, 0.16, 1.0), true)
	_draw_grid(preview_size)
	_draw_terrain(preview_size)
	_draw_marker(preview_size)
	_draw_border(preview_size)

func _draw_grid(preview_size: Vector2) -> void:
	var columns := 10
	var rows := 10
	var grid_color := Color(1.0, 1.0, 1.0, 0.08)
	for column in range(1, columns):
		var x = preview_size.x * float(column) / float(columns)
		draw_line(Vector2(x, 0), Vector2(x, preview_size.y), grid_color, 1.0)
	for row in range(1, rows):
		var y = preview_size.y * float(row) / float(rows)
		draw_line(Vector2(0, y), Vector2(preview_size.x, y), grid_color, 1.0)

func _draw_terrain(preview_size: Vector2) -> void:
	if terrain_cells.is_empty():
		return

	var cell_width = max(1.0, preview_size.x / float(max(1, sample_columns)))
	var cell_height = max(1.0, preview_size.y / float(max(1, sample_rows)))
	for entry in terrain_cells:
		if typeof(entry) != TYPE_DICTIONARY:
			continue
		var cell = entry.get("cell")
		if typeof(cell) != TYPE_VECTOR2I:
			continue
		var source_id = int(entry.get("source_id", -1))
		var cell_color = Color(0.24, 0.54, 0.25, 0.95)
		if source_id == 1:
			cell_color = Color(0.21, 0.42, 0.75, 0.95)
		var top_left = Vector2(float(cell.x) * cell_width, float(cell.y) * cell_height)
		draw_rect(Rect2(top_left, Vector2(cell_width + 0.2, cell_height + 0.2)), cell_color, true)

func _draw_marker(preview_size: Vector2) -> void:
	var marker_size = Vector2(10, 10)
	var point = _world_to_screen(marker_position, preview_size)
	var top_left = point - marker_size * 0.5
	draw_circle(point, 6.0, Color(1.0, 0.20, 0.20, 0.95))
	draw_rect(Rect2(top_left, marker_size), Color(1.0, 1.0, 1.0, 0.30), false, 1.5)

func _draw_border(preview_size: Vector2) -> void:
	draw_rect(Rect2(Vector2.ZERO, preview_size), Color(1.0, 1.0, 1.0, 0.25), false, 2.0)

func _screen_to_world(screen_position: Vector2) -> Vector2:
	var preview_size = size
	if preview_size.x <= 1.0 or preview_size.y <= 1.0:
		preview_size = custom_minimum_size
	if preview_size.x <= 1.0 or preview_size.y <= 1.0:
		return marker_position
	return Vector2(
		clamp((screen_position.x / preview_size.x) * world_width, 0.0, world_width),
		clamp((screen_position.y / preview_size.y) * world_height, 0.0, world_height)
	)

func _world_to_screen(position_value: Vector2, preview_size: Vector2) -> Vector2:
	return Vector2(
		clamp(position_value.x, 0.0, world_width) / world_width * preview_size.x,
		clamp(position_value.y, 0.0, world_height) / world_height * preview_size.y
	)

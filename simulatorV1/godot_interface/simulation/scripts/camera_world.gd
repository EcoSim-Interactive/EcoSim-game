## Manages the world camera's movement with drag, inertia and zoom.
extends Camera2D

var dragging: bool = false
var velocity: Vector2 = Vector2.ZERO  # Velocity for inertia

var max_zoom: float = 15.0
var min_zoom: float = 0.1
var zoom_speed: float = 0.15

## Movement smoothing speed (higher = more responsive)
@export var smooth_speed: float = 12.0
## Friction for inertia (lower = slides longer)
@export var friction: float = 5.0
## Drag sensitivity multiplier
@export var drag_sensitivity: float = 1.0

## Initializes the camera's movement limits on startup.
func _ready() -> void:
	_set_camera_limits()

## Applies movement inertia when the user is no longer dragging the camera.
func _process(delta: float) -> void:
	# Apply inertia when not dragging
	if not dragging and velocity.length() > 0.5:
		global_position -= velocity * delta
		velocity = velocity.lerp(Vector2.ZERO, friction * delta)
		_clamp_position()

## Handles mouse drag (start/end, movement) and mouse wheel zoom.
func _input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		if event.button_index == MOUSE_BUTTON_LEFT:
			if event.pressed:
				dragging = true
				velocity = Vector2.ZERO  # Reset inertia at the start of the drag
			else:
				dragging = false
				# Inertia continues with the current velocity

		if event.button_index == MOUSE_BUTTON_WHEEL_UP and event.pressed:
			_set_zoom(zoom_speed, event.position)
		elif event.button_index == MOUSE_BUTTON_WHEEL_DOWN and event.pressed:
			_set_zoom(-zoom_speed, event.position)

	elif event is InputEventMouseMotion and dragging:
		var movement: Vector2 = event.relative * drag_sensitivity / zoom.x
		global_position -= movement
		velocity = movement / get_process_delta_time() * 0.1  # Capture the velocity for inertia
		_clamp_position()

## Restricts the camera's position to stay within the map's limits.
func _clamp_position() -> void:
	# Keep the camera within limits
	var vp_size = get_viewport_rect().size / zoom.x
	var half_vp = vp_size * 0.5
	
	var min_x = limit_left + half_vp.x
	var max_x = limit_right - half_vp.x
	if min_x > max_x:
		global_position.x = (limit_left + limit_right) / 2.0
	else:
		global_position.x = clamp(global_position.x, min_x, max_x)

	var min_y = limit_top + half_vp.y
	var max_y = limit_bottom - half_vp.y
	if min_y > max_y:
		global_position.y = (limit_top + limit_bottom) / 2.0
	else:
		global_position.y = clamp(global_position.y, min_y, max_y)

# Used for buttons zoom
## Zooms the camera in (used by the zoom buttons).
func zoom_in() -> void:
	_set_zoom(zoom_speed * 3.0)

## Zooms the camera out (used by the zoom buttons).
func zoom_out() -> void:
	_set_zoom(-zoom_speed * 3.0)

## Instantly centers the camera on a target position.
func center_on_target(target_pos: Vector2) -> void:
	global_position = target_pos
	velocity = Vector2.ZERO
	_clamp_position()


## Changes the zoom level while keeping the point under the mouse fixed on screen.
func _set_zoom(delta: float, mouse_pos: Vector2 = Vector2.ZERO) -> void:
	var old_z: float = zoom.x
	var new_z: float = clamp(old_z + delta, min_zoom, max_zoom)

	if is_equal_approx(new_z, old_z):
		return

	var vp_size: Vector2 = get_viewport_rect().size

	if mouse_pos != Vector2.ZERO:
		# Convert the mouse position to world coordinates before zooming
		var mouse_world_before: Vector2 = global_position + (mouse_pos - vp_size * 0.5) / old_z
		zoom = Vector2(new_z, new_z)
		# After zooming, adjust the position to keep the point under the mouse
		var mouse_world_after: Vector2 = global_position + (mouse_pos - vp_size * 0.5) / new_z
		global_position += mouse_world_before - mouse_world_after
	else:
		zoom = Vector2(new_z, new_z)
	
	velocity = Vector2.ZERO
	_clamp_position()

## Computes the movement limits and minimum zoom based on the map's size.
func _set_camera_limits() -> void:
	var grass := get_parent().get_node("Grass") as TileMapLayer
	var rect: Rect2i = grass.get_used_rect()
	
	if rect.size.x == 0 or rect.size.y == 0:
		return

	
	var tile_size: Vector2 = Vector2(grass.tile_set.tile_size) * grass.scale
	var map_size: Vector2 = Vector2(rect.size) * tile_size
	
	# Prevent zooming out further than the map's size
	var vp_size: Vector2 = get_viewport_rect().size
	var needed_zoom_x = vp_size.x / map_size.x
	var needed_zoom_y = vp_size.y / map_size.y
	min_zoom = max(0.1, max(needed_zoom_x, needed_zoom_y))
	if zoom.x < min_zoom:
		zoom = Vector2(min_zoom, min_zoom)
	
	var tile_origin: Vector2 = grass.global_position
	var map_origin: Vector2 = tile_origin + Vector2(rect.position) * tile_size
	var map_end: Vector2 = tile_origin + Vector2(rect.position + rect.size) * tile_size

	limit_left = int(map_origin.x)
	limit_top = int(map_origin.y)
	limit_right = int(map_end.x)
	limit_bottom = int(map_end.y)
	
	print("[Camera] Limites: ", limit_left, ",", limit_top, " -> ", limit_right, ",", limit_bottom)


## Adjusts the zoom and centers the camera so the whole map fits within the window.
func fit_camera_to_viewport(viewport_size: Vector2) -> void:
	var grass := get_parent().get_node("Grass") as TileMapLayer
	var rect: Rect2i = grass.get_used_rect()
	
	if rect.size.x == 0 or rect.size.y == 0:
		return
		
	# Get the actual tile size accounting for the scale
	var tile_size: Vector2 = Vector2(grass.tile_set.tile_size) * grass.scale
	
	var tile_origin: Vector2 = grass.global_position
	var map_origin: Vector2 = tile_origin + Vector2(rect.position) * tile_size
	var map_size: Vector2 = Vector2(rect.size) * tile_size

	var zoom_factor: float = min(viewport_size.x / map_size.x, viewport_size.y / map_size.y) * 1.5
	zoom_factor = clamp(zoom_factor, min_zoom, max_zoom)
	zoom = Vector2(zoom_factor, zoom_factor)

	global_position = map_origin + map_size * 0.5
	velocity = Vector2.ZERO
	
	print("[Camera] Centre: ", global_position, " | Taille map: ", map_size, " | Zoom: ", zoom_factor)

	_set_camera_limits()

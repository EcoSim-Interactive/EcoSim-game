extends Camera2D

var dragging: bool = false
var velocity: Vector2 = Vector2.ZERO  # Vélocité pour l'inertie

var max_zoom: float = 2.0
var min_zoom: float = 0.2
var zoom_speed: float = 0.1

## Vitesse de lissage du déplacement (plus élevé = plus réactif)
@export var smooth_speed: float = 12.0
## Friction pour l'inertie (plus bas = glisse plus longtemps)
@export var friction: float = 5.0
## Multiplicateur de sensibilité du drag
@export var drag_sensitivity: float = 1.0

func _ready() -> void:
	_set_camera_limits()

func _process(delta: float) -> void:
	# Appliquer l'inertie quand on ne drag pas
	if not dragging and velocity.length() > 0.5:
		global_position -= velocity * delta
		velocity = velocity.lerp(Vector2.ZERO, friction * delta)
		_clamp_position()

func _input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		if event.button_index == MOUSE_BUTTON_LEFT:
			if event.pressed:
				dragging = true
				velocity = Vector2.ZERO  # Reset inertie au début du drag
			else:
				dragging = false
				# L'inertie continue avec la vélocité actuelle

		if event.button_index == MOUSE_BUTTON_WHEEL_UP and event.pressed:
			_set_zoom(zoom_speed, event.position)
		elif event.button_index == MOUSE_BUTTON_WHEEL_DOWN and event.pressed:
			_set_zoom(-zoom_speed, event.position)

	elif event is InputEventMouseMotion and dragging:
		var movement: Vector2 = event.relative * drag_sensitivity / zoom.x
		global_position -= movement
		velocity = movement / get_process_delta_time() * 0.1  # Capturer la vélocité pour l'inertie
		_clamp_position()

func _clamp_position() -> void:
	# Garder la caméra dans les limites
	var vp_size = get_viewport_rect().size / zoom.x
	var half_vp = vp_size * 0.5
	
	global_position.x = clamp(global_position.x, limit_left + half_vp.x, limit_right - half_vp.x)
	global_position.y = clamp(global_position.y, limit_top + half_vp.y, limit_bottom - half_vp.y)

# Used for buttons zoom
func zoom_in() -> void:
	_set_zoom(-zoom_speed)

func zoom_out() -> void:
	_set_zoom(zoom_speed)


func _set_zoom(delta: float, mouse_pos: Vector2 = Vector2.ZERO) -> void:
	var old_z: float = zoom.x
	var new_z: float = clamp(old_z + delta, min_zoom, max_zoom)

	if is_equal_approx(new_z, old_z):
		return

	var vp_size: Vector2 = get_viewport_rect().size

	if mouse_pos != Vector2.ZERO:
		# Convertir la position souris en coordonnées monde avant zoom
		var mouse_world_before: Vector2 = global_position + (mouse_pos - vp_size * 0.5) / old_z
		zoom = Vector2(new_z, new_z)
		# Après zoom, ajuster la position pour garder le point sous la souris
		var mouse_world_after: Vector2 = global_position + (mouse_pos - vp_size * 0.5) / new_z
		global_position += mouse_world_before - mouse_world_after
	else:
		zoom = Vector2(new_z, new_z)
	
	velocity = Vector2.ZERO
	_clamp_position()

func _set_camera_limits() -> void:
	var grass := get_parent().get_node("Grass") as TileMapLayer
	var rect: Rect2i = grass.get_used_rect()
	
	# Obtenir la taille réelle d'une tile en tenant compte de l'échelle
	var tile_size: Vector2 = Vector2(grass.tile_set.tile_size) * grass.scale
	
	var tile_origin: Vector2 = grass.global_position

	var map_origin: Vector2 = tile_origin + Vector2(rect.position) * tile_size
	var map_end: Vector2 = tile_origin + Vector2(rect.position + rect.size) * tile_size

	limit_left = int(map_origin.x)
	limit_top = int(map_origin.y)
	limit_right = int(map_end.x)
	limit_bottom = int(map_end.y)
	
	print("[Camera] Limites: ", limit_left, ",", limit_top, " -> ", limit_right, ",", limit_bottom)


func fit_camera_to_viewport(viewport_size: Vector2) -> void:
	var grass := get_parent().get_node("Grass") as TileMapLayer
	var rect: Rect2i = grass.get_used_rect()
	
	# Obtenir la taille réelle d'une tile en tenant compte de l'échelle
	var tile_size: Vector2 = Vector2(grass.tile_set.tile_size) * grass.scale
	
	var tile_origin: Vector2 = grass.global_position
	var map_origin: Vector2 = tile_origin + Vector2(rect.position) * tile_size
	var map_size: Vector2 = Vector2(rect.size) * tile_size

	var zoom_factor: float = min(viewport_size.x / map_size.x, viewport_size.y / map_size.y)
	zoom_factor = clamp(zoom_factor, min_zoom, max_zoom)
	zoom = Vector2(zoom_factor, zoom_factor)

	global_position = map_origin + map_size * 0.5
	velocity = Vector2.ZERO
	
	print("[Camera] Centre: ", global_position, " | Taille map: ", map_size, " | Zoom: ", zoom_factor)

	_set_camera_limits()

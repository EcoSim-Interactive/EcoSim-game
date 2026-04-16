## Coordonne la communication WebSocket avec le backend et la mise a jour de la scene.
extends Node2D
class_name SimulationManager

var socket := WebSocketPeer.new()
var connected := false
var running := false   # false = pause par defaut
var precompute_ready := false
var precompute_pending := false

@export var animal_path: NodePath
@export var water_path: NodePath
@export var plant_food_path: NodePath
@export var meat_food_path: NodePath
@export var species_marker_path: NodePath

@onready var animal: Node2D = get_node_or_null(animal_path)
@onready var water_template: Node2D = get_node_or_null(water_path)
@onready var plant_food_template: Node2D = get_node_or_null(plant_food_path)
@onready var meat_food_template: Node2D = get_node_or_null(meat_food_path)
@onready var species_marker_template: Node2D = get_node_or_null(species_marker_path)
@onready var tilemap := $Grass
@onready var world_lighting = $world_lighting


var species_markers := {}
var food_markers := {}
var world_meta = {}
var terrain_chunks := {}
var chunks_received := 0
var total_chunks := 0
var world_ready := false
var resume_after_world_ready := false
var start_after_world_ready := false
var pending_steps: Array = []
var run_completed := false


const COLOR_PLANT := Color(0.15, 0.8, 0.15, 1.0)
const COLOR_OMNIVORE := Color(0.95, 0.85, 0.1, 1.0)
const COLOR_MEAT := Color(0.9, 0.35, 0.05, 1.0)

func _ready():
	socket.inbound_buffer_size = 1_000_000_000
	socket.outbound_buffer_size = 1_000_000_000  # pour autoriser l'envoi de gros JSON (rerun)
	var err = socket.connect_to_url("ws://localhost:8765")
	if err != OK:
		print("[CLIENT] Erreur de connexion :", err)
	set_process(true)

	if animal:
		animal.visible = false
	if species_marker_template:
		species_marker_template.visible = false
	if plant_food_template:
		plant_food_template.visible = false
	if meat_food_template:
		meat_food_template.visible = false
	if water_template:
		water_template.visible = false

func _process(_delta):
	socket.poll()
	var state = socket.get_ready_state()

	if not connected and state == WebSocketPeer.STATE_OPEN:
		connected = true
		print("[CLIENT] Connecte au serveur")
		_send_cmd("get_world")

	if state == WebSocketPeer.STATE_OPEN:
		while socket.get_available_packet_count() > 0:
			var pkt = socket.get_packet()
			var msg = pkt.get_string_from_utf8()
			_on_message(msg)
	elif state == WebSocketPeer.STATE_CLOSED and connected:
		print("[CLIENT] Connexion fermee")
		var close_code = socket.get_close_code()
		var close_reason = socket.get_close_reason()
		print("[CLIENT] Code de fermeture: ", close_code)
		print("[CLIENT] Raison: ", close_reason)
		connected = false
		running = false
		precompute_ready = false
		precompute_pending = false

func _on_message(msg: String):
	var data = JSON.parse_string(msg)
	if typeof(data) != TYPE_DICTIONARY:
		return

	match data.get("type", ""):
		"world_meta":
			_reset_visuals()
			world_ready = false
			resume_after_world_ready = running
			pending_steps.clear()
			run_completed = false
			if running:
				_send_cmd("pause")
				running = false
			world_meta = data["data"]
			terrain_chunks.clear()
			chunks_received = 0
			total_chunks = world_meta.get("total_chunks", 1)
			precompute_ready = false
			precompute_pending = false
		"terrain_chunk":
			var chunk = data["data"]
			var index = int(chunk.get("chunk_index", 0))
			var y_start = int(chunk.get("y_start", 0))
			var rows = chunk.get("rows", [])
			terrain_chunks[index] = {"y_start": y_start, "rows": rows}
			chunks_received += 1
			print("[CLIENT] Chunk recu :", index + 1, "/", total_chunks)
		"terrain_complete":
			if chunks_received == total_chunks:
				_spawn_world(world_meta)
				print("[CLIENT] Monde complet chargé")
				world_ready = true
				if start_after_world_ready:
					_request_precompute()
					_send_cmd("start")
					running = true
					start_after_world_ready = false
					print("[CLIENT] Start auto apres chargement du monde")
				elif resume_after_world_ready:
					_send_cmd("resume")
					running = true
					resume_after_world_ready = false
					print("[CLIENT] Resume auto apres chargement du monde")
				if pending_steps.size() > 0:
					for step_data in pending_steps:
						_update_simulation(step_data)
					pending_steps.clear()
			else:
				print("[CLIENT] Warning : chunks recus ", chunks_received, "attendu ", total_chunks)
		"step":
			if data["data"].has("hour") and data["data"].has("minute"):
				var h = int(data["data"]["hour"])
				var m = int(data["data"]["minute"])
				if world_lighting:
					world_lighting.update_time(h, m)
			if not world_ready:
				pending_steps.append(data["data"])
			else:
				_update_simulation(data["data"])
		"status":
			_handle_status(data["data"])
		"summary":
			print("[CLIENT] Resume recu")
			running = false
			run_completed = true
			start_after_world_ready = false
			resume_after_world_ready = false
		"error":
			print("[CLIENT] Erreur serveur :", data)

func _handle_status(payload):
	match typeof(payload):
		TYPE_STRING:
			print("[CLIENT] Etat serveur :", payload)
			var status_str := String(payload)
			if status_str.find("started") != -1 or status_str.find("resumed") != -1:
				running = true
				run_completed = false
			if status_str.find("paused") != -1:
				running = false
			if status_str.find("stopped") != -1:
				running = false
				precompute_ready = false
				precompute_pending = false
				run_completed = false
		TYPE_DICTIONARY:
			if payload.get("state", "") == "computed":
				precompute_ready = true
				precompute_pending = false
				print("[CLIENT] Pre-calcul termine :", payload)
			else:
				print("[CLIENT] Etat serveur :", payload)
		_:
			print("[CLIENT] Etat serveur (inconnu) :", payload)

func _spawn_world(world_data: Dictionary):
	_clear_species_markers()
	_clear_food_markers()
	_clear_water_markers()
	_clear_tilemap()
	
	if terrain_chunks.size() > 0:
		await _draw_terrain(terrain_chunks)

	for food in world_data.get("food_sources", []):
		_spawn_or_update_food(food)
	if world_data.get("water_sources", []):
		await _draw_water(world_data)

	#for w in world_data.get("water_sources", []):
		#var marker := _duplicate_water_template()
		#if marker:
			#marker.position = Vector2(float(w.get("x", 0.0)), float(w.get("y", 0.0)))
#
#func _duplicate_water_template() -> Node2D:
	#if water_template == null:
		#return null
	#var clone = water_template.duplicate()
	#clone.visible = true
	#clone.add_to_group("dynamic_water")
	#add_child(clone)
	#return clone

func _clear_water_markers() -> void:
	for node in get_tree().get_nodes_in_group("dynamic_water"):
		if node.get_parent() == self and is_instance_valid(node):
			node.queue_free()

# ---- Commandes (tout passe par cmd) ----
func _send_cmd(cmd: String, value = null):
	var payload := {"cmd": cmd}
	if value != null:
		payload["value"] = value
	socket.send_text(JSON.stringify(payload))

func _request_precompute(force: bool = false):
	if not connected:
		return
	if not force and (precompute_pending or precompute_ready):
		return
	if force:
		precompute_ready = false
	precompute_pending = true
	_send_cmd("compute")
	print("[CLIENT] Pre-calcul demande")

func compute_simulation():
	_request_precompute(true)

func start_simulation():
	if connected and not running:
		if run_completed:
			_reset_visuals()
			world_ready = false
			precompute_ready = false
			precompute_pending = false
			pending_steps.clear()
			start_after_world_ready = true
			run_completed = false
			_send_cmd("get_world")
			print("[CLIENT] Start apres fin de run : rechargement du monde")
		elif not world_ready:
			start_after_world_ready = true
			_request_precompute()
			run_completed = false
			print("[CLIENT] Start en attente de chargement du monde")
		else:
			_request_precompute()
			_send_cmd("start")
			running = true
			run_completed = false
			print("[CLIENT] Start envoye")

func pause_simulation():
	if connected and running:
		_send_cmd("pause")
		running = false
		print("[CLIENT] Pause envoyee")

func resume_simulation():
	if connected and not running:
		_send_cmd("resume")
		running = true
		print("[CLIENT] Reprise envoyee")

func stop_simulation():
	if connected:
		_send_cmd("stop")
		running = false
		precompute_ready = false
		precompute_pending = false
		print("[CLIENT] Stop envoye")

func set_speed(ms: int):
	if connected:
		_send_cmd("speed", ms)
		print("[CLIENT] Vitesse envoyee :", ms, "ms par step")

func rerun_simulation(sim_data: Dictionary):
	if not connected:
		print("[CLIENT] Rerun impossible : client non connecte")
		return
	stop_simulation()
	_reset_visuals()
	world_ready = false
	precompute_ready = false
	precompute_pending = false
	resume_after_world_ready = true
	var steps_count := 0
	if sim_data.has("steps") and typeof(sim_data["steps"]) == TYPE_ARRAY:
		steps_count = sim_data["steps"].size()
	_send_cmd("rerun", sim_data)
	running = true
	print("[CLIENT] Rerun envoye (", steps_count, " steps)")

# ---- Update visuel ----
func _update_simulation(step_data: Dictionary):
	_update_species_markers(step_data)
	_apply_food_updates(step_data)

func _update_species_markers(step_data: Dictionary) -> void:
	if not step_data.has("species"):
		return
	var species_states = step_data["species"]
	if typeof(species_states) != TYPE_ARRAY:
		return

	var active_names: Array = []
	for entry in species_states:
		if typeof(entry) != TYPE_DICTIONARY:
			continue
		var species_name := String(entry.get("name", ""))
		if species_name.is_empty():
			continue
		active_names.append(species_name)

		var pos_data: Dictionary = {}
		if entry.has("after") and typeof(entry["after"]) == TYPE_DICTIONARY:
			pos_data = entry["after"]
		elif entry.has("before") and typeof(entry["before"]) == TYPE_DICTIONARY:
			pos_data = entry["before"]

		var marker = _ensure_species_marker(species_name)
		if marker and pos_data.size() > 0:
			var px = float(pos_data.get("x", marker.position.x))
			var py = float(pos_data.get("y", marker.position.y))
			marker.position = Vector2(px, py)

	_remove_inactive_species_markers(active_names)

func _apply_food_updates(step_data: Dictionary) -> void:
	for food in step_data.get("new_food_sources", []):
		_spawn_or_update_food(food)
	for food in step_data.get("updated_food_sources", []):
		_spawn_or_update_food(food)
	for removed_id in step_data.get("removed_food_ids", []):
		_remove_food_marker(String(removed_id))

func _spawn_or_update_food(food_data: Dictionary) -> void:
	var food_id := String(food_data.get("id", ""))
	if food_id.is_empty():
		return

	var marker: Node2D = null
	if food_markers.has(food_id):
		var existing = food_markers[food_id]
		if is_instance_valid(existing):
			marker = existing

	if marker == null:
		marker = _create_food_marker(food_data)
		if marker == null:
			return
		food_markers[food_id] = marker

	if marker.has_method("update_state"):
		var color = _color_for_food_class(String(food_data.get("food_class", "plant")))
		marker.update_state(food_data, null, color)

func _create_food_marker(food_data: Dictionary) -> Node2D:
	var template := _get_food_template(String(food_data.get("food_class", "plant")))
	if template == null:
		return null
	var marker = template.duplicate()
	marker.visible = true
	marker.add_to_group("food_markers")
	add_child(marker)
	return marker

func _get_food_template(food_class: String) -> Node2D:
	var normalized := food_class.to_lower()
	if normalized in ["plant", "fungi"]:
		return plant_food_template
	if normalized in ["meat", "carrion"]:
		return meat_food_template if meat_food_template else plant_food_template
	if normalized == "omnivore":
		return plant_food_template
	return plant_food_template

func _color_for_food_class(food_class: String) -> Color:
	var normalized := food_class.to_lower()
	if normalized in ["plant", "fungi"]:
		return COLOR_PLANT
	if normalized in ["meat", "carrion"]:
		return COLOR_MEAT
	if normalized == "omnivore":
		return COLOR_OMNIVORE
	return COLOR_PLANT

func _remove_food_marker(food_id: String) -> void:
	if not food_markers.has(food_id):
		return
	var marker = food_markers[food_id]
	if is_instance_valid(marker):
		marker.queue_free()
	food_markers.erase(food_id)

func _clear_food_markers() -> void:
	for marker in get_tree().get_nodes_in_group("food_markers"):
		if marker.get_parent() == self and is_instance_valid(marker):
			marker.queue_free()
	food_markers.clear()
	
func _clear_tilemap():
	if $Grass:
		$Grass.clear()

func _draw_terrain(terrain):
	var tilemap_layer = $Grass as TileMapLayer
	tilemap_layer.scale = Vector2(1.0/16.0, 1.0/16.0)

	if not tilemap_layer:
		return
	
	print("[DEBUG] TileMapLayer trouvé, dessin du terrain...")
	print("[DEBUG] Chunks reçus : ", terrain.keys().size())
	
	for chunk_index in terrain.keys():
		var chunk = terrain[chunk_index]
		var y_start = chunk["y_start"]
		var rows = chunk["rows"]
		
		print("[DEBUG] Chunk ", chunk_index, " - y_start: ", y_start, " - rows: ", len(rows))
		
		for y in range(len(rows)):
			var row = rows[y]
			for x in range(len(row)):
				## var tile_id = int(row[x])
				var coords = Vector2i(x, y_start + y)
				
				# Avec tile_id = 0, on place la tuile à atlas_coords (0,12), A CHANGER EN FONCTION DE CE QU'ON VEUT (EAU ETCETC)
				tilemap_layer.set_cell(coords, 0, Vector2i(0, 12))
		# await get_tree().process_frame
				
		print("[DEBUG] Chunk ", chunk_index, " dessiné")
	
	print("[DEBUG] Terrain complet dessiné !")
	var camera = $Camera2D
	camera.fit_camera_to_viewport(get_viewport().size)

func _draw_water(world_data):
	var tilemap_layer = $Grass as TileMapLayer # Need to rename tilemaplayer to a better name
	tilemap_layer.scale = Vector2(1.0/16.0, 1.0/16.0)
	
	if not tilemap_layer:
		return
		
	var water_list = world_data.get("water_sources", [])
	if water_list.is_empty():
		return
		
	for w in water_list:
		var x = int(w.get("x", 0))
		var y = int(w.get("y", 0))

		# Exemple : tuile d’eau située à (5,15) dans l’atlas (1 is water_layer)
		tilemap_layer.set_cell(Vector2i(x, y), 1, Vector2i(4, 16))

func _ensure_species_marker(species_name: String) -> Node2D:
	if species_marker_template == null:
		return null

	if species_markers.has(species_name):
		var existing = species_markers[species_name]
		if is_instance_valid(existing):
			return existing

	var marker = species_marker_template.duplicate()
	marker.visible = true
	marker.name = "SpeciesMarker_%s" % species_name
	marker.position = Vector2.ZERO
	marker.add_to_group("species_markers")
	add_child(marker)
	species_markers[species_name] = marker
	return marker

func _remove_inactive_species_markers(active_names: Array) -> void:
	var to_remove: Array = []
	for species_name in species_markers.keys():
		if active_names.find(species_name) == -1:
			var marker = species_markers[species_name]
			if is_instance_valid(marker):
				marker.queue_free()
			to_remove.append(species_name)
	for name_to_remove in to_remove:
		species_markers.erase(name_to_remove)

func _clear_species_markers() -> void:
	for species_name in species_markers.keys():
		var marker = species_markers[species_name]
		if is_instance_valid(marker):
			marker.queue_free()
	species_markers.clear()

func _reset_visuals() -> void:
	_clear_species_markers()
	_clear_food_markers()
	_clear_water_markers()
	_clear_tilemap()
	pending_steps.clear()

func import_simulation(sim_data: Dictionary) -> void:
	print("[CLIENT] Import simulation...")

	if sim_data.has("world"):
		print("[CLIENT] Import world")
		_spawn_world(sim_data["world"])

	if sim_data.has("step"):
		print("[CLIENT] Import step data")
		_update_simulation(sim_data["step"])

	running = false
	precompute_ready = false
	precompute_pending = false

	print("[CLIENT] Simulation importée avec succès")

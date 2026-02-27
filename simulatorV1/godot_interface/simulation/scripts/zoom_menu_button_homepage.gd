extends MenuButton

@export var camera_path: NodePath
var camera: Node = null

func _ready() -> void:
	var popup: PopupMenu = get_popup()
	popup.hide_on_item_selection = false

	popup.add_item("Zoom In")
	popup.add_item("Zoom Out")

	var stylebox := StyleBoxFlat.new()
	stylebox.bg_color = Color(0.2, 0.2, 0.2)
	stylebox.content_margin_left = 10
	stylebox.content_margin_top = 8
	stylebox.content_margin_bottom = 8
	stylebox.content_margin_right = 10
	popup.add_theme_stylebox_override("item", stylebox)

	popup.add_theme_constant_override("align", 1)

	popup.connect("id_pressed", Callable(self, "_on_item_selected"))

	if camera_path != NodePath():
		camera = get_node(camera_path)

func _on_item_selected(id: int) -> void:
	if camera == null:
		return

	match id:
		0: camera.zoom_out()
		1: camera.zoom_in()

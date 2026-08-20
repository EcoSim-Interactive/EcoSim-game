## Provides a simple zoom menu to control the camera from the UI.
extends MenuButton

@export var camera_path: NodePath
var camera: Node = null

## Builds the zoom popup menu, styles it, connects the selection and retrieves the camera.
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

## Adjusts the camera zoom according to the chosen option, clamping the minimum zoom.
func _on_item_selected(id: int) -> void:
	if camera == null:
		return

	var zoom_step = Vector2(0.1, 0.1)
	match id:
		0: # Zoom In
			camera.zoom += zoom_step
		1: # Zoom Out
			camera.zoom -= zoom_step
			if camera.zoom.x < 0.1:
				camera.zoom = Vector2(0.1, 0.1)

## Plays an animal's base animation when it appears.
extends Sprite2D

## Starts the Idle animation when the animal spawns.
func _ready():
	$"Animal Animation".play("Idle")

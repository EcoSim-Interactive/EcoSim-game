## Joue l'animation de base d'un animal lors de son apparition.
extends Sprite2D

func _ready():
	$"Animal Animation".play("Idle")

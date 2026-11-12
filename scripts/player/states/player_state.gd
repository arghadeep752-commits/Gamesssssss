class_name PlayerState
extends RefCounted
## Base class for player states. The state machine calls these hooks.

var player: Player
var machine: PlayerStateMachine


func enter(_previous: String, _msg: Dictionary) -> void:
	pass


func exit() -> void:
	pass


func physics_update(_delta: float) -> void:
	pass


func on_animation_finished() -> void:
	pass


func on_frame_changed(_frame: int) -> void:
	pass


## Shared ground/air transitions used by several states. Returns true if it changed state.
func common_transitions() -> bool:
	var p := player
	if p.wants_special() and p.can_use_special():
		machine.change("special_attack", {"action": "special"})
		return true
	if p.wants_ability() and p.can_use_ability():
		machine.change("special_attack", {"action": "ability"})
		return true
	if p.wants_attack() and p.attack_cd <= 0.0:
		machine.change("attack")
		return true
	if p.near_ladder() and (Input.is_action_pressed("move_up") or (Input.is_action_pressed("move_down") and not p.is_on_floor())):
		machine.change("climb")
		return true
	return false

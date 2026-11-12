class_name PlayerStateMachine
extends RefCounted
## Finite state machine: IDLE, RUN, JUMP, FALL, ATTACK, SPECIAL_ATTACK, HURT, DEATH, VICTORY (+ CLIMB).

signal state_changed(from: String, to: String)

var states := {}
var current: PlayerState
var current_name := ""
var player: Player


func _init(p: Player) -> void:
	player = p
	_register("idle", PlayerIdleState.new())
	_register("run", PlayerRunState.new())
	_register("jump", PlayerJumpState.new())
	_register("fall", PlayerFallState.new())
	_register("attack", PlayerAttackState.new())
	_register("special_attack", PlayerSpecialState.new())
	_register("hurt", PlayerHurtState.new())
	_register("death", PlayerDeathState.new())
	_register("victory", PlayerVictoryState.new())
	_register("climb", PlayerClimbState.new())


func _register(name: String, s: PlayerState) -> void:
	s.player = player
	s.machine = self
	states[name] = s


func change(name: String, msg := {}) -> void:
	if not states.has(name):
		push_warning("Unknown player state " + name)
		return
	var prev := current_name
	if current:
		current.exit()
	current = states[name]
	current_name = name
	current.enter(prev, msg)
	state_changed.emit(prev, name)


func physics_update(delta: float) -> void:
	if current:
		current.physics_update(delta)

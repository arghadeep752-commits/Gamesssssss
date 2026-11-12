class_name HazardZone
extends Area2D
## Damaging area: spikes, lava, deep water, saw blades. Deadly zones send the player
## back to their last safe spot.

var damage := 20.0
var respawn := false     # lava/water/pits: teleport back after damage
var knock := 600.0


static func create(rect: Rect2, p_damage: float, p_respawn: bool) -> HazardZone:
	var h := HazardZone.new()
	h.damage = p_damage
	h.respawn = p_respawn
	h.collision_layer = 64
	h.collision_mask = 2 | 4
	h.position = rect.position + rect.size / 2.0
	var cs := CollisionShape2D.new()
	var r := RectangleShape2D.new()
	r.size = rect.size
	cs.shape = r
	h.add_child(cs)
	return h


func _physics_process(_delta: float) -> void:
	for b in get_overlapping_bodies():
		if b.is_in_group("player") and b.has_method("hazard_hit"):
			b.hazard_hit(self)
		elif b.is_in_group("enemy") and respawn and b.has_method("take_damage"):
			b.take_damage(9999.0, global_position, 0.0, false)

extends Node
## Generic object pool for frequently spawned nodes (projectiles, hit effects, popups).
## Usage: var n = Pool.take("kunai", factory_callable); ... Pool.give_back(n)

var _free := {}
var _created := 0


func take(key: String, factory: Callable) -> Node:
	var list: Array = _free.get(key, [])
	while list.size() > 0:
		var n = list.pop_back()
		if is_instance_valid(n):
			n.set_meta("pool_key", key)
			return n
	var node: Node = factory.call()
	node.set_meta("pool_key", key)
	_created += 1
	return node


func give_back(node: Node) -> void:
	if not is_instance_valid(node):
		return
	var key: String = node.get_meta("pool_key", "")
	if key == "":
		node.queue_free()
		return
	if node.get_parent():
		node.get_parent().remove_child(node)
	if not _free.has(key):
		_free[key] = []
	if _free[key].size() < 48:
		_free[key].append(node)
	else:
		node.queue_free()


func clear() -> void:
	for key in _free:
		for n in _free[key]:
			if is_instance_valid(n):
				n.queue_free()
	_free.clear()

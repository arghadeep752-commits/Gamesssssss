extends StaticBody3D
## Anything the player can use with the hand button.
## kind: "pickup", "door", "lock", "safe", "note", "search"

var kind := ""
var item_id := ""
var prompt := "Use"
var target: Node = null
var data := {}

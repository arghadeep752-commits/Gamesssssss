class_name Lane
extends RefCounted
## A polyline: a traffic lane (India drives on the left) or a footpath.

var p: PackedVector3Array = []
var d: PackedFloat32Array = []
var len := 0.1
var speed := 12.0
var next: Array[int] = []
var junction := false
var cls := "B"
var cars: Array = []          # TrafficCar


static func from_points(pts: Array) -> Lane:
	var l := Lane.new()
	for q in pts:
		l.p.append(G.v3(q))
	if l.p.size() == 0:
		l.p.append(Vector3.ZERO)
	if l.p.size() < 2:
		l.p.append(l.p[0] + Vector3.FORWARD)
	l.d.resize(l.p.size())
	l.d[0] = 0.0
	for i in range(1, l.p.size()):
		l.d[i] = l.d[i - 1] + l.p[i - 1].distance_to(l.p[i])
	l.len = maxf(0.1, l.d[l.p.size() - 1])
	return l


## [position, direction] at distance s along the line.
func at(s: float) -> Array:
	s = clampf(s, 0.0, len)
	var lo := 0
	var hi := d.size() - 1
	while hi - lo > 1:
		var m := (lo + hi) >> 1
		if d[m] <= s:
			lo = m
		else:
			hi = m
	var seg := d[hi] - d[lo]
	var t := (s - d[lo]) / seg if seg > 1e-4 else 0.0
	var dir := p[hi] - p[lo]
	dir = dir.normalized() if dir.length_squared() > 1e-6 else Vector3.FORWARD
	return [p[lo].lerp(p[hi], t), dir]


## [distance along the line, distance from it] of the closest point to q.
func nearest(q: Vector3) -> Array:
	var best := 1e18
	var bs := 0.0
	for i in p.size() - 1:
		var a := p[i]
		var ab := p[i + 1] - a
		var t := clampf((q - a).dot(ab) / maxf(1e-4, ab.length_squared()), 0.0, 1.0)
		var dd := (a + ab * t - q).length_squared()
		if dd < best:
			best = dd
			bs = d[i] + (d[i + 1] - d[i]) * t
	return [bs, sqrt(best)]

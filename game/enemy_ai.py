from __future__ import annotations

from math import acos, degrees

from panda3d.core import Vec3

from game.state import GameState


class BritishOfficerAI:
    def __init__(self, node, waypoints: list[tuple[float, float, float]], state: GameState) -> None:
        self.node = node
        self.waypoints = [Vec3(*p) for p in waypoints]
        self.state = state
        self.current = 0
        self.speed = 3.0
        self.detect_radius = 13.0
        self.detect_angle = 62.0
        self.cooldown = 0.0

    def update(self, dt: float, player_pos: Vec3, is_player_crouching: bool) -> bool:
        self._patrol(dt)
        self.cooldown = max(0.0, self.cooldown - dt)
        detected = self._can_see(player_pos, is_player_crouching)
        if detected and self.cooldown <= 0:
            self.state.add_suspicion(14 if is_player_crouching else 24)
            self.state.flags.add("officer_detected_player")
            self.cooldown = 2.0
        return detected

    def _patrol(self, dt: float) -> None:
        target = self.waypoints[self.current]
        pos = self.node.get_pos()
        delta = target - pos
        if delta.length() < 0.4:
            self.current = (self.current + 1) % len(self.waypoints)
            return
        delta.normalize()
        self.node.set_pos(pos + delta * self.speed * dt)
        self.node.look_at(target)

    def _can_see(self, player_pos: Vec3, crouching: bool) -> bool:
        to_player = player_pos - self.node.get_pos()
        distance = to_player.length()
        radius = self.detect_radius * (0.55 if crouching else 1.0)
        if distance > radius:
            return False
        to_player.z = 0
        if to_player.length_squared() == 0:
            return True
        to_player.normalize()
        forward = self.node.get_quat().get_forward()
        forward.z = 0
        if forward.length_squared() == 0:
            return True
        forward.normalize()
        dot = max(-1.0, min(1.0, forward.dot(to_player)))
        return degrees(acos(dot)) <= self.detect_angle * 0.5

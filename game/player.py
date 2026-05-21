from __future__ import annotations

from math import sin, cos, radians

from panda3d.core import Vec3, WindowProperties

import config


class FirstPersonPlayer:
    def __init__(self, app, input_handler) -> None:
        self.app = app
        self.input = input_handler
        self.node = app.render.attach_new_node("player")
        self.node.set_pos(*config.PLAYER_START_POS)
        self.heading = 0.0
        self.pitch = 0.0
        self.eye_height = 1.8
        self.crouch_height = 1.15
        self.capture_mouse()

    def capture_mouse(self) -> None:
        props = WindowProperties()
        props.set_cursor_hidden(True)
        self.app.win.request_properties(props)
        self.app.win.move_pointer(0, self.app.win.get_x_size() // 2, self.app.win.get_y_size() // 2)

    def release_mouse(self) -> None:
        props = WindowProperties()
        props.set_cursor_hidden(False)
        self.app.win.request_properties(props)

    def update(self, dt: float, paused: bool = False, can_move_to=None) -> None:
        if paused:
            return
        self._mouse_look()
        self._move(dt, can_move_to)
        height = self.crouch_height if self.input.keys["crouch"] else self.eye_height
        pos = self.node.get_pos()
        self.node.set_z(height)
        self.app.camera.set_pos(pos.x, pos.y, height)
        self.app.camera.set_hpr(self.heading, self.pitch, 0)

    def _mouse_look(self) -> None:
        if not self.app.mouseWatcherNode.has_mouse():
            return
        cx = self.app.win.get_x_size() // 2
        cy = self.app.win.get_y_size() // 2
        pointer = self.app.win.get_pointer(0)
        dx = pointer.get_x() - cx
        dy = pointer.get_y() - cy
        self.heading -= dx * config.MOUSE_SENSITIVITY
        self.pitch = max(-85, min(85, self.pitch - dy * config.MOUSE_SENSITIVITY))
        self.app.win.move_pointer(0, cx, cy)

    def _move(self, dt: float, can_move_to=None) -> None:
        direction = Vec3(0, 0, 0)
        if self.input.keys["forward"]:
            direction.y += 1
        if self.input.keys["backward"]:
            direction.y -= 1
        if self.input.keys["left"]:
            direction.x -= 1
        if self.input.keys["right"]:
            direction.x += 1
        if direction.length_squared() == 0:
            return
        direction.normalize()
        speed = config.PLAYER_SPRINT_SPEED if self.input.keys["sprint"] else config.PLAYER_SPEED
        if self.input.keys["crouch"]:
            speed *= 0.45
        h = radians(self.heading)
        forward = Vec3(-sin(h), cos(h), 0)
        right = Vec3(cos(h), sin(h), 0)
        delta = (right * direction.x + forward * direction.y) * speed * dt
        pos = self.node.get_pos()
        next_x = Vec3(max(-58, min(58, pos.x + delta.x)), pos.y, pos.z)
        if can_move_to is None or can_move_to(next_x):
            pos = next_x
        next_y = Vec3(pos.x, max(-58, min(58, pos.y + delta.y)), pos.z)
        if can_move_to is None or can_move_to(next_y):
            pos = next_y
        self.node.set_pos(pos.x, pos.y, self.node.get_z())

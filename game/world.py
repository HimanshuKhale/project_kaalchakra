from __future__ import annotations

import json
from pathlib import Path
from dataclasses import dataclass

from panda3d.core import AmbientLight, DirectionalLight, TextNode, Vec3, Vec4

from game.npc import NPC


@dataclass(frozen=True)
class Blocker:
    name: str
    min_x: float
    max_x: float
    min_y: float
    max_y: float

    def contains(self, point: Vec3, padding: float = 0.65) -> bool:
        return (
            self.min_x - padding <= point.x <= self.max_x + padding
            and self.min_y - padding <= point.y <= self.max_y + padding
        )

    def intersects_segment(self, start: Vec3, end: Vec3, steps: int = 24) -> bool:
        for index in range(1, steps):
            t = index / steps
            point = start + (end - start) * t
            if self.contains(point, padding=0.1):
                return True
        return False


class World:
    def __init__(self, app, locations_path: Path, npcs_path: Path) -> None:
        self.app = app
        self.locations = {loc["id"]: loc for loc in json.loads(locations_path.read_text(encoding="utf-8"))}
        self.npcs = [NPC.from_dict(n) for n in json.loads(npcs_path.read_text(encoding="utf-8"))]
        self.npc_by_id = {npc.id: npc for npc in self.npcs}
        self.blockers: list[Blocker] = []
        self.officer_node = None
        self._setup_lighting()
        self._build_ground()
        self._build_locations()
        self._build_npcs()

    def _setup_lighting(self) -> None:
        ambient = AmbientLight("warm ambient")
        ambient.set_color(Vec4(0.45, 0.39, 0.33, 1))
        self.app.render.set_light(self.app.render.attach_new_node(ambient))
        sun = DirectionalLight("low sun")
        sun.set_color(Vec4(0.95, 0.78, 0.52, 1))
        sun_np = self.app.render.attach_new_node(sun)
        sun_np.set_hpr(-35, -45, 0)
        self.app.render.set_light(sun_np)
        self.app.set_background_color(0.55, 0.66, 0.72)

    def _cube(self, name: str, pos, scale, color, blocks: bool = False):
        node = self.app.loader.load_model("models/box")
        node.reparent_to(self.app.render)
        node.set_name(name)
        node.set_pos(*pos)
        node.set_scale(*scale)
        node.set_color(*color)
        if blocks:
            self.blockers.append(Blocker(name, pos[0] - scale[0], pos[0] + scale[0], pos[1] - scale[1], pos[1] + scale[1]))
        return node

    def _label(self, text: str, parent, pos, scale: float, color=(1, 1, 1, 1)):
        text_node = TextNode(f"{text} label")
        text_node.set_text(text)
        text_node.set_align(TextNode.ACenter)
        text_node.set_text_color(*color)
        label = parent.attach_new_node(text_node)
        label.set_pos(*pos)
        label.set_scale(scale)
        label.set_billboard_point_eye()
        return label

    def _build_ground(self) -> None:
        self._cube("earth road grid", (0, 0, -0.06), (62, 62, 0.04), (0.43, 0.34, 0.23, 1))
        self._cube("hooghly river", (-48, 0, 0.0), (10, 62, 0.03), (0.12, 0.34, 0.48, 1))
        for y in range(-48, 49, 12):
            self._cube("main road", (0, y, 0.01), (45, 1.1, 0.02), (0.58, 0.49, 0.36, 1))
        for x in [-22, -5, 14, 32]:
            self._cube("lane", (x, 0, 0.02), (0.85, 46, 0.02), (0.54, 0.45, 0.32, 1))

    def _build_locations(self) -> None:
        colors = {
            "river_ghat": (0.72, 0.66, 0.52, 1),
            "bazaar": (0.72, 0.43, 0.27, 1),
            "scholars_house": (0.54, 0.41, 0.32, 1),
            "printing_press": (0.30, 0.30, 0.34, 1),
            "palace_outer": (0.76, 0.64, 0.44, 1),
            "palace_inner": (0.85, 0.74, 0.52, 1),
            "alley_escape": (0.28, 0.24, 0.22, 1),
        }
        for loc in self.locations.values():
            x, y, z = loc["pos"]
            sx, sy, sz = loc["scale"]
            blocks = loc["id"] in {"scholars_house", "printing_press"}
            self._cube(loc["name"], (x, y, z + sz), (sx, sy, sz), colors.get(loc["id"], (0.5, 0.5, 0.5, 1)), blocks=blocks)
            self._label(loc["name"], self.app.render, (x, y, z + sz * 2 + 1.2), 1.25, (1, 0.93, 0.72, 1))
        self._build_palace_walls()
        self._build_bazaar_stalls()

    def _build_palace_walls(self) -> None:
        self._cube("palace north wall", (28, 36, 1.5), (19, 0.6, 1.5), (0.62, 0.49, 0.34, 1), blocks=True)
        self._cube("palace south wall", (28, 10, 1.5), (19, 0.6, 1.5), (0.62, 0.49, 0.34, 1), blocks=True)
        self._cube("palace west wall", (9, 23, 1.5), (0.6, 13, 1.5), (0.62, 0.49, 0.34, 1), blocks=True)
        self._cube("palace east wall", (47, 23, 1.5), (0.6, 13, 1.5), (0.62, 0.49, 0.34, 1), blocks=True)
        self._cube("treasury marker", (39, 30, 1.2), (2.4, 2.4, 1.2), (0.18, 0.42, 0.52, 1), blocks=True)

    def _build_bazaar_stalls(self) -> None:
        for i, x in enumerate([-22, -15, -8, -1, 6]):
            self._cube("bazaar stall", (x, -18 + (i % 2) * 5, 0.8), (2.2, 1.5, 0.8), (0.63, 0.22 + i * 0.08, 0.21, 1), blocks=True)

    def _build_npcs(self) -> None:
        npc_colors = {
            "scholar": (0.18, 0.34, 0.62, 1),
            "printer": (0.22, 0.22, 0.24, 1),
            "boatman": (0.16, 0.44, 0.38, 1),
            "minister": (0.55, 0.40, 0.16, 1),
            "nawab": (0.62, 0.24, 0.40, 1),
            "sage": (0.86, 0.65, 0.24, 1),
            "british_officer": (0.70, 0.10, 0.08, 1),
        }
        for npc in self.npcs:
            pos = self.locations[npc.location]["npc_positions"].get(npc.id, self.locations[npc.location]["pos"])
            npc.node = self._cube(npc.id, (pos[0], pos[1], 1.0), (0.55, 0.55, 1.0), npc_colors.get(npc.id, (0.4, 0.4, 0.4, 1)))
            self._label(npc.name, npc.node, (0, 0, 1.45), 0.55)
            if npc.id == "british_officer":
                self.officer_node = npc.node

    def nearest_npc(self, player_pos: Vec3, max_distance: float, state) -> NPC | None:
        nearest = None
        nearest_dist = max_distance
        for npc in self.npcs:
            if npc.id == "british_officer" or npc.node is None:
                continue
            if npc.location not in state.unlocked_locations:
                continue
            dist = (npc.node.get_pos() - player_pos).length()
            if dist < nearest_dist:
                nearest = npc
                nearest_dist = dist
        return nearest

    def location_of_player(self, player_pos: Vec3) -> str:
        closest = min(self.locations.values(), key=lambda loc: (Vec3(*loc["pos"]) - player_pos).length())
        return closest["name"]

    def is_blocked(self, position: Vec3) -> bool:
        return any(blocker.contains(position) for blocker in self.blockers)

    def has_line_of_sight(self, start: Vec3, end: Vec3) -> bool:
        return not any(blocker.intersects_segment(start, end) for blocker in self.blockers)

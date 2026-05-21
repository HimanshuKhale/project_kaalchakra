from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from panda3d.core import AmbientLight, DirectionalLight, Fog, NodePath, TextNode, Vec3, Vec4

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

    def intersects_segment(self, start: Vec3, end: Vec3, steps: int = 32) -> bool:
        for index in range(1, steps):
            t = index / steps
            point = start + (end - start) * t
            if self.contains(point, padding=0.05):
                return True
        return False


class World:
    def __init__(self, app, locations_path: Path, npcs_path: Path) -> None:
        self.app = app
        self.locations = {loc["id"]: loc for loc in json.loads(locations_path.read_text(encoding="utf-8"))}
        self.npcs = [NPC.from_dict(n) for n in json.loads(npcs_path.read_text(encoding="utf-8"))]
        self.npc_by_id = {npc.id: npc for npc in self.npcs}
        self.blockers: list[Blocker] = []
        self.officer_node: NodePath | None = None

        self.palette = {
            "dirt": (0.43, 0.35, 0.24, 1),
            "road": (0.58, 0.50, 0.38, 1),
            "river": (0.08, 0.31, 0.43, 1),
            "wet_edge": (0.23, 0.35, 0.32, 1),
            "mud_brick": (0.54, 0.40, 0.28, 1),
            "plaster": (0.74, 0.65, 0.50, 1),
            "palace": (0.78, 0.66, 0.45, 1),
            "palace_dark": (0.54, 0.42, 0.30, 1),
            "wood": (0.34, 0.20, 0.12, 1),
            "cloth_red": (0.62, 0.18, 0.12, 1),
            "cloth_yellow": (0.86, 0.65, 0.26, 1),
            "leaf": (0.18, 0.40, 0.20, 1),
        }

        self._setup_lighting()
        self._build_ground_and_roads()
        self._build_river_ghat()
        self._build_town_houses()
        self._build_bazaar()
        self._build_scholar_house()
        self._build_printing_press()
        self._build_palace()
        self._build_alley()
        self._build_atmosphere_props()
        self._build_npcs()

    def _setup_lighting(self) -> None:
        ambient = AmbientLight("soft bengal daylight")
        ambient.set_color(Vec4(0.42, 0.38, 0.32, 1))
        self.app.render.set_light(self.app.render.attach_new_node(ambient))

        sun = DirectionalLight("late afternoon sun")
        sun.set_color(Vec4(1.0, 0.82, 0.55, 1))
        sun_np = self.app.render.attach_new_node(sun)
        sun_np.set_hpr(-42, -38, 0)
        self.app.render.set_light(sun_np)

        fill = DirectionalLight("river fill")
        fill.set_color(Vec4(0.25, 0.34, 0.42, 1))
        fill_np = self.app.render.attach_new_node(fill)
        fill_np.set_hpr(120, -15, 0)
        self.app.render.set_light(fill_np)

        fog = Fog("soft distance haze")
        fog.set_color(0.58, 0.64, 0.64)
        fog.set_exp_density(0.012)
        self.app.render.set_fog(fog)
        self.app.set_background_color(0.58, 0.68, 0.72)

    def _cube(self, name: str, pos, scale, color, blocks: bool = False, parent: NodePath | None = None) -> NodePath:
        node = self.app.loader.load_model("models/box")
        node.reparent_to(parent or self.app.render)
        node.set_name(name)
        node.set_pos(*pos)
        node.set_scale(*scale)
        node.set_color(*color)
        if blocks and parent is None:
            self.blockers.append(Blocker(name, pos[0] - scale[0], pos[0] + scale[0], pos[1] - scale[1], pos[1] + scale[1]))
        return node

    def _label(self, text: str, parent: NodePath, pos, scale: float, color=(0.95, 0.88, 0.72, 1)) -> NodePath:
        text_node = TextNode(f"{text} label")
        text_node.set_text(text)
        text_node.set_align(TextNode.ACenter)
        text_node.set_text_color(*color)
        label = parent.attach_new_node(text_node)
        label.set_pos(*pos)
        label.set_scale(scale)
        label.set_billboard_point_eye()
        return label

    def _sign(self, text: str, pos, facing: float = 0.0) -> None:
        post = self._cube(f"{text} sign post", (pos[0], pos[1], 0.9), (0.08, 0.08, 0.9), self.palette["wood"])
        board = self._cube(f"{text} sign board", (0, 0, 0.6), (0.9, 0.08, 0.28), (0.24, 0.15, 0.09, 1), parent=post)
        board.set_h(facing)
        self._label(text, post, (0, -0.1, 1.52), 0.22)

    def _building(self, name: str, pos, scale, color, roof_color=None, door_side: str = "south") -> None:
        x, y, _ = pos
        sx, sy, sz = scale
        self._cube(name, (x, y, sz), (sx, sy, sz), color, blocks=True)
        self._cube(f"{name} roof", (x, y, sz * 2 + 0.22), (sx + 0.25, sy + 0.25, 0.22), roof_color or self.palette["wood"])

        door_offsets = {
            "south": (0, -sy - 0.03, 0.8, 0),
            "north": (0, sy + 0.03, 0.8, 0),
            "west": (-sx - 0.03, 0, 0.8, 90),
            "east": (sx + 0.03, 0, 0.8, 90),
        }
        dx, dy, dz, h = door_offsets[door_side]
        door = self._cube(f"{name} door", (x + dx, y + dy, dz), (0.55, 0.06, 0.8), self.palette["wood"])
        door.set_h(h)

        for wx, wy, hrot in [(-sx * 0.55, -sy - 0.04, 0), (sx * 0.55, -sy - 0.04, 0), (-sx - 0.04, sy * 0.35, 90), (sx + 0.04, sy * 0.35, 90)]:
            window = self._cube(f"{name} window", (x + wx, y + wy, 1.55), (0.36, 0.035, 0.32), (0.08, 0.12, 0.13, 1))
            window.set_h(hrot)

    def _arch_gate(self, name: str, center, width: float, height: float, depth: float, color) -> None:
        x, y, _ = center
        pillar_w = 0.45
        self._cube(f"{name} left pillar", (x - width * 0.5, y, height * 0.5), (pillar_w, depth, height * 0.5), color, blocks=True)
        self._cube(f"{name} right pillar", (x + width * 0.5, y, height * 0.5), (pillar_w, depth, height * 0.5), color, blocks=True)
        self._cube(f"{name} lintel", (x, y, height + 0.2), (width * 0.5 + pillar_w, depth, 0.32), color, blocks=True)

    def _build_ground_and_roads(self) -> None:
        self._cube("town earth", (0, 0, -0.08), (62, 62, 0.04), self.palette["dirt"])
        self._cube("river water", (-52, 0, -0.02), (10, 64, 0.03), self.palette["river"])
        self._cube("river wet edge", (-40.5, 0, 0.0), (1.4, 64, 0.035), self.palette["wet_edge"])

        roads = [
            ("ghat road", (-35, -30, 0.02), (10, 2.0, 0.035)),
            ("bazaar road", (-18, -22, 0.025), (18, 1.65, 0.035)),
            ("press lane", (-1, -27, 0.025), (1.55, 9, 0.035)),
            ("north lane", (-20, -3, 0.025), (1.55, 26, 0.035)),
            ("scholar lane", (-20, 12, 0.03), (10, 1.45, 0.035)),
            ("palace approach", (3, 8, 0.03), (26, 1.75, 0.035)),
            ("palace road", (14, 16, 0.03), (1.6, 10, 0.035)),
            ("alley bend", (11, 34, 0.03), (1.25, 15, 0.035)),
            ("alley exit", (7, 47, 0.03), (9, 1.25, 0.035)),
        ]
        for name, pos, scale in roads:
            self._cube(name, pos, scale, self.palette["road"])

        self._cube("river boundary north", (-42, 37, 0.55), (1, 25, 0.55), (0.25, 0.23, 0.18, 1), blocks=True)
        self._cube("river boundary south", (-42, -50, 0.55), (1, 8, 0.55), (0.25, 0.23, 0.18, 1), blocks=True)

    def _build_river_ghat(self) -> None:
        for i in range(6):
            self._cube(f"ghat step {i}", (-43.5 + i * 1.0, -30, 0.1 + i * 0.12), (0.55, 7.2, 0.12), (0.62, 0.56, 0.44, 1))
        self._cube("ghat landing", (-37, -30, 0.12), (3.5, 7.5, 0.12), (0.68, 0.62, 0.49, 1))
        self._cube("moored boat hull", (-48, -35, 0.25), (2.4, 0.55, 0.24), (0.20, 0.11, 0.06, 1))
        self._cube("moored boat cloth", (-48, -35, 0.65), (1.3, 0.5, 0.18), (0.78, 0.68, 0.44, 1))
        self._sign("River Ghat", (-35.5, -37.5, 0), facing=0)

    def _build_town_houses(self) -> None:
        houses = [
            ("south house a", (-31, -19, 0), (3.2, 2.8, 1.5), "south"),
            ("south house b", (-26, -34, 0), (2.8, 3.5, 1.35), "west"),
            ("bazaar back house", (-13, -31, 0), (3.1, 2.2, 1.35), "north"),
            ("lane house a", (-27, 2, 0), (3.3, 2.8, 1.45), "east"),
            ("lane house b", (-12, 2, 0), (3.0, 2.6, 1.35), "west"),
            ("palace approach house", (2, 1, 0), (3.8, 3.0, 1.45), "north"),
        ]
        for name, pos, scale, door in houses:
            self._building(name, pos, scale, self.palette["mud_brick"], roof_color=(0.22, 0.12, 0.08, 1), door_side=door)

    def _build_bazaar(self) -> None:
        self._cube("bazaar packed earth", (-13, -20, 0.02), (12, 8, 0.035), (0.52, 0.40, 0.28, 1))
        stall_specs = [
            (-23, -18, self.palette["cloth_red"]),
            (-18, -24, self.palette["cloth_yellow"]),
            (-12, -17, (0.24, 0.48, 0.43, 1)),
            (-6, -23, (0.64, 0.34, 0.18, 1)),
            (-1, -18, (0.42, 0.28, 0.55, 1)),
        ]
        for i, (x, y, cloth) in enumerate(stall_specs):
            self._cube(f"bazaar stall counter {i}", (x, y, 0.55), (1.5, 0.9, 0.5), self.palette["wood"], blocks=True)
            self._cube(f"bazaar stall canopy {i}", (x, y, 1.45), (1.8, 1.05, 0.12), cloth)
            self._cube(f"bazaar stall pole {i}a", (x - 1.35, y - 0.75, 0.9), (0.06, 0.06, 0.9), self.palette["wood"])
            self._cube(f"bazaar stall pole {i}b", (x + 1.35, y + 0.75, 0.9), (0.06, 0.06, 0.9), self.palette["wood"])
        for i, pos in enumerate([(-20, -16), (-10, -25), (-4, -15), (-16, -20)]):
            self._cube(f"bazaar crate {i}", (pos[0], pos[1], 0.35), (0.5, 0.5, 0.35), (0.28, 0.16, 0.08, 1), blocks=True)

    def _build_scholar_house(self) -> None:
        self._building("scholar house", (-25, 14, 0), (4.3, 4.0, 1.75), (0.62, 0.53, 0.42, 1), roof_color=(0.24, 0.13, 0.08, 1), door_side="east")
        self._cube("scholar veranda floor", (-19.6, 14, 0.18), (1.2, 3.6, 0.16), (0.55, 0.47, 0.36, 1))
        for y in [11.2, 13.0, 15.0, 16.8]:
            self._cube("scholar veranda pillar", (-18.6, y, 0.9), (0.12, 0.12, 0.9), (0.50, 0.42, 0.32, 1), blocks=True)
        self._sign("Scholar", (-17.3, 9.4, 0), facing=90)

    def _build_printing_press(self) -> None:
        self._building("printing press", (3, -28, 0), (4.8, 3.7, 1.65), (0.36, 0.34, 0.34, 1), roof_color=(0.15, 0.13, 0.12, 1), door_side="east")
        self._cube("press chimney", (0.3, -30.2, 3.55), (0.42, 0.42, 1.0), (0.18, 0.16, 0.15, 1), blocks=True)
        self._cube("press loading table", (8.6, -28.8, 0.55), (1.0, 0.7, 0.5), self.palette["wood"], blocks=True)
        self._sign("Press", (9.7, -31.6, 0), facing=90)

    def _build_palace(self) -> None:
        self._cube("palace outer floor", (28, 23, 0.04), (18, 14, 0.04), (0.69, 0.57, 0.39, 1))
        self._cube("palace court floor", (27, 22, 0.08), (9.5, 7.5, 0.04), (0.74, 0.63, 0.45, 1))

        self._cube("palace north wall left", (18, 36, 1.7), (9, 0.55, 1.7), self.palette["palace_dark"], blocks=True)
        self._cube("palace north wall right", (38, 36, 1.7), (9, 0.55, 1.7), self.palette["palace_dark"], blocks=True)
        self._cube("palace south wall left", (18, 10, 1.7), (7, 0.55, 1.7), self.palette["palace_dark"], blocks=True)
        self._cube("palace south wall right", (38, 10, 1.7), (7, 0.55, 1.7), self.palette["palace_dark"], blocks=True)
        self._cube("palace west wall lower", (9, 17, 1.7), (0.55, 7, 1.7), self.palette["palace_dark"], blocks=True)
        self._cube("palace west wall upper", (9, 31, 1.7), (0.55, 5, 1.7), self.palette["palace_dark"], blocks=True)
        self._cube("palace east wall", (47, 23, 1.7), (0.55, 13, 1.7), self.palette["palace_dark"], blocks=True)
        self._arch_gate("palace entrance gate", (28, 10, 0), 4.5, 3.0, 0.7, self.palette["palace"])

        for x in [16, 20, 24, 32, 36, 40]:
            self._cube("palace court pillar", (x, 16, 1.3), (0.22, 0.22, 1.3), self.palette["palace"], blocks=True)
            self._cube("palace court pillar rear", (x, 30, 1.3), (0.22, 0.22, 1.3), self.palette["palace"], blocks=True)
        self._cube("palace inner hall backdrop", (34, 32.8, 1.8), (7.0, 0.7, 1.8), self.palette["palace"], blocks=True)
        self._cube("palace inner hall west screen", (27.2, 29, 1.4), (0.45, 3.6, 1.4), self.palette["palace"], blocks=True)
        self._cube("palace inner hall east screen", (40.8, 29, 1.4), (0.45, 3.6, 1.4), self.palette["palace"], blocks=True)
        self._cube("palace inner hall floor", (34, 29, 0.12), (7.0, 4.8, 0.08), (0.80, 0.70, 0.50, 1))
        self._cube("palace inner hall roof", (34, 29, 3.85), (7.5, 5.3, 0.3), (0.42, 0.21, 0.12, 1))
        self._arch_gate("inner wing arch", (34, 23.8, 0), 3.8, 2.5, 0.45, self.palette["palace"])
        self._cube("inner wing open floor", (34, 24.8, 0.12), (4.8, 1.2, 0.08), (0.76, 0.66, 0.47, 1))
        self._cube("treasury plinth", (40, 30, 0.45), (1.7, 1.7, 0.45), (0.16, 0.36, 0.44, 1), blocks=True)
        self._cube("treasury glow", (40, 30, 1.05), (0.55, 0.55, 0.55), (0.25, 0.75, 0.85, 1))

    def _build_alley(self) -> None:
        self._cube("alley ground", (9, 41, 0.04), (4.0, 13, 0.04), (0.30, 0.26, 0.22, 1))
        self._cube("alley west wall", (5, 39, 1.55), (0.45, 12, 1.55), (0.28, 0.22, 0.18, 1), blocks=True)
        self._cube("alley east wall lower", (13, 34, 1.55), (0.45, 6, 1.55), (0.34, 0.27, 0.21, 1), blocks=True)
        self._cube("alley east wall upper", (13, 48, 1.55), (0.45, 5, 1.55), (0.34, 0.27, 0.21, 1), blocks=True)
        self._cube("sage shrine base", (7, 48, 0.4), (1.2, 1.0, 0.35), (0.52, 0.44, 0.34, 1), blocks=True)
        self._cube("sage lamp", (7, 46.2, 0.75), (0.18, 0.18, 0.55), (0.88, 0.58, 0.22, 1))

    def _build_atmosphere_props(self) -> None:
        for i, (x, y) in enumerate([(-32, -10), (-24, -6), (-4, 7), (14, 6), (45, 5), (2, 42)]):
            self._tree(f"tree {i}", x, y)
        for i, (x, y) in enumerate([(-33, -28), (-18, -22), (-2, -27), (-15, 12), (15, 10), (12, 37), (30, 12)]):
            self._lamp(f"lamp {i}", x, y)

    def _tree(self, name: str, x: float, y: float) -> None:
        self._cube(f"{name} trunk", (x, y, 0.9), (0.18, 0.18, 0.9), (0.22, 0.13, 0.07, 1), blocks=True)
        self._cube(f"{name} crown low", (x, y, 1.9), (0.9, 0.7, 0.45), self.palette["leaf"])
        self._cube(f"{name} crown high", (x, y, 2.45), (0.65, 0.5, 0.38), (0.13, 0.32, 0.16, 1))

    def _lamp(self, name: str, x: float, y: float) -> None:
        self._cube(f"{name} post", (x, y, 0.8), (0.07, 0.07, 0.8), (0.16, 0.12, 0.08, 1))
        self._cube(f"{name} flame", (x, y, 1.65), (0.18, 0.18, 0.22), (1.0, 0.62, 0.22, 1))

    def _build_npcs(self) -> None:
        for npc in self.npcs:
            pos = self.locations[npc.location]["npc_positions"].get(npc.id, self.locations[npc.location]["pos"])
            npc.node = self.app.render.attach_new_node(npc.id)
            npc.node.set_pos(pos[0], pos[1], 0)
            self._humanoid(npc)
            self._label(npc.name, npc.node, (0, 0, 2.35), 0.30, (1, 0.96, 0.82, 1))
            if npc.id == "british_officer":
                self.officer_node = npc.node

    def _humanoid(self, npc: NPC) -> None:
        looks = {
            "boatman": {"torso": (0.16, 0.44, 0.38, 1), "legs": (0.86, 0.78, 0.58, 1), "accent": (0.90, 0.72, 0.42, 1), "height": 1.0},
            "scholar": {"torso": (0.20, 0.32, 0.58, 1), "legs": (0.70, 0.66, 0.52, 1), "accent": (0.95, 0.90, 0.72, 1), "height": 1.08},
            "printer": {"torso": (0.28, 0.27, 0.25, 1), "legs": (0.44, 0.33, 0.24, 1), "accent": (0.74, 0.62, 0.43, 1), "height": 1.0},
            "minister": {"torso": (0.56, 0.38, 0.16, 1), "legs": (0.28, 0.20, 0.14, 1), "accent": (0.91, 0.75, 0.32, 1), "height": 1.08},
            "nawab": {"torso": (0.62, 0.20, 0.36, 1), "legs": (0.36, 0.20, 0.28, 1), "accent": (0.95, 0.80, 0.30, 1), "height": 1.18},
            "british_officer": {"torso": (0.68, 0.08, 0.06, 1), "legs": (0.08, 0.10, 0.12, 1), "accent": (0.95, 0.88, 0.60, 1), "height": 1.1},
            "sage": {"torso": (0.82, 0.58, 0.22, 1), "legs": (0.52, 0.34, 0.16, 1), "accent": (0.95, 0.82, 0.42, 1), "height": 1.05},
        }
        look = looks.get(npc.id, looks["printer"])
        parent = npc.node
        h = look["height"]
        skin = (0.58, 0.40, 0.28, 1)
        self._cube(f"{npc.id} torso", (0, 0, 1.12 * h), (0.34, 0.20, 0.48 * h), look["torso"], parent=parent)
        self._cube(f"{npc.id} head", (0, 0, 1.78 * h), (0.24, 0.22, 0.24), skin, parent=parent)
        self._cube(f"{npc.id} left arm", (-0.43, 0, 1.10 * h), (0.10, 0.12, 0.42 * h), look["accent"], parent=parent)
        self._cube(f"{npc.id} right arm", (0.43, 0, 1.10 * h), (0.10, 0.12, 0.42 * h), look["accent"], parent=parent)
        self._cube(f"{npc.id} left leg", (-0.15, 0, 0.44 * h), (0.12, 0.12, 0.42 * h), look["legs"], parent=parent)
        self._cube(f"{npc.id} right leg", (0.15, 0, 0.44 * h), (0.12, 0.12, 0.42 * h), look["legs"], parent=parent)
        self._cube(f"{npc.id} sash", (0, -0.03, 1.17 * h), (0.39, 0.04, 0.08), look["accent"], parent=parent)
        if npc.id in {"minister", "nawab", "british_officer"}:
            self._cube(f"{npc.id} hat", (0, 0, 2.05 * h), (0.30, 0.26, 0.10), look["accent"], parent=parent)
        if npc.id == "sage":
            self._cube("sage cloak", (0, 0.08, 1.02), (0.46, 0.08, 0.70), (0.70, 0.42, 0.14, 1), parent=parent)

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

from __future__ import annotations

import json
from pathlib import Path

from game.state import GameState


class MissionManager:
    def __init__(self, path: Path, state: GameState) -> None:
        self.missions = {m["id"]: m for m in json.loads(path.read_text(encoding="utf-8"))}
        self.state = state

    @property
    def current(self) -> dict:
        return self.missions[self.state.current_mission]

    def objective_text(self) -> str:
        mission = self.current
        objectives = []
        for obj in mission.get("objectives", []):
            mark = "x" if obj.get("flag") in self.state.flags else " "
            objectives.append(f"[{mark}] {obj['text']}")
        return f"{mission['title']}\n" + "\n".join(objectives)

    def update(self) -> None:
        while True:
            mission = self.current
            completion_flags = set(mission.get("completion_flags", []))
            required = set(mission.get("required_flags", []))
            if required.issubset(self.state.flags) and completion_flags.issubset(self.state.flags):
                next_mission = mission.get("next_mission")
                if next_mission:
                    self.state.current_mission = next_mission
                    self.state.flags.add(f"mission_started:{next_mission}")
                    continue
            break

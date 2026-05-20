from __future__ import annotations

import json
from pathlib import Path

from game.state import GameState


class SaveLoadManager:
    def __init__(self, path: Path) -> None:
        self.path = path

    def save(self, state: GameState, player_pos: tuple[float, float, float]) -> None:
        payload = state.to_json()
        payload["player_pos"] = list(player_pos)
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def load(self) -> tuple[GameState, tuple[float, float, float]] | None:
        if not self.path.exists():
            return None
        data = json.loads(self.path.read_text(encoding="utf-8"))
        pos = tuple(data.pop("player_pos", [0, 0, 1.8]))
        return GameState.from_json(data), pos  # type: ignore[return-value]

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class GameState:
    ripple: int = 0
    suspicion: int = 0
    elapsed_time: float = 0.0
    current_mission: str = "arrival_at_ghat"
    flags: set[str] = field(default_factory=set)
    clues: set[str] = field(default_factory=set)
    unlocked_locations: set[str] = field(default_factory=lambda: {"river_ghat", "bazaar", "scholars_house", "printing_press"})
    inventory: list[str] = field(default_factory=lambda: ["Chrono Remote", "Historical Dossier", "Translation Lens"])
    trust: dict[str, int] = field(default_factory=dict)
    journal: dict[str, list[str]] = field(default_factory=lambda: {
        "Political": [],
        "Economic": [],
        "Social": [],
        "Technological": [],
        "Environmental": [],
        "Legal": [],
    })
    game_over: bool = False
    ending_id: str | None = None

    def add_ripple(self, amount: int) -> None:
        self.ripple = max(0, min(100, self.ripple + amount))

    def add_suspicion(self, amount: int) -> None:
        self.suspicion = max(0, min(100, self.suspicion + amount))

    def add_trust(self, npc_id: str, amount: int) -> None:
        self.trust[npc_id] = max(-100, min(100, self.trust.get(npc_id, 0) + amount))

    def add_item(self, item: str) -> None:
        if item and item not in self.inventory:
            self.inventory.append(item)

    def remove_item(self, item: str) -> None:
        if item in self.inventory:
            self.inventory.remove(item)

    def add_journal_note(self, category: str, note: str) -> None:
        notes = self.journal.setdefault(category, [])
        if note and note not in notes:
            notes.append(note)

    def to_json(self) -> dict[str, Any]:
        data = asdict(self)
        data["flags"] = sorted(self.flags)
        data["clues"] = sorted(self.clues)
        data["unlocked_locations"] = sorted(self.unlocked_locations)
        return data

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "GameState":
        state = cls()
        for key, value in data.items():
            if key in {"flags", "clues", "unlocked_locations"}:
                setattr(state, key, set(value))
            elif hasattr(state, key):
                setattr(state, key, value)
        return state

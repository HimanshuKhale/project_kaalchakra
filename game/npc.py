from __future__ import annotations

from dataclasses import dataclass
from panda3d.core import NodePath


@dataclass
class NPC:
    id: str
    name: str
    role: str
    location: str
    personality: str
    greeting: str
    trust_score: int
    suspicion_score: int
    node: NodePath | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "NPC":
        return cls(
            id=data["id"],
            name=data["name"],
            role=data["role"],
            location=data["location"],
            personality=data.get("personality", ""),
            greeting=data.get("greeting", ""),
            trust_score=data.get("trust_score", 0),
            suspicion_score=data.get("suspicion_score", 0),
        )

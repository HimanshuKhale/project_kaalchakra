from __future__ import annotations

from typing import Protocol


class DialogueProvider(Protocol):
    def get_reply(self, npc_id: str, player_text: str, context: dict) -> str:
        ...


class RuleBasedDialogueProvider:
    """Current MVP provider. Replace this class with an API-backed adapter later."""

    def get_reply(self, npc_id: str, player_text: str, context: dict) -> str:
        return context.get("fallback_reply", "The conversation shifts back to the mission.")

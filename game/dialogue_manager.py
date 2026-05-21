from __future__ import annotations

import json
from pathlib import Path

from game.llm_adapter import RuleBasedDialogueProvider
from game.npc import NPC
from game.state import GameState


class DialogueManager:
    def __init__(self, path: Path, state: GameState) -> None:
        self.dialogues = json.loads(path.read_text(encoding="utf-8"))
        self.state = state
        self.provider = RuleBasedDialogueProvider()

    def get_dialogue(self, npc: NPC) -> dict:
        return self.dialogues.get(npc.id, {"text": npc.greeting, "options": []})

    def choose(self, npc: NPC, option_index: int) -> str:
        dialogue = self.get_dialogue(npc)
        options = dialogue.get("options", [])
        if option_index >= len(options):
            return "No response."
        option = options[option_index]
        effects = option.get("effects", {})
        self.state.add_trust(npc.id, effects.get("trust", 0))
        self.state.add_suspicion(effects.get("suspicion", 0))
        self.state.add_ripple(effects.get("ripple", 0))
        for clue in effects.get("unlock_clues", []):
            self.state.clues.add(clue)
        for flag in effects.get("set_flags", []):
            self.state.flags.add(flag)
        for item in effects.get("add_items", []):
            self.state.add_item(item)
        for loc in effects.get("unlock_locations", []):
            self.state.unlocked_locations.add(loc)
        for note in effects.get("pestel_notes", []):
            self.state.add_journal_note(note["category"], note["text"])
        if effects.get("enemy_suspicion"):
            self.state.add_suspicion(effects["enemy_suspicion"])
        return option.get("reply", self.provider.get_reply(npc.id, option["text"], {"fallback_reply": npc.greeting}))

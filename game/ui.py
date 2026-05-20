from __future__ import annotations

from direct.gui.DirectGui import DirectButton, DirectFrame, DirectLabel
from panda3d.core import TextNode


class GameUI:
    def __init__(self, app) -> None:
        self.app = app
        self.hud = DirectLabel(text="", pos=(-1.28, 0, 0.9), scale=0.045, frameColor=(0, 0, 0, 0), text_align=TextNode.ALeft, text_fg=(1, 1, 1, 1))
        self.objective = DirectLabel(text="", pos=(-1.28, 0, 0.74), scale=0.042, frameColor=(0, 0, 0, 0.35), text_align=TextNode.ALeft, text_fg=(0.95, 0.9, 0.72, 1))
        self.prompt = DirectLabel(text="", pos=(0, 0, -0.72), scale=0.052, frameColor=(0, 0, 0, 0.45), text_fg=(1, 1, 1, 1))
        self.dialogue_frame = None
        self.panel = None
        self.ending = None

    def update_hud(self, state, objective_text: str, prompt: str = "") -> None:
        self.hud["text"] = f"Ripple: {state.ripple:03d}   Suspicion: {state.suspicion:03d}"
        self.objective["text"] = objective_text
        self.prompt["text"] = prompt

    def show_dialogue(self, npc, dialogue: dict, choose_callback) -> None:
        self.close_dialogue()
        self.dialogue_frame = DirectFrame(frameColor=(0.03, 0.025, 0.02, 0.9), frameSize=(-1.05, 1.05, -0.58, 0.58), pos=(0, 0, -0.08))
        DirectLabel(parent=self.dialogue_frame, text=f"{npc.name} - {npc.role}", pos=(-0.98, 0, 0.46), scale=0.052, frameColor=(0, 0, 0, 0), text_align=TextNode.ALeft, text_fg=(1, 0.86, 0.55, 1))
        DirectLabel(parent=self.dialogue_frame, text=dialogue.get("text", npc.greeting), pos=(-0.98, 0, 0.3), scale=0.04, frameColor=(0, 0, 0, 0), text_align=TextNode.ALeft, text_fg=(1, 1, 1, 1), text_wordwrap=46)
        for i, option in enumerate(dialogue.get("options", [])[:4]):
            DirectButton(parent=self.dialogue_frame, text=f"{i + 1}. {option['text']}", command=choose_callback, extraArgs=[i], pos=(-0.02, 0, 0.08 - i * 0.15), scale=0.04, frameColor=(0.16, 0.12, 0.08, 1), text_fg=(1, 1, 1, 1), text_align=TextNode.ALeft, frameSize=(-23, 23, -1.2, 1.2))

    def close_dialogue(self) -> None:
        if self.dialogue_frame:
            self.dialogue_frame.destroy()
            self.dialogue_frame = None

    def toggle_panel(self, state, mission_text: str) -> None:
        if self.panel:
            self.panel.destroy()
            self.panel = None
            return
        self.panel = DirectFrame(frameColor=(0.02, 0.025, 0.03, 0.88), frameSize=(-1.12, 1.12, -0.76, 0.76), pos=(0, 0, 0))
        text = (
            f"OBJECTIVES\n{mission_text}\n\n"
            f"INVENTORY\n" + "\n".join(f"- {i}" for i in state.inventory) + "\n\n"
            f"CLUES\n" + ("\n".join(f"- {c}" for c in sorted(state.clues)) or "- None")
        )
        DirectLabel(parent=self.panel, text=text, pos=(-1.04, 0, 0.65), scale=0.043, frameColor=(0, 0, 0, 0), text_align=TextNode.ALeft, text_fg=(1, 1, 1, 1), text_wordwrap=48)

    def show_message(self, text: str) -> None:
        self.prompt["text"] = text

    def show_ending(self, text: str) -> None:
        if self.ending:
            self.ending.destroy()
        self.ending = DirectFrame(frameColor=(0, 0, 0, 0.94), frameSize=(-1.25, 1.25, -0.86, 0.86), pos=(0, 0, 0))
        DirectLabel(parent=self.ending, text=text, pos=(-1.12, 0, 0.65), scale=0.047, frameColor=(0, 0, 0, 0), text_align=TextNode.ALeft, text_fg=(1, 0.94, 0.78, 1), text_wordwrap=48)
        DirectLabel(parent=self.ending, text="Press Esc to quit", pos=(0, 0, -0.75), scale=0.045, frameColor=(0, 0, 0, 0), text_fg=(1, 1, 1, 1))

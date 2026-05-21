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
        self.pause_menu = None
        self.journal = None
        self.debug = None
        self.banner_timer = 0.0
        self.banner = DirectLabel(text="", pos=(0, 0, 0.58), scale=0.064, frameColor=(0.05, 0.04, 0.03, 0.8), text_fg=(1, 0.85, 0.45, 1))
        self.banner.hide()
        self.warning = DirectLabel(text="", pos=(0, 0, 0.78), scale=0.048, frameColor=(0.35, 0.02, 0.02, 0.72), text_fg=(1, 0.88, 0.82, 1))
        self.warning.hide()
        self.radar = DirectFrame(frameColor=(0.02, 0.025, 0.03, 0.62), frameSize=(-0.22, 0.22, -0.22, 0.22), pos=(1.05, 0, 0.71))
        DirectLabel(parent=self.radar, text="N", pos=(0, 0, 0.17), scale=0.03, frameColor=(0, 0, 0, 0), text_fg=(0.7, 0.9, 1, 1))
        self.radar_player = DirectLabel(parent=self.radar, text="P", pos=(0, 0, 0), scale=0.035, frameColor=(0, 0, 0, 0), text_fg=(0.4, 1, 0.5, 1))
        self.radar_target = DirectLabel(parent=self.radar, text="*", pos=(0, 0, 0), scale=0.045, frameColor=(0, 0, 0, 0), text_fg=(1, 0.88, 0.25, 1))
        self.radar_officer = DirectLabel(parent=self.radar, text="H", pos=(0, 0, 0), scale=0.035, frameColor=(0, 0, 0, 0), text_fg=(1, 0.25, 0.2, 1))

    def update_hud(self, state, objective_text: str, prompt: str = "", dt: float = 0.0) -> None:
        self.hud["text"] = f"Ripple: {state.ripple:03d}   Suspicion: {state.suspicion:03d}"
        self.objective["text"] = objective_text
        self.prompt["text"] = prompt
        if self.banner_timer > 0:
            self.banner_timer -= dt
            if self.banner_timer <= 0:
                self.banner.hide()

    def show_mission_banner(self, title: str) -> None:
        self.banner["text"] = f"MISSION UPDATED\n{title}"
        self.banner_timer = 3.2
        self.banner.show()

    def show_warning(self, text: str, visible: bool) -> None:
        self.warning["text"] = text
        if visible:
            self.warning.show()
        else:
            self.warning.hide()

    def update_radar(self, player_pos, officer_pos, target_pos) -> None:
        scale = 0.006
        self.radar_player.set_pos(0, 0, 0)
        self.radar_officer.set_pos(
            max(-0.18, min(0.18, (officer_pos.x - player_pos.x) * scale)),
            0,
            max(-0.18, min(0.18, (officer_pos.y - player_pos.y) * scale)),
        )
        if target_pos:
            self.radar_target.show()
            self.radar_target.set_pos(
                max(-0.18, min(0.18, (target_pos.x - player_pos.x) * scale)),
                0,
                max(-0.18, min(0.18, (target_pos.y - player_pos.y) * scale)),
            )
        else:
            self.radar_target.hide()

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

    def toggle_journal(self, state) -> None:
        if self.journal:
            self.journal.destroy()
            self.journal = None
            return
        self.journal = DirectFrame(frameColor=(0.03, 0.025, 0.02, 0.9), frameSize=(-1.15, 1.15, -0.78, 0.78), pos=(0, 0, 0))
        sections = []
        for category, notes in state.journal.items():
            body = "\n".join(f"- {note}" for note in notes) if notes else "- No notes discovered"
            sections.append(f"{category}\n{body}")
        DirectLabel(parent=self.journal, text="PESTEL JOURNAL\n\n" + "\n\n".join(sections), pos=(-1.06, 0, 0.68), scale=0.036, frameColor=(0, 0, 0, 0), text_align=TextNode.ALeft, text_fg=(1, 0.96, 0.84, 1), text_wordwrap=58)

    def toggle_debug(self, text: str) -> None:
        if self.debug:
            self.debug.destroy()
            self.debug = None
            return
        self.debug = DirectFrame(frameColor=(0, 0, 0, 0.82), frameSize=(-1.22, 1.22, -0.8, 0.8), pos=(0, 0, 0))
        DirectLabel(parent=self.debug, text=text, pos=(-1.12, 0, 0.68), scale=0.035, frameColor=(0, 0, 0, 0), text_align=TextNode.ALeft, text_fg=(0.85, 1, 0.85, 1), text_wordwrap=62)

    def toggle_pause_menu(self, resume_cb, save_cb, load_cb, quit_cb) -> None:
        if self.pause_menu:
            self.pause_menu.destroy()
            self.pause_menu = None
            return
        self.pause_menu = DirectFrame(frameColor=(0.02, 0.02, 0.025, 0.92), frameSize=(-0.45, 0.45, -0.48, 0.48), pos=(0, 0, 0))
        DirectLabel(parent=self.pause_menu, text="PAUSED", pos=(0, 0, 0.32), scale=0.07, frameColor=(0, 0, 0, 0), text_fg=(1, 0.9, 0.6, 1))
        buttons = [("Resume", resume_cb), ("Save", save_cb), ("Load", load_cb), ("Quit", quit_cb)]
        for i, (label, callback) in enumerate(buttons):
            DirectButton(parent=self.pause_menu, text=label, command=callback, pos=(0, 0, 0.12 - i * 0.16), scale=0.052, frameColor=(0.16, 0.12, 0.08, 1), text_fg=(1, 1, 1, 1), frameSize=(-5.8, 5.8, -0.75, 0.75))

    def show_message(self, text: str) -> None:
        self.prompt["text"] = text

    def show_ending(self, text: str) -> None:
        if self.ending:
            self.ending.destroy()
        self.ending = DirectFrame(frameColor=(0, 0, 0, 0.94), frameSize=(-1.25, 1.25, -0.86, 0.86), pos=(0, 0, 0))
        DirectLabel(parent=self.ending, text=text, pos=(-1.12, 0, 0.65), scale=0.047, frameColor=(0, 0, 0, 0), text_align=TextNode.ALeft, text_fg=(1, 0.94, 0.78, 1), text_wordwrap=48)
        DirectLabel(parent=self.ending, text="Press Esc to quit", pos=(0, 0, -0.75), scale=0.045, frameColor=(0, 0, 0, 0), text_fg=(1, 1, 1, 1))

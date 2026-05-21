from __future__ import annotations

from direct.showbase.ShowBase import ShowBase
from panda3d.core import ClockObject, Vec3, load_prc_file_data

import config
from game.camera import CameraRig
from game.dialogue_manager import DialogueManager
from game.ending_manager import EndingManager
from game.enemy_ai import BritishOfficerAI
from game.input_handler import InputHandler
from game.inventory import Inventory
from game.mission_manager import MissionManager
from game.player import FirstPersonPlayer
from game.save_load import SaveLoadManager
from game.state import GameState
from game.ui import GameUI
from game.world import World

load_prc_file_data("", f"window-title {config.WINDOW_TITLE}")
load_prc_file_data("", f"win-size {config.WINDOW_SIZE[0]} {config.WINDOW_SIZE[1]}")
load_prc_file_data("", "show-frame-rate-meter true")


class KaalchakraApp(ShowBase):
    def __init__(self) -> None:
        super().__init__()
        self.state = GameState()
        self.save_load = SaveLoadManager(config.SAVE_PATH)
        self.paused = False
        self.in_dialogue = False
        self.sprint_noise_timer = 0.0
        self.suspicion_decay_timer = 0.0

        CameraRig(self)
        self.input = InputHandler(self)
        self.player = FirstPersonPlayer(self, self.input)
        self.inventory = Inventory(self.state)
        self.world = World(self, config.DATA_DIR / "locations.json", config.DATA_DIR / "npcs.json")
        self.missions = MissionManager(config.DATA_DIR / "missions.json", self.state)
        self.dialogue = DialogueManager(config.DATA_DIR / "dialogues.json", self.state)
        self.endings = EndingManager(config.DATA_DIR / "endings.json")
        self.ui = GameUI(self)
        self.current_npc = None
        self.detected_recently = False
        self.ui.show_mission_banner(self.missions.current["title"])

        self.officer_ai = BritishOfficerAI(
            self.world.officer_node,
            [(17, 14, 1), (39, 14, 1), (39, 33, 1), (17, 33, 1)],
            self.state,
        )

        self._bind_controls()
        self.taskMgr.add(self.update, "game_update")

    def _bind_controls(self) -> None:
        self.accept("e", self.interact)
        self.accept("tab", self.toggle_panel)
        self.accept("j", self.toggle_journal)
        self.accept("f3", self.toggle_debug)
        self.accept("escape", self.pause_or_quit)
        self.accept("f5", self.save_game)
        self.accept("f9", self.load_game)
        for key in ["1", "2", "3", "4"]:
            self.accept(key, self.choose_dialogue, [int(key) - 1])

    def update(self, task) -> int:
        dt = min(ClockObject.get_global_clock().get_dt(), 0.05)
        if not self.state.game_over and not self.paused:
            self.state.elapsed_time += dt
            self.player.update(dt, paused=self.in_dialogue, can_move_to=lambda pos: not self.world.is_blocked(pos))
            self.detected_recently = self.officer_ai.update(
                dt,
                self.player.node.get_pos(),
                self.input.keys["crouch"],
                line_of_sight_clear=self.world.has_line_of_sight,
            )
            self._ambient_rules(dt)
            self._objective_triggers()
            if self.missions.update():
                self.ui.show_mission_banner(self.missions.current["title"])
            self._check_ending()

        prompt = ""
        self.current_npc = self.world.nearest_npc(self.player.node.get_pos(), config.INTERACTION_DISTANCE, self.state)
        if self.current_npc and not self.in_dialogue:
            prompt = f"Press E to speak with {self.current_npc.name}"
        if self.detected_recently:
            prompt = "Captain Haines has spotted you. Break line of sight or crouch."
        self.ui.show_warning("WANTED: Captain Haines has line of sight", self.detected_recently)
        self.ui.update_radar(self.player.node.get_pos(), self.world.officer_node.get_pos(), self._mission_target_pos())
        if not self.state.game_over:
            self.ui.update_hud(self.state, self.missions.objective_text(), prompt, dt)
        return task.cont

    def _ambient_rules(self, dt: float) -> None:
        self.sprint_noise_timer = max(0.0, self.sprint_noise_timer - dt)
        if self.input.keys["sprint"] and self.world.location_of_player(self.player.node.get_pos()).startswith("Palace"):
            if self.sprint_noise_timer <= 0:
                self.state.add_suspicion(4)
                self.sprint_noise_timer = 1.0
        self.suspicion_decay_timer = max(0.0, self.suspicion_decay_timer - dt)
        officer_distance = (self.world.officer_node.get_pos() - self.player.node.get_pos()).length()
        if not self.detected_recently and officer_distance > 18 and self.state.suspicion > 0 and self.suspicion_decay_timer <= 0:
            self.state.add_suspicion(-1)
            self.suspicion_decay_timer = 3.0
        if self.state.ripple >= config.RIPPLE_COLLAPSE:
            self.state.game_over = True
            self.state.ending_id = "chaotic_timeline" if "Shakti Crystal" in self.state.inventory else "failed_mission"
        if self.state.suspicion >= config.SUSPICION_CAPTURE:
            self.state.game_over = True
            self.state.ending_id = "colonial_capture"

    def _objective_triggers(self) -> None:
        pos = self.player.node.get_pos()
        location = self.world.location_of_player(pos)
        if location == "River Ghat":
            self.state.flags.add("entered_river_ghat")
        if location == "Bazaar":
            self.state.flags.add("entered_bazaar")
        if location == "Palace Outer Court" and "Palace Pass" in self.state.inventory:
            self.state.flags.add("entered_palace_outer")
        if location == "Palace Inner Wing" and "first_meeting_failed" in self.state.flags:
            self.state.flags.add("returned_to_inner_wing")
        treasury_dist = (Vec3(39, 30, 1) - pos).length()
        if treasury_dist < 4 and "nawab_granted_crystal" in self.state.flags:
            self.state.add_item("Shakti Crystal")
            self.state.flags.add("crystal_acquired")
            self.ui.show_message("The Shakti Crystal hums inside your satchel.")
        if location == "River Ghat" and "Shakti Crystal" in self.state.inventory:
            self.state.flags.add("returned_to_present")

    def interact(self) -> None:
        if self.state.game_over or self.paused:
            return
        if self.in_dialogue:
            self.ui.close_dialogue()
            self.in_dialogue = False
            self.player.capture_mouse()
            return
        if self.current_npc:
            self.in_dialogue = True
            self.player.release_mouse()
            self.ui.show_dialogue(self.current_npc, self.dialogue.get_dialogue(self.current_npc), self.choose_dialogue)

    def choose_dialogue(self, index: int) -> None:
        if not self.in_dialogue or not self.current_npc:
            return
        reply = self.dialogue.choose(self.current_npc, index)
        self._story_gate_rewards(self.current_npc.id)
        if self.missions.update():
            self.ui.show_mission_banner(self.missions.current["title"])
        self.ui.close_dialogue()
        self.in_dialogue = False
        self.player.capture_mouse()
        self.ui.show_message(reply)

    def _story_gate_rewards(self, npc_id: str) -> None:
        trust = self.state.trust.get(npc_id, 0)
        if npc_id == "scholar" and trust >= 20:
            self.state.add_item("Scholar Recommendation")
            self.state.flags.add("scholar_recommended_agent")
        if npc_id == "printer" and "scholar_recommended_agent" in self.state.flags:
            self.state.add_item("Printed Invitation")
            self.state.flags.add("printed_invitation_ready")
        if npc_id == "minister" and "Printed Invitation" in self.state.inventory:
            self.state.add_item("Palace Pass")
            self.state.flags.add("palace_access_granted")
            self.state.unlocked_locations.update({"palace_outer", "palace_inner"})
        if npc_id == "nawab" and "first_meeting_failed" not in self.state.flags:
            self.state.flags.add("first_meeting_failed")
            self.state.add_suspicion(10)
            self.state.unlocked_locations.add("alley_escape")
        elif npc_id == "nawab" and self.state.trust.get("sage", 0) >= 25 and self.state.trust.get("nawab", 0) >= 45:
            self.state.flags.add("nawab_granted_crystal")
        if npc_id == "sage" and trust >= 25:
            self.state.flags.add("kaal_rishi_reputation")

    def _mission_target_pos(self):
        if self.state.current_mission == "get_palace_access" and "Printed Invitation" not in self.state.inventory:
            printer = self.world.npc_by_id["printer"].node
            return printer.get_pos() if printer else None
        target_by_mission = {
            "arrival_at_ghat": "boatman",
            "gather_bazaar_clues": "printer",
            "speak_to_scholar": "scholar",
            "get_palace_access": "minister",
            "avoid_british_officer": "minister",
            "first_nawab_meeting": "nawab",
            "escape_palace": "sage",
            "meet_sage": "sage",
            "build_kaal_rishi_reputation": "nawab",
            "final_nawab_negotiation": "nawab",
        }
        npc_id = target_by_mission.get(self.state.current_mission)
        if npc_id and self.world.npc_by_id[npc_id].node:
            return self.world.npc_by_id[npc_id].node.get_pos()
        if self.state.current_mission == "return_to_present":
            return Vec3(*self.world.locations["river_ghat"]["pos"])
        return None

    def toggle_panel(self) -> None:
        if self.state.game_over:
            return
        self.ui.toggle_panel(self.state, self.missions.objective_text())

    def toggle_journal(self) -> None:
        if self.state.game_over:
            return
        self.ui.toggle_journal(self.state)

    def toggle_debug(self) -> None:
        location = self.world.location_of_player(self.player.node.get_pos())
        text = (
            f"Mission: {self.state.current_mission}\n"
            f"Location: {location}\n"
            f"Ripple: {self.state.ripple}\n"
            f"Suspicion: {self.state.suspicion}\n\n"
            f"Inventory: {', '.join(self.state.inventory)}\n\n"
            f"Flags:\n" + "\n".join(sorted(self.state.flags))
        )
        self.ui.toggle_debug(text)

    def pause_or_quit(self) -> None:
        if self.state.game_over:
            self.userExit()
            return
        self.paused = not self.paused
        if self.paused:
            self.player.release_mouse()
            self.ui.show_message("Paused.")
            self.ui.toggle_pause_menu(self.resume_game, self.save_game, self.load_game, self.userExit)
        else:
            self.resume_game()

    def resume_game(self) -> None:
        self.paused = False
        if self.ui.pause_menu:
            self.ui.toggle_pause_menu(self.resume_game, self.save_game, self.load_game, self.userExit)
        self.player.capture_mouse()

    def save_game(self) -> None:
        self.save_load.save(self.state, tuple(self.player.node.get_pos()))
        self.ui.show_message("Game saved.")

    def load_game(self) -> None:
        loaded = self.save_load.load()
        if not loaded:
            self.ui.show_message("No save file found.")
            return
        self.state, pos = loaded
        self.inventory.state = self.state
        self.missions.state = self.state
        self.dialogue.state = self.state
        self.officer_ai.state = self.state
        self.player.node.set_pos(*pos)
        self.ui.show_mission_banner(self.missions.current["title"])
        self.ui.show_message("Game loaded.")

    def _check_ending(self) -> None:
        ending_id = self.state.ending_id or self.endings.evaluate(self.state)
        if not ending_id:
            return
        self.state.game_over = True
        self.state.ending_id = ending_id
        self.player.release_mouse()
        self.ui.show_ending(self.endings.build_summary(ending_id, self.state))

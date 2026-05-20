from __future__ import annotations

import json
from pathlib import Path

from game.state import GameState


class EndingManager:
    def __init__(self, path: Path) -> None:
        self.endings = {e["id"]: e for e in json.loads(path.read_text(encoding="utf-8"))}

    def evaluate(self, state: GameState) -> str | None:
        if state.suspicion >= 100:
            return "colonial_capture"
        if "Shakti Crystal" in state.inventory and "returned_to_present" in state.flags:
            if state.ripple < 35 and state.suspicion < 50:
                return "silent_success"
            if 35 <= state.ripple <= 65 and state.trust.get("nawab", 0) >= 45:
                return "golden_ripple"
            if state.ripple > 65:
                return "chaotic_timeline"
            return "golden_ripple"
        if state.elapsed_time >= 1800:
            return "failed_mission"
        return None

    def build_summary(self, ending_id: str, state: GameState) -> str:
        ending = self.endings[ending_id]
        trust = ", ".join(f"{k}: {v}" for k, v in sorted(state.trust.items())) or "No bonds formed"
        consequences = self._consequences(ending_id, state)
        return (
            f"{ending['title']}\n\n"
            f"{ending['result']}\n\n"
            f"Ripple Score: {state.ripple}\n"
            f"Suspicion Score: {state.suspicion}\n"
            f"Trust Summary: {trust}\n\n"
            f"{consequences}"
        )

    def _consequences(self, ending_id: str, state: GameState) -> str:
        if ending_id == "silent_success":
            return "Present-day consequence: KAALCHAKRA records a clean extraction. Bengal's timeline remains almost untouched."
        if ending_id == "golden_ripple":
            return "Present-day consequence: Small legends of a Kaal Rishi survive, subtly strengthening cultural memory without rupturing history."
        if ending_id == "chaotic_timeline":
            return "Present-day consequence: The crystal returns, but altered archives and contradictory memories hint at a wounded chronology."
        if ending_id == "colonial_capture":
            return "Present-day consequence: Colonial records mention an impossible device. DRDO loses contact with the agent."
        return "Present-day consequence: The mission window closes. The Shakti Crystal remains locked in 1905."

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def load_json(name: str):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def test_all_json_files_load() -> None:
    for path in DATA.glob("*.json"):
        assert json.loads(path.read_text(encoding="utf-8"))


def test_required_npc_ids_exist() -> None:
    npcs = load_json("npcs.json")
    npc_ids = {npc["id"] for npc in npcs}
    assert {
        "scholar",
        "printer",
        "boatman",
        "minister",
        "nawab",
        "british_officer",
        "sage",
    }.issubset(npc_ids)


def test_mission_ids_and_next_references_are_valid() -> None:
    missions = load_json("missions.json")
    mission_ids = {mission["id"] for mission in missions}
    assert "arrival_at_ghat" in mission_ids
    assert "return_to_present" in mission_ids

    for mission in missions:
        next_mission = mission.get("next_mission")
        if next_mission is not None:
            assert next_mission in mission_ids


def test_dialogues_reference_valid_npcs() -> None:
    npc_ids = {npc["id"] for npc in load_json("npcs.json")}
    dialogue_ids = set(load_json("dialogues.json"))
    assert dialogue_ids.issubset(npc_ids)


def test_npc_locations_are_valid() -> None:
    location_ids = {location["id"] for location in load_json("locations.json")}
    for npc in load_json("npcs.json"):
        assert npc["location"] in location_ids


def test_dialogue_pestel_notes_have_valid_categories() -> None:
    valid_categories = {"Political", "Economic", "Social", "Technological", "Environmental", "Legal"}
    dialogues = load_json("dialogues.json")
    for dialogue in dialogues.values():
        for option in dialogue.get("options", []):
            for note in option.get("effects", {}).get("pestel_notes", []):
                assert note["category"] in valid_categories
                assert note["text"]

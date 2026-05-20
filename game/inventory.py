from game.state import GameState


class Inventory:
    def __init__(self, state: GameState) -> None:
        self.state = state

    def has(self, item: str) -> bool:
        return item in self.state.inventory

    def add(self, item: str) -> None:
        self.state.add_item(item)

    def summary(self) -> str:
        return "\n".join(f"- {item}" for item in self.state.inventory)

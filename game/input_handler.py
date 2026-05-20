class InputHandler:
    def __init__(self, app) -> None:
        self.app = app
        self.keys = {
            "forward": False,
            "backward": False,
            "left": False,
            "right": False,
            "sprint": False,
            "crouch": False,
        }

        bindings = {
            "w": ("forward", True), "w-up": ("forward", False),
            "s": ("backward", True), "s-up": ("backward", False),
            "a": ("left", True), "a-up": ("left", False),
            "d": ("right", True), "d-up": ("right", False),
            "shift": ("sprint", True), "shift-up": ("sprint", False),
            "control": ("crouch", True), "control-up": ("crouch", False),
        }
        for event, (key, value) in bindings.items():
            app.accept(event, self.set_key, [key, value])

    def set_key(self, key: str, value: bool) -> None:
        self.keys[key] = value

class CameraRig:
    def __init__(self, app) -> None:
        self.app = app
        app.disable_mouse()
        app.camLens.set_fov(85)
        app.camLens.set_near_far(0.1, 350)

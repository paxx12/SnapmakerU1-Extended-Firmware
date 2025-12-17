from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from confighelper import ConfigHelper

class Timelapse:

    def __init__(self, confighelper: ConfigHelper) -> None:
        self.confighelper = confighelper
        self.server = confighelper.get_server()

        # setup eventhandlers and endpoints
        file_manager = self.server.lookup_component("file_manager")
        camera_path = file_manager.datapath.joinpath("camera")
        file_manager.register_directory("timelapse",
                                        str(camera_path),
                                        full_access=True
                                        )

def load_component(config: ConfigHelper) -> Timelapse:
    return Timelapse(config)

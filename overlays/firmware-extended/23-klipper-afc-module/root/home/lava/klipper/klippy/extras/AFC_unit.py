class AFCUnit:
    def __init__(self, config):
        # Prevent klipper error
        config.get("enabled", True)

        self.printer = config.get_printer()
        self.fullname = config.get_name()
        self.name = self.fullname.split()[-1]

        self.lanes = {}
        self.printer.register_event_handler("klippy:connect", self._handle_connect)

    def _handle_connect(self):
        for name, obj in self.printer.lookup_objects("AFC_lane"):
            if hasattr(obj, 'unit') and obj.unit == self.name:
                lane_name = name.split()[-1] if " " in name else name.replace("AFC_lane_", "", 1)
                self.lanes[lane_name] = obj

    def get_status(self, eventtime=None):
        response = {}
        response['lanes'] = [lane.name for lane in self.lanes.values()]
        response["extruders"] = []
        response["hubs"] = []
        response["buffers"] = []
        return response

def load_config_prefix(config):
    return AFCUnit(config)

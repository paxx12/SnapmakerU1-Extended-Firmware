class AFCLaneState:
    EMPTY = "empty"
    LOADING = "loading"
    LOADED = "loaded"
    UNLOADING = "unloading"
    TOOL_LOADED = "tool_loaded"
    ERROR = "error"

class AFCState:
    IDLE = "idle"
    LOADING = "loading"
    UNLOADING = "unloading"
    TOOL_CHANGE = "tool_change"
    ERROR = "error"

class AFC:
    def __init__(self, config):
        self.printer = config.get_printer()
        config.get("enabled", "True")
        self.gcode = self.printer.lookup_object("gcode")
        self.reactor = self.printer.get_reactor()

        self.current_state = AFCState.IDLE
        self.current = None
        self.current_loading = None
        self.next_lane_load = None
        self.error_state = False
        self.bypass_state = False
        self.quiet_mode = False
        self.current_toolchange = 0
        self.number_of_toolchanges = 0
        self.spoolman = True
        self.td1_present = False
        self.lane_data_enabled = False
        self.position_saved = False
        self.message = ""
        self.led_state = ""

        self.units = {}
        self.lanes = {}

        self.printer.register_event_handler("klippy:connect", self._handle_connect)

    def _handle_connect(self):
        for name, obj in self.printer.lookup_objects("AFC_unit"):
            unit_name = name.replace("AFC_", "", 1)
            self.units[unit_name] = obj

        for name, obj in self.printer.lookup_objects("AFC_lane"):
            lane_name = name.split(None, 1)[1] if " " in name else name
            self.lanes[lane_name] = obj

    def _get_current_lane(self):
        try:
            toolhead = self.printer.lookup_object('toolhead')
            current_extruder = toolhead.extruder.name
            for lane_name, lane in self.lanes.items():
                if lane.extruder == current_extruder:
                    return lane_name
        except:
            pass
        return None

    def get_status(self, eventtime=None):
        str = {}
        str['current_load'] = self.current
        str['current_lane'] = self._get_current_lane()
        str['next_lane'] = self.next_lane_load
        str['current_state'] = self.current_state
        str["current_toolchange"] = self.current_toolchange if self.current_toolchange >= 0 else 0
        str["number_of_toolchanges"] = self.number_of_toolchanges
        str['spoolman'] = self.spoolman
        str["td1_present"] = self.td1_present
        str["lane_data_enabled"] = self.lane_data_enabled
        str['error_state'] = self.error_state
        str["bypass_state"] = bool(self.bypass_state)
        str["quiet_mode"] = bool(self.quiet_mode)
        str["position_saved"] = self.position_saved

        str['units'] = list(self.units.keys())
        str['lanes'] = list(self.lanes.keys())
        str["extruders"] = []
        str["hubs"] = []
        str["buffers"] = []
        str["message"] = self.message
        str["led_state"] = self.led_state
        return str

def load_config(config):
    return AFC(config)

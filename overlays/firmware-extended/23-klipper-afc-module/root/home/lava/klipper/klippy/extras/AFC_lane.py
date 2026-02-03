class AFCLaneState:
    EMPTY = "empty"
    LOADING = "loading"
    LOADED = "loaded"
    UNLOADING = "unloading"
    TOOL_LOADED = "tool_loaded"
    ERROR = "error"

class AFCLane:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.gcode = self.printer.lookup_object('gcode')
        self.name = config.get_name().replace("AFC_lane ", "", 1)

        self.unit = config.get("unit", "")
        self.channel = config.getint("channel", 0)
        self.extruder = config.get("extruder", None)
        self.toolhead_sensor = config.get("toolhead_sensor", None)

        self.status = AFCLaneState.EMPTY
        self.tool_loaded = False

        self.connect_done = False
        self.print_task_config = None
        self.sensor = None

        self.weight = -1 # -1 means weight is not supported/configured
        self.filament_density = 1.24
        self.filament_diameter = 1.75
        self.empty_spool_weight = 0

        self.printer.register_event_handler("klippy:connect", self._handle_connect)

    def _handle_connect(self):
        self.connect_done = True
        try:
            self.print_task_config = self.printer.lookup_object("print_task_config")
        except:
            self.print_task_config = None

        # Lookup toolhead sensor if configured
        if self.toolhead_sensor:
            try:
                self.sensor = self.printer.lookup_object(self.toolhead_sensor)
            except:
                self.sensor = None

    def _get_filament_info(self):
        """Get filament info from print_task_config based on channel index"""
        if not self.print_task_config:
            return {}

        try:
            status = self.print_task_config.get_status()
            filament_exist = status.get('filament_exist', [False])[self.channel] if self.channel < len(status.get('filament_exist', [])) else False

            # Return empty dict if no filament exists
            if not filament_exist:
                return {}

            config = {
                'map': f"T{self.channel}",
                'material': 'NONE',
                'color': 'FFFFFFFF',
                'vendor': 'NONE',
                'sub_type': 'NONE',
                'runout_lane': '?',
                'spool_id': None,
                'filament_exist': True
            }

            config['material'] = dict(enumerate(status.get('filament_type', []))).get(self.channel, 'NONE')
            config['color'] = dict(enumerate(status.get('filament_color_rgba', []))).get(self.channel, 'FFFFFFFF')
            config['vendor'] = dict(enumerate(status.get('filament_vendor', []))).get(self.channel, 'NONE')
            config['sub_type'] = dict(enumerate(status.get('filament_sub_type', []))).get(self.channel, 'NONE')
            config['spool_id'] = dict(enumerate(status.get('filament_spool_id', []))).get(self.channel, None)

            tool_to_extruder = dict(enumerate(status.get('extruder_map_table', [])))
            for tool_idx, extruder_name in tool_to_extruder.items():
                if extruder_name == self.channel:
                    config['map'] = f"T{tool_idx}"
                    break

            return config
        except:
            return {}

    def _tool_loaded(self, eventtime=None):
        if not self.sensor:
            return False
        try:
            sensor_status = self.sensor.get_status(eventtime)
            return sensor_status.get('filament_detected', False)
        except:
            return False

    def get_status(self, eventtime=None):
        response = {}
        if not self.connect_done:
            return response

        filament_info = self._get_filament_info()
        filament_exist = filament_info.get('filament_exist', False)

        response['name'] = self.name
        response['unit'] = self.unit
        response['channel'] = self.channel
        response['extruder'] = self.extruder
        response['map'] = filament_info.get('map', f"T{self.channel}")
        response['load'] = filament_exist
        response['prep'] = True
        response['tool_loaded'] = self._tool_loaded(eventtime)
        response['loaded_to_hub'] = False
        response['material'] = filament_info.get('material', 'NONE')
        response['filament_vendor'] = filament_info.get('vendor', 'NONE')
        response['filament_sub_type'] = filament_info.get('sub_type', 'NONE')
        response['density'] = self.filament_density
        response['diameter'] = self.filament_diameter
        response['empty_spool_weight'] = self.empty_spool_weight
        response['spool_id'] = filament_info.get('spool_id', None)
        response['color'] = f"#{filament_info.get('color', 'FFFFFFFF')}"
        response['weight'] = self.weight
        response['runout_lane'] = filament_info.get('runout_lane', '?')
        response['filament_exist'] = filament_exist
        response['filament_status'] = 'unknown'
        response['filament_status_led'] = 'gray'
        response['status'] = self.status

        return response

def load_config_prefix(config):
    return AFCLane(config)

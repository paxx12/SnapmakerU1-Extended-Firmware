SPOOLMAN_PROXY_ENDPOINT_BASE = "klippy/spoolman_proxy"

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
        self.webhooks = self.printer.lookup_object('webhooks')
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
        self.pending_refresh = False

        self.weight = -1 # -1 means weight is not supported/configured
        self.filament_density = 1.24
        self.filament_diameter = 1.75
        self.empty_spool_weight = 0
        self.pending_spool_id = None

        self.printer.register_event_handler("klippy:connect", self._handle_connect)

        self.gcode.register_mux_command(
            "SET_SPOOL_ID", "LANE", self.name,
            self.cmd_SET_SPOOL_ID,
            desc=self.cmd_SET_SPOOL_ID_help)

        self.gcode.register_mux_command(
            "REFRESH_SPOOL", "LANE", self.name,
            self.cmd_REFRESH_SPOOL,
            desc=self.cmd_REFRESH_SPOOL_help)

        self.find_by_spool_id_callback = f"{SPOOLMAN_PROXY_ENDPOINT_BASE}/find_by_spool_id/{config.get_name()}"
        self.webhooks.register_endpoint(
            self.find_by_spool_id_callback,
            self._handle_find_by_spool_id_callback)

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

    cmd_SET_SPOOL_ID_help = "Set spool ID and fetch filament data from Spoolman"
    def cmd_SET_SPOOL_ID(self, gcmd):
        """Set spool ID and fetch filament info from spoolman"""
        spool_id = gcmd.get_int('SPOOL_ID')

        gcmd.respond_info(f"Fetching spool {spool_id} data for lane {self.name}...")

        self.pending_refresh = False
        self.pending_spool_id = spool_id

        try:
            self.webhooks.call_remote_method(
                "spoolman_proxy",
                cb_endpoint=self.find_by_spool_id_callback,
                request_method="GET",
                path=f"/v1/spool/{spool_id}"
            )
        except Exception as e:
            gcmd.respond_error(f"Failed to query spoolman: {e}")

    def _handle_find_by_spool_id_callback(self, web_request):
        try:
            payload = web_request.get_dict('payload', {})
            error = web_request.get('error', None)

            if error:
                self.gcode.respond_error(f"Spoolman error: {error}")
                return

            self._apply_spool_data_from_webhook(payload)
        except Exception as e:
            raise web_request.error(f"Failed to process spoolman response: {e}")

    cmd_REFRESH_SPOOL_help = "Refresh current spool data from Spoolman"
    def cmd_REFRESH_SPOOL(self, gcmd):
        filament_info = self._get_filament_info()
        spool_id = filament_info.get('spool_id', None)

        if not spool_id:
            gcmd.respond_error(f"No spool configured for lane {self.name}")
            return

        self.pending_refresh = True

        try:
            self.webhooks.call_remote_method(
                "spoolman_proxy",
                cb_endpoint=self.find_by_spool_id_callback,
                request_method="GET",
                path=f"/v1/spool/{spool_id}"
            )
        except Exception as e:
            gcmd.respond_error(f"Failed to query spoolman: {e}")

    def _apply_spool_data_from_webhook(self, response):
        """Apply spool data from spoolman response via webhook"""
        if not response:
            self.gcode.respond_error("Empty response from spoolman")
            return

        filament = response.get('filament', {})
        material = filament.get('material', 'PLA')
        vendor = filament.get('vendor', {}).get('name', 'Generic')
        color_hex = filament.get('color_hex', 'FFFFFFFF')
        sub_type = filament.get('extra', {}).get('sub_type', 'Basic')

        spool_id = response.get('id', 0)
        self.weight = response.get('remaining_weight', -1)
        self.filament_diameter = filament.get('diameter', 1.75)
        self.filament_density = filament.get('density', 1.24)
        self.empty_spool_weight = filament.get('spool_weight', 0)
        self.pending_spool_id = spool_id

        if self.pending_refresh:
            self.pending_refresh = False
            return

        material = material.replace('"', '\\"').replace("'", "\\'")
        vendor = vendor.replace('"', '\\"').replace("'", "\\'")
        sub_type = sub_type.replace('"', '\\"').replace("'", "\\'")

        gcode_cmd = (
            f'SET_PRINT_FILAMENT_CONFIG '
            f'CONFIG_EXTRUDER={self.channel} '
            f'FILAMENT_TYPE="{material}" '
            f'VENDOR="{vendor}" '
            f'FILAMENT_SUBTYPE="{sub_type}" '
            f'FILAMENT_COLOR_RGBA="{color_hex}" '
            f'FILAMENT_SPOOL_ID={spool_id} '
            'FORCE=1'
        )

        self.gcode.respond_info(f"Applying spool {spool_id} to lane {self.name}: {vendor} {material} ({sub_type}) #{color_hex}")
        self.gcode.run_script(f"M118 {gcode_cmd}")
        self.gcode.run_script(gcode_cmd)

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

    def _update(self, spool_id):
        """Update lane state when spool_id changes"""
        if spool_id == self.pending_spool_id:
            return

        # Weight tracking is supported only by spoolman
        if spool_id == 0:
            self.weight = -1
            return

        try:
            self.pending_refresh = True
            self.webhooks.call_remote_method(
                "spoolman_proxy",
                cb_endpoint=self.find_by_spool_id_callback,
                request_method="GET",
                path=f"/v1/spool/{spool_id}"
            )
        except Exception:
            self.pending_refresh = False
        finally:
            self.pending_spool_id = spool_id

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

        self._update(filament_info.get('spool_id', 0))

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

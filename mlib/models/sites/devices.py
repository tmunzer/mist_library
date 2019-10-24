import json


class Device:

    def __init__(self):
        self.name = None
        self.notes = None
        self.map_id = None
        self.x = -1
        self.y = -1
        self.orientation_overwrite = None # T/F
        self.orientation = -1
        self.height = -1
        self.radio_config = None # object
        self.ip_config = None # object
        self.ble_config = None # object
        self.led = None # object
        self.mesh = None # object
        self.switch_config = None # object
        self.iot_config = None # object
        self.disable_eth1 = None # T/F
        self.disable_module = None # T/F
        self.poe_passthrough = None # T/F
        self.pwr_config = None # object
        self.vars = None # ???
        self.deviceprofile_id = None
        self.image1_url = None

    def __str__(self):
        return json.dumps(self, default=lambda o: o.__dict__)

    def toJSON(self):
        json = {}
        if self.name != None: json["name"] = self.name
        if self.notes != None: json["notes"] = self.notes
        if self.map_id != None: json["map_id"] = self.map_id
        if self.x >= 0: json["x"] = self.x
        if self.y >= 0: json["y"] = self.y
        if self.orientation_overwrite != None: json["orientation_overwrite"] = self.orientation_overwrite
        if self.orientation >= 0: json["orientation"] = self.orientation
        if self.height >= 0: json["height"] = self.height
        if self.radio_config != None: json["radio_config"] = self.radio_config
        if self.ip_config != None: json["ip_config"] = self.ip_config
        if self.ble_config != None: json["ble_config"] = self.ble_config
        if self.led != None: json["led"] = self.led
        if self.mesh != None: json["mesh"] = self.mesh
        if self.switch_config != None: json["switch_config"] = self.switch_config
        if self.iot_config != None: json["iot_config"] = self.iot_config
        if self.disable_eth1 != None: json["disable_eth1"] = self.disable_eth1
        if self.disable_module != None: json["disable_module"] = self.disable_module
        if self.poe_passthrough != None: json["poe_passthrough"] = self.poe_passthrough
        if self.pwr_config != None: json["pwr_config"] = self.pwr_config
        if self.vars != None: json["vars"] = self.vars
        if self.deviceprofile_id != None: json["deviceprofile_id"] = self.deviceprofile_id
        if self.image1_url != None; json["image1_url"] = self.image1_url
        return json
        
    def set_name(self, value):
        if value != "":
            self.name = value
            return True
        else:
            console.error("You must enter a name.")
            return False
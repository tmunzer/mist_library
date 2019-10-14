import json

try:
    from config import log_level
except:
    log_level = 6
finally:
    from mlib.debug import Console
    console = Console(log_level)


class Rogue:

    def __init__(self, enabled = False, honeypot_enabled = True, min_rssi = -85, min_duration = 10, whitelisted_ssids = [], whitelisted_bssids = []):
        self.enabled = enabled
        self.honeypot_enabled = honeypot_enabled
        self.min_rssi = min_rssi
        self.min_duration = min_duration
        self.whitelisted_ssids = whitelisted_ssids
        self.whitelisted_bssids = whitelisted_bssids


    def __str__(self):
        string = ""
        string += "Enabled: %s\r\n" %self.enabled
        string += "honeypot_enabled: %s\r\n" %self.honeypot_enabled
        string += "min_rssi: %s\r\n" %self.min_rssi
        string += "min_duration: %s\r\n" %self.min_duration
        string += "whitelisted_ssids: %s\r\n" %self.whitelisted_ssids
        string += "whitelisted_bssids: %s\r\n" %self.whitelisted_bssids
        return string
        
    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__)

    def define(self, enabled = False, honeypot_enabled = True, min_rssi = -85, min_duration = 10, whitelisted_ssids = [], whitelisted_bssids = []):
        self.set_enabled(enabled)
        self.set_honeypot_enabled(honeypot_enabled)    
        self.set_min_rssi(min_rssi)
        self.set_min_duration(min_duration)
        self.set_whitelisted_ssids(whitelisted_ssids)
        self.set_whitelisted_bssids(whitelisted_bssids)

    def cli(self):
        resp = False
        while not resp:
            val = input("Enable Rogue detection (Y/n)?")
            if val.lower() == "n":
                val = False
                resp = self.set_enabled(val)
            elif val.lower() == "y" or val == "":
                val = True     
                resp = self.set_enabled(val)       
        if self.enabled == False:
            console.info("Rogue detection will be disabled.")
        else:
            resp = False
            while not resp:
                val = input("Enable Honeypot detection (Y/n):")
                if val.lower() == "n":
                    val = False
                    resp = self.set_honeypot_enabled(val)
                elif val.lower() == "y" or val == "":
                    val = True            
                    resp = self.set_honeypot_enabled(val)
            resp = False
            while not resp:
                val = input("Min RSSI for detection (default: -85dBm):")
                if val == "":
                    val = -85
                resp = self.set_min_rssi(val)
            resp = False
            while not resp:
                val = input("Min duration for detection (default: 10sec):")
                if val == "":
                    val = 10
                resp = self.set_min_duration(val)
            resp = False
            while not resp:
                val = input("Comma separated of Whitelist SSIDs:")
                ssids = []
                if "," in val:
                    for ssid in val.split(","):
                        ssids.append(ssid.strip())
                resp = self.set_whitelisted_ssids(ssids)
            resp = False
            while not resp:
                val = input("Comma separated of Whitelist BSSIDs:")
                bssids = []
                if "," in val:
                    for bssid in val.split(","):
                        bssids.append(bssid.strip())
                resp = self.set_whitelisted_bssids(bssids)
            resp = False


    def set_enabled(self, value):
        try:
            enabled = bool(value)
            self.enabled = enabled
            return True
        except:
            console.error("Value %s is not accepted. Must be \"true\", \"false\", \"0\" or \"1\"." %value)
            return False
    
    def set_honeypot_enabled(self, value):
        try:
            enabled = bool(value)
            self.honeypot_enabled = enabled
            return True
        except:
            console.error("Value %s is not accepted. Must be \"true\", \"false\", \"0\" or \"1\"." %value)
            return False

    def set_min_rssi(self, value):
        try:
            min_rssi = int(value)
            if min_rssi >= -85:
                self.min_rssi = min_rssi
                return True
            else:
                console.error("min_rssi value must be higher or equal to -85.")
                return False
        except:
            console.error("Value %s is not accepted. min_rssi must an integer higher or equal to -85." %value)
            return False

    def set_min_duration(self, value):
        try:
            min_duration = int(value)
            if min_duration >= 0 and min_duration <= 59:
                self.min_duration = min_duration
                return True
            else:
                console.error("min_duration value must be between 0 and 59.")
                return False
        except:
            console.error("Value %s is not accepted. min_duration must an integer higher than 0 and lower than 60." %value)
            return False

    def set_whitelisted_ssids(self, value):
        if type(value) == str:
            self.whitelisted_ssids = [value]
            return True
        elif type(value) == list:
            self.whitelisted_ssids = value
            return True
        else:
            console.error("%s is not accepted." %value)
            return False

    def set_whitelisted_bssids(self, value):
        if type(value) == str:
            self.whitelisted_bssids = [value]
            return True
        elif type(value) == list:
            self.whitelisted_bssids = value
            return True
        else:
            console.error("%s is not accepted." %value)
            return False

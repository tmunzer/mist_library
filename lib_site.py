"""
A site represents a project, a deployment. For MSP, it can be 
as small as a coffee shop or a five-star 600-room hotel. A 
site contains a set of Maps, Wlans, Policies, Zones.
"""
import lib_wlan

class Psk:
    def madd(self, mist_session, site_id, ssid, passphrase):
        uri = "/api/v1/sites/%s/psks" % site_id
        body = {
            "ssid": ssid,
            "passphrase": passphrase
        }
        resp = mist_session.mist_post(uri, site_id=site_id, body=body)
        return resp

    def mget(self, mist_session, site_id, name="", ssid=""):
        uri = "/api/v1/sites/%s/psks" % site_id
        if site_id != "":
            uri += "?name=%s" % name
        elif  ssid != "":
            uri += "?ssid=%s" % ssid
        elif site_id != "" and ssid != "":
            uri += "?name=%s&ssid=%s" % (name, ssid)
        resp = mist_session.mist_get(uri, site_id=site_id)
        return resp 

    def mdelete(self, mist_session, site_id, name="", ssid=""):
        uri = "/api/v1/sites/%s/psks" % site_id
        if site_id != "":
            uri += "?name=%s" % name
        elif  ssid != "":
            uri += "?ssid=%s" % ssid
        elif site_id != "" and ssid != "":
            uri += "?name=%s&ssid=%s" % (name, ssid)
        resp = mist_session.mist_delete(uri, site_id=site_id)
        return resp 

class Wlan:
    """ 
    Wlans are the wireless networks created under a site.
    """
    def __init__(self, ssid="", enabled=""):
        self.ssid = ssid
        self.enabled = enabled
        self.auth = lib_wlan.Auth()
        self.vlan = lib_wlan.Vlan()
        self.dynamic_vlan = lib_wlan.Dynamic_Vlan()
        self.radius = lib_wlan.Radius()

    def mget(self, mist_session, site_id):
        uri = "/api/v1/sites/%s/wlans" % site_id
        resp = mist_session.mist_get(uri, site_id=site_id)
        return resp

    def summarize(self, mist_session, site_id):
        wlans = self.mget(mist_session, site_id)
        result = []
        fields = ["ssid", "enabled", "auth", "auth_servers", "acct_servers", "band", "interface", "vlan_id", "dynamic_vlan", "hide_ssid" ]
        for wlan in wlans['result']:
            temp= []
            for field in fields:
                if field not in wlan:
                    temp.append("")
                elif field == "auth":
                    temp.append(str(wlan["auth"]["type"]))
                elif field == "auth_servers":
                    string = ""
                    for server_num, server_val in enumerate(wlan["auth_servers"]):
                        if "host" in server_val:
                            string += "%s:%s" %(server_val["host"], server_val["port"])
                        else:
                            string += "%s:%s" %(server_val["ip"], server_val["port"])
                        if server_num < len(wlan["auth_servers"]) -1:
                            string += " - "
                    temp.append(string)
                elif field == "acct_servers":
                    string = ""
                    for server_num, server_val in enumerate(wlan["auth_servers"]):
                        if "host" in server_val:
                            string += "%s:%s" %(server_val["host"], server_val["port"])
                        else:
                            string += "%s:%s" %(server_val["ip"], server_val["port"])
                        if server_num < len(wlan["acct_servers"]) -1:
                            string += " - "
                    temp.append(string)
                elif field == "dynamic_vlan" :
                    string = "Disabled"
                    if wlan["dynamic_vlan"] != None and wlan["dynamic_vlan"]["enabled"] == True: 
                        string = "default: "
                        if "default_vlan_id" in wlan["dynamic_vlan"]:
                            string += "%s | others: " % wlan["dynamic_vlan"]["default_vlan_id"]
                        else:
                            string += "N/A | others: "
                        if wlan["dynamic_vlan"]["vlans"] != None:
                            for vlan_num, vlan_val in enumerate(wlan["dynamic_vlan"]["vlans"]):
                                string += "%s" % vlan_val
                                if vlan_num < len(wlan["dynamic_vlan"]["vlans"]) -1:
                                    string += " - "
                        else:
                            string += "None"
                    temp.append(string)
                else:
                    temp.append("%s" %wlan[field])
            result.append(temp)
        return result

class RRM:
    def get_current_channel_planning(self, mist_session, site_id):
        uri = "/api/v1/sites/%s/rrm/current" % site_id
        resp = mist_session.mist_get(uri, site_id=site_id)
        return resp

    def get_device_rrm_info(self, mist_session, site_id, device_id, band):
        uri = "/api/v1/sites/%s/rrm/current/devices/%s/band/%s" % (site_id, device_id, band)
        resp = mist_session.mist_get(uri,site_id=site_id)
        return resp

    def optimize(self, mist_session, site_id, band_24=False, band_5=False):
        bands = []
        if band_24:
            bands.append("24")
        if band_5:
            bands.append("5")
        body = { "bands": bands}
        uri = "/api/v1/sites/%s/rrm/optimize" % site_id
        resp = mist_session.mist_post(uri, site_id=site_id, body=body)
        return resp

    def reset(self, mist_session, site_id):
        uri = "/api/v1/sites/%s/devices/reset_radio_config" % site_id
        resp = mist_session.mist_post(uri, site_id=site_id)
        return resp

    def get_events(self, mist_session, site_id, band, limit="", duration=""):
        uri ="/api/v1/sites/%s/rrm/events?band=%s" % (site_id, band)
        if limit != "":
            uri += "&limit=%s" % limit
        if duration != "":
            uri += "&duration=%s" % duration
        resp = mist_session.mist_get(uri, site_id=site_id)
        return resp

    def get_interference_events(self, mist_session, site_id, limit="", page=1, duration=""):
        uri = "/api/v1/sites/%s/events/interference?page=%s" % (site_id, page)
        if limit != "":
            uri += "&limit=%s" % limit
        if duration != duration:
            uri += "&duration=%s" %duration
        resp = mist_session.mist_get(uri, site_id=site_id)
        return resp

    def get_roaming_events(self, mist_session, site_id, mtype, start="", end="", limit=""):
        uri = "/api/v1/sites/%s/events/fast_roam?type=%s" % (site_id, mtype)
        if start != "":
            uri += "&limit=%s" % start
        if end != "":
            uri += "&duration=%s" % end
        if limit != "":
            uri += "&duration=%s" % limit
        resp = mist_session.mist_get(uri, site_id=site_id)
        return resp

class Const:
    def get_applications(self, mist_session):
        uri = "/api/v1/const/applications"
        resp = mist_session.mist_get(uri)
        return resp

    def get_ap_led_status(self, mist_session):
        uri = "/api/v1/const/ap_led_status"
        resp = mist_session.mist_get(uri)
        return resp

class Client_events:
    def get_definition(self, mist_session):
        uri = "/api/v1/const/client_events"
        resp = mist_session.mist_get(uri)
        return resp

class System_events:
    def get_definition(self, mist_session):
        uri = "/api/v1/const/system_events"
        resp = mist_session.mist_get(uri)
        return resp
    def search(self, mist_session, site_id, mtype, start, end):
        uri = "/api/v1/sites/%s/events/system/search?type=%s&start=%s&end=%s" % (site_id, mtype, start, end)
        resp = mist_session.mist_get(uri)
        return resp
    def count(self, mist_session, site_id, mtype, start, end):
        uri = "/api/v1/sites/%s/events/system/count?type=%s&start=%s&end=%s" % (site_id, mtype, start, end)
        resp = mist_session.mist_get(uri)
        return resp
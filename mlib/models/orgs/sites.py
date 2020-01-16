
import json

try:
    from config import log_level
except:
    log_level = 6
finally:
    from mlib.__debug import Console
    console = Console(log_level)


class Site:

    def __init__(self):
        self.name = ""
        self.timezone = ""
        self.country_code = ""
        self.address = ""
        self.lat = ""
        self.lng = ""
        self.sitegroup_ids = ""
        self.rftemplate_id = ""
        self.secpolicy_id = ""
        self.alarmtemplate_id = ""

    def __str__(self):
        string = ""
        string += "Name: %s\r\n" % self.name,
        string += "Address: %s\r\n" % self.address
        string += "Lat/Lng:"
        string += "   Lat: %s\r\n" % self.lat,
        string += "   Lng: %s\r\n" % self.lng,
        string += "Timezone: %s\r\n" % self.timezone,
        string += "Country_code: %s\r\n" % self.country_code,
        string += "RF Template id: %s\r\n" % self.rftemplate_id,
        string += "Sec Policy id: %s\r\n" % self.secpolicy_id,
        string += "Alarm Template id: %s\r\n" % self.alarmtemplate_id,
        string += "Site Group ids: %s\r\n" % self.sitegroup_ids,
        return string

    def toJSON(self):
        site = {
            "name": self.name,
            "timezone": self.timezone,
            "country_code": self.country_code,
            "rftemplate_id": self.rftemplate_id,
            "secpolicy_id": self.secpolicy_id,
            "alarmtemplate_id": self.alarmtemplate_id,
            "latlng": {
                "lat": self.lat,
                "lng": self.lng},
            "sitegroup_ids": self.sitegroup_ids,
            "address": self.address
        }
        return site

    def define(self, site_settings):
        if "name" in site_settings:
            self.set_name(site_settings.name)
        if "timezone" in site_settings:
            self.set_timezone(site_settings.timezone)
        if "country_code" in site_settings:
            self.set_country_code(site_settings.country_code)
        if "rftemplate_id" in site_settings:
            self.set_rftemplate_id(site_settings.rftemplate_id)
        if "secpolicy_id" in site_settings:
            self.set_secpolicy_id(site_settings.secpolicy_id)
        if "alarmtemplate_id" in site_settings:
            self.set_alarmtemplate_id(site_settings.alarmtemplate_id)
        if "sitegroup_ids" in site_settings:
            self.set_sitegroup_ids(site_settings.sitegroup_ids)
        if "address" in site_settings:
            self.set_address(site_settings.address)
        
    def set_name(self, name):
        if name != None:
            self.name = name
            return None
        else: 
            return "Invalid Name"
 
    def set_timezone(self, timezone):
        if timezone.split("/") == 2:
            self.timezone = timezone
            return None
        else:
            return "Invalid Timezone"

    def set_country_code(self, country_code):
        if len(country_code) == 2:
            self.country_code = country_code
            return None
        else: 
            return "Invalid Country Code"

    def set_rftemplate_id(self, rftemplateid):
        self.rftemplate_id = rftemplateid
        return None

    def set_secpolicy_id(self, secpolicy_id):
        self.secpolicy_id = secpolicy_id
        return None

    def set_alarmtemplate_id(self, alarmtemplate_id):
        self.alarmtemplate_id = alarmtemplate_id
        return None

    def set_latlnt(self, latlng):
        if type(latlng) == dict:
            self.latlng = latlng
            return None
        else:
            return "Invalid Lat/Lng"
    
    def set_sitegroup_ids(self, sitegroup_ids):
        if type(sitegroup_ids) == list:
            self.sitegroup_ids = sitegroup_ids
            return None
        else:
            return "Invalid sitegroup_ids"

    def set_address(self, address):
        self.address = address

    
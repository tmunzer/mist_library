'''
Written by Thomas Munzer (tmunzer@juniper.net)
Github repository: https://github.com/tmunzer/Mist_library/
'''

import mlib as mist_lib
from mlib import cli
import requests
import time
from geopy import Nominatim
from tzwhere import tzwhere

try:
    from config import log_level
except:
    log_level = 6
finally:
    from mlib.__debug import Console
    console = Console(log_level)

#####################################################################
#### SETTINGS #####
# This variables are used to create the sites. All the fields are required
sites = [
    {
        "name": "test",
        "address": '41 rue de Villiers, Neuilly sur Seine, France',
        "groups": ["test1", "test2"]
    }
]
# org_id is optional. If not configured, the script will let you select an org
org_id = ""

# This Script can use Google APIs (optional) to retrieve lat/lng, tz and country code. To be 
# able to use Google API, you need an API Key first. Mode information available here:
# https://developers.google.com/maps/documentation/javascript/get-api-key?hl=en
google_api_key = ""

#####################################################################
#### GLOBALS #####
geolocator = Nominatim(user_agent="import_app")
tzwhere = tzwhere.tzwhere()

#####################################################################
# Open Geocoding
#####################################################################


def get_open_geocoding(address):
    console.notice(">> Retrieving lat/lng from OpenStreetMap API")
    location = geolocator.geocode(address, addressdetails=True)
    if type(location) == "NoneType":
        console.error("Unable to find the address %s" % address)
    else:
        return location


def get_open_tz(location):
    console.notice(">> Retrieving tz and country code with tzwhere")
    tz = tzwhere.tzNameAt(location.latitude, location.longitude)
    country_code = str(location.raw["address"]["country_code"]).upper()
    return {"tz": tz, "country_code": country_code}


def use_open(address):
    data = {}
    location = get_open_geocoding(address)
    data = {
        "location": {
            "latitude": location.latitude,
            "longitude": location.longitude
        },
        **get_open_tz(location)
    }
    return data

#####################################################################
# Google Geocoding
#####################################################################


def get_google_geocoding(address):
    console.notice(">> Retrieving lat/lng and country code from Google API")
    data = {"location": None, "country_code": ""}
    url = "https://maps.googleapis.com/maps/api/geocode/json?address={0}&key={1}".format(
        address, google_api_key)
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data["status"] == "OK":
            if len(data["results"]) > 0:
                data["location"] = {
                    "address": data["results"][0]["formatted_address"],
                    "latitude": data["results"][0]["geometry"]["location"]["lat"],
                    "longitude": data["results"][0]["geometry"]["location"]["lng"]
                }
                for entry in data["results"][0]["address_components"]:
                    if "country" in entry["types"]:
                        data["country_code"] = entry["short_name"]
                return data
        elif data["status"] == "REQUEST_DENIED":
            console.error(data["error_message"])
            return data
    else:
        console.error("Unable to get the location from Google API")
        return data


def get_google_tz(location):
    console.notice(">> Retrieving tz from Google API")
    ts = int(time.time())
    url = "https://maps.googleapis.com/maps/api/timezone/json?location={0},{1}&timestamp={2}&key={3}".format(
        location["latitude"], location["longitude"], ts, google_api_key)
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data["status"] == "OK":
            tz = data["timeZoneId"]
            return tz
        elif data["status"] == "REQUEST_DENIED":
            console.error(data["error_message"])
    else:
        console.error("Unable to get the timezone from Google API")


def use_google(address):
    data = get_google_geocoding(address)
    if data["location"] is not None:
        data["tz"] = get_google_tz(data["location"])
        return data
    else:
        return None

#####################################################################
# Site Groups Management
#####################################################################


def get_site_groups_list():
    response = mist_lib.orgs.sitegroups.get(mist, org_id)
    tmp = {}
    for group in response["result"]:
        if "site_ids" in group:
            site_ids = group["site_ids"]
        else:
            site_ids = []
        tmp[group["name"]] = {"id": group["id"], "site_ids": site_ids}
    return tmp


def create_site_group(group_name):
    response = mist_lib.orgs.sitegroups.create(
        mist, org_id, {"name": group_name})
    if response['status_code'] == 200:
        name = response["result"]["name"]
        sitegroups_id = response["result"]["id"]
        console.notice(
            "> Site Group {0} created with ID {1}".format(name, sitegroups_id))
        return sitegroups_id


def assign_site_to_group(site_id, group_name):
    site_groups = get_site_groups_list()
    if site_groups == {} or not group_name in site_groups:
        group_id = create_site_group(group_name)
        site_ids = [site_id]
    else:
        group_id = site_groups[group_name]["id"]
        site_ids = site_groups[group_name]["site_ids"]
        site_ids.append(site_id)
    response = mist_lib.orgs.sitegroups.update(
        mist, org_id, group_id, {"site_ids": site_ids})
    if response["status_code"] == 200:
        console.info("> Site succesfully added to group {0} (group_id {1})".format(
            group_name, group_id))
        return group_id
    else:
        console.warning("> Unable to add the site to group {0} (group_id {1})".format(
            group_name, group_id))
        return None


def assign_groups_to_site(site_id, group_ids):
    response = mist_lib.orgs.sites.update(
        mist, org_id, site_id, {"sitegroup_ids": group_ids})
    if response["status_code"] == 200:
        console.info("> Groups assigned to the site")
        return response
    else:
        console.warning("> Unable to assign groups")
        return None

#####################################################################
# Site  Management
#####################################################################


def create_site(name, address):
    console.info("> Retrieving additional data")
    if google_api_key:
        data = use_google(site["address"])
    if not google_api_key or data is None:
        data = use_open(site["address"])
        payload = {
            "name": name,
            "address": address,
            "latlng": {
                "lat": data["location"]["latitude"],
                "lng": data["location"]["longitude"]
            },
            "timezone": data["tz"],
            "country_code": data["country_code"]
        }
    response = mist_lib.orgs.sites.create(mist, org_id, payload)
    if response["status_code"] == 200:
        console.info("> Site created succesfully with ID {0}".format(
            response["result"]["id"]))
        return response["result"]
    else:
        console.error("> Unable to create site with the payload: {0}".format(payload))



def new_site(name, address, groups):
    console.info("Site {0}: Starting process".format(name))
    site = create_site(name, address)
    group_ids = []
    console.notice("> Retrieving site group ids")
    for group in groups:
        group_id = assign_site_to_group(site["id"], group)
        if group_id:
            group_ids.append(group_id)
    assign_groups_to_site(site["id"], group_ids)


#####################################################################
##### ENTRY POINT #####
#####################################################################
if __name__ == "__main__":
    mist = mistapi.APISession("./session.py")
    # mist.save()
    if not org_id:
        org_id = cli.select_org(mist)[0]
    for site in sites:
        new_site(name=site["name"], address=site["address"],
                 groups=site["groups"])

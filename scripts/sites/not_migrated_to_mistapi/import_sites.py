'''
Written by Thomas Munzer (tmunzer@juniper.net)
Github repository: https://github.com/tmunzer/Mist_library/
'''

import mistapi
from mistapi.__logger import console
import requests
import time
from geopy import Nominatim
from tzwhere import tzwhere


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
    console.info(">> Retrieving lat/lng from OpenStreetMap API")
    location = geolocator.geocode(address, addressdetails=True)
    if type(location) == "NoneType":
        console.error(f"Unable to find the address {address}")
    else:
        return location


def get_open_tz(location):
    console.info(">> Retrieving tz and country code with tzwhere")
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
    console.info(">> Retrieving lat/lng and country code from Google API")
    data = {"location": None, "country_code": ""}
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={address}&key={google_api_key}"
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
    console.info(">> Retrieving tz from Google API")
    ts = int(time.time())
    url = f"https://maps.googleapis.com/maps/api/timezone/json?location={location['latitude']},{location['longitude']}&timestamp={ts}&key={google_api_key}"
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


def get_site_groups_list(apisession):
    response = mistapi.api.v1.orgs.sitegroups.getOrgSiteGroups(apisession, org_id)
    tmp = {}
    for group in response.data:
        if "site_ids" in group:
            site_ids = group["site_ids"]
        else:
            site_ids = []
        tmp[group["name"]] = {"id": group["id"], "site_ids": site_ids}
    return tmp


def create_site_group(apisession, group_name):
    response = mistapi.api.v1.orgs.sitegroups.createOrgSiteGroup(apisession, org_id, {"name": group_name})
    if response.status_code == 200:
        name = response.data["name"]
        sitegroups_id = response.data["id"]
        console.info(
            f"> Site Group {name} created with ID {sitegroups_id}")
        return sitegroups_id


def assign_site_to_group(apisession, site_id, group_name):
    site_groups = get_site_groups_list(apisession)
    if site_groups == {} or not group_name in site_groups:
        group_id = create_site_group(apisession, group_name)
        site_ids = [site_id]
    else:
        group_id = site_groups[group_name]["id"]
        site_ids = site_groups[group_name]["site_ids"]
        site_ids.append(site_id)
    response = mistapi.api.v1.orgs.sitegroups.updateOrgSiteGroup(
        apisession, org_id, group_id, {"site_ids": site_ids})
    if response.status_code == 200:
        console.info(f"> Site succesfully added to group {group_name} (group_id {group_id})")
        return group_id
    else:
        console.warning(f"> Unable to add the site to group {group_name} (group_id {group_id})")
        return None


def assign_groups_to_site(apisession, site_id, group_ids):
    response = mistapi.api.v1.sites.sites.updateSiteInfo(apisession, site_id, {"sitegroup_ids": group_ids})
    if response.status_code == 200:
        console.info("> Groups assigned to the site")
        return response
    else:
        console.warning("> Unable to assign groups")
        return None

#####################################################################
# Site  Management
#####################################################################


def create_site(apisession, name, address):
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
    response = mistapi.api.v1.orgs.sites.countOrgSites(apisession, org_id, payload)
    if response.status_code == 200:
        console.info(f"> Site created succesfully with ID {response.data['id']}")
        return response.data
    else:
        console.error(f"> Unable to create site with the payload: {payload}")



def new_site(apisession, name, address, groups):
    console.info(f"Site {name}: Starting process")
    site = create_site(apisession, name, address)
    group_ids = []
    console.info("> Retrieving site group ids")
    for group in groups:
        group_id = assign_site_to_group(apisession, site["id"], group)
        if group_id:
            group_ids.append(group_id)
    assign_groups_to_site(apisession, site["id"], group_ids)


#####################################################################
##### ENTRY POINT #####
#####################################################################
if __name__ == "__main__":
    apisession = mistapi.APISession("./session.py")
    if not org_id:
        org_id = mistapi.cli.select_org(apisession)[0]
    for site in sites:
        new_site(apisession, name=site["name"], address=site["address"],
                 groups=site["groups"])

'''
Written by Thomas Munzer (tmunzer@juniper.net)
Github repository: https://github.com/tmunzer/Mist_library/
'''

#### IMPORTS #####
import requests
import time
from geopy import Nominatim
import sys
import csv
import getopt
import logging
from typing import Tuple

try:
    import mistapi
    from mistapi.__logger import console
except:
    print("""
Critical: 
\"mistapi\" package is missing. Please use the pip command to install it.

# Linux/macOS
python3 -m pip install mistapi

# Windows
py -m pip install mistapi
    """)
    sys.exit(2)

try:
    from timezonefinder import TimezoneFinder
except:
    print("""
Critical: 
\"timezonefinder\" package is missing. Please use the pip command to install it.

# Linux/macOS
python3 -m pip install timezonefinder

# Windows
py -m pip install timezonefinder
    """)
    sys.exit(2)

#### LOGS ####
logger = logging.getLogger(__name__)
out=sys.stdout

#####################################################################
#### PARAMETERS #####
# Required site parameters:
# - name
# - address
#
# Optional site parameters (if id and name is defined, the name will 
# be used):
# - alarmtemplate_id or alarmtemplate_name
# - aptemplate_id or aptemplate_name
# - gatewaytemplate_id or gatewaytemplate_name
# - networktemplate_id or networktemplate_name
# - rftemplate_id or rftemplate_name
# - secpolicy_id or secpolicy_name
# - site_group_ids or site_group_names      list of groups. If multiple groups, 
#                                           must be enclosed by double quote and 
#                                           comma separated (ex: "group1, group2")
# - country_code                            can be detected by the script based on 
#                                           the address
# - timezone                                can be detected by the script based on 
#                                           the address

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
log_file = "./script.log"
env_file = "~/.mist_env"

#####################################################################
#### GLOBALS #####
geolocator = Nominatim(user_agent="import_app")
tf = TimezoneFinder() 
parameter_types = ["alarmtemplate", "aptemplate", "gatewaytemplate", "networktemplate", "rftemplate", "secpolicy", "sitegroup" ]
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
    tz = tf.timezone_at(lat=location.latitude, lng=location.longitude)
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
def _get_geo_info(site:dict) -> dict:
    console.info("> Retrieving additional data")
    if google_api_key:
        data = use_google(site["address"])
    if not google_api_key or data is None:
        data = use_open(site["address"])
    site["latlng"] = {
            "lat": data["location"]["latitude"],
            "lng": data["location"]["longitude"]
        }
    site["timezone"]= data["tz"]
    site["country_code"]= data["country_code"]

def _create_site(apisession:mistapi.APISession, site:dict, org_id:str):
    site = _get_geo_info(site)
    response = mistapi.api.v1.orgs.sites.countOrgSites(apisession, org_id, site)
    if response.status_code == 200:
        console.info(f"> Site created succesfully with ID {response.data['id']}")
        return response.data
    else:
        console.error(f"> Unable to create site with the payload: {site}")



def _new_site(apisession:mistapi.APISession, org_id:str, site:list, parameters:dict) -> None:
    console.info(f"Site {site['name']}: Starting process")
    site = _create_site(apisession, site, org_id)
    group_ids = []
    console.info("> Retrieving site group ids")
    for group in site["groups"]:
        group_id = assign_site_to_group(apisession, site["id"], group)
        if group_id:
            group_ids.append(group_id)
    assign_groups_to_site(apisession, site["id"], group_ids)

###############################################################################
### SITE GROUPS
def _replace_sitegroup_names(apisession:mistapi.APISession, org_id:str, sitegroups:dict, sitegroup_names:dict) -> Tuple[dict, str]:
    sitegroup_ids = []
    for sitegroup_name in sitegroup_names:
        if sitegroup_name not in sitegroups: 
            response = mistapi.api.v1.orgs.sitegroups.createOrgSiteGroup(apisession, org_id, {"name":sitegroup_name })
            if response.status_code == 200:
                sitegroups[sitegroup_name] = response.data["id"]
            else:
                console.error(f"Unable to create site group {sitegroup_name}")
        sitegroup_ids.append(sitegroups[sitegroup_name])
    return sitegroups, sitegroup_ids

###############################################################################
### MATCHING OBJECT NAME / OBJECT ID
def _replace_object_names_by_ids(apisession:mistapi.APISession, org_id:str, site:dict, parameters:dict)->dict:
    if "sitegroup_names" in site:
        parameters["sitegroup"], site["sitegroup_ids"] = _replace_sitegroup_names(apisession, org_id, parameters["sitegroup"], site["sitegroup_names"])
        del site["sitegroup_names"]
    for parameter in parameter_types:
        if f"{parameter}_name" in site:
            name = site[f"{parameter}_name"]
            site[f"{parameter}_id"] = parameters[parameter][name]
            del site[f"{parameter}_name"]
    return site


def _retrieve_objects(apisession:mistapi.APISession, org_id:str, parameter_type:str) -> list:
    result = {}
    data = []
    if parameter_type == "alarmtemplate":
        response = mistapi.api.v1.orgs.alarmtemplates.getOrgAlarmTemplates(apisession, org_id)
    elif parameter_type == "aptemplate":
        response = mistapi.api.v1.orgs.aptemplates.getOrgAptemplates(apisession, org_id)
    elif parameter_type == "gatewaytemplate":
        response = mistapi.api.v1.orgs.gatewaytemplates.getOrgGatewayTemplates(apisession, org_id)
    elif parameter_type == "networktemplate":
        response = mistapi.api.v1.orgs.networktemplates.getOrgNetworkTemplates(apisession, org_id)
    elif parameter_type == "rftemplate":
        response = mistapi.api.v1.orgs.rftemplates.getOrgRfTemplates(apisession, org_id)
    elif parameter_type == "secpolicy":
        response = mistapi.api.v1.orgs.secpolicies.getOrgSecPolicies(apisession, org_id)
    elif parameter_type == "sitegroup":
        response = mistapi.api.v1.orgs.sitegroups.getOrgSiteGroups(apisession, org_id)
    data = response.data
    while response.next:
        response = mistapi.get_next(apisession, response) 
        data += response.data
    for entry in data:
        result[entry["name"]] = entry["id"]
    return result
    

###############################################################################
### PARSE CSV
def _extract_groups(data:str) -> list:
    entries = data.split(",")
    result = []
    for entry in entries:
        result.append(entry.strip())
    return result

###############################################################################
# Optional site parameters (if id and name is defined, the name will 
# be used):
# - alarmtemplate_id or alarmtemplate_name
# - aptemplate_id or aptemplate_name
# - gatewaytemplate_id or gatewaytemplate_name
# - networktemplate_id or networktemplate_name
# - rftemplate_id or rftemplate_name
# - secpolicy_id or secpolicy_name
# - site_group_ids or site_group_names      list of groups. If multiple groups, 
#                                           must be enclosed by double quote and 
#                                           comma separated (ex: "group1, group2")
# - country_code                            can be detected by the script based on 
#                                           the address
# - timezone                                can be detected by the script based on 
#                                           the address
def start(apisession:mistapi.APISession, org_id:str, sites:list):
    parameters = {}
    for parameter in parameter_types:
        parameters[parameter] = _retrieve_objects(apisession, org_id, parameters)
    for site in sites:
        _replace_object_names_by_ids(apisession, org_id, site, parameters)
        _new_site(apisession, org_id, site, parameters)

###############################################################################
### ENTRY POINT
if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(sys.argv[1:], "ho:g:f:c:e:", ["help", "org_id=", "google_api_key=", "file=", "env=", "log_file="])
    except getopt.GetoptError as err:
        console.error(err)
        usage()

    csv_file = None
    for o, a in opts:
        if o in ["-h", "--help"]:
            usage()
        elif o in ["-o", "--org_id"]:
            org_id = a
        elif o in ["-g", "--google_api_key"]:
            google_api_key = a
        elif o in ["-f", "--file"]:
            csv_file=a
        elif o in ["e", "--env"]:
            env_file=a
        elif o in ["l", "--log_file"]:
            log_file = a
        
        else:
            assert False, "unhandled option"

    #### LOGS ####
    logging.basicConfig(filename=log_file, filemode='w')
    logger.setLevel(logging.DEBUG)
    ### MIST SESSION ###
    apisession = mistapi.APISession(env_file=env_file)
    apisession.login()

    ### START ###
    # if not org_id:
    #     org_id = mistapi.cli.select_org(apisession)[0]
    
    if csv_file:
        with open(csv_file, "r") as f:
            data = csv.reader(f, skipinitialspace=True, quotechar='"')
            fields = []
            sites = []
            for line in data:
                if not fields:
                    for column in line:                        
                        fields.append(column.strip().replace("#",""))
                else:
                    site = {}
                    i = 0
                    for column in line:
                        field = fields[i]
                        if field == "groups": column= _extract_groups(column)
                        site[field] = column
                        i+=1
                    sites.append(site)
    
    start(apisession,org_id, sites)
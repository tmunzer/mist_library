'''
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script automate the sites creation in a Mist Org from a CSV file.

This Script can use Google APIs (optional) to retrieve lat/lng, tz and country code. 
To be able to use Google API, you need an API Key first. Mode information available 
here: https://developers.google.com/maps/documentation/javascript/get-api-key?hl=en


-------
Requirements:
mistapi: https://pypi.org/project/mistapi/

-------
Usage:
This script requires a parameter to locate the csv file. Other parameters listed below
are optional. If the optional parameters are not defined, the script will ask for the 
additional required settings.

It is recomended to use an environment file to store the required information
to request the Mist Cloud (see https://pypi.org/project/mistapi/ for more 
information about the available parameters).

-------
CSV Format:
The first line MUST start with a "#" and defines each columns of the CSV file. The allowed
values are listed below.

When defining the templates, the policies and the sitegroups, it is possible to use the
object name OR the object id (this must be defined in the first line, by appending "_name" or 
"_id"). In case both name and id are defined, the name will be used.

-------
CSV Example:
#name,address,sitegroup_names,rftemplate_id,networktemplate_name,gatewaytemplate_name,vars
Juniper France, "41 rue de Villiers, Neuilly sur Seine, France", "test1, test2",39ce2...ab5ee,ex-lab,test,"vlan_guest:3,vlan_corp:2"

-------
CSV Parameters:
Required:
- name
- address

Optional:
- alarmtemplate_id or alarmtemplate_name
- aptemplate_id or aptemplate_name
- gatewaytemplate_id or gatewaytemplate_name
- networktemplate_id or networktemplate_name
- rftemplate_id or rftemplate_name
- secpolicy_id or secpolicy_name
- site_group_ids or site_group_names    list of groups. If multiple groups ,must
                                        be enclosed by double quote and comma
                                        separated (ex: "group1, group2")
- country_code                          can be detected by the script based on the
                                        address
- timezone                              can be detected by the script based on the
                                        address
- vars                                  dict of all the site variables. Format must
                                        be key1:var1. If multiple vars, must be
                                        enclosed by double quote and comma separated
                                        (e.g. "key1:var1,key2:var2, ...")

-------
Script Parameters:
-h, --help          display this help
-f, --file=         REQUIRED: path to the CSV file
-o, --org_id=       Set the org_id (only one of the org_id or site_id can be defined)
-s, --site_ids=     list of sites to use, comma separated
-l, --log_file=     define the filepath/filename where to write the logs
                    default is "./script.log"
-e, --env=          define the env file to use (see mistapi env file documentation 
                    here: https://pypi.org/project/mistapi/)
                    default is "~/.mist_env"

-------
Examples:
python3 ./import_sites.py -f ./my_new_sites.csv                 
python3 ./import_sites.py -f ./my_new_sites.csv --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 

'''

#### IMPORTS #####
import requests
import time
import sys
import os
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

#### LOGS ####
logger = logging.getLogger(__name__)
out = sys.stdout

#####################################################################
#### PARAMETERS #####

#



# This Script can use Google APIs (optional) to retrieve lat/lng, tz and country code. To be
# able to use Google API, you need an API Key first. Mode information available here:
# https://developers.google.com/maps/documentation/javascript/get-api-key?hl=en
google_api_key = ""
log_file = "./script.log"
env_file = "~/.mist_env"

#####################################################################
#### GLOBALS #####
parameter_types = [
    "alarmtemplate",
    "aptemplate",
    "gatewaytemplate",
    "networktemplate",
    "rftemplate",
    "secpolicy",
    "sitegroup"
]
geolocator = None
tzfinder = None
steps_total = 0
steps_count = 0
###############################################################################
# PROGRESS BAR
def _progress_bar_update(size:int=80):   
    global steps_count, steps_total
    if steps_count > steps_total: steps_count = steps_total

    percent = steps_count/steps_total
    delta = 17
    x = int((size-delta)*percent)
    out.write(f"Progress: ")
    out.write(f"[{'█'*x}{'.'*(size-delta-x)}]")
    if percent < 1:
        out.write(f"  {int(percent*100)}%\r".rjust(5))
    else:
        out.write(f" {int(percent*100)}%\r".rjust(5))
    out.flush()

def _progress_bar_end(size:int=80): 
    global steps_count, steps_total
    if steps_count < 0: steps_count = steps_total
    _progress_bar_update(size)
    out.write("\n")
    out.flush()

def _new_step(text:str, success:bool=True, inc:bool=False, size:int=80):
    global steps_count
    if inc: steps_count += 1

    if success: 
        if text:
            print(f"{text} ".ljust(size - 3, "."), end="")
            print(f" OK")
        else:
            print("".ljust(80))
        _progress_bar_update(size)
    else: 
        console.error(f"{text}".ljust(80))
        _progress_bar_end(size)

def _new_title(text:str, size:int=80):
    print(f" {text} ".center(size, "-"))
    _progress_bar_update(size)

def _new_end(size:int=80):
    _progress_bar_end(size)

def _calculate_steps_number(sites:list):
    global steps_total
    # 1 = sites validation
    # 3 = geocoding + site creation + site settings update
    steps_total = 1 + len(parameter_types) + len(sites) * 3

#####################################################################
# Geocoding
#####################################################################
##################
# GOOGLE LAT/LNG


def _get_google_geocoding(address):
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


def _get_google_tz(location):
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


def _geocoding_google(address):
    data = _get_google_geocoding(address)
    if data["location"] is not None:
        data["tz"] = _get_google_tz(data["location"])
        return data
    else:
        return None

################
# OPEN LAT/LNG


def _import_tzfinder():
    try:
        global tzfinder
        from timezonefinder import TimezoneFinder
        tzfinder = TimezoneFinder()
    except:
        print("""
    Critical: 
    \"timezonefinder\" package is required when \"google_api_key\" is not defined.
    Please use the pip command to install it.

    # Linux/macOS
    python3 -m pip install timezonefinder

    # Windows
    py -m pip install timezonefinder
        """)
        sys.exit(2)


def _import_geopy():
    try:
        global geolocator
        from geopy import Nominatim
        geolocator = Nominatim(user_agent="import_app")
    except:
        print("""
    Critical: 
    \"geopy\" package is required when \"google_api_key\" is not defined.
    Please use the pip command to install it.

    # Linux/macOS
    python3 -m pip install geopy

    # Windows
    py -m pip install geopy
        """)
        sys.exit(2)


def _import_open_geocoding():
    _import_geopy()
    _import_tzfinder()


def _get_open_geocoding(address):
    location = geolocator.geocode(address, addressdetails=True)
    if type(location) == "NoneType":
        console.error(f"Unable to find the address {address}")
    else:
        return location


def _get_open_tz(location):
    tz = tzfinder.timezone_at(lat=location.latitude, lng=location.longitude)
    country_code = str(location.raw["address"]["country_code"]).upper()
    return {"tz": tz, "country_code": country_code}


def _geocoding_open(address):
    data = {}
    location = _get_open_geocoding(address)
    data = {
        "location": {
            "latitude": location.latitude,
            "longitude": location.longitude
        },
        **_get_open_tz(location)
    }
    return data

#####################################################################
# Site  Management
#####################################################################


def _get_geo_info(site: dict) -> dict:
    if google_api_key:
        data = _geocoding_google(site["address"])
    if not google_api_key or data is None:
        data = _geocoding_open(site["address"])
    site["latlng"] = {
        "lat": data["location"]["latitude"],
        "lng": data["location"]["longitude"]
    }
    site["timezone"] = data["tz"]
    site["country_code"] = data["country_code"]
    _new_step(f"Site {site['name']}: Retrievning geo informations", True, True)
    return site


def _create_site(apisession: mistapi.APISession, org_id: str, site: dict):
    site = _get_geo_info(site).copy()
    if "vars" in site:
        del site["vars"]
    response = mistapi.api.v1.orgs.sites.createOrgSite(
        apisession, org_id, site)
    if response.status_code == 200:
        _new_step(f"Site {site['name']}: Created (ID  {response.data['id']})", True, True)
        return response.data
    else:
        console.error(f"> Unable to create site with the payload: {site}")

def _update_site(apisession: mistapi.APISession, site: dict, site_id:str):
    if "vars" in site and site["vars"]:
        vars = site["vars"]
        site_vars = {}
        for entry in vars.split(","):
            key = entry.split(":")[0]
            val = entry.split(":")[1]
            site_vars[key] = val
        mistapi.api.v1.sites.setting.updateSiteSettings(apisession, site_id, {"vars": site_vars})
        _new_step(f"Site {site['name']}: Site variables deployed", True, True)
        _new_step("")
    else:
        _new_step(f"Site {site['name']}: No site variables to deploy", True, True)
        _new_step("")


###############################################################################
# MATCHING OBJECT NAME / OBJECT ID
###############################################################################
# SPECIFIC TO SITE GROUPS
def _replace_sitegroup_names(apisession: mistapi.APISession, org_id: str, sitegroups: dict, sitegroup_names: dict) -> Tuple[dict, str]:
    sitegroup_ids = []
    for sitegroup_name in sitegroup_names:
        if sitegroup_name not in sitegroups:
            response = mistapi.api.v1.orgs.sitegroups.createOrgSiteGroup(
                apisession, org_id, {"name": sitegroup_name})
            if response.status_code == 200:
                sitegroups[sitegroup_name] = response.data["id"]
            else:
                console.error(f"Unable to create site group {sitegroup_name}")
        sitegroup_ids.append(sitegroups[sitegroup_name])
    return sitegroups, sitegroup_ids

# GENERIC REPLACE FUNCTION
def _replace_object_names_by_ids(apisession: mistapi.APISession, org_id: str, site: dict, parameters: dict) -> dict:
    '''
    replace the template/policy/groups names by the corresponding ids
    '''
    if "sitegroup_names" in site:
        parameters["sitegroup"], site["sitegroup_ids"] = _replace_sitegroup_names(
            apisession, org_id, parameters["sitegroup"], site["sitegroup_names"])
        del site["sitegroup_names"]
    for parameter in parameter_types:
        if f"{parameter}_name" in site:
            name = site[f"{parameter}_name"]
            site[f"{parameter}_id"] = parameters[parameter][name]
            del site[f"{parameter}_name"]
    return site

# GET FROM MIST
def _retrieve_objects(apisession: mistapi.APISession, org_id: str) -> dict:
    '''
    Get the list of the current templates, policies and sitegoups
    '''
    parameters = {}
    for parameter_type in parameter_types:
        parameter_values = {}
        data = []
        response = None
        if parameter_type == "alarmtemplate":
            response = mistapi.api.v1.orgs.alarmtemplates.getOrgAlarmTemplates(
                apisession, org_id)
        elif parameter_type == "aptemplate":
            response = mistapi.api.v1.orgs.aptemplates.getOrgAptemplates(
                apisession, org_id)
        elif parameter_type == "gatewaytemplate":
            response = mistapi.api.v1.orgs.gatewaytemplates.getOrgGatewayTemplates(
                apisession, org_id)
        elif parameter_type == "networktemplate":
            response = mistapi.api.v1.orgs.networktemplates.getOrgNetworkTemplates(
                apisession, org_id)
        elif parameter_type == "rftemplate":
            response = mistapi.api.v1.orgs.rftemplates.getOrgRfTemplates(
                apisession, org_id)
        elif parameter_type == "secpolicy":
            response = mistapi.api.v1.orgs.secpolicies.getOrgSecPolicies(
                apisession, org_id)
        elif parameter_type == "sitegroup":
            response = mistapi.api.v1.orgs.sitegroups.getOrgSiteGroups(
                apisession, org_id)
        data = mistapi.get_all(apisession, response)
        for entry in data:
            parameter_values[entry["name"]] = entry["id"]
        parameters[parameter_type] = parameter_values
        _new_step(f"Retrieving {parameter_type} list ", True, True)
    return parameters


###############################################################################
# PARSE CSV
def _extract_groups(data: str) -> list:
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
# - vars                                    dict of all the site variables. Format
#                                           must be key1:var1. If multiple vars,
#                                           must be enclosed by double quote and
#                                           comma separated (ex: "key1:var1,key2:var2")
#                                           

def _check_settings(sites: list):
    site_name = []
    for site in sites:
        if "name" not in site:
            _new_step(f"Missing site parameter \"name\"", False)
            sys.exit(0)
        elif site["name"] in site_name:
            _new_step(f"Site Name \"{site['name']}\" duplicated".ljust(80))
            sys.exit(0)
        else:
            site_name.append(site["name"])
        if "address" not in site:
            _new_step(f"Missing site parameter \"address\"", False)
            sys.exit(0)
        for key in site:
            parameter_name = key.split("_")
            if key in ["name", "address", "sitegroup_names", "sitegroup_ids", "vars"]:
                pass
            elif parameter_name[0] in parameter_types and parameter_name[1] in ["name", "id"]:
                pass
            else:
                _new_step(f"Invalid site parameter \"{key}\"", False)
                sys.exit(0)
    _new_step("Sites validated", True, True)

def _process_sites_data(apisession: mistapi.APISession, org_id: str, sites: list) -> dict:
    '''
    Function to validate sites data and retrieve the required object from Mist
    '''
    _new_title(" Processing Sites ")
    parameters = {}
    _check_settings(sites)
    parameters = _retrieve_objects(apisession, org_id)
    return parameters

def _create_sites(apisession: mistapi.APISession, org_id: str, sites: list, parameters:dict):
    '''
    Function to create and update all the sites
    '''
    _new_title(" Creating Sites ")
    for site in sites:
        _new_step("")
        site = _replace_object_names_by_ids(
            apisession, org_id, site, parameters)
        new_site = _create_site(apisession, org_id, site)
        _update_site(apisession, site, new_site["id"])

def start(apisession: mistapi.APISession, org_id: str, sites: list):
    _calculate_steps_number(sites)
    parameters = _process_sites_data(apisession, org_id, sites)
    _create_sites(apisession, org_id, sites, parameters)
    _new_end()


###############################################################################
# USAGE
def usage():
    print('''
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script automate the sites creation in a Mist Org from a CSV file.

This Script can use Google APIs (optional) to retrieve lat/lng, tz and country code. 
To be able to use Google API, you need an API Key first. Mode information available 
here: https://developers.google.com/maps/documentation/javascript/get-api-key?hl=en


-------
Requirements:
mistapi: https://pypi.org/project/mistapi/

-------
Usage:
This script requires a parameter to locate the csv file. Other parameters listed below
are optional. If the optional parameters are not defined, the script will ask for the 
additional required settings.

It is recomended to use an environment file to store the required information
to request the Mist Cloud (see https://pypi.org/project/mistapi/ for more 
information about the available parameters).

-------
CSV Format:
The first line MUST start with a "#" and defines each columns of the CSV file. The allowed
values are listed below.

When defining the templates, the policies and the sitegroups, it is possible to use the
object name OR the object id (this must be defined in the first line, by appending "_name" or 
"_id"). In case both name and id are defined, the name will be used.

-------
CSV Example:
#name,address,sitegroup_names,rftemplate_id,networktemplate_name,gatewaytemplate_name,vars
Juniper France, "41 rue de Villiers, Neuilly sur Seine, France", "test1, test2",39ce2...ab5ee,ex-lab,test,"vlan_guest:3,vlan_corp:2"

-------
CSV Parameters:
Required:
- name
- address

Optional:
- alarmtemplate_id or alarmtemplate_name
- aptemplate_id or aptemplate_name
- gatewaytemplate_id or gatewaytemplate_name
- networktemplate_id or networktemplate_name
- rftemplate_id or rftemplate_name
- secpolicy_id or secpolicy_name
- site_group_ids or site_group_names    list of groups. If multiple groups ,must
                                        be enclosed by double quote and comma
                                        separated (ex: "group1, group2")
- country_code                          can be detected by the script based on the
                                        address
- timezone                              can be detected by the script based on the
                                        address
- vars                                  dict of all the site variables. Format must
                                        be key1:var1. If multiple vars, must be
                                        enclosed by double quote and comma separated
                                        (e.g. "key1:var1,key2:var2, ...")

-------
Script Parameters:
-h, --help          display this help
-f, --file=         REQUIRED: path to the CSV file
-o, --org_id=       Set the org_id (only one of the org_id or site_id can be defined)
-s, --site_ids=     list of sites to use, comma separated
-l, --log_file=     define the filepath/filename where to write the logs
                    default is "./script.log"
-e, --env=          define the env file to use (see mistapi env file documentation 
                    here: https://pypi.org/project/mistapi/)
                    default is "~/.mist_env"

-------
Examples:
python3 ./import_sites.py -f ./my_new_sites.csv                 
python3 ./import_sites.py -f ./my_new_sites.csv --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 

''')


###############################################################################
# ENTRY POINT
if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(sys.argv[1:], "ho:g:f:c:e:", [
                                   "help", "org_id=", "google_api_key=", "file=", "env=", "log_file="])
    except getopt.GetoptError as err:
        console.error(err)
        usage()

    csv_file = None
    org_id = None
    for o, a in opts:
        if o in ["-h", "--help"]:
            usage()
        elif o in ["-o", "--org_id"]:
            org_id = a
        elif o in ["-g", "--google_api_key"]:
            google_api_key = a
        elif o in ["-f", "--file"]:
            csv_file = a
        elif o in ["-e", "--env"]:
            env_file = a
        elif o in ["-l", "--log_file"]:
            log_file = a
        else:
            assert False, "unhandled option"

    if not google_api_key:
        _import_open_geocoding()
    #### LOGS ####
    logging.basicConfig(filename=log_file, filemode='w')
    logger.setLevel(logging.DEBUG)
    ### MIST SESSION ###
    apisession = mistapi.APISession(env_file=env_file)
    apisession.login()

    ### START ###
    if not org_id:
        org_id = mistapi.cli.select_org(apisession)[0]

    if not csv_file:
        console.error("")
        with open(os.path(csv_file), "r") as f:
            data = csv.reader(f, skipinitialspace=True, quotechar='"')
            fields = []
            sites = []
            for line in data:
                if not fields:
                    for column in line:
                        fields.append(column.strip().replace("#", ""))
                else:
                    site = {}
                    i = 0
                    for column in line:
                        field = fields[i]
                        if field.startswith("sitegroup_"):
                            column = _extract_groups(column)
                        site[field] = column
                        i += 1
                    sites.append(site)

    start(apisession, org_id, sites)

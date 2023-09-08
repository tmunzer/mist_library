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
- site_id or site_name                      site used as a template to create 
                                            the new site. The name, address, 
                                            groups, vars and template will not
                                            be copied from the source site
- alarmtemplate_id or alarmtemplate_name
- aptemplate_id or aptemplate_name
- gatewaytemplate_id or gatewaytemplate_name
- networktemplate_id or networktemplate_name
- rftemplate_id or rftemplate_name
- secpolicy_id or secpolicy_name
- site_group_ids or site_group_names        list of groups. If multiple groups,
                                            must be enclosed by double quote 
                                            and comma separated 
                                            (ex: "group1, group2")
- country_code                              can be detected by the script based
                                            on the address
- timezone                                  can be detected by the script based
                                            on the address
- vars                                      dict of all the site variables. 
                                            Format must be key1:var1. 
                                            If multiple vars, must be enclosed
                                            by double quote and comma separated
                                            (e.g. "key1:var1,key2:var2, ...")

-------
Script Parameters:
-h, --help          display this help
-f, --file=         REQUIRED: path to the CSV file

-o, --org_id=       Set the org_id (only one of the org_id or site_id can be defined)
-n, --org_name=     Org name where to deploy the configuration:
                        - if org_id is provided (existing org), used to validate 
                        the destination org
                        - if org_id is not provided (new org), the script will 
                        create a new org and name it with the org_name value   

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
import time

MISTAPI_MIN_VERSION = "0.44.1"

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

#####################################################################
#### PARAMETERS #####
log_file = "./script.log"
env_file = "~/.mist_env"
# This Script can use Google APIs (optional) to retrieve lat/lng, tz and country code. To be
# able to use Google API, you need an API Key first. Mode information available here:
# https://developers.google.com/maps/documentation/javascript/get-api-key?hl=en
google_api_key = ""

#####################################################################
#### LOGS ####
logger = logging.getLogger(__name__)
out = sys.stdout

#####################################################################
#### GLOBALS #####
parameter_types = [
    "site",
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
#####################################################################
# PROGRESS BAR
#####################################################################
# PROGRESS BAR AND DISPLAY


class ProgressBar():
    def __init__(self):
        self.steps_total = 0
        self.steps_count = 0

    def _pb_update(self, size: int = 80):
        if self.steps_count > self.steps_total:
            self.steps_count = self.steps_total

        percent = self.steps_count/self.steps_total
        delta = 17
        x = int((size-delta)*percent)
        print("\033[A")
        print(f"Progress: ", end="")
        print(f"[{'█'*x}{'.'*(size-delta-x)}]", end="")
        print(f"{int(percent*100)}%".rjust(5), end="")

    def _pb_new_step(self, message: str, result: str, inc: bool = False, size: int = 80, display_pbar: bool = True):
        if inc:
            self.steps_count += 1
        text = f"\033[A\033[F{message}"
        print(f"{text} ".ljust(size + 4, "."), result)
        print("".ljust(80))
        if display_pbar:
            self._pb_update(size)

    def _pb_title(self, text: str, size: int = 80, end: bool = False, display_pbar: bool = True):
        print()
        print("\033[A")
        print(f" {text} ".center(size, "-"), "\n")
        if not end and display_pbar:
            print("".ljust(80))
            self._pb_update(size)

    def inc(self, size: int = 80):
        self.steps_count += 1
        self._pb_update(size)

    def set_steps_total(self, steps_total: int):
        self.steps_total = steps_total

    def log_message(self, message, display_pbar: bool = True):
        self._pb_new_step(message, " ", display_pbar=display_pbar)

    def log_success(self, message, inc: bool = False, display_pbar: bool = True):
        logger.info(f"{message}: Success")
        self._pb_new_step(
            message, "\033[92m\u2714\033[0m\n", inc=inc, display_pbar=display_pbar)

    def log_warning(self, message, inc: bool = False, display_pbar: bool = True):
        logger.warning(f"{message}: Warning")
        self._pb_new_step(
            message, "\033[93m\u2B58\033[0m\n", inc=inc, display_pbar=display_pbar)

    def log_failure(self, message, inc: bool = False, display_pbar: bool = True):
        logger.error(f"{message}: Failure")
        self._pb_new_step(
            message, "\033[31m\u2716\033[0m\n", inc=inc, display_pbar=display_pbar)

    def log_title(self, message, end: bool = False, display_pbar: bool = True):
        logger.info(message)
        self._pb_title(message, end=end, display_pbar=display_pbar)


pb = ProgressBar()

#####################################################################
# Geocoding
#####################################################################
##################
# GOOGLE LAT/LNG


def _get_google_geocoding(address):
    try:
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
            pb.log_warning("Unable to get the location from Google API")
            return data
    except:
        pb.log_warning("Unable to get the location from Google API")
        return None


def _get_google_tz(location):
    try:
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
            pb.log_warning("Unable to find the site timezone")
            return None
    except:
        pb.log_warning("Unable to find the site timezone")
        return None


def _geocoding_google(site):
    message = "Retrievning geo information"
    pb.log_message(message)
    data = _get_google_geocoding(site["address"])
    if data["location"] is not None:
        tz = _get_google_tz(data["location"])
        if tz:
            data["tz"] = tz
    return data

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


def _get_open_geocoding(site):
    location = geolocator.geocode(site["address"], addressdetails=True)
    if type(location) == "NoneType":
        pb.log_warning(f"Site {site['name']}: Unable to find the address")
        return None
    else:
        return location


def _get_open_tz(location):
    tz = tzfinder.timezone_at(lat=location.latitude, lng=location.longitude)
    country_code = str(location.raw["address"]["country_code"]).upper()
    return {"tz": tz, "country_code": country_code}


def _geocoding_open(site):
    data = {}
    location = _get_open_geocoding(site)
    if location:
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
    message = f"Site {site['name']}: Retrievning geo information"
    pb.log_message(message)
    if google_api_key:
        data = _geocoding_google(site)
    if not google_api_key or data is None:
        data = _geocoding_open(site)
    if data:
        site["latlng"] = {
            "lat": data["location"]["latitude"],
            "lng": data["location"]["longitude"]
        }
        site["timezone"] = data["tz"]
        site["country_code"] = data["country_code"]
        pb.log_success(message, True)
    else:
        pb.log_warning(message, True)
    return site


def _create_site(apisession: mistapi.APISession, org_id: str, site: dict):
    site = _get_geo_info(site).copy()
    if site:
        message = f"Site {site['name']}: Site creation"
        pb.log_message(message)
        try:
            if "vars" in site:
                del site["vars"]
            response = mistapi.api.v1.orgs.sites.createOrgSite(
                apisession, org_id, site)
            if response.status_code == 200:
                pb.log_success(
                    f"Site {site['name']}: Created (ID {response.data['id']})", True)
                return response.data
            else:
                pb.log_failure(message, True)
        except:
            pb.log_failure(message, True)
    else:
        pb.inc()
        return None


def _update_site(apisession: mistapi.APISession, site: dict, site_id: str):
    if "vars" in site and site["vars"]:
        message = f"Site {site['name']}: Updating Site settings"
        pb.log_message(message)
        try:
            vars = site["vars"]
            site_vars = {}
            for entry in vars.split(","):
                key = entry.split(":")[0]
                val = entry.split(":")[1]
                site_vars[key] = val
            mistapi.api.v1.sites.setting.updateSiteSettings(
                apisession, site_id, {"vars": site_vars})
            pb.log_success(message, True)
        except:
            pb.log_failure(message, True)
    else:
        pb.log_success(
            f"Site {site['name']}: No Site settings to update", True)


###############################################################################
# CLONING FROM SOURCE SITE
###############################################################################
def _clone_src_site_settings(apisession:mistapi.APISession, src_site_id:str, dst_site_id:str, site_name:str):
    src_site = None
    message= f"Site {site_name}: Retrievning settings from src site"
    pb.log_message(message)
    try:
        resp = mistapi.api.v1.sites.setting.getSiteSetting(apisession, src_site_id)
        if resp.status_code != 200:
            pb.log_failure(message, True)
        else:
            src_site = resp.data
            if "vars" in src_site: del src_site["vars"]            
    except:
        pb.log_failure(message, True)
    
    if src_site:
        message= f"Site {site_name}: Deploying settings from src site"
        pb.log_message(message)
        try:
            resp = mistapi.api.v1.sites.setting.updateSiteSettings(apisession, dst_site_id, src_site)
            if resp.status_code != 200:
                pb.log_failure(message, True)
            else:
                pb.log_success(f"Site {site_name}: Cloning settings from src site", True)      
        except:
            pb.log_failure(message, True)



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
                pb.log_warning(
                    f"Unable to create site group {sitegroup_name}", inc=False)
        sitegroup_ids.append(sitegroups[sitegroup_name])
    return sitegroups, sitegroup_ids

# GENERIC REPLACE FUNCTION


def _replace_object_names_by_ids(apisession: mistapi.APISession, org_id: str, site: dict, parameters: dict) -> dict:
    '''
    replace the template/policy/groups names by the corresponding ids
    '''
    warning = False
    source_site_id = None
    message = f"Site {site['name']}: updating IDs"
    pb.log_message(message)


    if "site_id" in site:
        source_site_id = site["site_id"]
        del site["site_id"]
    elif "site_name" in site:
        source_site_id = parameters["site"].get(site["site_name"], None)
        if not source_site_id:
            pb.log_warning(f"Site {site['name']}: Source site {site['site_name']} not found")
        del site["site_name"]

    if "sitegroup_names" in site:
        parameters["sitegroup"], site["sitegroup_ids"] = _replace_sitegroup_names(
            apisession, org_id, parameters["sitegroup"], site["sitegroup_names"])
        del site["sitegroup_names"]

    for parameter in parameter_types:
        try:
            if f"{parameter}_name" in site:
                name = site[f"{parameter}_name"]
                site[f"{parameter}_id"] = parameters[parameter][name]
                del site[f"{parameter}_name"]
        except:
            warning = True
            pb.log_warning(
                f"Site {site['name']}: Missing {parameter} on dest org", inc=False)
    if not warning:
        pb.log_success(message, True)
    else:
        pb.log_warning(message, True)
    return site, source_site_id

# GET FROM MIST


def _retrieve_objects(apisession: mistapi.APISession, org_id: str, parameters_in_use:list) -> dict:
    '''
    Get the list of the current templates, policies and sitegoups
    '''
    parameters = {}
    print(parameters_in_use)
    for parameter_type in parameters_in_use:
        message = f"Retrieving {parameter_type} from Mist"
        pb.log_message(message, display_pbar=False)
        parameter_values = {}
        data = []
        response = None
        try:
            if parameter_type == "site":
                response = mistapi.api.v1.orgs.sites.listOrgSites(apisession, org_id)
            if parameter_type == "alarmtemplate":
                response = mistapi.api.v1.orgs.alarmtemplates.listOrgAlarmTemplates(
                    apisession, org_id)
            elif parameter_type == "aptemplate":
                response = mistapi.api.v1.orgs.aptemplates.listOrgAptemplates(
                    apisession, org_id)
            elif parameter_type == "gatewaytemplate":
                response = mistapi.api.v1.orgs.gatewaytemplates.listOrgGatewayTemplates(
                    apisession, org_id)
            elif parameter_type == "networktemplate":
                response = mistapi.api.v1.orgs.networktemplates.listOrgNetworkTemplates(
                    apisession, org_id)
            elif parameter_type == "rftemplate":
                response = mistapi.api.v1.orgs.rftemplates.listOrgRfTemplates(
                    apisession, org_id)
            elif parameter_type == "secpolicy":
                response = mistapi.api.v1.orgs.secpolicies.listOrgSecPolicies(
                    apisession, org_id)
            elif parameter_type == "sitegroup":
                response = mistapi.api.v1.orgs.sitegroups.listOrgSiteGroups(
                    apisession, org_id)
            data = mistapi.get_all(apisession, response)
            for entry in data:
                parameter_values[entry["name"]] = entry["id"]
            parameters[parameter_type] = parameter_values
            pb.log_success(message, display_pbar=False)
        except:
            pb.log_failure(message, display_pbar=False)
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
    message = "Validating Sites data"
    pb.log_title(message, display_pbar=False)
    site_name = []
    parameters_in_use = []
    line = 1
    for site in sites:
        line +=1
        if "name" not in site:
            pb.log_failure(message, display_pbar=False)
            console.error(f"Line {line}: Missing site parameter \"name\"")
            sys.exit(0)
        elif site["name"] in site_name:
            pb.log_failure(message, display_pbar=False)
            console.error(f"Line {line}: Site Name \"{site['name']}\" duplicated")
            sys.exit(0)
        else:
            site_name.append(site["name"])

        if "address" not in site:
            pb.log_failure(message, display_pbar=False)
            console.error(f"Line {line}: Missing site parameter \"address\"")
            sys.exit(0)

        for key in site:
            parameter_name = key.split("_")
            if key in [ "name", "address", "vars", "country_code", "timezone"]:
                pass
            elif key in [ "sitegroup_names", "sitegroup_ids"]:
                if not "sitegroup" in parameters_in_use:
                    parameters_in_use.append("sitegroup")
                pass
            elif parameter_name[0] in parameter_types and parameter_name[1] in ["name", "id"]:
                if not parameter_name[0] in parameters_in_use:
                    parameters_in_use.append(parameter_name[0])
                pass
            else:
                pb.log_failure(message, display_pbar=False)
                console.error(f"Line {line}: Invalid site parameter \"{key}\"")
                sys.exit(0)
    pb.log_success(message, display_pbar=False)
    return parameters_in_use


def _process_sites_data(apisession: mistapi.APISession, org_id: str, sites: list) -> dict:
    '''
    Function to validate sites data and retrieve the required object from Mist
    '''
    parameters = {}
    pb.log_title("Preparing Sites Import", display_pbar=False)
    parameters_in_use = _check_settings(sites)
    parameters = _retrieve_objects(apisession, org_id, parameters_in_use)
    return parameters


def _create_sites(apisession: mistapi.APISession, org_id: str, sites: list, parameters: dict):
    '''
    Function to create and update all the sites
    '''
    pb.log_title("Creating Sites", display_pbar=True)
    for site in sites:        
        site, source_site_id = _replace_object_names_by_ids(
            apisession, org_id, site, parameters)
        new_site = _create_site(apisession, org_id, site)
        if not new_site:
            pb.inc()
        else:
            if source_site_id:
                _clone_src_site_settings(apisession, source_site_id, new_site["id"], new_site["name"])
            else:
                pb.inc()
            _update_site(apisession, site, new_site["id"])


def _read_csv_file(file_path: str):
    with open(file_path, "r") as f:
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
        return sites


def _check_org_name_in_script_param(apisession: mistapi.APISession, org_id: str, org_name: str = None):
    response = mistapi.api.v1.orgs.orgs.getOrg(apisession, org_id)
    if response.status_code != 200:
        console.critical(
            f"Unable to retrieve the org information: {response.data}")
        sys.exit(3)
    org_name_from_mist = response.data["name"]
    return org_name == org_name_from_mist


def _check_org_name(apisession: mistapi.APISession, org_id: str, org_name: str = None):
    if not org_name:
        response = mistapi.api.v1.orgs.orgs.getOrg(apisession, org_id)
        if response.status_code != 200:
            console.critical(
                f"Unable to retrieve the org information: {response.data}")
            sys.exit(3)
        org_name = response.data["name"]
    while True:
        print()
        resp = input(
            "To avoid any error, please confirm the current destination orgnization name: ")
        if resp == org_name:
            return org_id, org_name
        else:
            print()
            print("The orgnization names do not match... Please try again...")


def _create_org(apisession: mistapi.APISession, custom_dest_org_name: str = None):
    while True:
        if not custom_dest_org_name:
            custom_dest_org_name = input("Organization name? ")
        if custom_dest_org_name:
            org = {
                "name": custom_dest_org_name
            }
            message = f"Creating the organisation \"{custom_dest_org_name}\" in {apisession.get_cloud()} "
            pb.log_message(message, display_pbar=False)
            try:
                pb.log_success(message, display_pbar=False)
            except Exception as e:
                pb.log_failure(message, display_pbar=False)
                logger.error("Exception occurred", exc_info=True)
                sys.exit(10)
            org_id = mistapi.api.v1.orgs.orgs.createOrg(
                apisession, org).data["id"]
            return org_id, custom_dest_org_name


def _select_dest_org(apisession: mistapi.APISession):
    print()
    print(" Destination Org ".center(80, "-"))
    print()
    while True:
        res = input(
            "Do you want to create a (n)ew organisation or (r)estore to an existing one? ")
        if res.lower() == "r":
            org_id = mistapi.cli.select_org(apisession)[0]
            org_name = mistapi.api.v1.orgs.orgs.getOrg(
                apisession, org_id).data["name"]
            if _check_org_name(apisession, org_id, org_name):
                return org_id, org_name
        elif res.lower() == "n":
            return _create_org(apisession)


def start(apisession: mistapi.APISession, file_path: str, org_id: str = None, org_name: str = None):
    if org_id and org_name:
        if not _check_org_name_in_script_param(apisession, org_id, org_name):
            console.critical(
                f"Org name {org_name} does not match the org {org_id}")
            sys.exit(0)
    elif org_id and not org_name:
        org_id, org_name = _check_org_name(apisession, org_id)
    elif not org_id and org_name:
        org_id, org_name = _create_org(apisession, org_name)
    elif not org_id and not org_name:
        org_id, org_name = _select_dest_org(apisession)
    else:  # should not since we covered all the possibilities...
        sys.exit(0)

    sites = _read_csv_file(file_path)
    # 4 = IDs +  geocoding + site creation + clone site settings + site settings update
    pb.set_steps_total(len(sites) * 5)

    parameters = _process_sites_data(apisession, org_id, sites)

    _create_sites(apisession, org_id, sites, parameters)
    pb.log_title("Site Import Done", end=True)


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
- source_site_id or source_site_name        site used as a template to create 
                                            the new site. The name, address, 
                                            vars and template will not be 
                                            copied from the source site
- alarmtemplate_id or alarmtemplate_name
- aptemplate_id or aptemplate_name
- gatewaytemplate_id or gatewaytemplate_name
- networktemplate_id or networktemplate_name
- rftemplate_id or rftemplate_name
- secpolicy_id or secpolicy_name
- site_group_ids or site_group_names        list of groups. If multiple groups,
                                            must be enclosed by double quote 
                                            and comma separated 
                                            (ex: "group1, group2")
- country_code                              can be detected by the script based
                                            on the address
- timezone                                  can be detected by the script based
                                            on the address
- vars                                      dict of all the site variables. 
                                            Format must be key1:var1. 
                                            If multiple vars, must be enclosed
                                            by double quote and comma separated
                                            (e.g. "key1:var1,key2:var2, ...")

-------
Script Parameters:
-h, --help          display this help
-f, --file=         REQUIRED: path to the CSV file

-o, --org_id=       Set the org_id (only one of the org_id or site_id can be defined)
-n, --org_name=     Org name where to deploy the configuration:
                        - if org_id is provided (existing org), used to validate 
                        the destination org
                        - if org_id is not provided (new org), the script will 
                        create a new org and name it with the org_name value   

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
    sys.exit(0)

def check_mistapi_version():
    if mistapi.__version__ < MISTAPI_MIN_VERSION:
        logger.critical(f"\"mistapi\" package version {MISTAPI_MIN_VERSION} is required, you are currently using version {mistapi.__version__}.")
        logger.critical(f"Please use the pip command to updated it.")
        logger.critical("")
        logger.critical(f"    # Linux/macOS")
        logger.critical(f"    python3 -m pip upgrade mistapi")
        logger.critical("")
        logger.critical(f"    # Windows")
        logger.critical(f"    py -m pip upgrade mistapi")
        print(f"""
    Critical: 
    \"mistapi\" package version {MISTAPI_MIN_VERSION} is required, you are currently using version {mistapi.__version__}. 
    Please use the pip command to updated it.

    # Linux/macOS
    python3 -m pip upgrade mistapi

    # Windows
    py -m pip upgrade mistapi
        """)
        sys.exit(2)
    else: 
        logger.info(f"\"mistapi\" package version {MISTAPI_MIN_VERSION} is required, you are currently using version {mistapi.__version__}.")


###############################################################################
# ENTRY POINT
if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(sys.argv[1:], "ho:n:g:f:e:l:", [
                                   "help", "org_id=", "--org_name=", "google_api_key=", "file=", "env=", "log_file="])
    except getopt.GetoptError as err:
        console.error(err)
        usage()

    csv_file = None
    org_id = None
    org_name = None
    for o, a in opts:
        if o in ["-h", "--help"]:
            usage()
        elif o in ["-o", "--org_id"]:
            org_id = a
        elif o in ["-n", "--org_name"]:
            org_name = a
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
    check_mistapi_version()
    ### MIST SESSION ###
    apisession = mistapi.APISession(env_file=env_file)
    apisession.login()

    ### START ###
    if not csv_file:
        console.error("CSV File is missing")
        usage()
    else:
        start(apisession, csv_file, org_id, org_name)

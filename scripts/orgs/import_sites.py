'''
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script automate the sites creation in a Mist Org from a CSV file.

**NOTE**
This Script can use Google APIs (optional) to retrieve lat/lng, tz and country code. 
To be able to use Google API, you need an API Key first. Mode information available 
here: https://developers.google.com/maps/documentation/javascript/get-api-key?hl=en

If the Google API Key is not provided, the script will use geopy and timezonefinder
packages to generate the required information.

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
- sitetemplate_id or sitetemplate_name
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
- subnet                                    if set, will add this subnet in the
                                            auto assignment rules to automatically 
                                            assign the APs deployed on this subnet
                                            to this site

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

-g, --google_api_key=   Google API key used for geocoding
                        If not set, the script will use timezonefinder and geopy
                        package to generate the geo information 

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
import time
import sys
import csv
import getopt
import logging
import types
import urllib
from typing import Tuple
import requests

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
LOG_FILE = "./script.log"
ENV_FILE = "~/.mist_env"
# This Script can use Google APIs (optional) to retrieve lat/lng, tz and country code. To be
# able to use Google API, you need an API Key first. Mode information available here:
# https://developers.google.com/maps/documentation/javascript/get-api-key?hl=en
GOOGLE_API_KEY = ""
MAX_RETRY = 3
#####################################################################
#### LOGS ####
LOGGER = logging.getLogger(__name__)

#####################################################################
#### GLOBALS #####
PARAMETER_TYPES = [
    "site",
    "sitetemplate",
    "alarmtemplate",
    "aptemplate",
    "gatewaytemplate",
    "networktemplate",
    "rftemplate",
    "secpolicy",
    "sitegroup"
]
GEOLOCATOR = None
TZFINDER = None
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
        LOGGER.info(f"{message}: Success")
        self._pb_new_step(
            message, "\033[92m\u2714\033[0m\n", inc=inc, display_pbar=display_pbar)

    def log_warning(self, message, inc: bool = False, display_pbar: bool = True):
        LOGGER.warning(f"{message}: Warning")
        self._pb_new_step(
            message, "\033[93m\u2B58\033[0m\n", inc=inc, display_pbar=display_pbar)

    def log_failure(self, message, inc: bool = False, display_pbar: bool = True):
        LOGGER.error(f"{message}: Failure")
        self._pb_new_step(
            message, "\033[31m\u2716\033[0m\n", inc=inc, display_pbar=display_pbar)

    def log_title(self, message, end: bool = False, display_pbar: bool = True):
        LOGGER.info(message)
        self._pb_title(message, end=end, display_pbar=display_pbar)

PB = ProgressBar()

#####################################################################
# Geocoding
#####################################################################
##################
# GOOGLE LAT/LNG
class GoogleGeocoding:

    def __init__(self, google_api_key:str) -> None:
        self.google_api_key = google_api_key

    def _log_url(self, url):
        query_params = url.split("?")[1].split("&")
        for param in query_params:
            key = param.split("=")[0]
            value = param.split("=")[1]
            if key == "key":
                value = f"{value[0:3]}...{value[-3:len(value)]}"
                url = url.replace(param, f"{key}:{value}")
        return url

    def _get_google_geocoding(self, address, retry:int=0):
        if retry == MAX_RETRY:
            LOGGER.error(f"_get_google_geocoding: too many retries...")
            return None
        else:
            try:
                data = {"location": None, "country_code": ""}
                url = f"https://maps.googleapis.com/maps/api/geocode/json?address={urllib.parse.quote(address)}&key={self.google_api_key}"
                LOGGER.debug(f"_get_google_geocoding: URL: {self._log_url(url)}")
                response = requests.get(url)
                LOGGER.debug(f"_get_google_geocoding: Response: {response.content}")
                if response.status_code == 200:
                    data = response.json()
                    LOGGER.debug(f"_get_google_geocoding: Response JSON: {data}")
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
                            LOGGER.info("_get_google_geocoding: Request succeed with Data")
                            return data
                        else:
                            LOGGER.warning("_get_google_geocoding: Request succeed without Data")
                            LOGGER.info(f"_get_google_geocoding: retrying")
                            return self._get_google_geocoding(address, retry + 1)
                    elif data["status"] == "REQUEST_DENIED":
                        LOGGER.warning(f"_get_google_geocoding: Request failed: {data['error_message']}")
                        LOGGER.warning(response.content)
                        LOGGER.info(f"_get_google_geocoding: retrying")
                        return self._get_google_geocoding(address, retry + 1)
                    else:
                        LOGGER.warning("_get_google_geocoding: Request failed without Data")
                        LOGGER.info(f"_get_google_geocoding: retrying")
                        return self._get_google_geocoding(address, retry + 1)
                else:
                    LOGGER.warning("_get_google_geocoding: Unable to get the location from Google API")
                    LOGGER.warning(response.content)
                    LOGGER.info(f"_get_google_geocoding: retrying")
                    return self._get_google_geocoding(address, retry + 1)
            except:
                LOGGER.warning("_get_google_geocoding: Unable to get the location from Google API")
                LOGGER.error("Exception occurred", exc_info=True)
                LOGGER.info(f"_get_google_geocoding: retrying")
                return self._get_google_geocoding(address, retry + 1)


    def _get_google_tz(self, location, retry:int=0):
        if retry == MAX_RETRY:
            LOGGER.error(f"_get_google_tz: too many retries...")
            return None
        else:
            try:
                ts = int(time.time())
                url = f"https://maps.googleapis.com/maps/api/timezone/json?location={location['latitude']},{location['longitude']}&timestamp={ts}&key={self.google_api_key}"
                response = requests.get(url)
                LOGGER.debug(f"_get_google_tz: Response: {response.content}")
                if response.status_code == 200:
                    data = response.json()
                    LOGGER.debug(f"_get_google_geocoding: Response JSON: {data}")
                    if data["status"] == "OK":
                        tz = data["timeZoneId"]
                        LOGGER.info("_get_google_tz: Request succeed with Data")
                        return tz
                    elif data["status"] == "REQUEST_DENIED":
                        LOGGER.warning(f"_get_google_tz: Request failed: {data['error_message']}")
                        LOGGER.info(f"_get_google_tz: retrying")
                        return self._get_google_tz(location, retry + 1)
                    else:
                        LOGGER.warning("_get_google_tz: Request failed without Data")
                        LOGGER.info(f"_get_google_tz: retrying")
                        return self._get_google_tz(location, retry + 1)
                else:
                    LOGGER.warning("_get_google_tz: Unable to find the site timezone")
                    LOGGER.info(f"_get_google_tz: retrying")
                    return self._get_google_tz(location, retry + 1)
            except:
                LOGGER.warning("_get_google_tz: Unable to find the site timezone")
                LOGGER.error("Exception occurred", exc_info=True)
                LOGGER.info(f"_get_google_tz: retrying")
                return self._get_google_tz(location, retry + 1)


    def geocoding(self, site):
        data = self._get_google_geocoding(site["address"])
        if data and data.get("location"):
            tz = self._get_google_tz(data["location"])
            if tz:
                data["tz"] = tz
        LOGGER.debug(f"geocoding: Returns {data}")
        return data

################
# OPEN LAT/LNG
class OpenGeocoding:

    def __init__(self) -> None:
        try:
            from timezonefinder import TimezoneFinder
            self.tzfinder = TimezoneFinder()
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
        try:
            from geopy import Nominatim
            self.geolocator = Nominatim(user_agent="import_app")
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


    def _get_open_geocoding(self, site):
        try:
            time.sleep(.01)
            location = self.geolocator.geocode(site["address"], addressdetails=True, timeout=5)
            if isinstance(location, types.NoneType):
                LOGGER.warning(f"_get_open_geocoding: Unable to find the address")
                return None
            else:
                LOGGER.info(f"_get_open_geocoding: Address found")
                return location
        except:
            LOGGER.warning("_get_open_geocoding: Unable to get the location")
            LOGGER.error("Exception occurred", exc_info=True)
            return None


    def _get_open_tz(self, location):
        try:
            tz = self.tzfinder.timezone_at(lat=location.latitude, lng=location.longitude)
            country_code = str(location.raw["address"]["country_code"]).upper()
            LOGGER.info(f"_get_open_tz: Timezone found")
            return {"tz": tz, "country_code": country_code}
        except:
            LOGGER.warning("_get_open_tz: Unable to find the site timezone")
            LOGGER.error("Exception occurred", exc_info=True)
            return None


    def geocoding(self, site):
        data = {}
        location = self._get_open_geocoding(site)
        if location:
            data = {
                "location": {
                    "latitude": location.latitude,
                    "longitude": location.longitude
                },
                **self._get_open_tz(location)
            }
        LOGGER.debug(f"geocoding: Returns {data}")
        return data



#####################################################################
# Auto Assignment Rules
#####################################################################
def _get_current_org_config(apisession:mistapi.APISession, org_id:str):
    message = "Retrieving current Org Rules"
    PB.log_message(message, display_pbar=False)
    try:
        res = mistapi.api.v1.orgs.setting.getOrgSettings(apisession, org_id)
        if res.status_code == 200:
            PB.log_success(message, inc=True)
            auto_site_assignment = res.data.get("auto_site_assignment", {"enable": True})
            return auto_site_assignment
        else:
            PB.log_failure(message, inc=True)
    except:
        PB.log_failure(message, inc=True)
        LOGGER.error("Exception occurred", exc_info=True)

def _set_new_org_config(apisession:mistapi.APISession, org_id:str, auto_site_assignment:dict):
    message = "Updating Org Rules"
    PB.log_message(message, display_pbar=False)
    try:
        res = mistapi.api.v1.orgs.setting.updateOrgSettings(
                apisession, org_id, {"auto_site_assignment": auto_site_assignment}
            )
        if res.status_code == 200:
            PB.log_success(message, inc=True)
        else:
            PB.log_failure(message, inc=True)
    except:
        PB.log_failure(message, inc=True)
        LOGGER.error("Exception occurred", exc_info=True)

def _compare_rules(org_rules:list, new_rules:list):
    errors = []
    if not org_rules:
        org_rules = []
    for rule in new_rules:
        message = f"Checking subnet {rule.get('subnet')}"
        PB.log_message(message)
        try:
            subnet_exists = list(r for r in org_rules if r.get("subnet") == rule.get("subnet"))
            if subnet_exists:
                LOGGER.warning(
                    f"_compare_rules:subnet {rule.get('subnet')} configured for site {rule.get('value')} already exists: {subnet_exists}"
                    )
                errors.append(
                    f"subnet {rule.get('subnet')} configured for site {rule.get('value')} already exists: {subnet_exists}"
                    )
            else:
                org_rules.append(rule)
        except:
            LOGGER.error("Exception occurred", exc_info=True)
            errors.append(
                f"error when processing subnet {rule.get('subnet')} configured for site {rule.get('value')}"
                )
    if errors:
        PB.log_warning(message, inc=True)
    return org_rules


def _update_org_rules(apisession:mistapi.APISession, org_id:str, new_rules:list):
    PB.log_title("Updating Autoprovisioning Rules")
    auto_site_assignment = _get_current_org_config(apisession, org_id)
    auto_site_assignment["rules"] = _compare_rules(auto_site_assignment.get("rules", {}), new_rules)
    _set_new_org_config(apisession, org_id, auto_site_assignment)



#####################################################################
# Site  Management
#####################################################################
def _get_geo_info(site: dict, geocoder: callable) -> dict:
    message = f"Site {site['name']}: Retrievning geo information"
    PB.log_message(message)
    data = geocoder.geocoding(site)
    if data:
        site["latlng"] = {
            "lat": data["location"]["latitude"],
            "lng": data["location"]["longitude"]
        }
        site["timezone"] = data["tz"]
        site["country_code"] = data["country_code"]
        PB.log_success(message, True)
    else:
        PB.log_warning(message, True)
    return site


def _create_site(apisession: mistapi.APISession, org_id: str, site: dict, geocoder:callable):
    site = _get_geo_info(site, geocoder).copy()
    if site:
        message = f"Site {site['name']}: Site creation"
        PB.log_message(message)
        try:
            if "vars" in site:
                del site["vars"]
            response = mistapi.api.v1.orgs.sites.createOrgSite(
                apisession, org_id, site)
            if response.status_code == 200:
                PB.log_success(
                    f"Site {site['name']}: Created (ID {response.data['id']})", True)
                return response.data
            else:
                PB.log_failure(message, True)
        except:
            PB.log_failure(message, True)
    else:
        PB.inc()
        return None


def _update_site(apisession: mistapi.APISession, site: dict, site_id: str):
    if "vars" in site and site["vars"]:
        message = f"Site {site['name']}: Updating Site settings"
        PB.log_message(message)
        try:
            vars = site["vars"]
            site_vars = {}
            for entry in vars.split(","):
                key = entry.split(":")[0]
                val = entry.split(":")[1]
                site_vars[key] = val
            mistapi.api.v1.sites.setting.updateSiteSettings(
                apisession, site_id, {"vars": site_vars})
            PB.log_success(message, True)
        except:
            PB.log_failure(message, True)
    else:
        PB.log_success(
            f"Site {site['name']}: No Site settings to update", True)


###############################################################################
# CLONING FROM SOURCE SITE
###############################################################################
def _clone_src_site_settings(
        apisession:mistapi.APISession, src_site_id:str, dst_site_id:str, site_name:str
    ):
    src_site = None
    message= f"Site {site_name}: Retrievning settings from src site"
    PB.log_message(message)
    try:
        resp = mistapi.api.v1.sites.setting.getSiteSetting(apisession, src_site_id)
        if resp.status_code != 200:
            PB.log_failure(message, True)
        else:
            src_site = resp.data
            if "vars" in src_site:
                del src_site["vars"]
    except:
        PB.log_failure(message, True)

    if src_site:
        message= f"Site {site_name}: Deploying settings from src site"
        PB.log_message(message)
        try:
            resp = mistapi.api.v1.sites.setting.updateSiteSettings(
                apisession,
                dst_site_id, src_site
                )
            if resp.status_code != 200:
                PB.log_failure(message, True)
            else:
                PB.log_success(f"Site {site_name}: Cloning settings from src site", True)
        except:
            PB.log_failure(message, True)



###############################################################################
# MATCHING OBJECT NAME / OBJECT ID
###############################################################################
# SPECIFIC TO SITE GROUPS
def _replace_sitegroup_names(
        apisession: mistapi.APISession, org_id: str, sitegroups: dict, sitegroup_names: dict
    ) -> Tuple[dict, str]:
    sitegroup_ids = []
    for sitegroup_name in sitegroup_names:
        if sitegroup_name not in sitegroups:
            response = mistapi.api.v1.orgs.sitegroups.createOrgSiteGroup(
                apisession, org_id, {"name": sitegroup_name})
            if response.status_code == 200:
                sitegroups[sitegroup_name] = response.data["id"]
            else:
                PB.log_warning(
                    f"Unable to create site group {sitegroup_name}", inc=False)
        sitegroup_ids.append(sitegroups[sitegroup_name])
    return sitegroups, sitegroup_ids

# GENERIC REPLACE FUNCTION


def _replace_object_names_by_ids(
        apisession: mistapi.APISession, org_id: str, site: dict, parameters: dict
    ) -> dict:
    '''
    replace the template/policy/groups names by the corresponding ids
    '''
    warning = False
    source_site_id = None
    message = f"Site {site['name']}: updating IDs"
    PB.log_message(message)


    if "site_id" in site:
        source_site_id = site["site_id"]
        del site["site_id"]
    elif "site_name" in site:
        source_site_id = parameters["site"].get(site["site_name"], None)
        if not source_site_id:
            PB.log_warning(f"Site {site['name']}: Source site {site['site_name']} not found")
        del site["site_name"]

    if "sitegroup_names" in site:
        parameters["sitegroup"], site["sitegroup_ids"] = _replace_sitegroup_names(
            apisession, org_id, parameters["sitegroup"], site["sitegroup_names"])
        del site["sitegroup_names"]

    for parameter in PARAMETER_TYPES:
        try:
            if f"{parameter}_name" in site:
                name = site[f"{parameter}_name"]
                site[f"{parameter}_id"] = parameters[parameter][name]
                del site[f"{parameter}_name"]
        except:
            warning = True
            PB.log_warning(
                f"Site {site['name']}: Missing {parameter} on dest org", inc=False)
    if not warning:
        PB.log_success(message, True)
    else:
        PB.log_warning(message, True)
    return site, source_site_id

# GET FROM MIST


def _retrieve_objects(apisession: mistapi.APISession, org_id: str, parameters_in_use:list) -> dict:
    '''
    Get the list of the current templates, policies and sitegoups
    '''
    parameters = {}
    for parameter_type in parameters_in_use:
        message = f"Retrieving {parameter_type} from Mist"
        PB.log_message(message, display_pbar=False)
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
            elif parameter_type == "sitetemplate":
                response = mistapi.api.v1.orgs.sitetemplates.listOrgSiteTemplates(
                    apisession, org_id)
            data = mistapi.get_all(apisession, response)
            for entry in data:
                parameter_values[entry["name"]] = entry["id"]
            parameters[parameter_type] = parameter_values
            PB.log_success(message, display_pbar=False)
        except:
            PB.log_failure(message, display_pbar=False)
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
# - sitetemplate_id or sitetemplate_name
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
    PB.log_title(message, display_pbar=False)
    site_name = []
    parameters_in_use = []
    line = 1
    for site in sites:
        line +=1
        if "name" not in site:
            PB.log_failure(message, display_pbar=False)
            console.error(f"Line {line}: Missing site parameter \"name\"")
            sys.exit(0)
        elif site["name"] in site_name:
            PB.log_failure(message, display_pbar=False)
            console.error(f"Line {line}: Site Name \"{site['name']}\" duplicated")
            sys.exit(0)
        else:
            site_name.append(site["name"])

        if "address" not in site:
            PB.log_failure(message, display_pbar=False)
            console.error(f"Line {line}: Missing site parameter \"address\"")
            sys.exit(0)

        for key in site:
            parameter_name = key.split("_")
            if key in [ "name", "address", "vars", "country_code", "timezone"]:
                pass
            elif key in [ "sitegroup_names", "sitegroup_ids"]:
                if "sitegroup" not in parameters_in_use:
                    parameters_in_use.append("sitegroup")
                pass
            elif parameter_name[0] in PARAMETER_TYPES and parameter_name[1] in ["name", "id"]:
                if not parameter_name[0] in parameters_in_use:
                    parameters_in_use.append(parameter_name[0])
                pass
            else:
                PB.log_failure(message, display_pbar=False)
                console.error(f"Line {line}: Invalid site parameter \"{key}\"")
                sys.exit(0)
    PB.log_success(message, display_pbar=False)
    return parameters_in_use


def _process_sites_data(
        apisession: mistapi.APISession, org_id: str, sites: list
    ) -> dict:
    '''
    Function to validate sites data and retrieve the required object from Mist
    '''
    parameters = {}
    PB.log_title("Preparing Sites Import", display_pbar=False)
    parameters_in_use = _check_settings(sites)
    parameters = _retrieve_objects(apisession, org_id, parameters_in_use)
    return parameters

def _check_sites(apisession:mistapi.APISession, org_id:str, sites:list):
    '''
    function to remove sites already created in the Org (based on the site name)
    '''
    message = "Retrieving Sites from Org"
    PB.log_message(message)
    try:
        res = mistapi.api.v1.orgs.sites.listOrgSites(apisession, org_id, limit=1000)
        sites_from_mist = mistapi.get_all(apisession, res)
        PB.log_success(message, inc=True)
    except:
        PB.log_failure(message, inc=True)
        sys.exit(1)

    sites_to_create = []
    if not sites_from_mist:
        sites_to_create = sites
    else:
        site_already_created = []
        for site in sites:
            try:
                site_exists = list(s for s in sites_from_mist if s.get("name").lower() == site.get("name").lower())
                if site_exists:
                    LOGGER.warning(
                        f"_check_sites:site {site.get('name')} already exists. Won't be created..."
                        )
                    site_already_created.append(site.get("name"))
                else:
                    sites_to_create.append(site)
            except:
                sites_to_create.append(site)

    return sites_to_create


def _create_sites(
        apisession: mistapi.APISession,
        org_id: str,
        sites: list,
        parameters: dict,
        geocoder:callable
    ):
    '''
    Function to create and update all the sites
    '''
    PB.log_title("Creating Sites", display_pbar=True)
    for site in sites:
        site, source_site_id = _replace_object_names_by_ids(
            apisession, org_id, site, parameters)
        new_site = _create_site(apisession, org_id, site, geocoder)
        if not new_site:
            PB.inc()
        else:
            if source_site_id:
                _clone_src_site_settings(
                        apisession, source_site_id, new_site["id"], new_site["name"]
                    )
            else:
                PB.inc()
            _update_site(apisession, site, new_site["id"])


def _read_csv_file(file_path: str):
    with open(file_path, "r") as f:
        data = csv.reader(f, skipinitialspace=True, quotechar='"')
        data = [[c.replace('\ufeff', '') for c in row] for row in data]
        fields = []
        sites = []
        auto_assignment_rules = []
        for line in data:
            if not fields:
                for column in line:
                    fields.append(column.strip().replace("#", ""))
            else:
                site = {}
                i = 0
                subnet = None
                for column in line:

                    field = fields[i]
                    if field == "subnet":
                        subnet = column
                    else:
                        if field.startswith("sitegroup_"):
                            column = _extract_groups(column)
                        site[field] = column
                    i += 1
                if subnet:
                    auto_assignment_rules.append({
                        "src": "subnet",
                        "subnet": subnet,
                        "value": site["name"]
                    })
                sites.append(site)
        return sites, auto_assignment_rules


def _check_org_name_in_script_param(
        apisession: mistapi.APISession, org_id: str, org_name: str = None
    ):
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
            PB.log_message(message, display_pbar=False)
            try:
                PB.log_success(message, display_pbar=False)
            except Exception as e:
                PB.log_failure(message, display_pbar=False)
                LOGGER.error("Exception occurred", exc_info=True)
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
            "Do you want to import into a (n)ew organisation or (e)xisting one, (q) to quit? ")
        if res.lower() == "q":
            sys.exit(0)
        elif res.lower() == "e":
            org_id = mistapi.cli.select_org(apisession)[0]
            org_name = mistapi.api.v1.orgs.orgs.getOrg(
                apisession, org_id).data["name"]
            if _check_org_name(apisession, org_id, org_name):
                return org_id, org_name
        elif res.lower() == "n":
            return _create_org(apisession)


def start(
        apisession: mistapi.APISession,
        file_path: str,
        org_id: str = None,
        org_name: str = None,
        google_api_key:str = None
    ):
    '''
    Start the process to create the sites

    PARAMS
    -------
    :param  mistapi.APISession  apisession      mistapi session with `Super User` access the source 
                                                Org, already logged in
    :param  str                 file_path       path to the CSV file with all the sites to create
    :param  str                 org_id          Optional, org_id of the org where to process the sites
    :param  str                 org_name        Optional, name of the org where to process the sites
                                                (used for validation)
    :param  str                 google_api_key  Optional, Google API key used for geocoding. 
                                                If not set, the script will use timezonefinder and
                                                geopy package to generate the geo information
    '''
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


    message = "Loading Geocoder"
    PB.log_message(message, display_pbar=False)
    try:
        geocoder = None
        if google_api_key:
            geocoder = GoogleGeocoding(google_api_key)
            PB.log_success(f"{message}: Google", display_pbar=False)
        else:
            geocoder = OpenGeocoding()
            PB.log_success(f"{message}: Open", display_pbar=False)
    except:
            PB.log_failure(message, display_pbar=False)
            LOGGER.critical("start: Unable to load the Geocoder")
            LOGGER.critical("Exception occurred", exc_info=True)
            sys.exit(0)

    sites, auto_assignment_rules = _read_csv_file(file_path)
    # 4 = IDs +  geocoding + site creation + clone site settings + site settings update
    addition_steps = 0
    if auto_assignment_rules:
        addition_steps += 3
    PB.set_steps_total(len(sites) * 5 + addition_steps)

    sites = _check_sites(apisession, org_id, sites)
    parameters = _process_sites_data(apisession, org_id, sites)

    _create_sites(apisession, org_id, sites, parameters, geocoder)

    if auto_assignment_rules:
        _update_org_rules(apisession, org_id, auto_assignment_rules)

    PB.log_title("Site Import Done", end=True)


###############################################################################
# USAGE
def usage(error:str=None):
    """
    display script usage
    """
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
- sitetemplate_id or sitetemplate_name
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
- subnet                                    if set, will add this subnet in the
                                            auto assignment rules to automatically 
                                            assign the APs deployed on this subnet
                                            to this site

-------
Script Parameters:
-h, --help              display this help
-f, --file=             REQUIRED: path to the CSV file

-o, --org_id=           Set the org_id (only one of the org_id or site_id can be defined)
-n, --org_name=         Org name where to deploy the configuration:
                        - if org_id is provided (existing org), used to validate 
                        the destination org
                        - if org_id is not provided (new org), the script will 
                        create a new org and name it with the org_name value

-g, --google_api_key=   Google API key used for geocoding
                        If not set, the script will use timezonefinder and geopy
                        package to generate the geo information

-l, --log_file=         define the filepath/filename where to write the logs
                        default is "./script.log"
-e, --env=              define the env file to use (see mistapi env file documentation 
                        here: https://pypi.org/project/mistapi/)
                        default is "~/.mist_env"

-------
Examples:
python3 ./import_sites.py -f ./my_new_sites.csv                 
python3 ./import_sites.py -f ./my_new_sites.csv --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 

''')
    if error:
        console.error(error)
    sys.exit(0)

def check_mistapi_version():
    """
    Function to check the mistapi package version
    """
    if mistapi.__version__ < MISTAPI_MIN_VERSION:
        LOGGER.critical(f"\"mistapi\" package version {MISTAPI_MIN_VERSION} is required, you are currently using version {mistapi.__version__}.")
        LOGGER.critical(f"Please use the pip command to updated it.")
        LOGGER.critical("")
        LOGGER.critical(f"    # Linux/macOS")
        LOGGER.critical(f"    python3 -m pip install --upgrade mistapi")
        LOGGER.critical("")
        LOGGER.critical(f"    # Windows")
        LOGGER.critical(f"    py -m pip install --upgrade mistapi")
        print(f"""
    Critical: 
    \"mistapi\" package version {MISTAPI_MIN_VERSION} is required, you are currently using version {mistapi.__version__}. 
    Please use the pip command to updated it.

    # Linux/macOS
    python3 -m pip install --upgrade mistapi

    # Windows
    py -m pip install --upgrade mistapi
        """)
        sys.exit(2)
    else:
        LOGGER.info(f"\"mistapi\" package version {MISTAPI_MIN_VERSION} is required, you are currently using version {mistapi.__version__}.")


###############################################################################
# ENTRY POINT
if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(sys.argv[1:],
                                    "ho:n:g:f:e:l:", 
                                    [
                                        "help",
                                        "org_id=",
                                        "org_name=",
                                        "google_api_key=",
                                        "file=",
                                        "env=",
                                        "log_file="
                                    ]
                                )
    except getopt.GetoptError as err:
        usage(err)

    CSV_FILE = None
    ORG_ID = None
    ORG_NAME = None
    PARAMS = {}

    for o, a in opts:
        if o in ["-h", "--help"]:
            usage()
        elif o in ["-o", "--org_id"]:
            PARAMS[o]=a
            ORG_ID = a
        elif o in ["-n", "--org_name"]:
            PARAMS[o]=a
            ORG_NAME = a
        elif o in ["-g", "--google_api_key"]:
            PARAMS[o]="*****************"
            GOOGLE_API_KEY = a
        elif o in ["-f", "--file"]:
            PARAMS[o]=a
            CSV_FILE = a
        elif o in ["-e", "--env"]:
            PARAMS[o]=a
            ENV_FILE = a
        elif o in ["-l", "--log_file"]:
            PARAMS[o]=a
            LOG_FILE = a
        else:
            assert False, "unhandled option"

    #### LOGS ####
    logging.basicConfig(filename=LOG_FILE, filemode='w')
    LOGGER.setLevel(logging.DEBUG)
    check_mistapi_version()
    #### LOG SCRIPT PARAMETERS ####
    for param, value in PARAMS.items():
        LOGGER.debug(f"opts: {param} is {value}")
    ### MIST SESSION ###
    apisession = mistapi.APISession(env_file=ENV_FILE)
    apisession.login()

    ### START ###
    if not CSV_FILE:
        console.error("CSV File is missing")
        usage()
    else:
        start(apisession, CSV_FILE, ORG_ID, ORG_NAME, GOOGLE_API_KEY)

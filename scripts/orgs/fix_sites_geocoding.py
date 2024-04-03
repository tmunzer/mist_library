'''
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script check if all the sites have geo information configured (lat/lng,
country_code, timezone), and update the site information when missing.

The script is retrieving the sites from the organization, and checking for each
of them if the lat/lng, country and timezone are set.
If not, it is generating these information with OpenStreetMap (Geopy and
Timezonefinder Python packages or Google Map APIs) and updating the site.
It is saving the result in a csv file (by default fix_sites_geocoding.csv) and
can be run in dry-run mode.


**NOTE**
This Script can use Google APIs (optional) to retrieve lat/lng, tz and country code. 
To be able to use Google API, you need an API Key first. Mode information available 
here: https://developers.google.com/maps/documentation/javascript/get-api-key?hl=en

The required API Key usages are:
- Geocoding API
- Time Zone API

If the Google API Key is not provided, the script will use OpenStreetMap (geopy and
timezonefinder packages) to generate the required information.

-------
Requirements:
mistapi: https://pypi.org/project/mistapi/

-------
Usage:
This script can be run as is (without parameters), or with the options below.
If no options are defined, or if options are missing, the missing options will
be asked by the script or the default values will be used.

It is recomended to use an environment file to store the required information
to request the Mist Cloud (see https://pypi.org/project/mistapi/ for more 
information about the available parameters).

-------
Script Parameters:
-h, --help          display this help
-f, --file=         REQUIRED: path to the CSV file

-o, --org_id=           Set the org_id (only one of the org_id or site_id can be defined)
-n, --org_name=         Org name where to deploy the configuration:
                        - if org_id is provided (existing org), used to validate 
                        the destination org
                        - if org_id is not provided (new org), the script will 
                        create a new org and name it with the org_name value  

-g, --google_api_key=   Google API key used for geocoding
                        If not set, the script will use timezonefinder and geopy
                        package to generate the geo information

-c, --csv_file=         CSV file where to save the result. 
                        default is "./fix_sites_geocoding.csv"
-d, --dry_run=          Do not update the sites but save the result in a CSV file

-l, --log_file=         define the filepath/filename where to write the logs
                        default is "./script.log"
-e, --env=              define the env file to use (see mistapi env file documentation 
                        here: https://pypi.org/project/mistapi/)
                        default is "~/.mist_env"

-------
Examples:
python3 ./fix_sites_geocoding.py 
python3 ./fix_sites_geocoding.py --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 \
                                    --n TM-LAB \
                                    --dry_run

'''

#### IMPORTS #####
import urllib.parse
import time
import sys
import csv
import getopt
import logging
import signal
import types
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
ENV_FILE = "~/.mist_env"
LOG_FILE = "./script.log"
CSV_FILE = "fix_sites_geocoding.csv"
MAX_RETRY = 3
# This Script can use Google APIs (optional) to retrieve lat/lng, tz and country code. To be
# able to use Google API, you need an API Key first. Mode information available here:
# https://developers.google.com/maps/documentation/javascript/get-api-key?hl=en
GOOGLE_API_KEY = ""
#####################################################################
#### LOGS ####
LOGGER = logging.getLogger(__name__)

#####################################################################
#### GLOBALS #####
SYS_EXIT = False

def sigint_handler(signal, frame):
    global SYS_EXIT
    SYS_EXIT = True
    ("[Ctrl C],KeyboardInterrupt exception occured.")

signal.signal(signal.SIGINT, sigint_handler)
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
# Site  Management
#####################################################################
def _get_geo_info(site_name:str, site: dict, geocoder: callable) -> dict:
    message = f"Site {site_name}: Retrievning geo information"
    PB.log_message(message)
    data = geocoder.geocoding(site)
    if data:
        site_data = {
            "address": site["address"],
            "latlng" : {
                "lat": data.get("location", {}).get("latitude"),
                "lng": data.get("location", {}).get("longitude")
            },
            "country_code" : data.get("country_code"),
            "timezone" : data.get("tz"),
        }
        LOGGER.debug(f"_get_geo_info: Data: {site_data}")
        PB.log_success(message, True)
        return site_data
    else:
        PB.log_warning(message, True)
        return False

def _update_site(
    apisession: mistapi.APISession,
    site_id: str,
    site_name:str,
    site_data: dict,
    dry_run
) -> bool:
    message = f"Site {site_name}: Updating Info"
    if dry_run:
        PB.log_message(f"{message} > Dry Run")
        PB.log_success(f"{message} > Dry Run", inc=True)
        return False
    else:
        try:
            resp = mistapi.api.v1.sites.sites.updateSiteInfo(apisession, site_id, site_data)
            if resp.status_code == 200:
                PB.log_success(message, True)
                return True
            else:
                return False
        except:
            LOGGER.error("_update_site: Unable to update the Mist site")
            LOGGER.error("Exception occurred", exc_info=True)
            PB.log_failure(message, True)
            return False


def _process_sites(apisession: mistapi.APISession, sites:dict, geocoder:callable, force:bool, dry_run:bool) -> list:
    csv_data = [
            [
                "#Site name",
                "Site ID",
                "OLD address",
                "OLD latlng",
                "OLD country_code",
                "OLD timezone",
                "NEW address",
                "NEW latlng",
                "NEW country_code",
                "NEW timezone",
                "need_update",
                "updated"
            ]
        ]
    for site in sites:
        if SYS_EXIT:
            sys.exit(0)
        site_id = site.get("id")
        site_name = site.get("name")
        site_data ={
            "address": site.get("address"),
            "latlng" : site.get("latlng"),
            "country_code" : site.get("country_code"),
            "timezone" : site.get("timezone"),
        }
        csv_entry=[
                site_name,
                site_id,
                site_data['address'],
                site_data['latlng'],
                site_data['country_code'],
                site_data['timezone']
            ]
        LOGGER.debug(f"_process_sites: Site {site_name} (id: {site_id}): address: {site_data['address']}, latlnt:{site_data['latlng']}, country_code: {site_data['country_code']}, tz: {site_data['timezone']}")
        message = f"Site {site_name}: Checking Info"
        PB.log_message(message)
        if not site.get('address'):
            PB.log_failure(f"{message} > address missing", inc=True)
            csv_entry += ['', '', '', '', True, False]
            PB.inc()
            PB.inc()
        elif not force and site_data['latlng'] and site_data['country_code'] and site_data['timezone']:
            PB.log_success(f"{message} > info configured", inc=True)
            csv_entry += ['', '', '', '', False, False]
            PB.inc()
            PB.inc()
        else:
            PB.log_warning(f"{message} > need update", inc=True)
            new_site_data = _get_geo_info(site_name, site, geocoder)
            if new_site_data:
                csv_entry += [
                        new_site_data['address'],
                        new_site_data['latlng'],
                        new_site_data['country_code'],
                        new_site_data['timezone'],
                        True
                    ]
                updated = _update_site(apisession, site_id, site_name, new_site_data, dry_run)
                csv_entry.append(updated)
            else:
                csv_entry += ['', '', '', '', True, False]
                PB.inc()
        csv_data.append(csv_entry)
    return csv_data

def _retrieve_sites(apisession:mistapi.APISession, org_id:str) -> dict:
    message = "Retrieving Mist Sites"
    try:
        PB.log_message(message, display_pbar=False)
        resp = mistapi.api.v1.orgs.sites.listOrgSites(apisession, org_id, limit=1000)
        sites = mistapi.get_all(apisession, resp)
        if sites:
            PB.log_success(message, display_pbar=False)
            return sites
        else:
            PB.log_failure(message, display_pbar=False)
            sys.exit(0)
    except:
            PB.log_failure(message, display_pbar=False)
            LOGGER.critical("_retrieve_sites: Unable to retrieve the Mist Sites")
            LOGGER.critical("Exception occurred", exc_info=True)
            sys.exit(0)

def _save_to_csv(csv_file, csv_data) -> None:
    message = f"Saving Result to {csv_file}"
    PB.log_message(message)
    try:
        with open(csv_file, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerows(csv_data)
            PB.log_success(message, inc=True)
    except:
            PB.log_failure(message, inc=True)
            LOGGER.error(f"_save_to_csv: Unable to save result to CSV file {csv_file}")
            LOGGER.error("Exception occurred", exc_info=True)
            sys.exit(0)

###############################################################################
# STARTER FUNCTIONS

def _check_org_name_in_script_param(
    apisession: mistapi.APISession,
    org_id: str,
    org_name: str = None
) -> bool:
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


def _select_dest_org(apisession: mistapi.APISession):
    print()
    print(" Destination Org ".center(80, "-"))
    print()
    while True:
        org_id = mistapi.cli.select_org(apisession)[0]
        org_name = mistapi.api.v1.orgs.orgs.getOrg(
            apisession, org_id).data["name"]
        if _check_org_name(apisession, org_id, org_name):
            return org_id, org_name

def start(apisession: mistapi.APISession, org_id: str = None, org_name: str = None, google_api_key:str = None, csv_file:str=CSV_FILE, force:bool=False, dry_run:bool=False):
    '''
    Start the process to update the sites geo information

    PARAMS
    -------
    :param  mistapi.APISession  apisession      mistapi session with `Super User` access the source 
                                                Org, already logged in
    :param  str                 org_id          Optional, org_id of the org where to process the sites
    :param  str                 org_name        Optional, name of the org where to process the sites
                                                (used for validation)
    :param  str                 google_api_key  Optional, Google API key used for geocoding. 
                                                If not set, the script will use timezonefinder and
                                                geopy package to generate the geo information
    :param  str                 csv_file        Optional, CSV file used to save the result
    :param  bool                force           Default is False. Force the script to generate the
                                                geo information even if alreay configured for the site
    :param  bool                dry_run         Default is False. If True, do not update the sites
                                                but save the result in a CSV file
    
    '''
    if org_id and org_name:
        if not _check_org_name_in_script_param(apisession, org_id, org_name):
            console.critical(
                f"Org name {org_name} does not match the org {org_id}")
            sys.exit(0)
    elif org_id and not org_name:
        org_id, org_name = _check_org_name(apisession, org_id)
    else:
        org_id, org_name = _select_dest_org(apisession)

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

    sites = _retrieve_sites(apisession, org_id)
    # 4 =  check site + geocoding +  site settings update
    PB.set_steps_total(len(sites) * 3 + 1 )
    PB.log_title("Site Processing Started")
    csv_data = _process_sites(apisession, sites, geocoder, force, dry_run)
    _save_to_csv(csv_file, csv_data)
    PB.log_title("Site Processing Done", end=True)


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
Python script check if all the sites have geo information configured (lat/lng,
country_code, timezone), and update the site information when missing.

The script is retrieving the sites from the organization, and checking for each
of them if the lat/lng, country and timezone are set.
If not, it is generating these information with OpenStreetMap (Geopy and
Timezonefinder Python packages or Google Map APIs) and updating the site.
It is saving the result in a csv file (by default fix_sites_geocoding.csv) and
can be run in dry-run mode.


**NOTE**
This Script can use Google APIs (optional) to retrieve lat/lng, tz and country code. 
To be able to use Google API, you need an API Key first. Mode information available 
here: https://developers.google.com/maps/documentation/javascript/get-api-key?hl=en

The required API Key usages are:
- Geocoding API
- Time Zone API

If the Google API Key is not provided, the script will use OpenStreetMap (geopy and
timezonefinder packages) to generate the required information.

-------
Requirements:
mistapi: https://pypi.org/project/mistapi/

-------
Usage:
This script can be run as is (without parameters), or with the options below.
If no options are defined, or if options are missing, the missing options will
be asked by the script or the default values will be used.

It is recomended to use an environment file to store the required information
to request the Mist Cloud (see https://pypi.org/project/mistapi/ for more 
information about the available parameters).

-------
Script Parameters:
-h, --help          display this help
-f, --file=         REQUIRED: path to the CSV file

-o, --org_id=           Set the org_id (only one of the org_id or site_id can be defined)
-n, --org_name=         Org name where to deploy the configuration:
                        - if org_id is provided (existing org), used to validate 
                        the destination org
                        - if org_id is not provided (new org), the script will 
                        create a new org and name it with the org_name value  

-g, --google_api_key=   Google API key used for geocoding
                        If not set, the script will use timezonefinder and geopy
                        package to generate the geo information

-c, --csv_file=         CSV file where to save the result. 
                        default is "./fix_sites_geocoding.csv"
-d, --dry_run=          Do not update the sites but save the result in a CSV file

-l, --log_file=         define the filepath/filename where to write the logs
                        default is "./script.log"
-e, --env=              define the env file to use (see mistapi env file documentation 
                        here: https://pypi.org/project/mistapi/)
                        default is "~/.mist_env"

-------
Examples:
python3 ./fix_sites_geocoding.py 
python3 ./fix_sites_geocoding.py --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 \
                                    --n TM-LAB \
                                    --dry_run

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
        opts, args = getopt.getopt(sys.argv[1:], "ho:n:g:c:dfe:l:", [
                                    "help",
                                    "org_id=",
                                    "org_name=",
                                    "google_api_key=",
                                    "csv_file=",
                                    "dry_run",
                                    "force",
                                    "env=",
                                    "log_file="
                                ])
    except getopt.GetoptError as err:
        usage(err)

    ORG_ID = None
    ORG_NAME = None
    DRY_RUN = False
    FORCE = False

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
            PARAMS[o]="***********"
            GOOGLE_API_KEY = a
        elif o in ["-c", "--csv_file"]:
            PARAMS[o]=a
            CSV_FILE = a
        elif o in ["-d", "--dry_run"]:
            PARAMS[o]=True
            DRY_RUN = True
        elif o in ["-f", "--force"]:
            PARAMS[o]=True
            FORCE = True
        elif o in ["-e", "--env"]:
            PARAMS[o]="************"
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
    start(apisession, ORG_ID, ORG_NAME, GOOGLE_API_KEY, CSV_FILE, FORCE, DRY_RUN)

"""
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script update the Mist AP Auto_upgrade parameters in the site settings

-------
Requirements:
mistapi: https://pypi.org/project/mistapi/

-------
Usage:
This script can be run as is (without parameters), or with the options below.
If no options are defined, or if options are missing, the missing options will
be asked by the script or the default values will be used.

The site(s) to update can selected during the script execution.

It is recomended to use an environment file to store the required information
to request the Mist Cloud (see https://pypi.org/project/mistapi/ for more 
information about the available parameters).

-------
Script Parameters:
-h, --help              display this help

-o, --org_id=           Optional, org_id of the org to clone
-n, --org_name=         Optional, name of the org to clone, for validation 
                        purpose. Requires src_org_id to be defined


-a, --all_sites         Run the script for all the org sites
-s, --site_ids=         Run the script only for the specified site_ids

--enabled               enable Auto Upgrade feature (other parameters will be 
                        required)
--disabled              disable Auto Upgrade feature (no other parameter 
                        required)
--day=                  Set the Auto Upgrade day. Possible values are:
                        "any", "mon", "tue", "wed", "thu", "fri", "sat", "sun"
--time=                 Set the time when the Auto Upgrade process will be 
                        started. 
                        Format must use the 24H format "HH:MM" (e.g., "14:00")
--version=              Set the version to deploy on the APs. Possible values 
                        are: "custom", "stable", "beta"
--custom=               Used if `version`==`custom`
                        Set the custom version to deploy on each AP. Format 
                        must a list of "MODEL:VERSION", commat separated 
                        (e.g., "AP34:0.14.28548,AP45:0.14.28548")

-e, --env=              Optional, env file to use to access the src org (see
                        mistapi env file documentation here: 
                        https://pypi.org/project/mistapi/)
                        default is "~/.mist_env"

-l, --log_file=         define the filepath/filename where to write the logs
                        default is "./script.log"
Examples:
python3 ./config_ap_auto_upgrade.py
python3 ./config_ap_auto_upgrade.py \
        -e ~/.mist_env \
        -o c1a6c819-xxxxx-xxxxx-xxxxx-a93e0afcc6de \
        -n "Demo Org" \
        --enabled --version=stable --day=sun --time=10:00 --all_sites
"""

#### IMPORTS #####
import sys
import logging
import json
import getopt
from functools import cmp_to_key

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


#### PARAMETERS #####
# for more information about the possible settings, please
# see https://doc.mist-lab.fr/#tag/Sites-Setting/operation/updateSiteSettings
#
# auto_upgrade_rule = {
#     "enabled": True,
#     "version": "custom",
#     "time_of_day": "02:00",
#     "custom_versions": {
#         "AP32": "0.10.24028",
#         "AP32E": "0.8.21602"
#     },
#     "day_of_week": "sun"
# }
auto_upgrade_rule = {"enabled": True}

LOG_FILE = "./script.log"
ENV_FILE = "~/.mist_env"

#### LOGS ####
LOGGER = logging.getLogger(__name__)



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
        LOGGER.warning(f"{message}")
        self._pb_new_step(
            message, "\033[93m\u2B58\033[0m\n", inc=inc, display_pbar=display_pbar)

    def log_failure(self, message, inc: bool = False, display_pbar: bool = True):
        LOGGER.error(f"{message}: Failure")
        self._pb_new_step(
            message, '\033[31m\u2716\033[0m\n', inc=inc, display_pbar=display_pbar)

    def log_title(self, message, end: bool = False, display_pbar: bool = True):
        LOGGER.info(message)
        self._pb_title(message, end=end, display_pbar=display_pbar)

PB = ProgressBar()

#####################################################################
# FUNCTIONS
#####################################################################
# SITE SETTINGS
def get_site_setting(mist_session, site_id, auto_upgrade_rule):
    message=f"Site {site_id}: Retrieving current settings"
    PB.log_message(message, display_pbar=True)
    try:
        current_auto_upgrade_rule = mistapi.api.v1.sites.setting.getSiteSetting(
            mist_session, site_id
        ).data.get("auto_upgrade", {})
        PB.log_success(message, inc=True)
        update_site_setting(mist_session, site_id, current_auto_upgrade_rule, auto_upgrade_rule)
    except:
        PB.log_failure(message, inc=True)


def update_site_setting(mist_session, site_id, current_auto_upgrade_rule, auto_upgrade_rule):
    parameters = ["enabled", "version", "time_of_day", "day_of_week", "custom_versions"]
    LOGGER.debug(f"update_site_setting:Current settings for site {site_id}: {current_auto_upgrade_rule}")
    for param in parameters:
        try:
            current_auto_upgrade_rule[param] = auto_upgrade_rule[param]
        except:
            LOGGER.error("update_site_setting: Unable to retrieve the list of Gateway Templates")
            LOGGER.error("Exception occurred", exc_info=True)
            pass
    LOGGER.debug(f"update_site_setting:New settings for site {site_id}: {current_auto_upgrade_rule}")
    message=f"Site {site_id}: Updating settings"
    PB.log_message(message, display_pbar=True)
    try:
        mistapi.api.v1.sites.setting.updateSiteSettings(
            mist_session, site_id, {"auto_upgrade": current_auto_upgrade_rule}
        )
        PB.log_success(message, inc=True)
    except:
        PB.log_failure(message, inc=True)


# INPPUT
def confirm_action(mist_session, site_ids, auto_upgrade_rule):
    while True:
        PB.log_title("New Auto Upgrade Configuration", display_pbar=False)
        print(json.dumps(auto_upgrade_rule, indent=2))
        print("".center(80, "-"))
        print()
        if len(site_ids) == 0:
            console.error("There is not site to update. Exiting...")
            sys.exit(0)
        elif len(site_ids) == 1:
            message = f"Are you sure you want to update the selected site with the configuration above (y/N)?"
        else:
            message = f"Are you sure you want to update the {len(site_ids)} selected sites with the configuration above (y/N)?"
        resp = input(message)
        if resp.lower() == "n" or resp == "":
            sys.exit(0)
        elif resp.lower() == "y":
            print("\n\n\n")
            PB.set_steps_total(len(site_ids) * 2)
            for site_id in site_ids:
                get_site_setting(mist_session, site_id, auto_upgrade_rule)
            break

###############################################################################
# GET AVAILABLE VERSIONS
def _get_ap_models(mist_session: mistapi.APISession, org_id: str, site_ids: list):
    ap_models = []
    try:
        resp = mistapi.api.v1.orgs.inventory.getOrgInventory(
            mist_session, org_id, type="ap", limit=1000
        )
        aps = mistapi.get_all(mist_session, resp)
        if aps:
            for ap in aps:
                if not site_ids or ap.get("site_id") in site_ids:
                    if not ap.get("model") in ap_models:         
                        ap_models.append(ap.get("model"))
        else:
            cont = ""
            while not cont.lower() == "y":
                cont = input(
                    "No APs on the selected sites. Do you want to continue (y/N)? "
                )
                if cont.lower() == "n":
                    sys.exit(0)
                elif cont.lower() != "y":
                    print("Invalid input...")
    except:
        print("Unable to retrieve the list of APs from the Org...")
        sys.exit(1)

    return ap_models


def sort_version(a, b):
    a_splitted = a.split(".")
    b_splitted = b.split(".")
    if int(a_splitted[0]) < int(b_splitted[0]):
        return -1
    elif int(a_splitted[0]) > int(b_splitted[0]):
        return 1
    elif int(a_splitted[1]) < int(b_splitted[1]):
        return -1
    elif int(a_splitted[1]) > int(b_splitted[1]):
        return 1
    elif int(a_splitted[2]) < int(b_splitted[2]):
        return -1
    elif int(a_splitted[2]) > int(b_splitted[2]):
        return 1
    else:
        return 0


def _get_ap_versions(mist_session: mistapi.APISession, site_id: str, ap_models: list):
    ap_versions = {}
    cmp_items_py3 = cmp_to_key(sort_version)
    try:
        resp = mistapi.api.v1.sites.devices.listSiteAvailableDeviceVersions(
            mist_session, site_id
        )
        versions = mistapi.get_all(mist_session, resp)
        for ap_model in ap_models:
            tmp = [ entry["version"] for entry in versions if entry.get("model") == ap_model ]
            tmp.sort(key=cmp_items_py3)
            ap_versions[ap_model] = tmp
        return ap_versions
    except:
        print("Unable to retrieve available versions")

###############################################################################
# MENUS
def _menu_enabled(auto_upgrade_rule:dict):
    PB.log_title(f"Auto Upgrade Activation", display_pbar=False)
    print("0) Disabled")
    print("1) Enabled")
    print()
    while True:
        resp = input(f"Do you want to Enabled or Disabled the Auto Upgrade (0-1)? ")
        if resp == "0":
            auto_upgrade_rule["enabled"] = False
            return auto_upgrade_rule
        elif resp == "1":
            auto_upgrade_rule["enabled"] = True
            return auto_upgrade_rule
        else:
            print(f"Invalid input. Only numbers between 0 and 1 are allowed...")


def _show_menu_version(ap_model: str, ap_versions: dict):
    i = 0
    PB.log_title(f"Available firmwares for {ap_model}", display_pbar=False)
    for version in ap_versions[ap_model]:
        print(f"{i}) {version}")
        i += 1
    while True:
        resp = input(f"Version to deploy (0-{i-1})? ")
        try:
            int_resp = int(resp)
            if int_resp < 0 or int_resp >= i:
                print(f"Invalid input. Only numbers between 0 and {i-1} are allowed...")
            else:
                return ap_versions[ap_model][int_resp]
        except:
            print(f"Invalid input. Only numbers between 0 and {i-1} are allowed...")


def _select_custom_version(
    mist_session: mistapi.APISession, org_id: str, site_ids: list
):
    ap_models = _get_ap_models(mist_session, org_id, site_ids)
    ap_versions = _get_ap_versions(mist_session, site_ids[0], ap_models)
    print(ap_versions)
    selected_firmwares = {}
    for ap_model in ap_models:
        selected_firmwares[ap_model] = _show_menu_version(ap_model, ap_versions)
    return selected_firmwares


def _menu_version(mist_session: mistapi.APISession, org_id: str, site_ids: list, auto_upgrade_rule:dict):
    PB.log_title("Firmware selection", display_pbar=False)
    print("0) Production")
    print("1) RC2")
    print("2) Custom")
    while True:
        print()
        resp = input("Which version to you want to deploy (0-2)? ")
        if resp == "0":
            auto_upgrade_rule["version"] = "stable"
            return auto_upgrade_rule
        elif resp == "1":
            auto_upgrade_rule["version"] = "beta"
            return auto_upgrade_rule
        elif resp == "2":
            auto_upgrade_rule["version"] = "custom"
            auto_upgrade_rule["custom_versions"] = _select_custom_version(
                mist_session, org_id, site_ids
            )
            return auto_upgrade_rule
        else:
            print("Invalid Input. Only numbers between 0 and 2 are allowed...")

def _menu_day(auto_upgrade_rule:dict):
    PB.log_title("Day of Week upgrade selection", display_pbar=False)
    days = ["Daily", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    i = 0
    for day in days:
        print(f"{i}) {day}")
        i+=1
    while True:
        print()
        resp = input("When do you want to deploy the new version (0-7, default: 7)? ")
        if resp == "":
            auto_upgrade_rule["day_of_week"] = "sun"
            return auto_upgrade_rule
        elif resp == "0":
            auto_upgrade_rule["day_of_week"] = "any"
            return auto_upgrade_rule
        elif resp in [ "1", "2", "3", "4", "5", "6", "7"]:
            auto_upgrade_rule["day_of_week"] = days[int(resp)].lower()[:3]
            return auto_upgrade_rule
        else:
            print("Invalid Input. Only numbers between 0 and 7 are allowed...")

def _menu_hours(auto_upgrade_rule:dict):
    while True:
        time_of_day = input("At what hour do you want to update the APs (24H format: \"HH:MM\", default: \"02:00\")? ")
        if time_of_day == "":
            auto_upgrade_rule["time_of_day"] = "02:00"
            return auto_upgrade_rule
        else:
            if _check_hours(time_of_day):
                auto_upgrade_rule["time_of_day"] = time_of_day
                return auto_upgrade_rule
            else:
                print("Invalid input...")

def get_site_ids(mist_session, org_id):
    site_ids = []
    response = mistapi.api.v1.orgs.sites.listOrgSites(mist_session, org_id)
    sites = mistapi.get_all(mist_session, response)
    for site in sites:
        site_ids.append(site["id"])
    return site_ids

###############################################################################
# START CONFIG
def _start_config(mist_session:mistapi.APISession, org_id:str, auto_upgrade_rule:dict, all_sites:bool=None, site_ids:list=None):
    if all_sites:
        site_ids = get_site_ids(mist_session, org_id)
    elif not site_ids:
        while True:
            resp = input(
                "Do you want to update the auto-upgrade settings on all the sites (y/N)? "
            )
            if resp.lower() == "n" or resp == "":
                site_ids = mistapi.cli.select_site(mist_session, org_id, allow_many=True)
                break
            elif resp.lower() == "y":
                site_ids = get_site_ids(mist_session, org_id)
                break

    if auto_upgrade_rule.get("enabled") is None:
        auto_upgrade_rule = _menu_enabled(auto_upgrade_rule)
    if auto_upgrade_rule["enabled"]:
        if auto_upgrade_rule.get("version") is None:
            auto_upgrade_rule = _menu_version(mist_session, org_id, site_ids, auto_upgrade_rule)
        elif auto_upgrade_rule["version"] == "custom" and auto_upgrade_rule.get("custom_versions") is None:
            auto_upgrade_rule["custom_versions"] = _select_custom_version(mist_session, org_id, site_ids)
        if auto_upgrade_rule.get("day_of_week") is None:
            auto_upgrade_rule = _menu_day(auto_upgrade_rule)
        if auto_upgrade_rule.get("time_of_day") is None:
            auto_upgrade_rule = _menu_hours(auto_upgrade_rule)
    LOGGER.debug(f"_start_config: auto_upgrade_rule: {auto_upgrade_rule}")
    confirm_action(mist_session, site_ids, auto_upgrade_rule)

###############################################################################
# CHECK PARAMETERS
def _check_day(day:str):
    if day in ["any", "mon", "tue", "wed", "thu", "fri", "sat", "sun"]:
        LOGGER.info(f"_check_day: day_of_week: {day}")
        return True
    else:
        console.critical("Inavlid Parameters: \"--day\" is only accepting the follwing values: \"any\", \"mon\", \"tue\", \"wed\", \"thu\", \"fri\", \"sat\", \"sun\"")
        return False

def _check_hours(time_of_day: str):
    time_splitted = time_of_day.split(":")
    if len(time_splitted) != 2:
        console.critical("Inavlid Parameters: \"--time\" must use the 24H format \"HH:MM\" (e.g., \"14:00\")")
        return False
    else:
        try:
            hours = int(time_splitted[0])
            minutes = int(time_splitted[1])
            if hours < 0 or hours > 23 or minutes < 0 or minutes > 59:
                console.critical("Inavlid Parameters: \"--time\" must use the 24H format \"HH:MM\" (e.g., \"14:00\")")
                return False
            else:
                LOGGER.info(f"_check_hours: time_of_day: {time_of_day}")
                return True
        except:
            console.critical("Inavlid Parameters: \"--time\" must use the 24H format \"HH:MM\" (e.g., \"14:00\")")
            return False

def _check_version(version:str):
    if version in ["custom", "stable", "beta"]:
        LOGGER.info(f"_check_version: version: {version}")
        return True
    else:
        console.critical("Inavlid Parameters: \"--version\" is only accepting the follwing values: \"custom\", \"stable\", \"beta\"")
        return False

def _check_custom(custom:str):
    custom_versions={}
    entries = custom.split(",")
    if len(entries) > 0:
        for entry in entries:
            model = entry.split(":")[0]
            version = entry.split(":")[1]
            if model and version:
                custom_versions[model]=version
            else:
                console.warning(f"Invalid Parameters: \"--custom\" has an invalid entry: {entry}")
        LOGGER.info(f"_check_custom: custom_versions: {custom_versions}")
        return custom_versions

    console.critical("Inavlid Parameters: \"--custom\" must a list of \"MODEL:VERSION\", commat separated (e.g., \"AP34:0.14.28548,AP45:0.14.28548\")")
    return None

###############################################################################
# ORG SELECTION
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
        org_name = mistapi.api.v1.orgs.orgs.getOrg(
            apisession, org_id).data["name"]
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
    org_id = mistapi.cli.select_org(apisession)[0]
    org_name = mistapi.api.v1.orgs.orgs.getOrg(
        apisession, org_id).data["name"]
    if _check_org_name(apisession, org_id, org_name):
        return org_id, org_name

def start(apisession: mistapi.APISession, org_id: str = None, org_name: str = None, enabled: bool = None, day:str=None, time_of_day:str=None, version:str=None, custom:str=None, all_sites:bool=None, site_ids:list=None):
    if org_id and org_name:
        if not _check_org_name_in_script_param(apisession, org_id, org_name):
            console.critical(
                f"Org name {org_name} does not match the org {org_id}")
            sys.exit(0)
    elif org_id and not org_name:
        org_id, org_name = _check_org_name(apisession, org_id)
    elif not org_id and not org_name:
        org_id, org_name = _select_dest_org(apisession)
    else:
        usage()
        sys.exit(0)

    auto_upgrade_rule = {}
    if enabled != None:
        auto_upgrade_rule["enabled"] = enabled
    if day != None:
        if _check_day(day):
            auto_upgrade_rule["day_of_week"] = day
        else: return False
    if time_of_day != None:
        if _check_hours(time_of_day):
            auto_upgrade_rule["time_of_day"] = time_of_day
        else: return False
    if version != None:
        if _check_version(version):
            auto_upgrade_rule["version"] = version
        else: return False
    if custom != None:
        tmp_custom = _check_custom(custom)
        if tmp_custom:
            auto_upgrade_rule["custom_versions"] = tmp_custom
        else: return False
    LOGGER.debug(f"start: auto_upgrade_rule: {auto_upgrade_rule}")
    _start_config(apisession, org_id, auto_upgrade_rule, all_sites, site_ids)

#####################################################################
#### USAGE ####
def usage():
    print("""
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script update the Mist AP Auto_upgrade parameters in the site settings

-------
Requirements:
mistapi: https://pypi.org/project/mistapi/

-------
Usage:
This script can be run as is (without parameters), or with the options below.
If no options are defined, or if options are missing, the missing options will
be asked by the script or the default values will be used.

The site(s) to update will can selected during the script execution.

It is recomended to use an environment file to store the required information
to request the Mist Cloud (see https://pypi.org/project/mistapi/ for more 
information about the available parameters).

-------
Script Parameters:
-h, --help              display this help

-o, --org_id=           Optional, org_id of the org to clone
-n, --org_name=         Optional, name of the org to clone, for validation 
                        purpose. Requires src_org_id to be defined

-a, --all_sites         Run the script for all the org sites
-s, --site_ids=         Run the script only for the specified site_ids

--enabled               enable Auto Upgrade feature (other parameters will be 
                        required)
--disabled              disable Auto Upgrade feature (no other parameter 
                        required)
--day=                  Set the Auto Upgrade day. Possible values are:
                        "any", "mon", "tue", "wed", "thu", "fri", "sat", "sun"
--time=                 Set the time when the Auto Upgrade process will be 
                        started. 
                        Format must use the 24H format "HH:MM" (e.g., "14:00")
--version=              Set the version to deploy on the APs. Possible values 
                        are: "custom", "stable", "beta"
--custom=               Used if `version`==`custom`
                        Set the custom version to deploy on each AP. Format 
                        must a list of "MODEL:VERSION", commat separated 
                        (e.g., "AP34:0.14.28548,AP45:0.14.28548")

-e, --env=              Optional, env file to use to access the src org (see
                        mistapi env file documentation here: 
                        https://pypi.org/project/mistapi/)
                        default is "~/.mist_env"

-l, --log_file=         define the filepath/filename where to write the logs
                        default is "./script.log"
Examples:
python3 ./config_ap_auto_upgrade.py
python3 ./config_ap_auto_upgrade.py \
        -e ~/.mist_env \
        -o c1a6c819-xxxxx-xxxxx-xxxxx-a93e0afcc6de \
        -n "Demo Org" \
        --enabled --version=stable --day=sun --time=10:00 --all_sites
""")
    sys.exit(0)

def check_mistapi_version():
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

#####################################################################
#### SCRIPT ENTRYPOINT ####
if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(sys.argv[1:], "ho:n:e:l:as:", [
                                   "help", "org_id=", "--org_name=", "env=", "log_file=", "enabled", "disabled", "day=", "time=", "version=", "custom=", "all_sites", "site_ids="])
    except getopt.GetoptError as err:
        console.error(err)
        usage()

    ORG_ID = None
    ORG_NAME = None
    ENABLED = None
    DAY = None
    TIME_OF_DAY = None
    VERSION = None
    CUSTOM = None
    ALL_SITES = False
    SITE_IDS = None
    for o, a in opts:
        if o in ["-h", "--help"]:
            usage()
        elif o in ["-o", "--org_id"]:
            ORG_ID = a
        elif o in ["-n", "--org_name"]:
            ORG_NAME = a
        elif o in ["-e", "--env"]:
            ENV_FILE = a
        elif o in ["-l", "--log_file"]:
            LOG_FILE = a
        elif o == "--enabled":
            if ENABLED is None:
                ENABLED = True
            else:
                console.critical("Inavlid Parameters: \"--enabled\" and \"--disabled\" are exclusive")
                sys.exit(1)
        elif o == "--disabled":
            if ENABLED is None:
                ENABLED = False
            else:
                console.critical("Inavlid Parameters: \"--enabled\" and \"--disabled\" are exclusive")
                sys.exit(1)
        elif o == "--day":
            DAY = a
        elif o == "--time":
            TIME_OF_DAY = a
        elif o == "--version":
            VERSION = a
        elif o == "--custom":
            CUSTOM = a
        elif o in ["-a", "--all_sites"]:
            ALL_SITES = True
        elif o in ["-s", "--site_ids"]:
            SITE_IDS = a.split(",")
        else:
            assert False, "unhandled option"
    

    #### LOGS ####
    logging.basicConfig(filename=LOG_FILE, filemode='w')
    LOGGER.setLevel(logging.DEBUG)
    check_mistapi_version()
    ### MIST SESSION ###
    APISESSION = mistapi.APISession(env_file=ENV_FILE)
    APISESSION.login()

    ### START ###
    start(APISESSION,  ORG_ID, ORG_NAME, ENABLED, DAY, TIME_OF_DAY, VERSION, CUSTOM, ALL_SITES, SITE_IDS)

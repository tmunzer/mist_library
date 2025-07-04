"""
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to backup all the devices from an organization. It will backup the
devices claim codes (if any), configuration (including position on the maps) and 
pictures.
You can use the script "org_inventory_deploy.py" to restore the generated backup 
files to an existing organization or to a new one.

This script will not change/create/delete/touch any existing objects. It will 
just retrieve every single object from the organization.

-------
Requirements:
mistapi: https://pypi.org/project/mistapi/

-------
Usage:
This script can be run as is (without parameters), or with the options below.
If no options are defined, or if options are missing, the missing options will
be asked by the script or the default values will be used.

It is recommended to use an environment file to store the required information
to request the Mist Cloud (see https://pypi.org/project/mistapi/ for more 
information about the available parameters).

-------
Script Parameters:
-h, --help              display this help
-o, --org_id=           Set the org_id
-b, --backup_folder=    Path to the folder where to save the org backup (a 
                        subfolder will be created with the org name)
                        default is "./org_backup"

-d, --datetime          append the current date and time (ISO format) to the
                        backup name 
-t, --timestamp         append the current timestamp to the backup 

-l, --log_file=         define the filepath/filename where to write the logs
                        default is "./script.log"
-e, --env=              define the env file to use (see mistapi env file 
                        documentation here: https://pypi.org/project/mistapi/)
                        default is "~/.mist_env"

-------
Examples:
python3 ./org_inventory_backup.py     
python3 ./org_inventory_backup.py --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 

"""

#### IMPORTS ####
import logging
import sys
import os
import datetime
import json
import argparse
import urllib.request


MISTAPI_MIN_VERSION = "0.44.1"

try:
    import mistapi
    from mistapi.__logger import console
except ImportError:
    print(
        """
        Critical: 
        \"mistapi\" package is missing. Please use the pip command to install it.

        # Linux/macOS
        python3 -m pip install mistapi

        # Windows
        py -m pip install mistapi
        """
    )
    sys.exit(2)

#####################################################################
#### PARAMETERS #####
DEFAULT_BACKUP_FOLDER = "./org_backup"
BACKUP_FILE = "./org_inventory_file.json"
FILE_PREFIX = ".".join(BACKUP_FILE.split(".")[:-1])
LOG_FILE = "./script.log"
ENV_FILE = "~/.mist_env"

#####################################################################
#### LOGS ####
LOGGER = logging.getLogger(__name__)

#####################################################################
# BACKUP OBJECTS REFS
DEVICE_TYPES = ["ap", "switch", "gateway", "mxedge"]


#####################################################################
# PROGRESS BAR AND DISPLAY
class ProgressBar:
    """
    PROGRESS BAR AND DISPLAY
    """

    def __init__(self):
        self.steps_total = 0
        self.steps_count = 0

    def _pb_update(self, size: int = 80):
        if self.steps_count > self.steps_total:
            self.steps_count = self.steps_total

        percent = self.steps_count / self.steps_total
        delta = 17
        x = int((size - delta) * percent)
        print("Progress: ", end="")
        print(f"[{'█' * x}{'.' * (size - delta - x)}]", end="")
        print(f"{int(percent * 100)}%".rjust(5), end="")

    def _pb_new_step(
        self,
        message: str,
        result: str,
        inc: bool = False,
        size: int = 80,
        display_pbar: bool = True,
    ):
        if inc:
            self.steps_count += 1
        text = f"\033[A\033[F{message}"
        print(f"{text} ".ljust(size + 4, "."), result)
        print("".ljust(80))
        if display_pbar:
            self._pb_update(size)

    def _pb_title(
        self, text: str, size: int = 80, end: bool = False, display_pbar: bool = True
    ):
        print("\033[A")
        print(f" {text} ".center(size, "-"), "\n")
        if not end and display_pbar:
            print("".ljust(80))
            self._pb_update(size)

    def set_steps_total(self, steps_total: int) -> None:
        """
        Set the total number of steps for the progress bar.
        :param steps_total: The total number of steps
        """
        self.steps_total = steps_total

    def log_message(self, message, display_pbar: bool = True) -> None:
        """
        Log a message in the progress bar.
        :param message: The message to log
        :param display_pbar: If True, the progress bar will be displayed after the message
        """
        self._pb_new_step(message, " ", display_pbar=display_pbar)

    def log_debug(self, message) -> None:
        """
        Log a debug message.
        :param message: The debug message to log
        """
        LOGGER.debug(message)

    def log_success(
        self, message, inc: bool = False, display_pbar: bool = True
    ) -> None:
        """
        Log a success message in the progress bar.
        :param message: The success message to log
        :param inc: If True, the step count will be incremented
        :param display_pbar: If True, the progress bar will be displayed after the success
        """
        LOGGER.info("%s: Success", message)
        self._pb_new_step(
            message, "\033[92m\u2714\033[0m\n", inc=inc, display_pbar=display_pbar
        )

    def log_warning(
        self, message, inc: bool = False, display_pbar: bool = True
    ) -> None:
        """
        Log a warning message in the progress bar.
        :param message: The warning message to log
        :param inc: If True, the step count will be incremented
        :param display_pbar: If True, the progress bar will be displayed after the warning
        """
        LOGGER.warning(message)
        self._pb_new_step(
            message, "\033[93m\u2b58\033[0m\n", inc=inc, display_pbar=display_pbar
        )

    def log_failure(
        self, message, inc: bool = False, display_pbar: bool = True
    ) -> None:
        """
        Log a failure message in the progress bar.
        :param message: The failure message to log
        :param inc: If True, the step count will be incremented
        :param display_pbar: If True, the progress bar will be displayed after the failure
        """
        LOGGER.error("%s: Failure", message)
        self._pb_new_step(
            message, "\033[31m\u2716\033[0m\n", inc=inc, display_pbar=display_pbar
        )

    def log_title(self, message, end: bool = False, display_pbar: bool = True) -> None:
        """
        Log a title message in the progress bar.
        :param message: The title message to log
        :param end: If True, the progress bar will not be displayed after the title
        :param display_pbar: If True, the progress bar will be displayed after the title
        """
        LOGGER.info(message)
        self._pb_title(message, end=end, display_pbar=display_pbar)


PB = ProgressBar()


#####################################################################
#### SITE FUNCTIONS ####
def _save_site_info(site: dict, backup: dict):
    backup["org"]["sites"][site["name"]] = {
        "id": site["id"],
        "old_maps_ids": {},
        "devices": [],
    }
    backup["org"]["old_sites_id"][site["name"]] = site["id"]


def _backup_site_id_dict(site: dict, backup: dict) -> None:
    if site["name"] in backup["org"]["sites"]:
        console.warning(f"Two sites are using the same name {site['name']}!")
        console.warning(
            "This will cause issue during the backup and the restore process."
        )
        console.warning("I recommend you to rename one of the two sites.")
        loop = True
        while loop:
            resp = input("Do you want to continue anyway (y/N)? ")
            if resp.lower() == "y":
                loop = False
                _save_site_info(site, backup)
            elif resp.lower() == "n" or resp == "":
                loop = False
                sys.exit(200)
    else:
        _save_site_info(site, backup)


def _backup_site_maps(mist_session: mistapi.APISession, site) -> dict:
    response = mistapi.api.v1.sites.maps.listSiteMaps(mist_session, site["id"])
    backup_maps = mistapi.get_all(mist_session, response)
    maps_ids = {}
    for xmap in backup_maps:
        if xmap["name"] in maps_ids:
            console.warning(
                f"Two maps are using the same name {xmap['name']} in the same site {site['name']}!"
            )
            console.warning(
                "This will cause issue during the backup and the restore process."
            )
            console.warning("It is recommended you to rename one of the two maps.")
            loop = True
            while loop:
                resp = input("Do you want to continue anyway (y/N)? ")
                if resp.lower() == "y":
                    loop = False
                    maps_ids[xmap["name"]] = xmap["id"]
                elif resp.lower() == "n" or resp == "":
                    loop = False
                    sys.exit(200)
        else:
            maps_ids[xmap["name"]] = xmap["id"]
    return maps_ids


def _no_magic(backup: dict, site_name: str, device: dict, device_type: str = ""):
    if  device["mac"] not in backup["org"]["magics"]:
        backup["org"]["devices_without_magic"].append(
            {
                "site": site_name,
                "device_type": device.get("type", device_type),
                "model": device.get("model"),
                "name": device.get("name"),
                "mac": device.get("mac"),
                "serial": device.get("serial"),
            }
        )


#####################################################################
#### INVENTORY FUNCTIONS ####
def _backup_inventory(
    mist_session: mistapi.APISession,
    org_id: str,
    org_name: str = "",
    backup: dict|None = None,
) -> None:
    PB.log_title(f"Backing up Org {org_name} Elements ")
    if backup is None:
        backup = {}
    backup["org"]["id"] = org_id
    ################################################
    ##  Backing up inventory
    for device_type in DEVICE_TYPES:
        message = f"Backing up {device_type} magics"
        PB.log_message(message)
        try:
            response = mistapi.api.v1.orgs.inventory.getOrgInventory(
                mist_session, org_id, type=device_type, limit=1000, vc=True
            )
            inventory = mistapi.get_all(mist_session, response)
            for data in inventory:
                if data.get("magic"):
                    backup["org"]["magics"][data["mac"]] = data["magic"]
                    backup["org"]["devices"].append({
                        "mac": data["mac"],
                        "serial": data["serial"],
                        "type": data["type"],
                    })
            PB.log_success(message, True)
        except Exception:
            PB.log_failure(message, True)
            LOGGER.error("Exception occurred", exc_info=True)

    ################################################
    ##  Retrieving org MxEdges

    message = "Backing up Org MxEdges"
    PB.log_message(message)
    try:
        response = mistapi.api.v1.orgs.mxedges.listOrgMxEdges(
            mist_session, org_id, limit=1000
        )
        mxedges = mistapi.get_all(mist_session, response)
        backup["org"]["mxedges"] = mxedges
        PB.log_success(message, True)
    except Exception :
        PB.log_failure(message, True)
        LOGGER.error("Exception occurred", exc_info=True)
    for mxedge in mxedges:
        _no_magic(backup, "Org", mxedge, "mxedge")

    ################################################
    ##  Retrieving device profiles
    message = "Backing up Device Profiles"
    PB.log_message(message)
    deviceprofile:dict
    try:
        response = mistapi.api.v1.orgs.deviceprofiles.listOrgDeviceProfiles(
            mist_session, org_id, limit=1000
        )
        deviceprofiles = mistapi.get_all(mist_session, response)
        for deviceprofile in deviceprofiles:
            backup["org"]["old_deviceprofiles_id"][
                deviceprofile["name"]
            ] = deviceprofile["id"]
        PB.log_success(message, True)
    except Exception:
        PB.log_failure(message, True)
        LOGGER.error("Exception occurred", exc_info=True)
    ################################################
    ##  Retrieving evpn topologies
    message = "Backing up EVPN Topologies"
    PB.log_message(message)
    try:
        response = mistapi.api.v1.orgs.evpn_topologies.listOrgEvpnTopologies(
            mist_session, org_id
        )
        evpn_topologies = mistapi.get_all(mist_session, response)
        for evpn_topology in evpn_topologies:
            backup["org"]["old_evpntopo_id"][deviceprofile["name"]] = evpn_topology[
                "id"
            ]
        PB.log_success(message, True)
    except Exception:
        PB.log_failure(message, True)
        LOGGER.error("Exception occurred", exc_info=True)

    ################################################
    ##  Retrieving Sites list
    message = "Retrieving Sites list"
    PB.log_message(message)
    try:
        response = mistapi.api.v1.orgs.sites.listOrgSites(
            mist_session, org_id, limit=1000
        )
        sites = mistapi.get_all(mist_session, response)
        PB.log_success(message, True)
    except Exception:
        PB.log_failure(message, True)
        LOGGER.error("Exception occurred", exc_info=True)

    ################################################
    ## Backing up Sites Devices
    for site in sites:
        PB.log_title(f"Backing up Site {site['name']}")
        message = "Devices List"
        PB.log_message(message)
        try:
            _backup_site_id_dict(site, backup)
            backup["org"]["sites"][site["name"]]["old_maps_ids"] = _backup_site_maps(
                mist_session, site
            )
            response = mistapi.api.v1.sites.devices.listSiteDevices(
                mist_session, site["id"], type="all", limit=1000
            )
            devices = mistapi.get_all(mist_session, response)
            backup["org"]["sites"][site["name"]]["devices"] = devices
            PB.log_success(message, True)
        except Exception:
            PB.log_failure(message, True)
            LOGGER.error("Exception occurred", exc_info=True)
        ################################################
        ## Backing up Site Devices Images
        for device in devices:
            _no_magic(backup, site["name"], device)
            message = f"Backing up {device['type'].upper()} {device['serial']} images"
            PB.log_message(message)
            try:
                i = 1
                while f"image{i}_url" in device:
                    url = device[f"image{i}_url"]
                    image_name = f"{FILE_PREFIX}_org_{org_id}_device_{device['serial']}_image_{i}.png"
                    urllib.request.urlretrieve(url, image_name)
                    i += 1
                PB.log_success(message, True)
            except Exception:
                PB.log_failure(message, True)
                LOGGER.error("Exception occurred", exc_info=True)

    ################################################
    ## End
    PB.log_title("Backup Done", end=True)
    print()


def _save_to_file(backup_data:dict,backup_file:str,  backup_name:str):
    backup_path = f"./org_backup/{backup_name}/{backup_file.replace('./','')}"
    message = f"Saving to file {backup_path} "
    PB.log_message(message, display_pbar=False)
    try:
        with open(backup_file, "w") as f:
            json.dump(backup_data, f)
        PB.log_success(message, display_pbar=False)
    except Exception:
        PB.log_failure(message, display_pbar=False)
        LOGGER.error("Exception occurred", exc_info=True)


def _start_inventory_backup(
    mist_session: mistapi.APISession,
    org_id: str,
    org_name: str,
    backup_folder:str,
    backup_name:str
):
    # FOLDER
    try:
        if not os.path.exists(backup_folder):
            os.makedirs(backup_folder)
        os.chdir(backup_folder)
        if not os.path.exists(backup_name):
            os.makedirs(backup_name)
        os.chdir(backup_name)
    except Exception as e:
        print(e)
        LOGGER.error("Exception occurred", exc_info=True)
    # PREPARE PROGRESS BAR
    try:
        device_count = 0
        for device_type in DEVICE_TYPES:
            response = mistapi.api.v1.orgs.inventory.getOrgInventory(
                mist_session, org_id, type=device_type, limit=1
            )
            if response.headers and response.headers.get("X-Page-Total"):
                device_count += int(response.headers.get("X-Page-Total", 0))
            else:
                device_count += len(response.data)
        response = mistapi.api.v1.orgs.sites.countOrgSites(
            mist_session, org_id, limit=1
        )
        if response.headers and response.headers.get("X-Page-Total"):
            site_count = int(response.headers.get("X-Page-Total", 0))
        else:
            site_count = len(response.data)
        PB.set_steps_total(2 + len(DEVICE_TYPES) + site_count + device_count)
    except Exception:
        LOGGER.error("Exception occurred", exc_info=True)
        sys.exit(0)

    backup = {
        "org": {
            "id": "",
            "sites": {},
            "old_sites_id": {},
            "old_deviceprofiles_id": {},
            "old_evpntopo_id": {},
            "magics": {},
            "devices": [],
            "devices_without_magic": [],
        }
    }
    _backup_inventory(mist_session, org_id, org_name, backup)
    _save_to_file(backup, BACKUP_FILE, backup_name)
    if backup["org"]["devices_without_magic"]:
        console.warning(
            "It was not possible to retrieve the claim codes for the following devices:"
        )
        mistapi.cli.display_list_of_json_as_table(
            backup["org"]["devices_without_magic"],
            ["site", "device_type", "model", "name", "mac", "serial"],
        )
        print()


def start(
    mist_session: mistapi.APISession,
    org_id: str,
    backup_folder: str = "",
    backup_name:str="",
    backup_name_date:bool=False,
    backup_name_ts:bool=False,
):
    """
    Start the backup process

    PARAMS
    -------
    dst_apisession : mistapi.APISession
        mistapi session with `Super User` access the destination Org, already logged in
    org_id : str
        org_id of the org to backup
    org_name : str
        Org name where to deploy the inventory. This parameter requires "org_id" to be defined
    backup_folder_param : str
        Path to the folder where to save the org backup (a subfolder will be created with the 
        org name). default is "./org_backup"
    backup_name : str
        Name of the subfolder where the the backup files will be saved
        default is the org name
    backup_name_date : bool, default = False
        if `backup_name_date`==`True`, append the current date and time (ISO 
        format) to the backup name 
    backup_name_ts : bool, default = False
        if `backup_name_ts`==`True`, append the current timestamp to the backup 
        name 

    """
    current_folder = os.getcwd()
    if not backup_folder:
        backup_folder = DEFAULT_BACKUP_FOLDER
    if not org_id:
        org_id = mistapi.cli.select_org(mist_session)[0]
    org_name = mistapi.api.v1.orgs.orgs.getOrg(mist_session, org_id).data["name"]

    if not backup_name:
        backup_name = org_name
    if backup_name_date:
        backup_name = f"{backup_name}_{datetime.datetime.isoformat(datetime.datetime.now()).split('.')[0].replace(':','.')}"
    elif backup_name_ts:
        backup_name = f"{backup_name}_{round(datetime.datetime.timestamp(datetime.datetime.now()))}"

    _start_inventory_backup(mist_session, org_id, org_name, backup_folder, backup_name)
    os.chdir(current_folder)


#####################################################################
#### USAGE ####
def usage(error_message:str="") -> None:
    """
    display usage
    """
    print(
        """
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to backup all the devices from an organization. It will backup the
devices claim codes (if any), configuration (including position on the maps) and 
pictures.
You can use the script "org_inventory_deploy.py" to restore the generated backup 
files to an existing organization or to a new one.

This script will not change/create/delete/touch any existing objects. It will 
just retrieve every single object from the organization.

-------
Requirements:
mistapi: https://pypi.org/project/mistapi/

-------
Usage:
This script can be run as is (without parameters), or with the options below.
If no options are defined, or if options are missing, the missing options will
be asked by the script or the default values will be used.

It is recommended to use an environment file to store the required information
to request the Mist Cloud (see https://pypi.org/project/mistapi/ for more 
information about the available parameters).

-------
Script Parameters:
-h, --help              display this help
-o, --org_id=           Set the org_id
-b, --backup_folder=    Path to the folder where to save the org backup (a 
                        subfolder will be created with the org name)
                        default is "./org_backup"

-d, --datetime          append the current date and time (ISO format) to the
                        backup name 
-t, --timestamp         append the current timestamp to the backup 

-l, --log_file=         define the filepath/filename where to write the logs
                        default is "./script.log"
-e, --env=              define the env file to use (see mistapi env file 
                        documentation here: https://pypi.org/project/mistapi/)
                        default is "~/.mist_env"

-------
Examples:
python3 ./org_inventory_backup.py     
python3 ./org_inventory_backup.py --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 

"""
    )
    if error_message:
        console.critical(error_message)
    sys.exit(0)


def check_mistapi_version():
    """Check if the installed mistapi version meets the minimum requirement."""

    current_version = mistapi.__version__.split(".")
    required_version = MISTAPI_MIN_VERSION.split(".")

    try:
        for i, req in enumerate(required_version):
            if current_version[int(i)] > req:
                break
            if current_version[int(i)] < req:
                raise ImportError(
                    f'"mistapi" package version {MISTAPI_MIN_VERSION} is required '
                    f"but version {mistapi.__version__} is installed."
                )
    except ImportError as e:
        LOGGER.critical(str(e))
        LOGGER.critical("Please use the pip command to update it.")
        LOGGER.critical("")
        LOGGER.critical("    # Linux/macOS")
        LOGGER.critical("    python3 -m pip install --upgrade mistapi")
        LOGGER.critical("")
        LOGGER.critical("    # Windows")
        LOGGER.critical("    py -m pip install --upgrade mistapi")
        print(
            f"""
Critical:\r\n
{e}\r\n
Please use the pip command to update it.
# Linux/macOS
python3 -m pip install --upgrade mistapi
# Windows
py -m pip install --upgrade mistapi
            """
        )
        sys.exit(2)
    finally:
        LOGGER.info(
            '"mistapi" package version %s is required, '
            "you are currently using version %s.",
            MISTAPI_MIN_VERSION,
            mistapi.__version__
        )


#####################################################################
#### SCRIPT ENTRYPOINT ####
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backup all devices from an organization")
    parser.add_argument("-o", "--org_id", help="Set the org_id")
    parser.add_argument("-e", "--env", default=ENV_FILE, help="define the env file to use")
    parser.add_argument("-l", "--log_file", default=LOG_FILE, help="define the filepath/filename where to write the logs")
    parser.add_argument("-b", "--backup_folder", default=DEFAULT_BACKUP_FOLDER, 
                       help="Path to the folder where to save the org backup")
    
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-d", "--datetime", action="store_true", 
                      help="append the current date and time (ISO format) to the backup name")
    group.add_argument("-t", "--timestamp", action="store_true",
                      help="append the current timestamp to the backup name")
    
    args = parser.parse_args()

    ORG_ID = args.org_id
    BACKUP_FOLDER = args.backup_folder
    BACKUP_NAME = ""
    BACKUP_NAME_DATE = args.datetime
    BACKUP_NAME_TS = args.timestamp
    ENV_FILE = args.env
    LOG_FILE = args.log_file

    #### LOGS ####
    logging.basicConfig(filename=LOG_FILE, filemode="w")
    LOGGER.setLevel(logging.DEBUG)
    check_mistapi_version()
    ### START ###
    APISESSION = mistapi.APISession(env_file=ENV_FILE)
    APISESSION.login()
    ### START ###
    start(APISESSION, ORG_ID, BACKUP_FOLDER, BACKUP_NAME, BACKUP_NAME_DATE, BACKUP_NAME_TS)

"""
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to deploy organization inventory backup file. By default, this 
script can run in "Dry Run" mode to validate the destination org configuration 
and raise warning if any object from the source org is missing in the 
destination org.

It will not do any changes in the source/destination organizations unless you 
pass the "-p"/"--proceed" parameter.
You can use the script "org_inventory_backup.py" to generate the backup file 
from an existing organization.

This script is trying to maintain objects integrity as much as possible. To do
so, when an object is referencing another object by its ID, the script will 
replace be ID from the original organization by the corresponding ID from the 
destination org.

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
-h, --help              display this help
-o, --org_id=           org_id where to deploy the inventory
-n, --org_name=         org name where to deploy the inventory. This parameter 
                        requires "org_id" to be defined                  
-f, --backup_folder=    Path to the folder where to save the org backup (a 
                        subfolder will be created with the org name)
                        default is "./org_backup"
-b, --source_backup=    Name of the backup/template to deploy. This is the name
                        of the folder where all the backup files are stored.
-s, --sites=            If only selected must be process, list a site names to
                        process, comma separated (e.g. -s "site 1","site 2")

-p, --proceed           By default this script is executed in Dry Run mode. It
                        will validate to destination org configuration, and 
                        check if the required configuration is present, but 
                        it will not change anything in the source/destination
                        organisation. 
                        Use this option to proceed to the changes.
                        WARNING: Proceed to the deployment. This mode will 
                        unclaim the APs from the source org (if -u is set) and
                        deploy them on the destination org. 

-u, --unclaim           if set the script will unclaim the devices from the 
                        source org (only for devices claimed in the source org,
                        not for adopted devices). Unclaim process will only be 
                        simulated if in Dry Run mode.
                        WARNING: this option will only unclaim Mist APs, use 
                        the -a option to also uncail switches and gatewys
-a, --unclaim_all       To be used with the -u option. Allows the script to
                        also migrate switches and gateways from the source
                        org to the destination org (works only for claimed
                        devices, not adopted ones).
                        WARNING: This process may reset and reboot the boxes.
                        Please make sure this will not impact users on site!

-l, --log_file=         define the filepath/filename where to write the logs
                        default is "./script.log"
-e, --env=              define the env file to use (see mistapi env file 
                        documentation here: https://pypi.org/project/mistapi/)
                        default is "~/.mist_env"
--source_env=           when using -u/--unclaim option, allows to define a 
                        different env file to access the Source Organization.
                        default is to use the env file from -e/--env

-------
Examples:
python3 ./org_inventory_deploy.py     
python3 ./org_inventory_deploy.py \
    --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 \
    --org_name="TEST ORG" \
    -p
    

"""
#####################################################################
#### IMPORTS ####
import json
import os
import sys
import re
import logging
import getopt
from typing import Callable

MISTAPI_MIN_VERSION = "0.44.1"

try:
    import mistapi
    from mistapi.__logger import console
except:
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
BACKUP_FOLDER = "./org_backup/"
BACKUP_FILE = "./org_inventory_file.json"
FILE_PREFIX = ".".join(BACKUP_FILE.split(".")[:-1])
LOG_FILE = "./script.log"
SOURCE_ENV_FILE = "~/.mist_env"
DEST_ENV_FILE = None

#####################################################################
#### LOGS ####
LOGGER = logging.getLogger(__name__)


#####################################################################
#### GLOBAL VARS ####

ORG_OBJECT_TO_MATCH = {
    "sites": {
        "mistapi_function": mistapi.api.v1.orgs.sites.listOrgSites,
        "text": "Site IDs",
        "old_ids_dict": "old_sites_id",
    },
    "deviceprofiles": {
        "mistapi_function": mistapi.api.v1.orgs.deviceprofiles.listOrgDeviceProfiles,
        "text": "Device Profile IDs",
        "old_ids_dict": "old_deviceprofiles_id",
    },
    "evpn_topologies": {
        "mistapi_function": mistapi.api.v1.orgs.evpn_topologies.listOrgEvpnTopologies,
        "text": "EVPN Topology IDs",
        "old_ids_dict": "old_evpntopo_id",
    },
}
SITE_OBJECT_TO_MATCH = {
    "maps": {
        "mistapi_function": mistapi.api.v1.sites.maps.listSiteMaps,
        "text": "Map IDs",
        "old_ids_dict": "old_maps_ids",
    },
}


##########################################################################################
# CLASS TO MANAGE UUIDS UPDATES (replace UUIDs from source org to the newly created ones)
class UUIDM:
    """
    CLASS TO MANAGE UUIDS UPDATES (replace UUIDs from source org to the newly created ones)
    """

    def __init__(self):
        self.uuids = {}
        self.old_uuid_names = {}
        self.missing_ids = {}
        self.requests_to_replay = []

    def add_uuid(self, new: str, old: str, name: str):
        if new and old:
            self.uuids[old] = new
            self.old_uuid_names[old] = name

    def get_new_uuid(self, old: str):
        return self.uuids.get(old)

    def add_missing_uuid(self, object_type: str, old_uuid: str, name: str):
        if not object_type in self.missing_ids:
            self.missing_ids[object_type] = {}
        if not old_uuid in self.missing_ids[object_type]:
            self.missing_ids[object_type][old_uuid] = name

    def get_missing_uuids(self):
        data = {}
        for object_type, old_uuids in self.missing_ids.items():
            data[object_type] = []
            for old_uuid in old_uuids:
                data[object_type].append(
                    {
                        "old_uuid": old_uuid,
                        "name": old_uuids[old_uuid],
                    }
                )
        return data

    def add_replay(
        self, mistapi_function: Callable, scope_id: str, object_type: str, data: dict
    ):
        self.requests_to_replay.append(
            {
                "mistapi_function": mistapi_function,
                "scope_id": scope_id,
                "data": data,
                "object_type": object_type,
                "retry": 0,
            }
        )

    def get_replay(self):
        return self.requests_to_replay

    def _uuid_string(self, obj_str: str, missing_uuids: list):
        uuid_re = '"[a-zA_Z_-]*": "[0-9a-f]{8}-[0-9a-f]{4}-[0-5][0-9a-f]{3}-[089ab][0-9a-f]{3}-[0-9a-f]{12}"'
        uuids_to_replace = re.findall(uuid_re, obj_str)
        if uuids_to_replace:
            for uuid in uuids_to_replace:
                uuid_key = uuid.replace('"', "").split(":")[0].strip()
                uuid_val = uuid.replace('"', "").split(":")[1].strip()
                if self.get_new_uuid(uuid_val):
                    obj_str = obj_str.replace(uuid_val, self.get_new_uuid(uuid_val))
                elif uuid_key not in [
                    "issuer",
                    "idp_sso_url",
                    "custom_logout_url",
                    "sso_issuer",
                    "sso_idp_sso_url",
                    "ibeacon_uuid",
                ]:
                    missing_uuids.append({uuid_key: uuid_val})
        return obj_str, missing_uuids

    def _uuid_list(self, obj_str: str, missing_uuids: list):
        uuid_list_re = r"(\"[a-zA_Z_-]*\": \[\"[0-9a-f]{8}-[0-9a-f]{4}-[0-5][0-9a-f]{3}-[089ab][0-9a-f]{3}-[0-9a-f]{12}\"[^\]]*)]"
        uuid_lists_to_replace = re.findall(uuid_list_re, obj_str)
        if uuid_lists_to_replace:
            for uuid_list in uuid_lists_to_replace:
                uuid_key = uuid_list.replace('"', "").split(":")[0].strip()
                uuids = (
                    uuid_list.replace('"', "")
                    .replace("[", "")
                    .replace("]", "")
                    .split(":")[1]
                    .split(",")
                )
                for uuid in uuids:
                    uuid_val = uuid.strip()
                    if self.get_new_uuid(uuid_val):
                        obj_str = obj_str.replace(uuid_val, self.get_new_uuid(uuid_val))
                    else:
                        missing_uuids.append({uuid_key: uuid_val})
        return obj_str, missing_uuids

    def find_and_replace(self, obj: dict, object_type: str):
        # REMOVE READONLY FIELDS
        ids_to_remove = []

        for id_name in ids_to_remove:
            if id_name in obj:
                del obj[id_name]

        # REPLACE REMAINING IDS
        obj_str = json.dumps(obj)
        obj_str, missing_uuids = self._uuid_string(obj_str, [])
        obj_str, missing_uuids = self._uuid_list(obj_str, missing_uuids)
        obj = json.loads(obj_str)

        return obj, missing_uuids


uuid_matching = UUIDM()


##########################################################################################
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
        print(f"Progress: ", end="")
        print(f"[{'█'*x}{'.'*(size-delta-x)}]", end="")
        print(f"{int(percent*100)}%".rjust(5), end="")

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

    def set_steps_total(self, steps_total: int):
        self.steps_total = steps_total

    def log_message(self, message, display_pbar: bool = True):
        self._pb_new_step(message, " ", display_pbar=display_pbar)

    def log_success(self, message, inc: bool = False, display_pbar: bool = True):
        LOGGER.info(f"{message}: Success")
        self._pb_new_step(
            message, "\033[92m\u2714\033[0m\n", inc=inc, display_pbar=display_pbar
        )

    def log_warning(self, message, inc: bool = False, display_pbar: bool = True):
        LOGGER.warning(f"{message}")
        self._pb_new_step(
            message, "\033[93m\u2B58\033[0m\n", inc=inc, display_pbar=display_pbar
        )

    def log_failure(self, message, inc: bool = False, display_pbar: bool = True):
        LOGGER.error(f"{message}: Failure")
        self._pb_new_step(
            message, "\033[31m\u2716\033[0m\n", inc=inc, display_pbar=display_pbar
        )

    def log_title(self, message, end: bool = False, display_pbar: bool = True):
        LOGGER.info(message)
        self._pb_title(message, end=end, display_pbar=display_pbar)


PB = ProgressBar()


##########################################################################################
##########################################################################################
# DEPLOY FUNCTIONS
##########################################################################################
## UNCLAIM/CLAIM FUNCTIONS
def _unclaim_devices(
    src_apisession: mistapi.APISession,
    src_org_id: str,
    devices: list,
    magics: dict,
    failed_devices: dict,
    proceed: bool = False,
    unclaim_all: bool = False,
):
    LOGGER.debug("inventory_deploy:_unclaim_devices")
    serials = []
    macs = []
    serial_to_mac = {}
    for device in devices:
        if device.get("mac") in magics:
            if device.get("type") == "ap" or unclaim_all:
                serials.append(device["serial"])
                macs.append(device["mac"])
                serial_to_mac[device["serial"]] = device["mac"]
    if serials:
        try:
            message = f"Unclaiming {len(serials)} devices from source Org"
            PB.log_message(message)
            if not proceed:
                PB.log_success(message, inc=True)
            else:
                response = mistapi.api.v1.orgs.inventory.updateOrgInventoryAssignment(
                    src_apisession, src_org_id, {"op": "delete", "serials": serials}
                )
                if response.data.get("error"):
                    PB.log_warning(message, inc=True)
                    i = 0
                    for failed_serial in response.data["error"]:
                        mac = serial_to_mac[failed_serial]
                        message = f"Unable to claim device {mac}: {response.data['reason'][i]}"
                        failed_devices[
                            mac
                        ] = f"Unable to unclaim device {mac}: {response.data['reason'][i]}"
                        i += 1
                elif response.status_code == 200:
                    PB.log_success(message, inc=True)
                else:
                    PB.log_failure(message, inc=True)
                    for device in devices:
                        if (
                            device.get("mac") in magics
                            and device.get("serial") not in failed_devices
                        ):
                            failed_devices[device["mac"]] = "Unable to claim the device"
        except:
            PB.log_failure(message, inc=True)
            LOGGER.error("Exception occurred", exc_info=True)


def _claim_devices(
    dst_apisession: mistapi.APISession,
    dst_org_id: str,
    devices: list,
    magics: dict,
    failed_devices: dict,
    proceed: bool = False,
    unclaim_all: bool = False,
):
    LOGGER.debug("inventory_deploy:_claim_devices")
    magics_to_claim = []
    magic_to_mac = {}
    for device in devices:
        if device.get("mac") in magics and device.get("mac") not in failed_devices:
            if device.get("type") == "ap" or unclaim_all:
                magics_to_claim.append(magics[device["mac"]])
                magic_to_mac[magics[device["mac"]]] = device["mac"]

    if not magics_to_claim:
        PB.log_success("No device to claim", inc=True)
        return
    else:
        try:
            message = f"Claiming {len(magics_to_claim)} devices"
            PB.log_message(message)
            if not proceed:
                PB.log_success(message, inc=True)
            else:
                response = mistapi.api.v1.orgs.inventory.addOrgInventory(
                    dst_apisession, dst_org_id, magics_to_claim
                )
                if response.data.get("error"):
                    PB.log_warning(message, inc=True)
                    i = 0
                    for failed_magic in response.data["error"]:
                        mac = magic_to_mac[failed_magic]
                        message = f"Unable to claim device {mac}: {response.data['reason'][i]}"
                        failed_devices[mac] = f"Unable to claim device {mac}: {response.data['reason'][i]}"
                        i += 1
                elif response.status_code == 200:
                    PB.log_success(message, inc=True)
                else:
                    PB.log_failure(message, inc=True)
                    for device in devices:
                        if (
                            device.get("mac") in magics
                            and device.get("serial") not in failed_devices
                        ):
                            failed_devices[device["mac"]] = "Unable to claim the device"
        except:
            PB.log_failure(message, inc=True)
            LOGGER.error("Exception occurred", exc_info=True)


def _assign_device_to_site(
    dst_apisession: mistapi.APISession,
    dst_org_id: str,
    dst_site_id: str,
    site_name: str,
    devices: list,
    failed_devices: dict,
    proceed: bool = False,
    unclaim_all: bool = False,
):
    LOGGER.debug("inventory_deploy:_assign_device_to_site")
    macs_to_assign = []
    for device in devices:
        if device.get("mac") and device["mac"] not in failed_devices:
            if device.get("type") == "ap" or unclaim_all:
                macs_to_assign.append(device["mac"])

    if not macs_to_assign:
        PB.log_success("No device to assign", inc=True)
        return
    else:
        if len(macs_to_assign) == 1:
            message = f"Assigning {len(macs_to_assign)} device to the Site"
        else:
            message = f"Assigning {len(macs_to_assign)} devices to the Site"

        try:
            PB.log_message(message)
            if not proceed:
                PB.log_success(message, inc=True)
            else:
                response = mistapi.api.v1.orgs.inventory.updateOrgInventoryAssignment(
                    dst_apisession,
                    dst_org_id,
                    {"macs": macs_to_assign, "site_id": dst_site_id, "op": "assign"},
                )
                if response.data.get("error"):
                    PB.log_warning(message, inc=True)
                    i = 0
                    for failed_mac in response.data["error"]:
                        message = f"Unable to assign device {failed_mac} to site {site_name}: {response.data['reason'][i]}"
                        failed_devices[failed_mac] = f"Unable to assign device {failed_mac} to site {site_name}: {response.data['reason'][i]}"
                        i += 1
                elif response.status_code == 200:
                    PB.log_success(message, inc=True)
                else:
                    PB.log_failure(message, inc=True)
                    for mac in macs_to_assign:
                        if mac and mac not in failed_devices:
                            failed_devices[mac] = f"Unable to assign the device to site {site_name}"
        except:
            PB.log_failure(message, inc=True)
            LOGGER.error("Exception occurred", exc_info=True)


##########################################################################################
## DEVICE RESTORE
def _update_device_configuration(
    dst_apisession: mistapi.APISession,
    dst_site_id: str,
    device: dict,
    devices_type: str = "device",
    proceed: bool = False,
):
    LOGGER.debug("inventory_deploy:_update_device_configuration")
    issue_config = False
    try:
        message = f"{device.get('type', devices_type).title()} {device.get('mac')} (S/N: {device.get('serial')}): Restoring Configuration"
        PB.log_message(message)
        data, missing_uuids = uuid_matching.find_and_replace(device, "device")
        if proceed:
            response = mistapi.api.v1.sites.devices.updateSiteDevice(
                dst_apisession, dst_site_id, device["id"], data
            )
            if response.status_code != 200:
                raise Exception
        PB.log_success(message, inc=True)
    except Exception as e:
        PB.log_failure(message, True)
        LOGGER.error("Exception occurred", exc_info=True)
        issue_config = True
    return issue_config


def _restore_device_images(
    dst_apisession: mistapi.APISession,
    src_org_id: str,
    dst_site_id: str,
    device: dict,
    devices_type: str = "device",
    proceed: bool = False,
):
    LOGGER.debug("inventory_deploy:_restore_device_images")
    i = 1
    image_exists = True
    issue_image = False
    while image_exists:
        image_name = (
            f"{FILE_PREFIX}_org_{src_org_id}_device_{device['serial']}_image_{i}.png"
        )
        if os.path.isfile(image_name):
            try:
                message = f"{device.get('type', devices_type).title()} {device.get('mac')} (S/N: {device.get('serial')}): Restoring Image #{i}"
                PB.log_message(message)
                if proceed:
                    response = mistapi.api.v1.sites.devices.addSiteDeviceImageFile(
                        dst_apisession, dst_site_id, device["id"], i, image_name
                    )
                    if response.status_code != 200:
                        raise Exception
                PB.log_success(message, inc=False)
            except:
                issue_image = True
                PB.log_failure(message, inc=False)
                LOGGER.error("Exception occurred", exc_info=True)
            i += 1
        else:
            image_exists = False
    return issue_image


def _restore_devices(
    src_apisession: mistapi.APISession,
    dst_apisession: mistapi.APISession,
    src_org_id: str,
    dst_org_id: str,
    dst_site_id: str,
    site_name: str,
    devices: dict,
    magics: list,
    processed_macs: list,
    failed_devices: dict,
    proceed: bool = False,
    unclaim: bool = False,
    unclaim_all: bool = False,
):
    LOGGER.debug("inventory_deploy:_restore_devices")
    if unclaim:
        _unclaim_devices(src_apisession, src_org_id, devices, magics, failed_devices, proceed, unclaim_all)
    _claim_devices(dst_apisession, dst_org_id, devices, magics, failed_devices, proceed, unclaim_all)
    _assign_device_to_site(dst_apisession, dst_org_id, dst_site_id, site_name, devices, failed_devices, proceed, unclaim_all)
    for device in devices:
        processed_macs.append(device["mac"])
        if device["mac"] not in failed_devices:
            if device.get("type") == "ap" or unclaim_all:
                issue_config = _update_device_configuration(dst_apisession, dst_site_id, device, device.get("type"), proceed)
                issue_image = _restore_device_images(dst_apisession, src_org_id, dst_site_id, device, device.get("type"), proceed)

                if issue_config:
                    failed_devices[device["mac"]] = f"Error when uploading device configuration (site {site_name})"
                if issue_image:
                    failed_devices[device["mac"]] = f"Error when uploading device image (site {site_name})"

def _restore_unassigned_devices(
    src_apisession: mistapi.APISession,
    dst_apisession: mistapi.APISession,
    src_org_id: str,
    dst_org_id: str,
    processed_macs: dict,
    magics: list,
    devices: dict,
    failed_devices: dict,
    proceed: bool = False,
    unclaim: bool = False,
    unclaim_all: bool = False,
):
    LOGGER.debug("inventory_deploy:_restore_unassigned_devices")
    devices_not_assigned = []

    for device in devices:
        if not device["mac"] in processed_macs:
            LOGGER.debug(f"inventory_deploy:_restore_unassigned_devices:new unassigned device found {device['mac']}")
            devices_not_assigned.append(device)
    LOGGER.debug(f"inventory_deploy:_restore_unassigned_devices:list of unassigned device found {devices_not_assigned}")
    if unclaim:
        _unclaim_devices(src_apisession, src_org_id, devices_not_assigned, magics, failed_devices, proceed, unclaim_all)
    _claim_devices(dst_apisession, dst_org_id, devices_not_assigned, magics, failed_devices, proceed, unclaim_all)


##########################################################################################
### IDs Matching
def _process_ids(
    dst_apisession: mistapi.APISession,
    step: dict,
    scope_id: str,
    old_ids: dict,
    message: str,
):
    LOGGER.debug("inventory_deploy:_process_ids")
    message = f"Loading {step['text']}"
    try:
        PB.log_message(message)
        response = step["mistapi_function"](dst_apisession, scope_id)
        data = mistapi.get_all(dst_apisession, response)
        for entry in data:
            if entry.get("name") in old_ids:
                uuid_matching.add_uuid(
                    entry.get("id"), old_ids[entry.get("name")], entry.get("name")
                )
        match_all = True
        for old_id_name in old_ids:
            if not uuid_matching.get_new_uuid(old_ids[old_id_name]):
                uuid_matching.add_missing_uuid(
                    step["text"], old_ids[old_id_name], old_id_name
                )
                match_all = False
        if match_all:
            PB.log_success(message, True)
        else:
            PB.log_warning(message, True)
    except:
        PB.log_failure(message, True)
        LOGGER.error("Exception occurred", exc_info=True)


def _process_org_ids(
    dst_apisession: mistapi.APISession, dst_org_id: str, org_backup: dict
):
    LOGGER.debug("inventory_deploy:_process_org_ids")
    for org_step_name, org_step_data in ORG_OBJECT_TO_MATCH.items():
        old_ids_dict = org_backup[org_step_data["old_ids_dict"]]
        _process_ids(
            dst_apisession,
            org_step_data,
            dst_org_id,
            old_ids_dict,
            "Checking Org Ids",
        )


def _process_site_ids(
    dst_apisession: mistapi.APISession,
    new_site_id: str,
    site_name: str,
    site_data: dict,
):
    LOGGER.debug("inventory_deploy:_process_site_ids")
    for site_step_name, site_step_data in SITE_OBJECT_TO_MATCH.items():
        old_ids_dict = site_data[site_step_data["old_ids_dict"]]
        _process_ids(
            dst_apisession,
            site_step_data,
            new_site_id,
            old_ids_dict,
            f"Checking Site {site_name} IDs",
        )


##########################################################################################
#### CORE FUNCTIONS ####
def _result(failed_devices: dict, proceed: bool) -> bool:
    LOGGER.debug("inventory_deploy:_result")
    PB.log_title("Result", end=True)
    missing_ids = uuid_matching.get_missing_uuids()
    if not proceed:
        console.warning("This script has been executed in Dry Run mode.")
        console.warning(
            "No modification have been done on the Source/Destination orgs."
        )
        console.warning('Use the "-p" / "--proceed" option to execute the changes.')
        print()
    if missing_ids:
        for object_type, ids in missing_ids.items():
            console.warning(
                f"Unable to find the following {object_type} in the Destination Org:"
            )
            print()
            mistapi.cli.display_list_of_json_as_table(
                ids, ["name", "old_uuid"]
            )
            print("")
    if failed_devices:
        console.warning(
            f"There was {len(failed_devices)} device error(s) during the process:"
        )
        for serial in failed_devices:
            print(f"{serial}: {failed_devices[serial]}")
    if not missing_ids and not failed_devices:
        console.info("Pre check validation succed!")
        console.info("No object missing, you can restore the devices")
        print("")
        return True
    return False


def _deploy(
    src_apisession: mistapi.APISession,
    dst_apisession: mistapi.APISession,
    src_org_id: str,
    dst_org_id: str,
    org_backup: dict,
    filter_site_names: list = [],
    proceed: bool = False,
    unclaim: bool = False,
    unclaim_all: bool = False,
) -> bool:
    LOGGER.debug("inventory_deploy:_deploy")
    print()
    PB.log_title("Processing Org")
    uuid_matching.add_uuid(dst_org_id, src_org_id, "Source Org ID")
    _process_org_ids(dst_apisession, dst_org_id, org_backup)

    failed_devices = {}
    processed_macs = []

    for restore_site_name in org_backup["sites"]:
        if not filter_site_names or restore_site_name in filter_site_names:
            PB.log_title(f"Processing Site {restore_site_name}")
            site = org_backup["sites"][restore_site_name]
            dst_site_id = uuid_matching.get_new_uuid(site["id"])

            if not dst_site_id:
                uuid_matching.add_missing_uuid("site", site["id"], restore_site_name)
            else:
                _process_site_ids(dst_apisession, dst_site_id, restore_site_name, site)
                _restore_devices(
                    src_apisession,
                    dst_apisession,
                    src_org_id,
                    dst_org_id,
                    dst_site_id,
                    restore_site_name,
                    site["devices"],
                    org_backup["magics"],
                    processed_macs,
                    failed_devices,
                    proceed,
                    unclaim,
                    unclaim_all,
                )
    if not filter_site_names:
        _restore_unassigned_devices(
            src_apisession,
            dst_apisession,
            src_org_id,
            dst_org_id,
            processed_macs,
            org_backup["magics"],
            org_backup["devices"],
            failed_devices,
            proceed,
            unclaim,
            unclaim_all,
        )
    return _result(failed_devices, proceed)


def _check_access(apisession: mistapi.APISession, org_id: str, message: str) -> bool:
    LOGGER.debug("inventory_deploy:_check_access")
    PB.log_message(message, display_pbar=False)
    try:
        response = mistapi.api.v1.self.self.getSelf(apisession)
        if response.status_code == 200:
            privileges = response.data.get("privileges", [])
            for p in privileges:
                if p.get("scope") == "org" and p.get("org_id") == org_id:
                    if p.get("role") == "admin":
                        PB.log_success(message, display_pbar=False)
                        return True
                    else:
                        PB.log_failure(message, display_pbar=False)
                        console.error(
                            "You don't have full access to this org. Please use another account"
                        )
                        return False
    except:
        PB.log_failure(message, display_pbar=False)
        console.critical("Unable to retrieve privileges from Mist Cloud")
        LOGGER.error("Exception occurred", exc_info=True)

    PB.log_failure(message, display_pbar=False)
    console.error("You don't have access to this org. Please use another account")
    return False


def _start_deploy(
    src_apisession: mistapi.APISession,
    dst_apisession: mistapi.APISession,
    dst_org_id: str,
    backup_folder_param: str,
    source_backup: str = None,
    src_org_name: str = None,
    filter_site_names: list = [],
    proceed: bool = False,
    unclaim: bool = False,
    unclaim_all: bool = False,
) -> bool:
    LOGGER.debug("inventory_deploy:_start_deploy")
    _go_to_backup_folder(backup_folder_param, src_org_name, source_backup)
    print()
    try:
        message = f"Loading inventory file {BACKUP_FILE} "
        PB.log_message(message, display_pbar=False)
        with open(BACKUP_FILE) as f:
            backup = json.load(f)
        PB.log_success(message, display_pbar=False)
    except:
        PB.log_failure(message, display_pbar=False)
        console.critical("Unable to load the inventory file")
        LOGGER.error("Exception occurred", exc_info=True)
        sys.exit(1)

    try:
        message = f"Analyzing template/backup file {BACKUP_FILE} "
        PB.log_message(message, display_pbar=False)
        src_org_id = backup["org"]["id"]
        steps_total = 2
        sites_len = len(backup["org"]["sites"])
        devices_len = 0
        for site_name in backup["org"]["sites"]:
            devices_len += len(backup["org"]["sites"][site_name])
        steps_total += sites_len * 2 + devices_len * 2
        PB.set_steps_total(steps_total)
        PB.log_success(message, display_pbar=False)
        console.info(f"The process will test the deployment of {steps_total} devices")
    except:
        PB.log_failure(message, display_pbar=False)
        console.critical("Unable to parse the template/backup file")
        LOGGER.error("Exception occurred", exc_info=True)
        sys.exit(1)

    if backup:
        if _check_access(
            dst_apisession, dst_org_id, "Validating access to the Destination Org"
        ):
            if (
                unclaim
                and _check_access(
                    src_apisession, src_org_id, "Validating access to the Source Org"
                )
            ) or not unclaim:
                return _deploy(
                    src_apisession,
                    dst_apisession,
                    src_org_id,
                    dst_org_id,
                    backup["org"],
                    filter_site_names,
                    proceed,
                    unclaim,
                    unclaim_all,
                )


#####################################################################
#### FOLDER MGMT ####
def _chdir(path: str):
    try:
        os.chdir(path)
        return True
    except FileNotFoundError:
        console.error(f"Folder path {path} does not exists")
        return False
    except NotADirectoryError:
        console.error(f"Folder path {path} is not a directory")
        return False
    except PermissionError:
        console.error(f"You don't have the rights to access the directory {path}")
        return False
    except Exception as e:
        console.error(f"An error occured : {e}")
        LOGGER.error("Exception occurred", exc_info=True)
        return False


def _select_backup_folder(folders):
    i = 0
    print("Available Templates/Backups:")
    while i < len(folders):
        print(f"{i}) {folders[i]}")
        i += 1
    folder = None
    while folder is None:
        resp = input(
            f"Which template/backup do you want to deploy (0-{i - 1}, or q to quit)? "
        )
        if resp.lower() == "q":
            console.error("Interruption... Exiting...")
            LOGGER.error("Interruption... Exiting...")
            sys.exit(0)
        try:
            respi = int(resp)
            if respi >= 0 and respi <= i:
                folder = folders[respi]
            else:
                print(f'The entry value "{respi}" is not valid. Please try again...')
        except:
            print("Only numbers are allowed. Please try again...")
    _chdir(folder)


def _go_to_backup_folder(
    backup_folder_param: str, src_org_name: str = None, source_backup: str = None
):
    print()
    print(" Source Backup/Template ".center(80, "-"))
    print()
    _chdir(backup_folder_param)
    folders = []
    for entry in os.listdir("./"):
        if os.path.isdir(os.path.join("./", entry)):
            folders.append(entry)
    folders = sorted(folders, key=str.casefold)
    if source_backup in folders and _chdir(source_backup):
        print(f"Template/Backup {source_backup} found. It will be automatically used.")
    elif src_org_name in folders:
        print(f"Template/Backup found for organization {src_org_name}.")
        loop = True
        while loop:
            resp = input("Do you want to use this template/backup (y/N)? ")
            if resp.lower() in ["y", "n", " "]:
                loop = False
                if resp.lower() == "y" and _chdir(src_org_name):
                    pass
                else:
                    _select_backup_folder(folders)
    else:
        print(
            f"No Template/Backup found for organization {src_org_name}. Please select a folder in the following list."
        )
        _select_backup_folder(folders)


#####################################################################
#### DEST ORG SELECTION ####
def _check_org_name_in_script_param(
    apisession: mistapi.APISession, dst_org_id: str, org_name: str = None
):
    response = mistapi.api.v1.orgs.orgs.getOrg(apisession, dst_org_id)
    if response.status_code != 200:
        console.critical(f"Unable to retrieve the org information: {response.data}")
        sys.exit(0)
    org_name_from_mist = response.data["name"]
    return org_name == org_name_from_mist


def _check_org_name(
    apisession: mistapi.APISession, dst_org_id: str, org_name: str = None
):
    if not org_name:
        org_name = mistapi.api.v1.orgs.orgs.getOrg(apisession, dst_org_id).data["name"]
    while True:
        print()
        resp = input(
            "To avoid any error, please confirm the current destination orgnization name: "
        )
        if resp == org_name:
            return dst_org_id, org_name
        else:
            print()
            print("The orgnization names do not match... Please try again...")


def _select_dest_org(apisession: mistapi.APISession):
    print()
    print(" Destination Org ".center(80, "-"))
    print()
    while True:
        dst_org_id = mistapi.cli.select_org(apisession)[0]
        org_name = mistapi.api.v1.orgs.orgs.getOrg(apisession, dst_org_id).data["name"]
        if _check_org_name(apisession, dst_org_id, org_name):
            return dst_org_id, org_name


#####################################################################
#### START ####
def start(
    dst_apisession: mistapi.APISession,
    src_apisession: mistapi.APISession = None,
    dst_org_id: str = None,
    dst_org_name: str = None,
    backup_folder_param: str = None,
    src_org_name: str = None,
    source_backup: str = None,
    filter_site_names: list = [],
    proceed: bool = False,
    unclaim: bool = False,
    unclaim_all: bool = False,
) -> bool:
    """
    Start the process to check if the inventory can be deployed without issue

    PARAMS
    -------
    dst_apisession : mistapi.APISession
        mistapi session with `Super User` access the destination Org, already logged in
    src_apisession : mistapi.APISession
        Only required if `unclaim`==`True`. mistapi session with `Super User` access the source Org,
        already logged in
    dst_org_id : str
        org_id where to deploy the inventory
    dst_org_name : str
        Org name where to deploy the inventory. This parameter requires "org_id" to be defined
    backup_folder_param : str
        Path to the folder where to save the org backup (a subfolder will be created with the org
        name).
        default is "./org_backup"
    src_org_name : str
        Name of the backup/template to deploy. This is the name of the folder where all the backup
        files are stored. If the backup is found, the script will ask for a confirmation to use it
    source_backup : str
        Name of the backup/template to deploy. This is the name of the folder where all the backup
        files are stored. If the backup is found, the script will NOT ask for a confirmation to use
        it
    filter_site_names : str
        If only selected must be process, list a site names to process
    proceed : bool
        By default, the script is executed in Dry Run mode (used to validate the destination org
        configuration). Set this parameter to True to disable the Dry Run mode and proceed to the
        deployment
    unclaim : bool
        If `unclaim`==`True`, the script will unclaim the devices from the source org. Unclaim
        process will only be simulated if in Dry Run mode. WARNING: this option will only unclaim
        Mist APs, set `unclaim_all` to True to also uncail switches and gatewys
    unclaim_all : bool
        If `unclaim_all`==`True`, the script will also migrate switches and gateways from the source
        org to the destination org (works only for claimed devices, not adopted ones). WARNING: This
        process may reset and reboot the boxes. Please make sure this will not impact users on site!

    RETURNS:
    -------
    bool
        Process success or not. If the process raised any warning/error (e.g. missing objects in the
        dest org), it will return False.
    """
    if not backup_folder_param:
        backup_folder_param = BACKUP_FOLDER

    current_folder = os.getcwd()

    if dst_org_id and dst_org_name:
        if not _check_org_name_in_script_param(
            dst_apisession, dst_org_id, dst_org_name
        ):
            console.critical(
                f"Org name {dst_org_name} does not match the org {dst_org_id}"
            )
            sys.exit(0)
    elif dst_org_id and not dst_org_name:
        dst_org_id, dst_org_name = _check_org_name(dst_apisession, dst_org_id)
    elif not dst_org_id and not dst_org_name:
        dst_org_id, dst_org_name = _select_dest_org(dst_apisession)
    elif not dst_org_id and dst_org_name:
        console.error(
            '"dst_org_name" required "dst_org_id" to be defined. You can either remove the '
            '"dst_org_name" parameter, or add the "dst_org_id" parameter.'
        )
        sys.exit(2)
    else:  # should not since we covered all the possibilities...
        sys.exit(0)

    success = _start_deploy(
        src_apisession,
        dst_apisession,
        dst_org_id,
        backup_folder_param=backup_folder_param,
        source_backup=source_backup,
        src_org_name=src_org_name,
        filter_site_names=filter_site_names,
        proceed=proceed,
        unclaim=unclaim,
        unclaim_all=unclaim_all,
    )
    os.chdir(current_folder)
    return success


#####################################################################
#### USAGE ####
def usage():
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
Python script to deploy organization inventory backup file. By default, this 
script runs in "Dry Run" mode to validate the destination org configuration and
raise warning if any object from the source org is missing in the destination 
org.
It will not do any changes in the source/destination organizations unless you 
pass the "-p"/"--proceed" parameter.
You can use the script "org_inventory_backup.py" to generate the backup file 
from an existing organization.

This script is trying to maintain objects integrity as much as possible. To do
so, when an object is referencing another object by its ID, the script will 
replace be ID from the original organization by the corresponding ID from the 
destination org.

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
-h, --help              display this help
-o, --org_id=           org_id where to deploy the inventory
-n, --org_name=         org name where to deploy the inventory. This parameter 
                        requires "org_id" to be defined                  
-f, --backup_folder=    Path to the folder where to save the org backup (a 
                        subfolder will be created with the org name)
                        default is "./org_backup"
-b, --source_backup=    Name of the backup/template to deploy. This is the name
                        of the folder where all the backup files are stored.
-s, --sites=            If only selected must be process, list a site names to
                        process, comma separated (e.g. -s "site 1","site 2")

-p, --proceed           By default this script is executed in Dry Run mode. It
                        will validate to destination org configuration, and 
                        check if the required configuration is present, but 
                        it will not change anything in the source/destination
                        organisation. 
                        Use this option to proceed to the changes.
                        WARNING: Proceed to the deployment. This mode will 
                        unclaim the APs from the source org (if -u is set) and
                        deploy them on the destination org. 

-u, --unclaim           if set the script will unclaim the devices from the 
                        source org (only for devices claimed in the source org,
                        not for adopted devices). Unclaim process will only be 
                        simulated if in Dry Run mode.
                        WARNING: this option will only unclaim Mist APs, use 
                        the -a option to also uncail switches and gatewys
-a, --unclaim_all       To be used with the -u option. Allows the script to
                        also migrate switches and gateways from the source
                        org to the destination org (works only for claimed
                        devices, not adopted ones).
                        WARNING: This process may reset and reboot the boxes.
                        Please make sure this will not impact users on site!

-l, --log_file=         define the filepath/filename where to write the logs
                        default is "./script.log"
-e, --env=              define the env file to use (see mistapi env file 
                        documentation here: https://pypi.org/project/mistapi/)
                        default is "~/.mist_env"
--source_env=           when using -u/--unclaim option, allows to define a 
                        different env file to access the Source Organization.
                        default is to use the env file from -e/--env

-------
Examples:
python3 ./org_inventory_deploy.py     
python3 ./org_inventory_deploy.py \
    --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 \
    --org_name="TEST ORG" \
    -p

"""
    )
    sys.exit(0)


def check_mistapi_version():
    """
    check mistapi package version
    """
    if mistapi.__version__ < MISTAPI_MIN_VERSION:
        LOGGER.critical(
            f'"mistapi" package version {MISTAPI_MIN_VERSION} is required, you are currently using version {mistapi.__version__}.'
        )
        LOGGER.critical(f"Please use the pip command to updated it.")
        LOGGER.critical("")
        LOGGER.critical(f"    # Linux/macOS")
        LOGGER.critical(f"    python3 -m pip install --upgrade mistapi")
        LOGGER.critical("")
        LOGGER.critical(f"    # Windows")
        LOGGER.critical(f"    py -m pip install --upgrade mistapi")
        print(
            f"""
    Critical: 
    \"mistapi\" package version {MISTAPI_MIN_VERSION} is required, you are currently using version {mistapi.__version__}. 
    Please use the pip command to updated it.

    # Linux/macOS
    python3 -m pip install --upgrade mistapi

    # Windows
    py -m pip install --upgrade mistapi
        """
        )
        sys.exit(2)
    else:
        LOGGER.info(
            f'"mistapi" package version {MISTAPI_MIN_VERSION} is required, '
            f"you are currently using version {mistapi.__version__}."
        )


#####################################################################
#### SCRIPT ENTRYPOINT ####
if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(
            sys.argv[1:],
            "ho:n:e:s:l:f:b:pua",
            [
                "help",
                "org_id=",
                "org_name=",
                "env=",
                "source_env=",
                "log_file=",
                "backup_folder=",
                "source_backup=",
                "sites=",
                "proceed",
                "unclaim",
                "unclaim_all",
            ],
        )
    except getopt.GetoptError as err:
        console.error(err)
        usage()

    DST_ORG_ID = None
    ORG_NAME = None
    BACKUP_FOLDER_PARAM = None
    FILTER_SITE_NAMES = []
    SOURCE_BACKUP = None
    PROCEED = False
    UNCLAIM = False
    UNCLAIM_ALL = False
    for o, a in opts:
        if o in ["-a", "--unclaim_all"]:
            UNCLAIM_ALL = True
        elif o in ["-b", "--source_backup"]:
            SOURCE_BACKUP = a
        elif o in ["-e", "--env"]:
            DEST_ENV_FILE = a
        elif o in ["-f", "--backup_folder"]:
            BACKUP_FOLDER_PARAM = a
        elif o in ["-h", "--help"]:
            usage()
            sys.exit(0)
        elif o in ["-l", "--log_file"]:
            LOG_FILE = a
        elif o in ["-n", "--org_name"]:
            ORG_NAME = a
        elif o in ["-o", "--org_id"]:
            DST_ORG_ID = a
        elif o in ["-p", "--proceed"]:
            PROCEED = True
        elif o in ["-u", "--unclaim"]:
            UNCLAIM = True
        elif o in ["--source_env"]:
            SOURCE_ENV_FILE = a
        elif o in ["-s", "--sites"]:
            try:
                tmp = a.split(",")
                for site_name in tmp:
                    FILTER_SITE_NAMES.append(site_name.strip())
            except:
                console.error(
                    'Unable to process the "sites" parameter. Please check it\'s value.'
                )
                sys.exit(3)
        elif o in ["-u", "--unclaim"]:
            UNCLAIM = True
        else:
            assert False, "unhandled option"

    #### LOGS ####
    logging.basicConfig(filename=LOG_FILE, filemode="w")
    LOGGER.setLevel(logging.DEBUG)
    check_mistapi_version()
    ### START ###
    if UNCLAIM:
        print(" API Session to access the Source Org ".center(80, "_"))
        SRC_APISESSION = mistapi.APISession(env_file=SOURCE_ENV_FILE)
        SRC_APISESSION.login()
    else:
        SRC_APISESSION = None
    print(" API Session to access the Destination Org ".center(80, "_"))
    DST_APISESSION = mistapi.APISession(env_file=DEST_ENV_FILE)
    DST_APISESSION.login()

    start(
        DST_APISESSION,
        SRC_APISESSION,
        dst_org_id=DST_ORG_ID,
        dst_org_name=ORG_NAME,
        backup_folder_param=BACKUP_FOLDER_PARAM,
        source_backup=SOURCE_BACKUP,
        filter_site_names=FILTER_SITE_NAMES,
        proceed=PROCEED,
        unclaim=UNCLAIM,
        unclaim_all=UNCLAIM_ALL,
    )

'''
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

-d, --dry               Dry Run mode. Will only simulate the process. Used to 
                        validate the destination org configuration. This mode 
                        will not send any requests to Mist and will not change
                        the Source/Dest Organisations.
                        Cannot be used with -p
-p, --proceed           WARNING: Proceed to the deployment. This mode will 
                        unclaim the APs from the source org (if -u is set) and
                        deploy them on the destination org. 
                        Cannot be used with -d

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

-------
Examples:
python3 ./org_inventory_deploy.py     
python3 ./org_inventory_deploy.py --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 -n "my test org" --dry

'''

#### PARAMETERS #####
session_file = None
org_id = ""

#### IMPORTS ####
import json
import os
import sys
import re
import logging
import getopt
from typing import Callable
try:
    import mistapi
    from mistapi.__api_response import APIResponse
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
backup_folder = "./org_backup"
backup_file = "./org_inventory_file.json"
file_prefix = ".".join(backup_file.split(".")[:-1])
log_file = "./script.log"
dest_env_file = "~/.mist_env"
source_env_file = None

#####################################################################
#### LOGS ####
logger = logging.getLogger(__name__)


#####################################################################
#### GLOBAL VARS ####

org_object_to_match = {
    "sites": {"mistapi_function": mistapi.api.v1.orgs.sites.getOrgSites, "text": "Site IDs", "old_ids_dict":"old_sites_id"},
    "deviceprofiles": {"mistapi_function": mistapi.api.v1.orgs.deviceprofiles.getOrgDeviceProfiles, "text": "Device Profile IDs", "old_ids_dict":"old_deviceprofiles_id"},
    "evpn_topologies": {"mistapi_function": mistapi.api.v1.orgs.evpn_topologies.getOrgEvpnTopologies, "text": "EVPN Topology IDs", "old_ids_dict":"old_evpntopo_id"},
}
site_object_to_match = {
    "maps": {"mistapi_function": mistapi.api.v1.sites.maps.getSiteMaps, "text": "Map IDs", "old_ids_dict":"old_maps_ids"},
}
##########################################################################################
# CLASS TO MANAGE UUIDS UPDATES (replace UUIDs from source org to the newly created ones)
class UUIDM():

    def __init__(self):
        self.uuids = {}
        self.old_uuid_names = {}
        self.missing_ids = {}
        self.requests_to_replay = []
    
    def add_uuid(self, new:str, old:str, name:str):
        if new and old: 
            self.uuids[old] = new
            self.old_uuid_names[old] = name 

    def get_new_uuid(self, old:str):
        return self.uuids.get(old)

    def add_missing_uuid(self, object_type:str, old_uuid:str, name:str):
        if not object_type in self.missing_ids:
            self.missing_ids[object_type] = {}
        if not old_uuid in self.missing_ids[object_type]:            
            self.missing_ids[object_type][old_uuid] = name

    def get_missing_uuids(self):
        data = {}
        for object_type in self.missing_ids:
            data[object_type] = []
            for old_uuid in self.missing_ids[object_type]:
                data[object_type].append({"old_uuid": old_uuid, "name": self.missing_ids[object_type][old_uuid]})
        return data

    def add_replay(self,mistapi_function:Callable, scope_id: str, object_type: str, data: dict):
        self.requests_to_replay.append({"mistapi_function": mistapi_function, "scope_id": scope_id, "data": data, "object_type": object_type, "retry": 0})

    def get_replay(self):
        return self.requests_to_replay

    def _uuid_string(self, obj_str:str, missing_uuids:list):
        uuid_re = "\"[a-zA_Z_-]*\": \"[0-9a-f]{8}-[0-9a-f]{4}-[0-5][0-9a-f]{3}-[089ab][0-9a-f]{3}-[0-9a-f]{12}\""
        uuids_to_replace = re.findall(uuid_re, obj_str)
        if uuids_to_replace:
            for uuid in uuids_to_replace:
                uuid_key = uuid.replace('"',"").split(":")[0].strip()
                uuid_val = uuid.replace('"',"").split(":")[1].strip()
                if self.get_new_uuid(uuid_val):
                    obj_str = obj_str.replace(uuid_val, self.get_new_uuid(uuid_val))
                elif uuid_key not in ["issuer", "idp_sso_url", "custom_logout_url", "sso_issuer", "sso_idp_sso_url", "ibeacon_uuid"]:
                    missing_uuids.append({uuid_key: uuid_val})
        return obj_str, missing_uuids

    def _uuid_list(self, obj_str:str, missing_uuids:list):
        uuid_list_re = "(\"[a-zA_Z_-]*\": \[\"[0-9a-f]{8}-[0-9a-f]{4}-[0-5][0-9a-f]{3}-[089ab][0-9a-f]{3}-[0-9a-f]{12}\"[^\]]*)]"
        uuid_lists_to_replace = re.findall(uuid_list_re, obj_str)
        if uuid_lists_to_replace:
            for uuid_list in uuid_lists_to_replace:
                uuid_key = uuid_list.replace('"',"").split(":")[0].strip()
                uuids = uuid_list.replace('"', "").replace('[',"").replace(']',"").split(":")[1].split(",")
                for uuid in uuids:
                    uuid_val = uuid.strip()
                    if self.get_new_uuid(uuid_val):
                        obj_str = obj_str.replace(uuid_val, self.get_new_uuid(uuid_val))
                    else:
                        missing_uuids.append({uuid_key: uuid_val})
        return obj_str, missing_uuids


    def find_and_replace(self, obj:dict, object_type:str):
        # REMOVE READONLY FIELDS 
        ids_to_remove = [ ]

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
class ProgressBar():
    def __init__(self):        
        self.steps_total = 0
        self.steps_count = 0

    def _pb_update(self, size:int=80):   
        if self.steps_count > self.steps_total: 
            self.steps_count = self.steps_total

        percent = self.steps_count/self.steps_total
        delta = 17
        x = int((size-delta)*percent)
        print(f"Progress: ", end="")
        print(f"[{'█'*x}{'.'*(size-delta-x)}]", end="")
        print(f"{int(percent*100)}%".rjust(5), end="")

    def _pb_new_step(self, message:str, result:str, inc:bool=False, size:int=80, display_pbar:bool=True):
        if inc: self.steps_count += 1
        text = f"\033[A\033[F{message}"
        print(f"{text} ".ljust(size + 4, "."), result)
        print("".ljust(80))
        if display_pbar: self._pb_update(size)

    def _pb_title(self, text:str, size:int=80, end:bool=False, display_pbar:bool=True):
        print("\033[A")
        print(f" {text} ".center(size, "-"),"\n")
        if not end and display_pbar: 
            print("".ljust(80))
            self._pb_update(size)

    def set_steps_total(self, steps_total:int):
        self.steps_total = steps_total

    def log_message(self, message, display_pbar:bool=True):
        self._pb_new_step(message, " ", display_pbar=display_pbar)

    def log_success(self, message, inc:bool=False, display_pbar:bool=True):
        logger.info(f"{message}: Success")
        self._pb_new_step(message, "\033[92m\u2714\033[0m\n", inc=inc, display_pbar=display_pbar)

    def log_warning(self, message, inc:bool=False, display_pbar:bool=True):
        logger.warning(f"{message}")
        self._pb_new_step(message, "\033[93m\u2B58\033[0m\n", inc=inc, display_pbar=display_pbar)

    def log_failure(self, message, inc:bool=False, display_pbar:bool=True):
        logger.error(f"{message}: Failure")
        self._pb_new_step(message, '\033[31m\u2716\033[0m\n', inc=inc, display_pbar=display_pbar)

    def log_title(self, message, end:bool=False, display_pbar:bool=True):
        logger.info(message)
        self._pb_title(message, end=end, display_pbar=display_pbar)

pb = ProgressBar()
##########################################################################################
##########################################################################################
# DEPLOY FUNCTIONS
##########################################################################################
## UNCLAIM/CLAIM FUNCTIONS
def _unclaim_devices(src_apisession:mistapi.APISession, src_org_id:str, devices:list, magics:dict, failed_devices:dict, proceed:bool=False, unclaim_all:bool=False):
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
            message=f"Unclaiming {len(serials)} devices from source Org"
            pb.log_message(message)
            if not proceed:
                    pb.log_success(message, inc=True)
            else:
                response = mistapi.api.v1.orgs.inventory.updateOrgInventoryAssignment(src_apisession, src_org_id, {"op":"delete", "serials": serials})
                if response.data.get("error"):
                    pb.log_warning(message, inc=True)
                    i = 0
                    for failed_serial in response.data["error"]:
                        mac = serial_to_mac[failed_serial]
                        message = f"Unable to claim device {mac}: {response.data['reason'][i]}"                        
                        failed_devices[mac] = f"Unable to unclaim device {mac}: {response.data['reason'][i]}"
                        i+=1
                elif response.status_code == 200:
                    pb.log_success(message, inc=True)
                else:
                    pb.log_failure(message, inc=True)
                    for device in devices:
                        if device.get("mac") in magics and device.get("serial") not in failed_devices:
                            failed_devices[device['mac']] = "Unable to claim the device"
        except:
            pb.log_failure(message, inc=True)
            logger.error("Exception occurred", exc_info=True)

def _claim_devices(dst_apisession:mistapi.APISession, dst_org_id:str, devices:list, magics:dict, failed_devices:dict, proceed:bool=False, unclaim_all:bool=False):
    magics_to_claim = []
    magic_to_mac = {}
    for device in devices:
        if device.get("mac") in magics and device.get("mac") not in failed_devices:
            if device.get("type") == "ap" or unclaim_all:
                magics_to_claim.append(magics[device["mac"]])
                magic_to_mac[magics[device["mac"]]] = device["mac"]

    if not magics_to_claim:
        pb.log_success("No device to claim", inc=True)
        return
    else:
        try:
            message = f"Claiming {len(magics_to_claim)} devices"
            pb.log_message(message)
            if not proceed:
                    pb.log_success(message, inc=True)
            else:
                response = mistapi.api.v1.orgs.inventory.addOrgInventory(dst_apisession, dst_org_id, magics_to_claim)
                if response.data.get("error"):
                    pb.log_warning(message, inc=True)
                    i = 0
                    for failed_magic in response.data["error"]:
                        mac = magic_to_mac[failed_magic]
                        message = f"Unable to claim device {mac}: {response.data['reason'][i]}"                        
                        failed_devices[mac] = f"Unable to claim device {mac}: {response.data['reason'][i]}"
                        i+=1
                elif response.status_code == 200:
                    pb.log_success(message, inc=True)
                else:
                    pb.log_failure(message, inc=True)
                    for device in devices:
                        if device.get("mac") in magics and device.get("serial") not in failed_devices:
                            failed_devices[device['mac']] = "Unable to claim the device"
        except:
            pb.log_failure(message, inc=True)
            logger.error("Exception occurred", exc_info=True)

def _assign_device_to_site(dst_apisession:mistapi.APISession, dst_org_id:str, dst_site_id:str, site_name:str, devices:list,failed_devices:dict, proceed:bool=False, unclaim_all:bool=False):
    macs_to_assign = []
    for device in devices:
        if device.get("mac") and device["mac"] not in failed_devices:
            if device.get("type") == "ap" or unclaim_all:
                macs_to_assign.append(device["mac"])

    if not macs_to_assign:
        pb.log_success("No device to assign", inc=True)
        return 
    else:
        if len(macs_to_assign) == 1:
            message = f"Assigning {len(macs_to_assign)} device to the Site"
        else:
            message = f"Assigning {len(macs_to_assign)} devices to the Site"

        try:
            pb.log_message(message)
            if not proceed:
                    pb.log_success(message, inc=True)
            else:
                response = mistapi.api.v1.orgs.inventory.updateOrgInventoryAssignment(
                    dst_apisession, 
                    dst_org_id, 
                    {"macs": macs_to_assign, "site_id": dst_site_id, "op":"assign"}
                )
                if response.data.get("error"):
                    pb.log_warning(message, inc=True)
                    i = 0
                    for failed_mac in response.data["error"]:
                        message = f"Unable to assign device {failed_mac} to site {site_name}: {response.data['reason'][i]}"                        
                        failed_devices[failed_mac] = f"Unable to assign device {failed_mac} to site {site_name}: {response.data['reason'][i]}"
                        i+=1
                elif response.status_code == 200:
                    pb.log_success(message, inc=True)
                else:
                    pb.log_failure(message, inc=True)   
                    for mac in macs_to_assign:
                        if mac and mac not in failed_devices:
                            failed_devices[mac] = f"Unable to assign the device to site {site_name}"
        except:
            pb.log_failure(message, inc=True)   
            logger.error("Exception occurred", exc_info=True)      

##########################################################################################
## DEVICE RESTORE
def _update_device_configuration(dst_apisession:mistapi.APISession, dst_site_id:str,  device:dict, devices_type:str="device", proceed:bool=False):
    issue_config = False
    try:
        message = f"{device.get('type', devices_type).title()} {device.get('mac')} (S/N: {device.get('serial')}): Restoring Configuration"
        pb.log_message(message)
        data, missing_uuids = uuid_matching.find_and_replace(device, "device")
        if proceed:
            response = mistapi.api.v1.sites.devices.updateSiteDevice(dst_apisession, dst_site_id, device["id"], data)
            if response.status_code != 200:
                raise Exception
        pb.log_success(message, inc=True)
    except Exception as e:
        pb.log_failure(message, True)
        logger.error("Exception occurred", exc_info=True)
        issue_config = True
    return issue_config

def _restore_device_images(dst_apisession:mistapi.APISession, src_org_id:str, dst_site_id:str, device:dict, devices_type:str="device", proceed:bool=False):
        i=1
        image_exists = True
        issue_image = False
        while image_exists:
                image_name = f"{file_prefix}_org_{src_org_id}_device_{device['serial']}_image_{i}.png"
                if os.path.isfile(image_name):
                    try:
                        message = f"{device.get('type', devices_type).title()} {device.get('mac')} (S/N: {device.get('serial')}): Restoring Image #{i}"
                        pb.log_message(message)
                        if proceed:
                            response = mistapi.api.v1.sites.devices.addSiteDeviceImageFile(dst_apisession, dst_site_id, device["id"], i, image_name)
                            if response.status_code != 200:
                                raise Exception
                        pb.log_success(message, inc=False)
                    except:
                        issue_image = True
                        pb.log_failure(message, inc=False)
                        logger.error("Exception occurred", exc_info=True)
                    i+=1
                else:
                    image_exists = False
        return issue_image

def _restore_devices(src_apisession:mistapi.APISession, dst_apisession:mistapi.APISession, src_org_id:str, dst_org_id:str, dst_site_id:str, site_name:str, devices:dict, magics:list, failed_devices:dict, proceed:bool=False, unclaim:bool=False, unclaim_all:bool=False):
    if unclaim: _unclaim_devices(src_apisession, src_org_id, devices, magics, failed_devices, proceed, unclaim_all)  
    _claim_devices(dst_apisession, dst_org_id, devices, magics, failed_devices, proceed, unclaim_all)
    _assign_device_to_site(dst_apisession, dst_org_id, dst_site_id, site_name, devices, failed_devices, proceed, unclaim_all)
    for device in devices:
        if device["mac"] not in failed_devices:
            if device.get("type") == "ap" or unclaim_all:
                issue_config = _update_device_configuration(dst_apisession, dst_site_id, device, device.get("type"), proceed)
                issue_image = _restore_device_images(dst_apisession, src_org_id, dst_site_id, device, device.get("type"), proceed)

                if issue_config: failed_devices[device["mac"]] = f"Error when uploading device configuration (site {site_name})"
                if issue_image: failed_devices[device["mac"]] = f"Error when uploading device image (site {site_name})"    


##########################################################################################
### IDs Matching
def _process_ids(dst_apisession: mistapi.APISession, step:dict, scope_id:str, old_ids:dict, message:str):
    message = f"Loading {step['text']}"
    try:
        pb.log_message(message)
        response = step["mistapi_function"](dst_apisession, scope_id)
        data = mistapi.get_all(dst_apisession, response)
        for entry in data:
            if entry.get("name") in old_ids:
                uuid_matching.add_uuid(entry.get("id"), old_ids[entry.get("name")], entry.get("name"))
        match_all = True
        for old_id_name in old_ids:
            if not uuid_matching.get_new_uuid(old_ids[old_id_name]):
                uuid_matching.add_missing_uuid(step["text"], old_ids[old_id_name], old_id_name)
                match_all = False
        if match_all:
            pb.log_success(message, True)
        else: 
            pb.log_warning(message, True)
    except:
        pb.log_failure(message, True)
        logger.error("Exception occurred", exc_info=True)

def _process_org_ids(dst_apisession:mistapi.APISession,dest_org_id:str, org_backup:dict):
    for org_step in org_object_to_match:        
        old_ids_dict = org_backup[org_object_to_match[org_step]["old_ids_dict"]]
        _process_ids(dst_apisession, org_object_to_match[org_step], dest_org_id, old_ids_dict, "Checking Org Ids")

def _process_site_ids(dst_apisession:mistapi.APISession, new_site_id:str, site_name:str, site_data:dict):
    for site_step in site_object_to_match:        
        old_ids_dict = site_data[site_object_to_match[site_step]["old_ids_dict"]]
        _process_ids(dst_apisession, site_object_to_match[site_step], new_site_id, old_ids_dict, f"Checking Site {site_name} IDs")
            
##########################################################################################
#### CORE FUNCTIONS ####
def _result(failed_devices:dict, proceed:bool) -> bool:
    pb.log_title("Result", end=True)
    missing_ids = uuid_matching.get_missing_uuids()
    if not proceed:
        console.info("This script has been executed in Dry Run mode.")
        console.info("No modification have been done on the Source/Destination orgs.")
        print()
    if missing_ids:
        for object_type in missing_ids:
            console.warning(f"Unable to find new ID for the following {object_type}:")
            print()
            mistapi.cli.display_list_of_json_as_table(missing_ids[object_type], ["name", "old_uuid"])
            print("")
    if failed_devices:
        console.warning(f"There was {len(failed_devices)} device error(s) during the process:")
        for serial in failed_devices:
            print(f"{serial}: {failed_devices[serial]}")
    if not missing_ids and not failed_devices:
        console.info("Pre check validation succed!")
        console.info("No object missing, you can restore the devices")
        print("")
        return True
    return False

def _precheck(src_apisession:mistapi.APISession, dst_apisession:mistapi.APISession, src_org_id:str, dst_org_id:str, org_backup:dict, filter_site_names:list = [], proceed:bool=False, unclaim:bool=False, unclaim_all:bool=False) -> bool:
    print()
    pb.log_title("Processing Org")
    uuid_matching.add_uuid(dst_org_id, src_org_id, "Source Org ID")
    _process_org_ids(dst_apisession, dst_org_id, org_backup)

    failed_devices = {}
    for restore_site_name in org_backup["sites"]:
        if not filter_site_names or restore_site_name in filter_site_names:
            pb.log_title(f"Processing Site {restore_site_name}")
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
                    failed_devices, 
                    proceed, 
                    unclaim,
                    unclaim_all
                )
    return _result(failed_devices, proceed)

def _check_access(apisession: mistapi.APISession, org_id:str, message:str) -> bool:
    pb.log_message(message, display_pbar=False)
    for p in apisession.privileges:
        if p.get("scope") == "org" and p.get("org_id") == org_id:
            if p.get("role") == "admin":
                pb.log_success(message, display_pbar=False)
                return True
            else:
                pb.log_failure(message, display_pbar=False)
                console.error("You don't have full access to this org. Please use another account")
                return False
    pb.log_failure(message, display_pbar=False)
    console.error("You don't have access to this org. Please use another account")
    return False

def _start_precheck(src_apisession:mistapi.APISession, dst_apisession:mistapi.APISession, dst_org_id:str, source_backup:str=None, source_org_name:str=None, filter_site_names:list=[], proceed:bool=False, unclaim:bool=False, unclaim_all:bool=False) -> bool: 
    _go_to_backup_folder(source_org_name, source_backup)
    print()    
    try:
        message = f"Loading inventory file {backup_file} "
        pb.log_message(message, display_pbar=False)
        with open(backup_file) as f:
            backup = json.load(f)
        pb.log_success(message, display_pbar=False)
    except:
        pb.log_failure(message, display_pbar=False)
        console.critical("Unable to load the inventory file")
        logger.error("Exception occurred", exc_info=True)
        sys.exit(1)

    try:
        message = f"Analyzing template/backup file {backup_file} "
        pb.log_message(message, display_pbar=False)
        src_org_id = backup["org"]["id"]
        steps_total = 2
        sites_len = len(backup["org"]["sites"])
        devices_len = 0
        for site_name in backup["org"]["sites"]:
            devices_len += len(backup["org"]["sites"][site_name])
        steps_total += sites_len * 2 + devices_len * 2
        pb.set_steps_total(steps_total)
        pb.log_success(message, display_pbar=False)
        console.info(f"The process will test the deployment of {steps_total} devices")
    except:
        pb.log_failure(message, display_pbar=False)
        console.critical("Unable to parse the template/backup file")
        logger.error("Exception occurred", exc_info=True)
        sys.exit(1)

    if backup:
        if _check_access(dst_apisession, dst_org_id, "Validating access to the Destination Org"):
            if (unclaim and _check_access(src_apisession, src_org_id, "Validating access to the Source Org")) or not unclaim:
                return _precheck(src_apisession, dst_apisession, src_org_id, dst_org_id, backup["org"], filter_site_names, proceed, unclaim, unclaim_all)    

#####################################################################
#### FOLDER MGMT ####
def _chdir(path:str):
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
        logger.error("Exception occurred", exc_info=True)
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
            f"Which template/backup do you want to deploy (0-{i - 1}, or q to quit)? ")
        if resp.lower() == "q":
            console.error("Interruption... Exiting...")
            logger.error("Interruption... Exiting...")
            sys.exit(0)
        try:
            respi = int(resp)
            if respi >= 0 and respi <= i:
                folder = folders[respi]
            else:
                print(
                    f"The entry value \"{respi}\" is not valid. Please try again...")
        except:
            print("Only numbers are allowed. Please try again...")
    _chdir(folder)


def _go_to_backup_folder(source_org_name:str=None, source_backup:str=None):
    print()
    print(" Source Backup/Template ".center(80, "-"))
    print()
    _chdir(backup_folder)
    folders = []
    for entry in os.listdir("./"):
        if os.path.isdir(os.path.join("./", entry)):
            folders.append(entry)
    if source_backup in folders and _chdir(source_backup):
        print(f"Template/Backup {source_backup} found. It will be automatically used.")
    elif source_org_name in folders:
        print(f"Template/Backup found for organization {source_org_name}.")
        loop = True
        while loop:
            resp = input("Do you want to use this template/backup (y/N)? ")
            if resp.lower() in ["y", "n", " "]:
                loop = False
                if resp.lower() == "y" and _chdir(source_org_name):
                    pass
                else:
                    _select_backup_folder(folders)
    else:
        print(
            f"No Template/Backup found for organization {source_org_name}. Please select a folder in the following list.")
        _select_backup_folder(folders)

#####################################################################
#### DEST ORG SELECTION ####
def _check_org_name_in_script_param(apisession:mistapi.APISession, dst_org_id:str, org_name:str=None):
    response = mistapi.api.v1.orgs.orgs.getOrgInfo(apisession, dst_org_id)
    if response.status_code != 200:
        console.critical(f"Unable to retrieve the org information: {response.data}")
        sys.exit(0)
    org_name_from_mist = response.data["name"]
    return org_name == org_name_from_mist


def _check_org_name(apisession:mistapi.APISession, dst_org_id:str, org_name:str=None):
    if not org_name:
        org_name = mistapi.api.v1.orgs.orgs.getOrgInfo(apisession, dst_org_id).data["name"]
    while True:
        print()
        resp = input(
            "To avoid any error, please confirm the current destination orgnization name: ")
        if resp == org_name:
            return True
        else:
            print()
            print("The orgnization names do not match... Please try again...")


def _select_dest_org(apisession: mistapi.APISession):
    print()
    print(" Destination Org ".center(80, "-"))
    print()
    while True:
        dst_org_id = mistapi.cli.select_org(apisession)[0]
        org_name = mistapi.api.v1.orgs.orgs.getOrgInfo(
            apisession, dst_org_id).data["name"]
        if _check_org_name(apisession, dst_org_id, org_name):
            return dst_org_id, org_name

#####################################################################
#### START ####
def start(dst_apisession:mistapi.APISession, src_apisession:mistapi.APISession=None, dst_org_id:str=None, org_name:str=None, backup_folder_param: str = None, source_org_name:str=None, source_backup:str=None, filter_site_names:list=[], proceed:bool=False, unclaim:bool=False, unclaim_all:bool=False) -> bool:
    '''
    Start the process to check if the inventory can be deployed without issue

    PARAMS
    -------
    :param  mistapi.APISession  dst_apisession      - mistapi session with `Super User` access the destination Org, already logged in
    :param  mistapi.APISession  src_apisession      - Only required if `unclaim`==`True`. mistapi session with `Super User` access the source Org, already logged in
    :param  str                 dst_org_id          - org_id where to deploy the inventory
    :param  str                 org_name            - Org name where to deploy the inventory. This parameter requires "org_id" to be defined
    :param  str                 backup_folder_param - Path to the folder where to save the org backup (a subfolder will be created with the org name). default is "./org_backup"
    :param  str                 source_org_name     - Name of the backup/template to deploy. This is the name of the folder where all the backup files are stored. If the backup is found, the script will ask for a confirmation to use it
    :param  str                 source_backup       - Name of the backup/template to deploy. This is the name of the folder where all the backup files are stored. If the backup is found, the script will NOT ask for a confirmation to use it
    :param  str                 filter_site_names   - If only selected must be process, list a site names to process
    :param  bool                proceed             - By default, the script is executed in Dry Run mode (used to validate the destination org configuration). Set this parameter to True to disable the Dry Run mode and proceed to the deployment
    :param  bool                unclaim             - If `unclaim`==`True`, the script will unclaim the devices from the source org. Unclaim process will only be simulated if in Dry Run mode. WARNING: this option will only unclaim Mist APs, set `unclaim_all` to True to also uncail switches and gatewys
    :param  bool                unclaim_all         - If `unclaim_all`==`True`, the script will also migrate switches and gateways from the source org to the destination org (works only for claimed devices, not adopted ones). WARNING: This process may reset and reboot the boxes. Please make sure this will not impact users on site!

    RETURNS:
    -------
    :return bool                Process success or not. If the precheck or the deployement raised any warning/error (e.g. missing objects in the dest org), it will return False.
    '''
    current_folder = os.getcwd()
    if backup_folder_param:
        global backup_folder 
        backup_folder = backup_folder_param

    if dst_org_id and org_name:
        if not _check_org_name_in_script_param(dst_apisession, dst_org_id, org_name):
            console.critical(f"Org name {org_name} does not match the org {dst_org_id}")
            sys.exit(0)
    elif dst_org_id and not org_name:
        dst_org_id, org_name = _check_org_name(dst_apisession, dst_org_id)
    elif not dst_org_id and not org_name:
        dst_org_id, org_name = _select_dest_org(dst_apisession)
    elif not dst_org_id and org_name:
        console.error("\"org_name\" required \"org_id\" to be defined. You can either remove the \"org_name\" parameter, or add the \"org_id\" parameter.")
        sys.exit(2)
    else: #should not since we covered all the possibilities...
        sys.exit(0)

    success = _start_precheck(
        src_apisession,
        dst_apisession,
        dst_org_id, 
        source_backup=source_backup, 
        source_org_name=source_org_name, 
        filter_site_names=filter_site_names, 
        proceed=proceed,
        unclaim=unclaim, 
        unclaim_all=unclaim_all
    )
    os.chdir(current_folder)
    return success

#####################################################################
#### USAGE ####
def usage():
    print('''
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

-d, --dry               Dry Run mode. Will only simulate the process. Used to 
                        validate the destination org configuration. This mode 
                        will not send any requests to Mist and will not change
                        the Source/Dest Organisations.
                        Cannot be used with -p
-p, --proceed           WARNING: Proceed to the deployment. This mode will 
                        unclaim the APs from the source org (if -u is set) and
                        deploy them on the destination org. 
                        Cannot be used with -d

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

-------
Examples:
python3 ./org_inventory_deploy.py     
python3 ./org_inventory_deploy.py --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 -n "my test org" --dry

'''
)
#####################################################################
#### SCRIPT ENTRYPOINT ####
if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(sys.argv[1:], "ho:n:e:s:l:f:b:s:dpua", [
                                   "help", "org_id=", "org_name=", "env=", "sourve_env=", "log_file=", "backup_folder=", "source_backup=", "sites=", "dry", "proceed", "unclaim", "unclaim_all"])
    except getopt.GetoptError as err:
        console.error(err)
        usage()

    dst_org_id = None
    org_name = None
    backup_folder_param = None
    filter_site_names = []
    source_backup=None
    proceed=None
    unclaim=False
    unclaim_all=False
    for o, a in opts:
        if o in ["-h", "--help"]:
            usage()
        elif o in ["-o", "--org_id"]:
            dst_org_id = a
        elif o in ["-n", "--org_name"]:
            org_name = a
        elif o in ["-e", "--env"]:
            dest_env_file = a
        elif o in ["-s", "--source_env"]:
            source_env_file = a
        elif o in ["-l", "--log_file"]:
            log_file = a
        elif o in ["-f", "--backup_folder"]:
            backup_folder_param = a
        elif o in ["-b", "--source_backup"]:
            source_backup = a
        elif o in ["-s", "--sites"]:
            try:
                tmp = a.split(",")
                for site_name in tmp:
                    filter_site_names.append(site_name.strip())
            except:
                console.error("Unable to process the \"sites\" parameter. Please check it's value.")
                sys.exit(3)
        elif o in ["-p", "--proceed"]:
            if type(proceed) == bool:
                console.error("\"-p\" option cannot be used with \"-d\" option")
                sys.exit(3)
            proceed = True
        elif o in ["-d", "--dry"]:
            if type(proceed) == bool:
                console.error("\"-d\" option cannot be used with \"-p\" option")
                sys.exit(3)
            proceed = False
        elif o in ["-u", "--unclaim"]:
            unclaim = True
        elif o in ["-a", "--unclaim_all"]:
            unclaim_all = True
        else:
            assert False, "unhandled option"
    
    #### LOGS ####
    logging.basicConfig(filename=log_file, filemode='w')
    logger.setLevel(logging.DEBUG)
    ### START ###
    dst_apisession = mistapi.APISession(env_file=dest_env_file)
    dst_apisession.login()
    if unclaim:
        if not source_env_file or dest_env_file == source_env_file:
            src_apisession = dst_apisession
        elif source_env_file:
            src_apisession = mistapi.APISession(env_file=source_env_file)
            src_apisession.login()
    else:
        src_apisession = None
    ### DRY RUN OR NOT DRY RUN ###
    if not type(proceed) == bool:
        while True:
            resp = input("Do you want to run this script in (d)ry-run mode, can we (p)roceed and deploy the devices to the new org, or do you want to quit (d/p/q)? ")
            if resp.lower() == "d":
                proceed = False
                break
            elif resp.lower() == "p":
                proceed = True
                break
            elif resp.lower() == "q":                
                sys.exit(0)
            else:
                "Invalid input. Only \"d\", \"p\" and \"q\" are allowed"
    
    start(
        dst_apisession, 
        src_apisession,
        dst_org_id=dst_org_id, 
        org_name=org_name, 
        backup_folder_param=backup_folder_param, 
        source_backup=source_backup, 
        filter_site_names=filter_site_names, 
        proceed=proceed, 
        unclaim=unclaim, 
        unclaim_all=unclaim_all
    )


'''
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to restore device images from an inventory backup file. 

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
    "sites": {"mistapi_function": mistapi.api.v1.orgs.sites.listOrgSites, "text": "Site IDs", "old_ids_dict":"old_sites_id"}
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
## IMAGE RESTORE
def _restore_device_images(dst_apisession:mistapi.APISession, src_org_id:str, dst_site_id:str, device:dict, devices_type:str="device"):
        i=1
        image_exists = True
        issue_image = False
        while image_exists:
                image_name = f"{file_prefix}_org_{src_org_id}_device_{device['serial']}_image_{i}.png"
                if os.path.isfile(image_name):
                    try:
                        message = f"{device.get('type', devices_type).title()} {device.get('mac')} (S/N: {device.get('serial')}): Restoring Image #{i}"
                        pb.log_message(message)
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

def _restore_devices_images(dst_apisession:mistapi.APISession, src_org_id:str, dst_site_id:str, site_name:str, devices:dict, failed_devices:dict):
    for device in devices:
        issue_image = _restore_device_images(dst_apisession, src_org_id, dst_site_id, device, device.get("type"))
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

def _process_org_ids(dst_apisession:mistapi.APISession,dst_org_id:str, org_backup:dict):
    for org_step in org_object_to_match:        
        old_ids_dict = org_backup[org_object_to_match[org_step]["old_ids_dict"]]
        _process_ids(dst_apisession, org_object_to_match[org_step], dst_org_id, old_ids_dict, "Checking Org Ids")
            
##########################################################################################
#### CORE FUNCTIONS ####
def _result(failed_devices:dict, proceed:bool=True) -> bool:
    pb.log_title("Result", end=True)
    missing_ids = uuid_matching.get_missing_uuids()
    if not proceed:
        console.warning("This script has been executed in Dry Run mode.")
        console.warning("No modification have been done on the Source/Destination orgs.")
        console.warning("Use the \"-p\" / \"--proceed\" option to execute the changes.")
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

def _deploy(apisession:mistapi.APISession, src_org_id:str, dst_org_id:str, org_backup:dict, filter_site_names:list = []) -> bool:
    print()
    pb.log_title("Processing Org")
    uuid_matching.add_uuid(dst_org_id, src_org_id, "Source Org ID")
    _process_org_ids(apisession, dst_org_id, org_backup)

    failed_devices = {}
    for restore_site_name in org_backup["sites"]:
        if not filter_site_names or restore_site_name in filter_site_names:
            pb.log_title(f"Processing Site {restore_site_name}")
            site = org_backup["sites"][restore_site_name]
            dst_site_id = uuid_matching.get_new_uuid(site["id"])
            
            if not dst_site_id:
                uuid_matching.add_missing_uuid("site", site["id"], restore_site_name)
            else:                       
                _restore_devices_images(
                    apisession, 
                    src_org_id, 
                    dst_site_id, 
                    restore_site_name, 
                    site["devices"], 
                    failed_devices
                )
    return _result(failed_devices)

def _check_access(apisession: mistapi.APISession, org_id:str, message:str) -> bool:
    pb.log_message(message, display_pbar=False)
    try:
        response = mistapi.api.v1.self.self.getSelf(apisession)
        if response.status_code == 200:
            privileges = response.data.get("privileges", [])
            for p in privileges:
                if p.get("scope") == "org" and p.get("org_id") == org_id:
                    if p.get("role") == "admin":
                        pb.log_success(message, display_pbar=False)
                        return True
                    else:
                        pb.log_failure(message, display_pbar=False)
                        console.error("You don't have full access to this org. Please use another account")
                        return False
    except:
        pb.log_failure(message, display_pbar=False)
        console.critical("Unable to retrieve privileges from Mist Cloud")
        logger.error("Exception occurred", exc_info=True)

    pb.log_failure(message, display_pbar=False)
    console.error("You don't have access to this org. Please use another account")
    return False

def _start_deploy(apisession:mistapi.APISession, dst_org_id:str, source_backup:str=None, src_org_name:str=None, filter_site_names:list=[]) -> bool: 
    _go_to_backup_folder(src_org_name, source_backup)
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
        if _check_access(apisession, dst_org_id, "Validating access to the Destination Org"):
            return _deploy(apisession, src_org_id, dst_org_id, backup["org"], filter_site_names)    

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


def _go_to_backup_folder(src_org_name:str=None, source_backup:str=None):
    print()
    print(" Source Backup/Template ".center(80, "-"))
    print()
    _chdir(backup_folder)
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
            f"No Template/Backup found for organization {src_org_name}. Please select a folder in the following list.")
        _select_backup_folder(folders)

#####################################################################
#### DEST ORG SELECTION ####
def _check_org_name_in_script_param(apisession:mistapi.APISession, dst_org_id:str, org_name:str=None):
    response = mistapi.api.v1.orgs.orgs.getOrg(apisession, dst_org_id)
    if response.status_code != 200:
        console.critical(f"Unable to retrieve the org information: {response.data}")
        sys.exit(0)
    org_name_from_mist = response.data["name"]
    return org_name == org_name_from_mist


def _check_org_name(apisession:mistapi.APISession, dst_org_id:str, org_name:str=None):
    if not org_name:
        org_name = mistapi.api.v1.orgs.orgs.getOrg(apisession, dst_org_id).data["name"]
    while True:
        print()
        resp = input(
            "To avoid any error, please confirm the current destination orgnization name: ")
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
        org_name = mistapi.api.v1.orgs.orgs.getOrg(
            apisession, dst_org_id).data["name"]
        if _check_org_name(apisession, dst_org_id, org_name):
            return dst_org_id, org_name

#####################################################################
#### START ####
def start(apisession:mistapi.APISession=None, dst_org_id:str=None, dst_org_name:str=None, backup_folder_param: str = None, src_org_name:str=None, source_backup:str=None, filter_site_names:list=[]) -> bool:
    '''
    Start the process to check if the inventory can be deployed without issue

    PARAMS
    -------
    :param  mistapi.APISession  apisession          - mistapi session with `Super User` access the destination Org, already logged in    
    :param  str                 dst_org_id          - org_id where to deploy the inventory
    :param  str                 dst_org_name        - Org name where to deploy the inventory. This parameter requires "org_id" to be defined
    :param  str                 backup_folder_param - Path to the folder where to save the org backup (a subfolder will be created with the org name). default is "./org_backup"
    :param  str                 src_org_name        - Name of the backup/template to deploy. This is the name of the folder where all the backup files are stored. If the backup is found, the script will ask for a confirmation to use it
    :param  str                 source_backup       - Name of the backup/template to deploy. This is the name of the folder where all the backup files are stored. If the backup is found, the script will NOT ask for a confirmation to use it
    :param  str                 filter_site_names   - If only selected must be process, list a site names to process

    RETURNS:
    -------
    :return bool                Process success or not. If the process raised any warning/error (e.g. missing objects in the dest org), it will return False.
    '''
    current_folder = os.getcwd()
    if backup_folder_param:
        global backup_folder 
        backup_folder = backup_folder_param

    if dst_org_id and dst_org_name:
        if not _check_org_name_in_script_param(apisession, dst_org_id, dst_org_name):
            console.critical(f"Org name {dst_org_name} does not match the org {dst_org_id}")
            sys.exit(0)
    elif dst_org_id and not dst_org_name:
        dst_org_id, dst_org_name = _check_org_name(apisession, dst_org_id)
    elif not dst_org_id and not dst_org_name:
        dst_org_id, dst_org_name = _select_dest_org(apisession)
    elif not dst_org_id and dst_org_name:
        console.error("\"dst_org_name\" required \"dst_org_id\" to be defined. You can either remove the \"dst_org_name\" parameter, or add the \"dst_org_id\" parameter.")
        sys.exit(2)
    else: #should not since we covered all the possibilities...
        sys.exit(0)

    success = _start_deploy(
        apisession,
        dst_org_id, 
        source_backup=source_backup, 
        src_org_name=src_org_name, 
        filter_site_names=filter_site_names
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
Python script to restore device images from an inventory backup file. 

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
    sys.exit(0)

def check_mistapi_version():
    if mistapi.__version__ < MISTAPI_MIN_VERSION:
        logger.critical(f"\"mistapi\" package version {MISTAPI_MIN_VERSION} is required, you are currently using version {mistapi.__version__}.")
        logger.critical(f"Please use the pip command to updated it.")
        logger.critical("")
        logger.critical(f"    # Linux/macOS")
        logger.critical(f"    python3 -m pip install --upgrade mistapi")
        logger.critical("")
        logger.critical(f"    # Windows")
        logger.critical(f"    py -m pip install --upgrade mistapi")
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
        logger.info(f"\"mistapi\" package version {MISTAPI_MIN_VERSION} is required, you are currently using version {mistapi.__version__}.")
    
#####################################################################
#### SCRIPT ENTRYPOINT ####
if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(sys.argv[1:], "ho:n:e:s:l:f:b", [
                                   "help", "org_id=", "org_name=", "env=", "log_file=", "backup_folder=", "source_backup=", "sites="])
    except getopt.GetoptError as err:
        console.error(err)
        usage()

    dst_org_id = None
    org_name = None
    backup_folder_param = None
    filter_site_names = []
    source_backup=None
    for o, a in opts:
        if o in ["-b", "--source_backup"]:
            source_backup = a
        elif o in ["-e", "--env"]:
            dest_env_file = a
        elif o in ["-f", "--backup_folder"]:
            backup_folder_param = a
        elif o in ["-h", "--help"]:
            usage()
            sys.exit(0)
        elif o in ["-l", "--log_file"]:
            log_file = a
        elif o in ["-n", "--org_name"]:
            org_name = a
        elif o in ["-o", "--org_id"]:
            dst_org_id = a
        elif o in ["-s", "--sites"]:
            try:
                tmp = a.split(",")
                for site_name in tmp:
                    filter_site_names.append(site_name.strip())
            except:
                console.error("Unable to process the \"sites\" parameter. Please check it's value.")
                sys.exit(3)
        else:
            assert False, "unhandled option"
    
    #### LOGS ####
    logging.basicConfig(filename=log_file, filemode='w')
    logger.setLevel(logging.DEBUG)
    check_mistapi_version()
    ### START ###   
    apisession = mistapi.APISession(env_file=dest_env_file)
    apisession.login()
    
    start(
        apisession, 
        dst_org_id=dst_org_id, 
        dst_org_name=org_name, 
        backup_folder_param=backup_folder_param, 
        source_backup=source_backup, 
        filter_site_names=filter_site_names
    )


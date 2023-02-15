'''
Written by: Thomas Munzer (tmunzer@juniper.net)
Github repository: https://github.com/tmunzer/Mist_library/

Python script to restore organization backup file.
You can use the script "org_conf_backup.py" to generate the backup file from an
existing organization.

This script will not overide existing objects. If you already configured objects in the 
destination organisation, new objects will be created. If you want to "reset" the 
destination organization, you can use the script "org_conf_zeroise.py".
This script is trying to maintain objects integrity as much as possible. To do so, when 
an object is referencing another object by its ID, the script will replace be ID from 
the original organization by the corresponding ID from the destination org.

You can run the script with the command "python3 org_admins_import.py <path_to_the_json_file>"

The script has 2 different steps:
1) admin login
2) choose the destination org
3) restore all the objects from the json file. 
'''

#### IMPORTS ####
import logging
import json
import os
import sys
import re
import getopt
from typing import Callable


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
backup_file = "org_conf_file.json"
log_file = "./script.log"
file_prefix = ".".join(backup_file.split(".")[:-1])
env_file = "~/.mist_env"

#####################################################################
#### LOGS ####
logger = logging.getLogger(__name__)

#### GLOBAL VARS ####

org_steps = {
    "assetfilters": {"mistapi_function": mistapi.api.v1.orgs.assetfilters.createOrgAssetFilters, "text": "Org assetfilters"},
    "deviceprofiles": {"mistapi_function": mistapi.api.v1.orgs.deviceprofiles.createOrgDeviceProfiles, "text": "Org deviceprofiles"},
    "hubprofiles": {"mistapi_function": mistapi.api.v1.orgs.deviceprofiles.createOrgDeviceProfiles, "text": "Org hubprofiles"},
    "evpn_topologies": {"mistapi_function": mistapi.api.v1.orgs.evpn_topologies.createOrgEvpnTopology, "text": "Org evpn_topologies"},
    "secpolicies": {"mistapi_function": mistapi.api.v1.orgs.secpolicies.createOrgSecPolicies, "text": "Org secpolicies"},
    "aptempaltes": {"mistapi_function": mistapi.api.v1.orgs.aptemplates.createOrgAptemplate, "text": "Org aptemplates"},
    "networktemplates": {"mistapi_function": mistapi.api.v1.orgs.networktemplates.createOrgNetworkTemplate, "text": "Org networktemplates"},
    "networks": {"mistapi_function": mistapi.api.v1.orgs.networks.createOrgNetwork, "text": "Org networks"},
    "services": {"mistapi_function": mistapi.api.v1.orgs.services.createOrgService, "text": "Org services"},
    "servicepolicies": {"mistapi_function": mistapi.api.v1.orgs.servicepolicies.createOrgServicePolicy, "text": "Org servicepolicies"},
    "vpns": {"mistapi_function": mistapi.api.v1.orgs.vpns.createOrgVpns, "text": "Org vpns"},
    "gatewaytemplates": {"mistapi_function": mistapi.api.v1.orgs.gatewaytemplates.createOrgGatewayTemplate, "text": "Org gatewaytemplates"},
    "alarmtemplates": {"mistapi_function": mistapi.api.v1.orgs.alarmtemplates.createOrgAlarmTemplate, "text": "Org alarmtemplates"},
    "rftemplates": {"mistapi_function": mistapi.api.v1.orgs.rftemplates.createOrgRfTemplate, "text": "Org rftemplates"},
    "webhooks": {"mistapi_function": mistapi.api.v1.orgs.webhooks.createOrgWebhook, "text": "Org webhooks"},
    "mxclusters": {"mistapi_function": mistapi.api.v1.orgs.mxclusters.createOrgMxEdgeCluster, "text": "Org mxclusters"},
    "mxtunnels": {"mistapi_function": mistapi.api.v1.orgs.mxtunnels.createOrgMxTunnel, "text": "Org mxtunnels"},
    "wxtunnels": {"mistapi_function": mistapi.api.v1.orgs.wxtunnels.createOrgWxTunnel, "text": "Org wxtunnels"},
    "sitetemplates": {"mistapi_function": mistapi.api.v1.orgs.sitetemplates.getOrgSiteTemplates, "text": "Org sitetemplates"},
    "sitegroups": {"mistapi_function": mistapi.api.v1.orgs.sitegroups.createOrgSiteGroup, "text": "Org sitegroups"},
    "sites": {"mistapi_function": mistapi.api.v1.orgs.sites.createOrgSite, "text": "Org Sites"},
    "templates": {"mistapi_function": mistapi.api.v1.orgs.templates.createOrgTemplate, "text": "Org templates"},
    "wlans": {"mistapi_function": mistapi.api.v1.orgs.wlans.createOrgWlan, "text": "Org wlans"},
    "wxtags": {"mistapi_function": mistapi.api.v1.orgs.wxtags.createOrgWxTag, "text": "Org wxtags"},
    "wxrules": {"mistapi_function": mistapi.api.v1.orgs.wxrules.createOrgWxRule, "text": "Org wxrules"},
    "pskportals": {"mistapi_function": mistapi.api.v1.orgs.pskportals.createOrgPskPortal, "text": "Org pskportals"},
    "psks": {"mistapi_function": mistapi.api.v1.orgs.psks.createOrgPsk, "text": "Org psks"},
    "nactags": {"mistapi_function": mistapi.api.v1.orgs.nactags.createOrgNacTag, "text": "Org nactags"},
    "nacrules": {"mistapi_function": mistapi.api.v1.orgs.nacrules.createOrgNacRule, "text": "Org nacrules"},
    "ssos": {"mistapi_function": mistapi.api.v1.orgs.ssos.createOrgSso, "text": "Org ssos"},
    "ssoroles": {"mistapi_function": mistapi.api.v1.orgs.ssoroles.createOrgSsoRole, "text": "Org ssoroles"},
}
site_steps = {
    "settings": {"mistapi_function": mistapi.api.v1.sites.setting.updateSiteSettings, "text": "Site settings"},
    "maps": {"mistapi_function": mistapi.api.v1.sites.maps.createSiteMap, "text": "Site maps"},
    "zones": {"mistapi_function": mistapi.api.v1.sites.zones.createSiteZone, "text": "Site zones"},
    "rssizones": {"mistapi_function": mistapi.api.v1.sites.rssizones.createSiteRssiZone, "text": "Site rssizones"},
    "assets": {"mistapi_function": mistapi.api.v1.sites.assets.createSiteAsset, "text": "Site assets"},
    "assetfilters": {"mistapi_function": mistapi.api.v1.sites.assetfilters.createSiteAssetFilters, "text": "Site assetfilters"},
    "beacons": {"mistapi_function": mistapi.api.v1.sites.beacons.createSiteBeacon, "text": "Site beacons"},
    "psks": {"mistapi_function": mistapi.api.v1.sites.psks.createSitePsk, "text": "Site psks"},
    "vbeacons": {"mistapi_function": mistapi.api.v1.sites.vbeacons.createSiteVBeacon, "text": "Site vbeacons"},
    "webhooks": {"mistapi_function": mistapi.api.v1.sites.webhooks.createSiteWebhook, "text": "Site webhooks"},
    "wxtunnels": {"mistapi_function": mistapi.api.v1.sites.wxtunnels.createSiteWxTunnel, "text": "Site wxtunnels"},
    "wlans": {"mistapi_function": mistapi.api.v1.sites.wlans.createSiteWlan, "text": "Site wlans"},
    "wxtags": {"mistapi_function": mistapi.api.v1.sites.wxtags.createSiteWxTag, "text": "Site wxtags"},
    "wxrules": {"mistapi_function": mistapi.api.v1.sites.wxrules.createSiteWxRule, "text": "Site wxrules"},
}

#### FUNCTIONS ####
def log_message(message):
    print(f"{message}".ljust(79, '.'), end="", flush=True)


def log_debug(message):
    logger.debug(f"{message}")


def log_error(message):
    logger.error(f"{message}")

def log_warning(message):
    print("\033[93m\u0097\033[0m")
    logger.warning(f"{message}")

def log_success(message):
    print("\033[92m\u2714\033[0m")
    logger.info(f"{message}: Success")


def log_failure(message):
    print('\033[31m\u2716\033[0m')
    logger.exception(f"{message}: Failure")

##########################################################################################
# COMMON FUNCTIONS
class UUIDM():

    def __init__(self):
        self.uuids = {}
        self.requests_to_replay = []
    
    def add_uuid(self, new:str, old:str):
        if new and old: self.uuids[old] = new

    def get_new_uuid(self, old:str):
        return self.uuids.get(old)

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
        ids_to_remove = [ "id", "msp_id", "org_id", "site_id", "site_ids", "url", "bg_image_url",
        "portal_template_url", "portal_sso_url", "thumbnail_url", "template_url", "ui_url" ]

        for id_name in ids_to_remove:
            if not object_type == "webhooks" or not id_name=="url":
                if id_name in obj:
                    del obj[id_name]
        if "service_policies" in obj:
            for service_policy in obj.get("service_policies", []):
                if "id" in service_policy:
                    del service_policy["id"]

        # REPLACE REMAINING IDS
        obj_str = json.dumps(obj)
        obj_str, missing_uuids = self._uuid_string(obj_str, [])
        obj_str, missing_uuids = self._uuid_list(obj_str, missing_uuids)
        obj = json.loads(obj_str)

        return obj, missing_uuids



def _common_restore(apisession: mistapi.APISession, mistapi_function:Callable, scope_id: str, object_type: str, data: dict, retry:bool=False):
    old_id = None
    new_id = None
    if "name" in data: object_name = f"\"{data['name']}\" "
    elif "ssid" in data: object_name = f"\"{data['ssid']}\" "
    else: object_name = ""
    if "id" in data: old_id = data["id"]
    else: old_id = None

    message = f"Creating {object_type} {object_name}"
    log_message(message)
    data, missing_uuids = uuid_matching.find_and_replace(data, object_type)
    
    if missing_uuids and not retry:
        uuid_matching.add_replay(mistapi_function, scope_id, object_type, data)
        log_warning(message)
    else:
        try:
            response = mistapi_function(apisession, scope_id, data).data
            if "id" in response:
                new_id = response["id"]
            log_success(message)
        except:
            log_failure(message)
        uuid_matching.add_uuid(new_id, old_id)
        return new_id
    return None

##########################################################################################
# WLAN FUNCTIONS
def _restore_wlan(apisession: mistapi.APISession, mistapi_function:Callable, scope_id: str, data: dict, old_org_id: str, old_site_id: str = None):
    old_wlan_id = data["id"]
    new_wlan_id = _common_restore(apisession, mistapi_function, scope_id, 'wlans', data)
    uuid_matching.add_uuid(new_wlan_id, old_wlan_id)
    _restore_wlan_portal(apisession, old_org_id,old_site_id, old_wlan_id, scope_id, new_wlan_id, data["ssid"])


def _restore_wlan_portal(apisession: mistapi.APISession, old_org_id:str, old_site_id:str, old_wlan_id:str, scope_id: str, new_wlan_id:str, wlan_name:str):
    if old_site_id is None:
        portal_file_name = f"{file_prefix}_org_{old_org_id}_wlan_{old_wlan_id}.json"
        portal_image = f"{file_prefix}_org_{old_org_id}_wlan_{old_wlan_id}.png"
        upload_image_function = mistapi.api.v1.orgs.wlans.uploadOrgWlanPortalImageFile
        update_template_function = mistapi.api.v1.orgs.wlans.updateOrgWlanPortalTemplate
    else:
        portal_file_name = f"{file_prefix}_org_{old_org_id}_site_{old_site_id}_wlan_{old_wlan_id}.json"
        portal_image = f"{file_prefix}_org_{old_org_id}_site_{old_site_id}_wlan_{old_wlan_id}.png"
        upload_image_function = mistapi.api.v1.sites.wlans.uploadSiteWlanPortalImageFile
        update_template_function = mistapi.api.v1.sites.wlans.updateSiteWlanPortalTemplate

    if os.path.isfile(portal_file_name):
        message = f"Creating Portal Template for WLAN \"{wlan_name}\" "
        log_message(message)
        try:
            template = open(portal_file_name, 'r')
        except Exception as e:
            log_failure(
                f"Unable to open the template file \"{portal_file_name}\" ")
            logger.error("Exception occurred", exc_info=True)
            return
        try:
            template = json.load(template)
        except Exception as e:
            log_failure(
                f"Unable to read the template file \"{portal_file_name}\" ")
            logger.error("Exception occurred", exc_info=True)
            return
        try:
            update_template_function(apisession, scope_id, new_wlan_id, template)
            log_success(message)
        except Exception as e:
            log_failure(
                f"Unable to upload the template \"{portal_file_name}\" ")
            logger.error("Exception occurred", exc_info=True)

    else:
        log_debug(f"No Portal template found for WLAN \"{wlan_name}\"")

    if os.path.isfile(portal_image):
        message = f"Uploading Portal image for WLAN \"{wlan_name}\" "
        try:
            upload_image_function(apisession, scope_id, new_wlan_id, portal_image)
            log_success(message)
        except Exception as e:
            log_failure(message)
            logger.error("Exception occurred", exc_info=True)
    else:
        log_debug(f"No Portal Template image found for WLAN {wlan_name} ")

##########################################################################################
# SITE FUNCTIONS
def _restore_site_maps(apisession: mistapi.APISession, old_org_id: str, old_site_id: str, new_site_id: str, data: dict):
    old_map_id = data["id"]
    new_map_id = _common_restore(
        apisession, site_steps["maps"]["mistapi_function"], new_site_id, 'maps', data)

    image_name = f"{file_prefix}_org_{old_org_id}_site_{old_site_id}_map_{old_map_id}.png"
    if os.path.isfile(image_name):
        message = f"Uploading image floorplan  \"{data['name']}\""
        log_message(message)
        try:
            mistapi.api.v1.sites.maps.addSiteMapImageFile(
                apisession, new_site_id, new_map_id, image_name)
            log_success(message)
        except:
            log_failure(message)
    else:
        log_debug(f"No image found for \"{data['name']}\"")


def _restore_site(apisession: mistapi.APISession, org_id:str, old_org_id:str, site_info:dict, sites_backup:dict):
    old_site_id = site_info["id"]
    site_data = sites_backup.get(old_site_id, {})

    print(f" Deploying Site {site_info['name']} ".center(80, "_"))
    new_site_id = _common_restore(
        apisession,org_steps["sites"]["mistapi_function"], org_id, "sites", site_info)

    for step_name in site_steps:
        step = site_steps[step_name]
        if step_name == "settings":
            step_data = site_data.get(step_name, {})
            _common_restore(apisession, step["mistapi_function"], new_site_id, step_name, step_data)
        else:
            for step_data in site_data.get(step_name, []):
                if step_name == "maps":
                    _restore_site_maps(apisession, old_org_id, old_site_id, new_site_id, step_data)
                elif step_name == "wlans":
                    _restore_wlan(apisession, step["mistapi_function"], org_id, step_data, old_org_id, old_site_id)
                else:
                    _common_restore(apisession, step["mistapi_function"], new_site_id, step_name, step_data)

##########################################################################################
#  ORG FUNCTIONS
def _restore_org(apisession: mistapi.APISession, org_id:str, org_name:str, backup:dict):
    print()
    print(f" Deploying Org {org_name} ".center(80, "_"))

    ####################
    ####  ORG MAIN  ####
    org_backup = backup["org"]
    sites_backup = backup["sites"]

    org_data = org_backup["data"]
    old_org_id = org_data["id"]
    uuid_matching.add_uuid(org_id, old_org_id)

    message = "Org Info "
    log_message(message)
    try:
        org_data["name"] = org_name
        mistapi.api.v1.orgs.orgs.updateOrg(apisession, org_id, org_data)
        log_success(message)
    except Exception as e:
        log_failure(message)
        logger.error("Exception occurred", exc_info=True)

    ########################
    ####  ORG SETTINGS  ####
    message = "Org Settings "
    log_message(message)
    try:
        mistapi.api.v1.orgs.setting.updateOrgSettings(apisession, org_id, org_data)
        log_success(message)
    except Exception as e:
        log_failure(message)
        logger.error("Exception occurred", exc_info=True)

    #######################
    ####  ORG OBJECTS  ####
    print(f" Deploying Common Org Objects ".center(80, "_"))
    for step_name in org_steps:
        if step_name in org_backup:
            step = org_steps[step_name]
            for step_data in org_backup[step_name]:
                if step_name == "sites":
                    _restore_site(apisession, org_id, old_org_id, step_data, sites_backup)
                    print(f" Deploying Reamining Org Objects ".center(80, "_"))
                elif step_name == "wlans":
                    _restore_wlan(apisession, step["mistapi_function"], org_id, step_data, old_org_id)
                else:
                    _common_restore(apisession, step["mistapi_function"], org_id, step_name, step_data)

    print(f" Retrying missing objects ".center(80, "_"))
    for replay in uuid_matching.get_replay():
        _common_restore(apisession, replay["mistapi_function"], replay["scope_id"], replay["object_type"], replay["data"], True)

#####################################################################
#### MENUS ####
def _display_warning(message):
    resp = "x"
    while not resp.lower() in ["y", "n", ""]:
        print()
        resp = input(message)
    if not resp.lower() == "y":
        print("Interruption... Exiting...")
        log_error("Interruption... Exiting...")
        sys.exit(0)


def _select_backup_folder(folders):
    i = 0
    print("Available Templates/Backups:")
    while i < len(folders):
        print(f"{i}) {folders[i]}")
        i += 1
    folder = None
    while folder is None:
        resp = input(
            f"Which template/backup do you want to restore (0-{i - 1}, or q to quit)? ")
        if resp.lower() == "q":
            print("Interruption... Exiting...")
            log_error("Interruption... Exiting...")
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
    os.chdir(folder)


def _go_to_backup_folder(source_org_name=None):
    print()
    print(" Source Backup/Template ".center(80, "-"))
    print()
    os.chdir(os.getcwd())
    os.chdir(backup_folder)
    folders = []
    for entry in os.listdir("./"):
        if os.path.isdir(os.path.join("./", entry)):
            folders.append(entry)
    if source_org_name in folders:
        print(f"Template/Backup found for organization {source_org_name}.")
        loop = True
        while loop:
            resp = input("Do you want to use this template/backup (y/n)? ")
            if resp.lower == "y":
                loop = False
                try:
                    os.chdir(source_org_name)
                except:
                    _select_backup_folder(folders)
            else:
                loop = False
                _select_backup_folder(folders)
    else:
        print(
            f"No Template/Backup found for organization {source_org_name}. Please select a folder in the following list.")
        _select_backup_folder(folders)


def _check_org_name_in_script_param(apisession:mistapi.APISession, org_id:str, org_name:str=None):
    response = mistapi.api.v1.orgs.orgs.getOrgInfo(apisession, org_id)
    if response.status_code != 200:
        console.critical(f"Unable to retrieve the org information: {response.error}")
        sys.exit(3)
    org_name_from_mist = response.data["name"]
    return org_name == org_name_from_mist
    

def _check_org_name(apisession:mistapi.APISession, org_id:str, org_name:str=None):
    if not org_name:
        org_name = mistapi.api.v1.orgs.orgs.getOrgInfo(apisession, org_id).data["name"]
    while True:
        print()
        resp = input(
            "To avoid any error, please confirm the current destination orgnization name: ")
        if resp == org_name:
            return True
        else:
            print()
            print("The orgnization names do not match... Please try again...")


def start_deploy_org(apisession: mistapi.APISession, org_id, org_name, source_backup):
    _go_to_backup_folder(source_backup)
    print()
    message = f"Loading template/backup file {backup_file} "
    log_message(message)
    try:
        with open(backup_file) as f:
            backup = json.load(f)
        log_success(message)
    except:
        print("Unable to load the template/bakup ".ljust(79, "."), end="", flush=True)
        log_failure(message)
        sys.exit(1)
    finally:
        if backup:
            _display_warning(
                f"Are you sure about this? Do you want to import the configuration into the organization {org_name} with the id {org_id} (y/N)? ")
            _restore_org(apisession, org_id, org_name, backup)
            print()
            print("Importation process finished...")


def _create_org(apisession: mistapi.APISession):
    while True:
        custom_dest_org_name = input("Organization name? ")
        if custom_dest_org_name:
            org = {
                "name": custom_dest_org_name
            }
            message = f"Creating the organisation \"{custom_dest_org_name}\" in {apisession.get_cloud()} "
            log_message(message)
            try:
                log_success(message)
            except Exception as e:
                log_failure(message)
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
            org_name = mistapi.api.v1.orgs.orgs.getOrgInfo(
                apisession, org_id).data["name"]
            if _check_org_name(apisession, org_id, org_name):
                return org_id, org_name
        elif res.lower() == "n":
            return _create_org(apisession)

#####################################################################
#### START ####
def start(apisession: mistapi.APISession, org_id: str, org_name: str, backup_folder_param: str = None, source_backup: str = None):
    current_folder = os.getcwd()
    if backup_folder_param:
        global backup_folder
        backup_folder = backup_folder_param

    if not org_id:
        org_id, org_name = _select_dest_org(apisession)
    elif not org_name:
        org_id, org_name = _check_org_name(apisession, org_id)
    elif not _check_org_name_in_script_param(apisession, org_id, org_name):
        console.critical(f"Org name {org_name} does not match the org {org_id}")
        sys.exit(0)
    
    start_deploy_org(apisession, org_id, org_name, source_backup)
    os.chdir(current_folder)


#####################################################################
#### SCRIPT ENTRYPOINT ####
uuid_matching = UUIDM()
if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(sys.argv[1:], "ho:n:e:l:b:s:", [
                                   "help", "org_id=", "org_name=", "env=", "log_file=", "backup_folder=", "source_backup="])
    except getopt.GetoptError as err:
        console.error(err)
        usage()

    org_id = None
    org_name = None
    backup_folder_param = None
    source_backup = None
    for o, a in opts:
        if o in ["-h", "--help"]:
            usage()
        elif o in ["-o", "--org_id"]:
            org_id = a
        elif o in ["-n", "--org_name"]:
            org_name = a
        elif o in ["-e", "--env"]:
            env_file = a
        elif o in ["-l", "--log_file"]:
            log_file = a
        elif o in ["-b", "--backup_folder"]:
            backup_folder_param = a
        elif o in ["-s", "--source_backup"]:
            source_backup = a
        else:
            assert False, "unhandled option"
    print(env_file)
    #### LOGS ####
    logging.basicConfig(filename=log_file, filemode='w')
    logger.setLevel(logging.DEBUG)
    ### START ###
    apisession = mistapi.APISession(env_file=env_file)
    apisession.login()
    start(apisession, org_id, org_name, backup_folder_param, source_backup)

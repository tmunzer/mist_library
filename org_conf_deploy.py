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
import os.path
import logging
import json
from mlib import cli
import mlib as mist_lib
import sys

#### PARAMETERS #####
backup_file = "./org_conf_file.json"
log_file = "./org_conf_deploy.log"
file_prefix = ".".join(backup_file.split(".")[:-1])
session_file = ""
backup_directory = "./org_backup/"
org_id = ""

#### LOGS ####
logging.basicConfig(filename=log_file, filemode='w')
# logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)




#### GLOBAL VARS ####
rftemplate_id_dict = {}
site_id_dict = {}
sitegroup_id_dict = {}
map_id_dict = {}
deviceprofile_id_dict = {}
template_id_dict = {}
mxtunnel_id_dict = {}
wxtunnel_id_dict = {}
secpolicy_id_dict = {}
wxtags_id_dict = {}
mxcluster_id_dict = {}
wlan_id_dict = {}
alarmtemplate_id_dict = {}
networktemplate_id_dict = {}
evpn_topology_id_dict = {}
service_id_dict = {}
network_id_dict = {}
hubprofile_id_dict = {}
gatewaytemplate_id_dict = {}
vpn_id_dict = {}



#### FUNCTIONS ####
def log_message(message):
    print(f"{message}".ljust(79, '.'), end="", flush=True)

def log_debug(message):
    logger.debug(f"{message}")

def log_error(message):
    logger.error(f"{message}")

def log_success(message):
    print("\033[92m\u2714\033[0m")
    logger.info(f"{message}: Success")


def log_failure(message):
    print('\033[31m\u2716\033[0m')
    logger.exception(f"{message}: Failure")



def _get_new_id(old_id, new_ids_dict):
    if old_id in new_ids_dict:
        new_id = new_ids_dict[old_id]
        log_debug(f"Replacing id {old_id} with id {new_id}")
        return new_id
    else:
        log_debug(f"Unable to replace id {old_id}")
        return None


def _replace_id(old_ids_list, new_ids_dict):
    if old_ids_list is None:
        return None
    if old_ids_list == {}:
        return {}
    elif type(old_ids_list) == str:
        return _get_new_id(old_ids_list, new_ids_dict)
    elif type(old_ids_list) == list:
        new_ids_list = []
        for old_id in old_ids_list:
            new_ids_list.append(_get_new_id(old_id, new_ids_dict))
        return new_ids_list
    else:
        log_error(f"Unable to replace ids: {old_ids_list}")


def _clean_ssorole_privileges(privilege, org_id):
    if "org_id" in privilege:
        privilege["org_id"] = org_id
    if "site_id" in privilege:
        privilege["site_id"] = _replace_id(privilege["site_id"], site_id_dict)
    if "sitegroup_id" in privilege:
        privilege["sitegroup_id"] = _replace_id(
            privilege["sitegroup_id"], sitegroup_id_dict)
    return privilege


def _clean_ids(data):
    if "id" in data:
        del data["id"]
    if "org_id" in data:
        del data["org_id"]
    if "modified_time" in data:
        del data["modified_time"]
    if "created_time" in data:
        del data["created_time"]
    return data


def _common_restore(mist_session, level, level_id, object_type, data):
    if "name" in data:
        object_name = f"\"{data['name']}\" "
    elif "ssid" in data:
        object_name = f"\"{data['ssid']}\" "
    else:
        object_name = ""
    if "id" in data:
        old_id = data["id"]
    else:
        old_id = None
    data = _clean_ids(data)
    new_id = None
    message=f"Creating {object_type} {object_name}"
    log_message(message)
    try:
        module = mist_lib.requests.route(level, object_type)
        result = module.create(mist_session, level_id, data)["result"]
        if "id" in result:
            new_id = result["id"]
        log_success(message)
    except:
        log_failure(message)
    finally:
        return {old_id: new_id}


def _wlan_restore(mist_session,  level, level_id, data, old_org_id, old_site_id):
    if "template_id" in data:
        data["template_id"] = _replace_id(
            data["template_id"], template_id_dict)
    if "wxtunnel_id" in data:
        data["wxtunnel_id"] = _replace_id(data["wxtunnel_id"], wxtags_id_dict)
    if "mxtunnel_id" in data:
        data["mxtunnel_id"] = _replace_id(
            data["mxtunnel_id"], mxtunnel_id_dict)
    if "app_limit" in data and "wxtag_ids" in data["app_limit"]:
        data["app_limit"]["wxtag_ids"] = _replace_id(
            data["app_limit"]["wxtag_ids"], wxtags_id_dict)
    ids = _common_restore(mist_session, level, level_id, 'wlans', data)
    old_wlan_id = next(iter(ids))
    new_wlan_id = ids[old_wlan_id]
    _wlan_restore_portal(mist_session, level_id,old_org_id, old_site_id, old_wlan_id, new_wlan_id, data["ssid"])
    wlan_id_dict.update(ids)


def _wlan_restore_portal(mist_session, level_id, old_org_id, old_site_id, old_wlan_id, new_wlan_id, wlan_name):
    if old_site_id is None:
        portal_file_name = f"{file_prefix}_org_{old_org_id}_wlan_{old_wlan_id}.json"
        portal_image = f"{file_prefix}_org_{old_org_id}_wlan_{old_wlan_id}.png"
        module = mist_lib.requests.route("orgs", "wlans")
    else:
        portal_file_name = f"{file_prefix}_org_{old_org_id}_site_{old_site_id}_wlan_{old_wlan_id}.json"
        portal_image = f"{file_prefix}_org_{old_org_id}_site_{old_site_id}_wlan_{old_wlan_id}.png"
        module = mist_lib.requests.route("sites", "wlans")


    if os.path.isfile(portal_file_name):
        message=f"Creating Portal Template for WLAN \"{wlan_name}\" "
        log_message(message)
        try:
            template = open(portal_file_name, 'r')
        except:
            log_failure(f"Unable to open the template file \"{portal_file_name}\" ")
            return
        try:
            template = json.load(template)
        except:
            
            log_failure(f"Unable to read the template file \"{portal_file_name}\" ")
            return
        try:
            module.set_portal_template(
                mist_session, level_id, new_wlan_id, template)
            log_success(message)
        except:
            log_failure(f"Unable to upload the template \"{portal_file_name}\" ")

    else:
        log_debug(f"No Portal template found for WLAN \"{wlan_name}\"")

    if os.path.isfile(portal_image):
        message=f"Uploading Portal image for WLAN \"{wlan_name}\" "
        try:
            module.add_portal_image(
                mist_session, level_id, new_wlan_id, portal_image)
            log_success(message)
        except:
            log_failure(message)
    else:
        log_debug(f"No Portal Template image found for WLAN {wlan_name} ")

##########################################################################################
################## RESTORE SITE
def _restore_site(mist_session, data, org_id, old_org_id):
    site = data["data"]
    old_site_id = site["id"]
    print(f" Deploying Site {site['name']} ".center(80, "_"))
    ####  SITES MAIN  ####
    if "rftemplate_id" in site:
        site["rftemplate_id"] = _replace_id(
            site["rftemplate_id"], rftemplate_id_dict)
    old_site_id = site["id"]
    if "networktemplate_id" in site:
        site["networktemplate_id"] = _replace_id(
            site["networktemplate_id"], networktemplate_id_dict)
    if "gatewaytemplate_id" in site:
        site["gatewaytemplate_id"] = _replace_id(
            site["gatewaytemplate_id"], gatewaytemplate_id_dict)
    if "secpolicy_id" in site:
        site["secpolicy_id"] = _replace_id(
            site["secpolicy_id"], secpolicy_id_dict)
    if "alarmtemplate_id" in site:
        site["alarmtemplate_id"] = _replace_id(
            site["alarmtemplate_id"], alarmtemplate_id_dict)
    if "sitegroup_ids" in site:
        site["sitegroup_ids"] = _replace_id(
            site["sitegroup_ids"], sitegroup_id_dict)
    ids = _common_restore(mist_session, 'orgs',  org_id, 'sites', site)
    site_id_dict.update(ids)
    new_site_id = ids[next(iter(ids))]
    settings = _clean_ids(data["settings"])
    if "site_id" in settings:
        del settings["site_id"]
    try:
        message=f"Updating settings "
        log_message(message)
        mist_lib.requests.sites.settings.update(
            mist_session, new_site_id, settings)
        log_success(message)
    except:
        log_failure(message)
    #### SITE > MAP ####
    if "maps" in data:
        for sub_data in data["maps"]:
            sub_data["site_id"] = new_site_id
            ids = _common_restore(mist_session, 'sites', new_site_id, 'maps', sub_data)
            map_id_dict.update(ids)

            old_map_id = next(iter(ids))
            new_map_id = ids[old_map_id]
            image_name = f"{file_prefix}_org_{old_org_id}_site_{old_site_id}_map_{old_map_id}.png"
            if os.path.isfile(image_name):
                message=f"Uploading image floorplan  \"{sub_data['name']}\""
                log_message(message)
                try:
                    mist_lib.requests.sites.maps.add_image(
                        mist_session, new_site_id, new_map_id, image_name)
                    log_success(message)
                except:
                    log_failure(message)
            else:
                log_debug(f"No image found for \"{sub_data['name']}\"")

        if "assetfilters" in data:
            for sub_data in data["assetfilters"]:
                _common_restore(mist_session,  'sites', new_site_id, 'assetfilters', sub_data)

        if "assets" in data:
            for sub_data in data["assets"]:
                _common_restore(mist_session, 'sites', new_site_id, 'assets', sub_data)

        if "beacons" in data:
            for sub_data in data["beacons"]:
                sub_data["map_id"] = _replace_id(
                    sub_data["map_id"], map_id_dict)
                _common_restore(mist_session,  'sites', new_site_id, 'beacons', sub_data)

        if "psks" in data:
            for sub_data in data["psks"]:
                sub_data["site_id"] = new_site_id
                _common_restore(mist_session,  'sites', new_site_id, 'psks', sub_data)

        if "rssizones" in data:
            for sub_data in data["rssizones"]:
                _common_restore(mist_session,  'sites', new_site_id, 'rssizones', sub_data)

        if "vbeacons" in data:
            for sub_data in data["vbeacons"]:
                sub_data["map_id"] = _replace_id(
                    sub_data["map_id"], map_id_dict)
                _common_restore(mist_session, 'sites', new_site_id, 'vbeacons', sub_data)

        if "webhooks" in data:
            for sub_data in data["webhooks"]:
                _common_restore(mist_session, 'sites', new_site_id, 'webhooks', sub_data)

        if "wxtunnels" in data:
            for sub_data in data["wxtunnels"]:
                ids = _common_restore(mist_session, 'sites', new_site_id, 'wxtunnels', sub_data)
                wxtunnel_id_dict.update(ids)

        if "zones" in data:
            for sub_data in data["zones"]:
                sub_data["map_id"] = _replace_id(
                    sub_data["map_id"], map_id_dict)
                _common_restore(mist_session, 'sites', new_site_id, 'zones', sub_data)

        if "wlans" in data:
            for sub_data in data["wlans"]:
                _wlan_restore(mist_session, 'sites', new_site_id, sub_data, old_org_id, old_site_id)

        if "wxtags" in data:
            for sub_data in data["wxtags"]:
                if sub_data["match"] == "wlan_id":
                    _replace_id(sub_data["values"], wlan_id_dict)
                ids = _common_restore(mist_session,  'sites', new_site_id, 'wxtags', sub_data)
                wxtags_id_dict.update(ids)

        if "wxrules" in data:
            for sub_data in data["wxrules"]:
                if "src_wxtags" in sub_data:
                    sub_data["src_wxtags"] = _replace_id(
                        sub_data["src_wxtags"], wxtags_id_dict)
                if "dst_allow_wxtags" in sub_data:
                    sub_data["dst_allow_wxtags"] = _replace_id(
                        sub_data["dst_allow_wxtags"], wxtags_id_dict)
                if "dst_deny_wxtags" in sub_data:
                    sub_data["dst_deny_wxtags"] = _replace_id(
                        sub_data["dst_deny_wxtags"], wxtags_id_dict)
                _common_restore(mist_session, 'sites', new_site_id, 'wxrules', sub_data)                


##########################################################################################
################## RESTORE ORG
def _restore_org(mist_session, org_id, org_name, org, custom_dest_org_name=None):
    print()
    print(f" Deploying Org {org_name} ".center(80, "_"))
    
    ####################
    ####  ORG MAIN  ####
    data = org["data"]
    old_org_id = data["id"]

    del data["id"]
    if "orggroup_ids" in data:
        del data["orggroup_ids"]
    if "msp_id" in data:
        del data["msp_id"]
    if "msp_name" in data:
        del data["msp_name"]
    if custom_dest_org_name:
        data["name"] = custom_dest_org_name

    message="Org Info "
    log_message(message)
    try:
        mist_lib.requests.orgs.info.update(mist_session, org_id, data)
        log_success(message)
    except:
        log_failure(message)
    
    ########################
    ####  ORG SETTINGS  ####
    mesage="Org Settings "
    log_message(message)
    try:
        data = _clean_ids(org["settings"])
        mist_lib.requests.orgs.settings.update(mist_session, org_id, data)
        log_success(message)
    except:
        log_failure(message)

    #######################
    ####  ORG OBJECTS  ####
    if "webhooks" in org:
        for data in org["webhooks"]:
            _common_restore(mist_session,'orgs', org_id, 'webhooks', data)

    if "assetfilters" in org:
        for data in org["assetfilters"]:
            _common_restore(mist_session, 'orgs',  org_id, 'assetfilters', data)

    if "deviceprofiles" in org:
        for data in org["deviceprofiles"]:
            ids = _common_restore(mist_session, 'orgs',  org_id, 'deviceprofiles', data)
            deviceprofile_id_dict.update(ids)

    if "alarmtemplates" in org:
        for data in org["alarmtemplates"]:
            ids = _common_restore(mist_session, 'orgs',  org_id, 'alarmtemplates', data)
            deviceprofile_id_dict.update(ids)

    if "mxclusters" in org:
        for data in org["mxclusters"]:
            ids = _common_restore(mist_session,  'orgs',  org_id, 'mxclusters', data)
            mxcluster_id_dict.update(ids)

    if "mxtunnels" in org:
        for data in org["mxtunnels"]:
            data["mxcluster_ids"] = _replace_id(
                data["mxcluster_ids"], mxcluster_id_dict)
            ids = _common_restore(mist_session, 'orgs',  org_id, 'mxtunnels', data)
            mxtunnel_id_dict.update(ids)

    if "psks" in org:
        for data in org["psks"]:
            _common_restore(mist_session,
                            'orgs', org_id, 'psks', data)

    if "secpolicies" in org:
        for data in org["secpolicies"]:
            ids = _common_restore(mist_session, 'orgs', org_id, 'secpolicies', data)
            secpolicy_id_dict.update(ids)

    if "rftemplates" in org:
        for data in org["rftemplates"]:
            ids = _common_restore(mist_session,  'orgs', org_id, 'rftemplates', data)
            rftemplate_id_dict.update(ids)

    if "networktemplates" in org:
        for data in org["networktemplates"]:
            ids = _common_restore(mist_session,'orgs', org_id, 'networktemplates', data)
            networktemplate_id_dict.update(ids)

    if "evpn_topologies" in org:
        for data in org["evpn_topologies"]:
            ids = _common_restore(mist_session, 'orgs', org_id, 'evpn_topologies', data)
            evpn_topology_id_dict.update(ids)

    if "services" in org:
        for data in org["services"]:
            ids = _common_restore(mist_session, 'orgs', org_id, 'services', data)
            service_id_dict.update(ids)

    if "networks" in org:
        for data in org["networks"]:
            ids = _common_restore(mist_session, 'orgs', org_id, 'networks', data)
            network_id_dict.update(ids)

    if "vpns" in org:
        for data in org["vpns"]:
            ids = _common_restore(mist_session, 'orgs', org_id, 'vpns', data)
            vpn_id_dict.update(ids)

    if "hubprofiles" in org:
        for data in org["hubprofiles"]:
            ids = _common_restore(mist_session,  'orgs', org_id, 'hubprofiles', data)
            hubprofile_id_dict.update(ids)

    if "gatewaytemplates" in org:
        for data in org["gatewaytemplates"]:
            ids = _common_restore(mist_session, 'orgs', org_id, 'gatewaytemplates', data)
            gatewaytemplate_id_dict.update(ids)

    if "sitegroups" in org:
        for data in org["sitegroups"]:
            if "site_ids" in data:
                del data["site_ids"]
            ids = _common_restore(mist_session, 'orgs', org_id, 'sitegroups', data)
            sitegroup_id_dict.update(ids)

    if "wxtags" in org:
        for data in org["wxtags"]:
            if data["match"] == "wlan_id":
                _replace_id(data["values"], wlan_id_dict)
            ids = _common_restore(mist_session,'orgs', org_id, 'wxtags', data)
            wxtags_id_dict.update(ids)

    for data in org["wxrules"]:
        data["src_wxtags"] = _replace_id(data["src_wxtags"], wxtags_id_dict)
        data["dst_allow_wxtags"] = _replace_id(
            data["dst_allow_wxtags"], wxtags_id_dict)
        data["dst_deny_wxtags"] = _replace_id(
            data["dst_deny_wxtags"], wxtags_id_dict)
        _common_restore(mist_session, 'orgs',  org_id, 'wxrules', data)

    for data in org["wxtunnels"]:
        ids = _common_restore(mist_session,'orgs', org_id, 'wxtunnels', data)
        wxtunnel_id_dict.update(ids)

    ######################
    ####  SITES LOOP  ####
    for data in org["sites"]:
        _restore_site(mist_session, data, org_id, old_org_id)
        

    #######################
    #### ORG FINALIZER ####
    print(f" Deploying Common Org Objects ".center(80, "_"))
    for data in org["templates"]:
        if "applies" in data:
            if "org_id" in data["applies"]:
                data["applies"]["org_id"] = org_id
            if "site_ids" in data["applies"]:
                data["applies"]["site_ids"] = _replace_id(
                    data["applies"]["site_ids"], site_id_dict)
            if "sitegroup_ids" in data["applies"]:
                data["applies"]["sitegroup_ids"] = _replace_id(
                    data["applies"]["sitegroup_ids"], sitegroup_id_dict)
        if "exceptions" in data:
            if "site_ids" in data["exceptions"]:
                data["exceptions"]["site_ids"] = _replace_id(
                    data["exceptions"]["site_ids"], site_id_dict)
            if "sitegroup_ids" in data["exceptions"]:
                data["exceptions"]["sitegroup_ids"] = _replace_id(
                    data["exceptions"]["sitegroup_ids"], sitegroup_id_dict)
        if "deviceprofile_ids" in data:
            data["deviceprofile_ids"] = _replace_id(
                data["deviceprofile_ids"], deviceprofile_id_dict)
        ids = _common_restore(mist_session, 'orgs', org_id, 'templates', data)
        template_id_dict.update(ids)

    for data in org["wlans"]:
        _wlan_restore(mist_session, 'orgs',org_id, data, old_org_id, None)

    for data in org["ssos"]:
        _common_restore(mist_session, 'orgs', org_id, 'ssos', data)

    for data in org["ssoroles"]:
        cleaned_privileges = {
            "privileges": [],
            "org_id": org_id,
            "name": data["name"]
        }
        for privilege in data["privileges"]:
            cleaned_privileges["privileges"].append(
                _clean_ssorole_privileges(privilege, org_id))
        _common_restore(mist_session,'orgs',org_id, 'ssoroles', cleaned_privileges)


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
    os.chdir(backup_directory)
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


def _check_org_name(org_name):
    while True:
        print()
        resp = input(
            "To avoid any error, please confirm the current destination orgnization name: ")
        if resp == org_name:
            return True
        else:
            print()            
            print("The orgnization names do not match... Please try again...")


def start_restore_org(mist_session, org_id, org_name, source_org_name, check_org_name=True, in_backup_folder=False, custom_dest_org_name=None, parent_logger=None):
    global logger
    if parent_logger:
        logger=parent_logger
    if check_org_name and not custom_dest_org_name:
        _check_org_name(org_name)
    if not in_backup_folder:
        _go_to_backup_folder(source_org_name)
    print()
    message=f"Loading template/backup file {backup_file} "
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
            _restore_org(mist_session, org_id, org_name,
                         backup["org"], custom_dest_org_name)
            print()
            print("Importation process finished...")


def _create_org(mist_session):
    while True:
        custom_dest_org_name = input("What is the new Organization name? ")
        if custom_dest_org_name:
            org = {
                "name": custom_dest_org_name
            }
            message=f"Creating the organisation \"{custom_dest_org_name}\" in {mist_session.host} "
            log_message(message)
            try:
                log_success(message)
            except:
                log_failure(message)
                sys.exit(10)
            org_id = mist_lib.requests.orgs.orgs.create(mist_session, org)[
                "result"]["id"]
            start_restore_org(mist_session, org_id, custom_dest_org_name, None,
                              check_org_name=False, custom_dest_org_name=custom_dest_org_name)
            break


def start(mist_session):
    print()
    print(" Destination Org ".center(80, "-"))
    print()
    while True:
        res = input(
            "Do you want to create a (n)ew organisation or (r)estore to an existing one? ")
        if res.lower() == "r":
            org_id = cli.select_org(mist_session)[0]
            org_name = mist_lib.requests.orgs.info.get(
                mist_session, org_id)["result"]["name"]
            start_restore_org(mist_session, org_id, org_name,
                              None, check_org_name=True)
            break
        elif res.lower() == "n":
            _create_org(mist_session)
            break


#### SCRIPT ENTRYPOINT ####
if __name__ == "__main__":
    mist_session = mist_lib.Mist_Session(session_file)
    start(mist_session)

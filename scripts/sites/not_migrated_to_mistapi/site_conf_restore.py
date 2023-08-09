'''
Written by: Thomas Munzer (tmunzer@juniper.net)
Github repository: https://github.com/tmunzer/Mist_library/

Python script to restore site template/backup file.
You can use the script "org_site_backup.py" to generate the backup file from an
existing organization.

This script will not overide existing objects. If you already configured objects in the 
destination organisation, new objects will be reused or created. If you want to "reset" the 
destination organization, you can use the script "org_conf_zeroise.py".
This script is trying to maintain objects integrity as much as possible. To do so, when 
an object is referencing another object by its ID, the script will replace be ID from 
the original organization by the corresponding ID from the destination org.

You can run the script with the command "python3 site_conf_import.py"

The script has 3 different steps:
1) admin login
2) choose the destination org
3) choose the backup/template to restore
all the objects will be created from the json file. 
'''

#### IMPORTS ####
import sys
import mistapi
from mistapi.__logger import console
import logging
import json
import os.path
#### PARAMETERS #####
backup_directory = "./site_backup/"
log_file = "./sites_scripts.log"
org_id = ""
env_file = "./.env"
#### LOGS ####
logger = logging.getLogger(__name__)

#### CONSTANTS ####
backup_file = "./site_conf_file.json"
file_prefix = ".".join(backup_file.split(".")[:-1])


#### GLOBAL VARS ####


rftemplate_id = None
sitegroup_ids = []
map_id_dict = {}
wlan_id_dict = {}
wxtags_id_dict = {}
secpolicy_id = None
alarmtemplate_id = None
networktemplate_id = None

#### FUNCTIONS ####

def _get_new_id(old_id, new_ids_dict):
    if old_id in new_ids_dict:
        new_id = new_ids_dict[old_id]
        console.debug("Replacing id {0} with id {1}".format(old_id, new_id))
        return new_id
    else:
        console.debug("Unable to replace id {0}".format(old_id))
        return None


def _replace_id(old_ids_list, new_ids_dict):
    if not old_ids_list:
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
        console.error("Unable to replace ids: {0}".format(old_ids_list))



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





def _wlan_restore(apisession, site_name, new_site_id, data, old_site_id):
    if "wxtunnel_id" in data:
        data["wxtunnel_id"] = _replace_id(data["wxtunnel_id"], wxtags_id_dict)
    if "app_limit" in data and "wxtag_ids" in data["app_limit"]:
        data["app_limit"]["wxtag_ids"] = _replace_id(data["app_limit"]["wxtag_ids"], wxtags_id_dict)
    ids = _common_restore(apisession, site_name, new_site_id, 'wlans', data)
    old_wlan_id = next(iter(ids))
    new_wlan_id = ids[old_wlan_id]
    _wlan_restore_portal(apisession, site_name, new_site_id, old_site_id, old_wlan_id, new_wlan_id, data["ssid"])
    wlan_id_dict.update(ids)


def _wlan_restore_portal_template(apisession, site_id, wlan_id, portal_file_name, wlan_name):
    if os.path.isfile(portal_file_name):
        print("Creating Portal Template for WLAN {0}".format(wlan_name).ljust(79, "."), end="", flush=True)
        try:
            f = open(portal_file_name, 'r')
        except:
            print('\033[31m\u2716\033[0m')
            print("Unable to open the template file {0} ".format(portal_file_name).ljust(79, ".") +'\033[31m\u2716\033[0m')
            return
        try:
            template = json.load(f)            
        except:
            print('\033[31m\u2716\033[0m')
            print("Unable to read the template file {0}".format(portal_file_name).ljust(79, ".") +'\033[31m\u2716\033[0m')
            return
        try:
            mistapi.api.v1.sites.wlans.set_portal_template(apisession, site_id, wlan_id, template)
            print("\033[92m\u2714\033[0m")
        except:
            print('\033[31m\u2716\033[0m')
            print("Unable to upload the template {0}...".format(portal_file_name).ljust(79, ".") +'\033[31m\u2716\033[0m')
    else: print("No Portal Template image found for WLAN {0} ".format(wlan_name).ljust(79, ".") + "\033[33m\u2731\033[0m")


def _wlan_restore_portal(apisession, site_name, new_site_id, old_site_id, old_wlan_id, new_wlan_id, wlan_name): 
    portal_file_name = "{0}_site_{1}_wlan_{2}.json".format(file_prefix, old_site_id, old_wlan_id) 
    portal_image = "{0}_site_{1}_wlan_{2}.png".format(file_prefix, old_site_id, old_wlan_id)
    module = mistapi.api.v1.route("sites", "wlans")

    _wlan_restore_portal_template(apisession, new_site_id, new_wlan_id, portal_file_name, wlan_name)       

    if os.path.isfile(portal_image):
        print("Uploading Portal image for WLAN {0} ".format(wlan_name).ljust(79, "."), end="", flush=True)
        try:            
            module.add_portal_image(apisession, new_site_id, new_wlan_id, portal_image)
            print('\033[31m\u2716\033[0m')
        except:
            print('\033[31m\u2716\033[0m')
    else: print("No Portal Template image found ".ljust(79, ".") + "\033[33m\u2731\033[0m")
        

def _common_restore(apisession, site_name, site_id, obj_type, data):       
    old_id = data["id"] if "id" in data else None
    if "name" in data:
        obj_name = data["name"]
    elif "ssid" in data:
        obj_name = data["ssid"]
    elif "order" in data:
        obj_name = "#{0}".format(data["order"])
    else:
        obj_name = None
    
    data = _clean_ids(data)
    
    module = mistapi.api.v1.route("sites", obj_type)
    new_id = _create_obj(module.create(apisession, site_id, data), obj_type, obj_name)        
    
    return {old_id: new_id}


def _create_obj(m_func_create, obj_type, obj_name=None):
    try:        
        if obj_name: print("Creating {0} \"{1}\" ".format(obj_type, obj_name).ljust(79, "."), end="", flush=True)
        else: print("Creating {0} ".format(obj_type).ljust(79, "."), end="", flush=True)
        response = m_func_create
        if "result" in response and "id" in response.data: new_id = response.data["id"]
        elif "id" in response: new_id = response["id"]
        else: new_id = None
        print("\033[92m\u2714\033[0m")
    except:
        new_id = None
        print('\033[31m\u2716\033[0m')
    finally:
        return new_id


def _process_org_obj(m_func_create, available_obj, obj_type, obj_name):
    print("Processing {0} \"{1}\" ".format(obj_type, obj_name).ljust(80, "."))
    try:
        new_id = next(item["id"] for item in available_obj if item["name"]==obj_name)
        print(" Reusing existing {0}".format(obj_type).ljust(79, ".") +"\033[92m\u2714\033[0m")
    except: 
        print(" {0} not found ".format(obj_type).ljust(79, ".") +"\033[33m\u2731\033[0m")
        new_id = _create_obj(m_func_create, obj_type, obj_name)        
    finally:
        return new_id


def _restore_site(apisession, org_id, org_name, site_name, backup):
    old_site_id = backup["site"]["info"]["id"]
    new_site_id = None
    assigned_sitegroup_ids = []
    assigned_rftempate_id = None
    assigned_secpolicy_id = None
    assigned_alarmtemplate_id = None
    assigned_networktemplate_id = None

    ### lookup for site groups ###
    if not backup["sitegroup_names"] == []:        
        available_sitegroups = mistapi.api.v1.orgs.sitegroups.listOrgSiteGroups(apisession, org_id).data
        for sitegroup_name in backup["sitegroup_names"]:
            new_sitegroup_id= _process_org_obj(mistapi.api.v1.orgs.sitegroups.createOrgSiteGroup(apisession, org_id, {"name":sitegroup_name}), available_sitegroups, "Site Group", sitegroup_name)            
            assigned_sitegroup_ids.append(new_sitegroup_id)

    ### lookup for RF templates ###
    if not backup["rftemplate"] == {}:
        available_rftemplates = mistapi.api.v1.orgs.rftemplates.listOrgRfTemplates(apisession, org_id).data
        new_rftemplate_id = _process_org_obj(mistapi.api.v1.orgs.rftemplates.createOrgRfTemplate(apisession, org_id, backup["rftemplate"]), available_rftemplates, "RF Template", backup["rftemplate"]["name"])   
        assigned_rftempate_id = new_rftemplate_id

    ### lookup for security policy ###
    if not backup["secpolicy"] == {}:
        available_secpolicies = mistapi.api.v1.orgs.secpolicies.listOrgSecPolicies(apisession, org_id).data
        new_secpolicy_id = _process_org_obj(mistapi.api.v1.orgs.secpolicies.createOrgSecPolicies(apisession, org_id, backup["secpolicy"]), available_secpolicies, "Security Policy", backup["secpolicy"]["name"])   
        assigned_secpolicy_id = new_secpolicy_id

    ### lookup for Alarm templates ###
    if not backup["alarmtemplate"] == {}:
        available_alarmtemplates = mistapi.api.v1.orgs.alarmtemplates.listOrgAlarmTemplates(apisession, org_id).data
        new_alarmtemplate_id = _process_org_obj(mistapi.api.v1.orgs.alarmtemplates.createOrgAlarmTemplate(apisession, org_id, backup["alarmtemplate"]), available_alarmtemplates, "Alarm Template", backup["alarmtemplate"]["name"])   
        assigned_alarmtemplate_id = new_alarmtemplate_id

    ### lookup for network templates ###
    if not backup["networktemplate"] == {}:
        available_networktemplates = mistapi.api.v1.orgs.networktemplates.listOrgNetworkTemplates(apisession, org_id).data
        new_networktemplate_id = _process_org_obj(mistapi.api.v1.orgs.networktemplates.createOrgNetworkTemplate(apisession, org_id, backup["networktemplate"]), available_networktemplates, "Network Template", backup["networktemplate"]["name"])  
        assigned_networktemplate_id = new_networktemplate_id

    ### restore site ###
    print("Updating site info with new IDs ".ljust(79, "."), end="", flush=True)
    new_site = backup["site"]["info"]
    new_site["name"] = site_name
    new_site["sitegroup_ids"] = assigned_sitegroup_ids
    new_site["rftemplate_id"] = assigned_rftempate_id
    new_site["secpolicy_id"] = assigned_secpolicy_id
    new_site["alarmtemplate_id"] = assigned_alarmtemplate_id
    new_site["networktemplate_id"] = assigned_networktemplate_id
    print("\033[92m\u2714\033[0m")

    ### create site ### 
    new_site_id = _create_obj(mistapi.api.v1.orgs.sites.createOrgSite(apisession, org_id, new_site), "Site", site_name)
    if not new_site_id:
        console.error("Unable to create the new site... Exiting...")
        sys.exit(1)

    ### set site settings ###
    try:        
        print("Configuring Site Settings ".ljust(79, "."), end="", flush=True)
        mistapi.api.v1.sites.setting.updateSiteSettings(apisession, new_site_id, backup["site"]["settings"])
        print("\033[92m\u2714\033[0m")
    except:    
        print('\033[31m\u2716\033[0m')
    
    ####  SITES MAIN  ####
    data = backup["site"]
    if "maps" in data:
        for sub_data in data["maps"]:
            sub_data["site_id"] = new_site_id
            ids = _common_restore(apisession, site_name, new_site_id, 'maps', sub_data)
            map_id_dict.update(ids)

            old_map_id = next(iter(ids))
            new_map_id = ids[old_map_id]

            image_name = "{0}_site_{1}_map_{2}.png".format(file_prefix, old_site_id, old_map_id)
            if os.path.isfile(image_name):
                print("Uploading image floorplan for the map {0} ".format(sub_data["name"]).ljust(79, "."), end="", flush=True)
                try:                
                    mistapi.api.v1.sites.maps.add_image(apisession, new_site_id, new_map_id, image_name)
                    print("\033[92m\u2714\033[0m")
                except:
                    print('\033[31m\u2716\033[0m')
            else:
                print("No image found for map {0}".format(sub_data["name"]).ljust(79, "."), end="", flush=True)
                print("\033[33m\u2731\033[0m")


    if "assetfilters" in data:
        for sub_data in data["assetfilters"]:
            _common_restore(apisession, site_name, new_site_id, 'assetfilters', sub_data)

    if "assets" in data:
        for sub_data in data["assets"]:
            _common_restore(apisession, site_name, new_site_id, 'assets', sub_data)

    if "beacons" in data:
        for sub_data in data["beacons"]:
            sub_data["map_id"] = _replace_id(sub_data["map_id"], map_id_dict)
            _common_restore(apisession, site_name, new_site_id, 'beacons', sub_data)

    if "psks" in data:
        for sub_data in data["psks"]:
            sub_data["site_id"] = new_site_id
            _common_restore(apisession, site_name, new_site_id, 'psks', sub_data)

    if "rssizones" in data:
        for sub_data in data["rssizones"]:
            _common_restore(apisession, site_name, new_site_id, 'rssizones', sub_data)

    if "vbeacons" in data:
        for sub_data in data["vbeacons"]:
            sub_data["map_id"] = _replace_id(sub_data["map_id"], map_id_dict)
            _common_restore(apisession, site_name, new_site_id, 'vbeacons', sub_data)

    if "webhooks" in data:
        for sub_data in data["webhooks"]:
            _common_restore(apisession, site_name, new_site_id, 'webhooks', sub_data)

    if "wxtunnels" in data:
        for sub_data in data["wxtunnels"]:
            _common_restore(apisession, site_name, new_site_id, 'wxtunnels', sub_data)

    if "zones" in data:
        for sub_data in data["zones"]:
            sub_data["map_id"] = _replace_id(sub_data["map_id"], map_id_dict)
            _common_restore(apisession, site_name, new_site_id,  'zones', sub_data)
    
    if "wlans" in data:
        for sub_data in data["wlans"]:
            _wlan_restore(apisession, site_name, new_site_id, sub_data, old_site_id)

    if "wxtags" in data:
        for sub_data in data["wxtags"]:
            if sub_data["match"] == "wlan_id":
                _replace_id(sub_data["values"], wlan_id_dict)
            ids = _common_restore(apisession, site_name, new_site_id, 'wxtags', sub_data)
            wxtags_id_dict.update(ids)

    if "wxrules" in data:
        for sub_data in data["wxrules"]:
            if "src_wxtags" in sub_data:
                sub_data["src_wxtags"] = _replace_id(sub_data["src_wxtags"], wxtags_id_dict)
            if "dst_allow_wxtags" in sub_data:
                sub_data["dst_allow_wxtags"] = _replace_id(sub_data["dst_allow_wxtags"], wxtags_id_dict)
            if "dst_deny_wxtags" in sub_data:
                sub_data["dst_deny_wxtags"] = _replace_id(sub_data["dst_deny_wxtags"], wxtags_id_dict)
            _common_restore(apisession, site_name, new_site_id, 'wxrules', sub_data)

    

def _display_warning(message):
    resp = "x"
    while not resp.lower() in ["y", "n", ""]:
        print()
        resp = input(message)
    if not resp.lower()=="y":
        console.warning("Interruption... Exiting...")
        sys.exit(0)

def _select_backup_folder(folders):   
    i = 0
    while i < len(folders):
        print("{0}) {1}".format(i, folders[i]))
        i += 1
    folder = None
    while folder is None:
        resp = input("Please select a folder (0-{0}, or q to quit)? ".format(i))
        if resp.lower() == "q":
            console.warning("Interruption... Exiting...")
            sys.exit(0)
        try:
            respi = int(resp)
            if respi >= 0 and respi <= i:
                folder = folders[respi]
            else:
                print("The value \"{0}\" is not valid. Please try again...".format(resp))
        except:
            print("Only numbers are allowed. Please try again...")
    os.chdir(folder)

def _got_to_site_folder():
    folders = []
    for entry in os.listdir("./"):
        if os.path.isdir(os.path.join("./", entry)):
            folders.append(entry)
    print()
    print("Available sites templates/backup folders:") 
    _select_backup_folder(folders)

def _go_to_backup_folder():
    os.chdir(os.getcwd())
    os.chdir(backup_directory)
    folders = []
    for entry in os.listdir("./"):
        if os.path.isdir(os.path.join("./", entry)):
            folders.append(entry)    
    print()
    print("Available templates/backups folders:")
    _select_backup_folder(folders)
    _got_to_site_folder()

def _print_warning():
    print(""" 

__          __     _____  _   _ _____ _   _  _____ 
\ \        / /\   |  __ \| \ | |_   _| \ | |/ ____|
 \ \  /\  / /  \  | |__) |  \| | | | |  \| | |  __ 
  \ \/  \/ / /\ \ |  _  /| . ` | | | | . ` | | |_ |
   \  /\  / ____ \| | \ \| |\  |_| |_| |\  | |__| |
    \/  \/_/    \_\_|  \_\_| \_|_____|_| \_|\_____|

This script is still in BETA. It won't hurt your original
organization or site, but the restoration may partially fail. 
It's your responsability to validate the importation result!


""")

def _check_org_name(org_name):
    while True:
        print()
        resp = input("To avoid any error, please confirm the current destination orgnization name: ")
        if resp == org_name:
            return True
        else:
            console.warning("The orgnization names do not match... Please try again...")
        print()


def _check_site_exists(org_id, site_name_to_create):    
    existing_sites = mistapi.api.v1.orgs.sites.get(apisession, org_id).data
    try:
        site_id = next(item["id"] for item in existing_sites if item["name"] == site_name_to_create)
        while True:
            print()
            console.warning("Site \"{0}\" already exists in the destination org! ".format(site_name_to_create))
            response = input("What do you want to do: (r)eplace, set a (n)ew name or (a)bort? ")
            if response.lower() == "a":
                console.warning("Interruption... Exiting...")
                sys.exit(0)
            elif response.lower() == "r":
                console.warning("I'm still working on this part... Please try with a later version...")
            elif response.lower() == "n":
                site_name_to_create = input("Name of the site to create: ")
                _check_site_exists(org_id, site_name_to_create)  
                break              
    except:
        pass
    finally:
        return site_name_to_create


def start_restore_org(apisession, org_id, org_name, check_org_name=True, in_backup_folder=False):
    if check_org_name: _check_org_name(org_name)
    if not in_backup_folder: _go_to_backup_folder()    
    print()
    print("Loading template/backup file {0}...".format(backup_file).ljust(79, "."), end="", flush=True)
    try:
        with open(backup_file) as f:
            backup = json.load(f)
        print("\033[92m\u2714\033[0m")
    except: 
        print("Unable to load the template/bakup!", end="", flush=True)
        print('\033[31m\u2716\033[0m')
        sys.exit(1)
    finally:
        if backup:
            print()
            site_name_to_create = input("Name of the site to create: ")
            site_name_to_create = _check_site_exists(org_id, site_name_to_create)

            _display_warning("Are you sure about this? Do you want to import the site configuration into the organization {0} with the id {1} (y/N)? ".format(org_name, org_id))
            _restore_site(apisession, org_id, org_name, site_name_to_create, backup)
        
            print()
            console.info("Importation process finished...")

def start(apisession, org_id=None):
    if org_id == "":
        org_id = mistapi.cli.select_org(apisession)[0]
    org_name = mistapi.api.v1.orgs.orgs.getOrg(apisession, org_id).data["name"]
    start_restore_org(apisession, org_id, org_name)


#### SCRIPT ENTRYPOINT ####


if __name__ == "__main__":
    #### LOGS ####
    logging.basicConfig(filename=log_file, filemode='w')
    logger.setLevel(logging.DEBUG)
    ### START ###
    apisession = mistapi.APISession(env_file=env_file)
    apisession.login()
    start(apisession, org_id)



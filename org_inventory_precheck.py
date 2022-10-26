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

#### PARAMETERS #####
session_file = None
org_id = ""

#### IMPORTS ####

import mlib as mist_lib
from mlib.__debug import Console
from mlib import cli
import json
import os.path
console = Console(6)



#### CONSTANTS ####
backup_file = "./org_inventory_file.json"
file_prefix = ".".join(backup_file.split(".")[:-1])
backup_directory = "./org_backup/"

#### GLOBAL VARS ####



site_id_dict = {}
map_id_dict = {}
deviceprofile_id_dict = {}

missing_ids = {
    "sites": [],
    "maps": [],
    "deviceprofiles": []
}

#### FUNCTIONS ####

## Final tests
def _find_name_by_old_id(object_id_dict, old_object_id):
    for name in object_id_dict:
        if object_id_dict["old_id"] == old_object_id: return name

def _result(backup):
    print('')
    if len(missing_ids["sites"]) == 0 and len(missing_ids["maps"]) == 0 and len(missing_ids["deviceprofiles"])==0:
        console.info("Pre check validation succed!")
        console.info("No object missing, you can restore the devices")
    else:
        console.error("Pre check validation failed!")
        console.error("Please create the following object to the new org before restoring the devices.")
        print("")
        if len(missing_ids["sites"]) > 0:
            console.error("Missing sites:")
            for missing_site in missing_ids["sites"]:
                console.error(f"    - {missing_site}")
        if len(missing_ids["maps"]) > 0:
            console.error("Missing maps:")
            for missing_map in missing_ids["maps"]:
                console.error(f"    - {missing_map}" )
        if len(missing_ids["deviceprofiles"]) > 0:
            console.error("Missing deviceprofiles:")
            for missing_deviceprofile in missing_ids["deviceprofiles"]:
                console.error(f"    - {missing_deviceprofile}" )
    print("")
## site id
def _link_sites_ids(mist_session, org_id, sites_ids):
    new_sites = mist_lib.requests.orgs.sites.get(mist_session, org_id)["result"] 
    return _link_objects_ids(new_sites, sites_ids)

def _find_new_site_id_by_old_id(site_id_dict, old_id):
    return _find_new_object_id_by_old_id("sites", site_id_dict, old_id)

def _find_new_site_id_by_name(site_id_dict, site_name):
    if "new_id" in site_id_dict[site_name]:
        return site_id_dict[site_name]["new_id"]
    _missing_name_object("sites", site_id_dict, site_name)
    return None

## map id
def _link_maps_id(mist_session, site_id, maps_ids):
    new_maps = mist_lib.requests.sites.maps.get(mist_session, site_id)["result"]
    return _link_objects_ids(new_maps, maps_ids)

def _find_new_map_id_by_old_id(map_id_dict, old_id):
    return _find_new_object_id_by_old_id("maps", map_id_dict, old_id)

def _find_new_site_id_by_name(map_id_dict, map_name):
    if "new_id" in map_id_dict[map_name]:
        return map_id_dict[map_name]["new_id"]
    _missing_name_object("maps", map_id_dict, map_name)
    return None

## device profiles
def _link_deviceprofiles_ids(mist_session, org_id, deviceprofiles_ids):
    new_deviceprofiles = mist_lib.requests.orgs.deviceprofiles.get(mist_session, org_id)["result"]
    return _link_objects_ids(new_deviceprofiles, deviceprofiles_ids)

def _find_new_deviceprofile_id_by_old_id(deviceprofile_id_dict, old_id):
    return _find_new_object_id_by_old_id("deviceprofiles", deviceprofile_id_dict, old_id)

def _find_new_deviceprofile_id_by_name(deviceprofile_id_dict, deviceprofile_name):
    if "new_id" in deviceprofile_id_dict[deviceprofile_name]:
        return deviceprofile_id_dict[deviceprofile_name]["new_id"]
    _missing_name_object("deviceprofiles", deviceprofile_id_dict, deviceprofile_name)
    return None

## commons
def _link_objects_ids(new_object_dict, objects_link_dict):
    if not objects_link_dict == {}:
        for obj in new_object_dict:
            if obj["name"] in objects_link_dict:
                objects_link_dict[obj["name"]]["new_id"] = obj["id"]
    return objects_link_dict

def _find_new_object_id_by_old_id(object_name, object_id_dict, old_id):
    new_id = None
    for obj in object_id_dict:
        if object_id_dict[obj]["old_id"] == old_id:
            if "new_id" in object_id_dict[obj]:
                new_id = object_id_dict[obj]["new_id"]
            else:
                _missing_old_id_object(object_name, object_id_dict, old_id)
            break
    return new_id


def _missing_old_id_object(object_name, object_id_dict, old_id):
    for obj in object_id_dict:
        if object_id_dict[obj]["old_id"] == old_id:
            console.error(f"Unable to find the new id for the {obj} with old id {old_id}")
            missing_ids[object_name].append(f"{obj} (old_id id: {old_id}")


def _missing_name_object(object_name, object_id_dict, name):
    missing_ids[object_name].append(f"{name} (old id: {object_id_dict[name]['old_id']})")

def _clean_ids(data):
    if "org_id" in data:
        del data["org_id"]
    if "modified_time" in data:
        del data["modified_time"]
    if "created_time" in data:
        del data["created_time"]
    return data

## restore
def _restore_device_image(org_id, site_id, device_id, i):
    image_name = f"{file_prefix}_org_{org_id}_device_{device_id}_image_{i}.png"
    if os.path.isfile(image_name):
        console.info(f"Image {image_name} will be restored to device {device_id}")
        return True
    else:
        console.debug(f"Image {image_name} not found for device id {device_id}")
        return False

def _restore_devices(new_site_id, site_name, deviceprofile_id_dict, map_id_dict, devices):
    for device in devices:
        console.info(f"SITE {site_name} > DEVICE SERIAL {device['serial']} > Updating ids")      

        device = _clean_ids(device)

        if device["deviceprofile_id"]:
            device["deviceprofile_id"] = _find_new_deviceprofile_id_by_old_id(deviceprofile_id_dict, device["deviceprofile_id"]) 

        if device["map_id"]:
            device["map_id"] = _find_new_map_id_by_old_id(map_id_dict, device["map_id"]) 

        device["site_id"] = new_site_id  

        console.info(f"SITE {site_name} > DEVICE SERIAL {device['serial']} > Restoration in progress")   
        i=1
        image_exists = True
        console.info(f"SITE {site_name} > DEVICE SERIAL {device['serial']} > Images Restoration in progress")  
        while image_exists:
            image_exists = _restore_device_image(org_id, new_site_id, device["id"], i)
            i+=1
        console.info(f"SITE {site_name} > DEVICE SERIAL {device['serial']} > Restoration finished")

#### SCRIPT ENTRYPOINT ####


def _precheck(mist_session, dest_org_id, backup, site_name = None):
    print(""" 

    This script is still in BETA. It won't hurt your original
    organization, but the restoration may partially fail. 
    It's your responsability to validate the importation result!


    """)
    deviceprofile_id_dict = _link_deviceprofiles_ids(mist_session, dest_org_id, backup["deviceprofiles_ids"])
    site_id_dict = _link_sites_ids(mist_session, dest_org_id, backup["sites_ids"])
    for restore_site_name in backup["sites_names"]:
        if not site_name or restore_site_name == site_name:
            site = backup["sites"][restore_site_name]
            console.notice(f"Restoring Site {restore_site_name}")

            new_site_id = _find_new_site_id_by_name(site_id_dict, restore_site_name) 
            
            if new_site_id is None:
                if new_site_id in missing_ids["sites"]: 
                    missing_ids["sites"].append(new_site_id)
            else:              
                map_id_dict = _link_maps_id(mist_session, new_site_id, site["maps_ids"]) 
                print(map_id_dict)
                _restore_devices(new_site_id, restore_site_name, deviceprofile_id_dict, map_id_dict, site["devices"])
        console.notice(f"Site {restore_site_name} restored")
    _result(backup)

def _select_backup_folder(folders):   
    i = 0
    print("Available backups:")
    while i < len(folders):
        print(f"{i}) {folders[i]}")
        i += 1
    folder = None
    while folder is None:
        resp = input(f"Which backup do you want to restore (0-{i}, or x or exit)? ")
        if resp.lower() == "x":
            console.warning("Interruption... Exiting...")
        try:
            respi = int(resp)
            if respi >= 0 and respi <= i:
                folder = folders[respi]
            else:
                print(f"The entry value \"{respi}\" is not valid. Please try again...")
        except:
            print("Only numbers are allowed. Please try again...")
    os.chdir(folder)

def _go_to_backup_folder(source_org_name=None):
    os.chdir(os.getcwd())
    os.chdir(backup_directory)
    folders = []
    for entry in os.listdir("./"):
        if os.path.isdir(os.path.join("./", entry)):
            folders.append(entry)
    if source_org_name in folders:
        print(f"Backup found for organization {source_org_name}.")
        loop = True
        while loop:
            resp = input("Do you want to use this backup (y/n)? ")
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
        print(f"Backup folder for organization {source_org_name} not found. Please select a folder in the following list.")
        _select_backup_folder(folders)

def start_precheck(mist_session, org_id, org_name=None, source_org_name=None, site_name=None, in_backup_folder=False, parent_logger=None):
    global logger
    if parent_logger:
        logger=parent_logger
    print(os.getcwd())  
    if not in_backup_folder: _go_to_backup_folder(source_org_name)
    #try:
    with open(backup_file) as f:
        backup = json.load(f)
    console.info(f"File {backup_file} loaded succesfully.")
    _precheck(mist_session, org_id, backup["org"], site_name)
    #except:
    #    return 255

def start(mist_session, org_id=None, source_org_name=None, site_name=None):
    if org_id == "":
        org_id = cli.select_org(mist_session)[0]
    org_name = mist_lib.requests.orgs.info.get(mist_session, org_id)["result"]["name"]
    start_precheck(mist_session, org_id, org_name, source_org_name, site_name)


#### SCRIPT ENTRYPOINT ####


if __name__ == "__main__":
    mist_session = mist_lib.Mist_Session(session_file)
    start(mist_session, org_id)


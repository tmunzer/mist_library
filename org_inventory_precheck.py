'''
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
from tabulate import tabulate
import json
import os.path
console = Console(6)



#### CONSTANTS ####
backup_file = "./org_inventory_file.json"
file_prefix = ".".join(backup_file.split(".")[:-1])
backup_directory = "./backup/"

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

## site id
def _link_sites_ids(mist_session, org_id, sites_ids):
    new_sites = mist_lib.requests.orgs.sites.get(mist_session, org_id)["result"] 
    for site in new_sites:
        if site["name"] in sites_ids:
            sites_ids[site["name"]]["new_id"] = site["id"]
    return sites_ids            

def _find_new_site_id_by_old_id(site_id_dict, old_id):
    for site in site_id_dict:
        if site["old_id"] == old_id:
            return site["new_id"]
    add_missing_object_by_old_id("sites", site_id_dict, old_id)
    return None

def _find_new_site_id_by_name(site_id_dict, site_name):
    if "new_id" in site_id_dict[site_name]:
        return site_id_dict[site_name]["new_id"]
    add_missing_object_by_name("sites", site_id_dict, site_name)
    return None

## map id
def _link_maps_id(mist_session, site_id, maps_ids):
    new_maps = mist_lib.requests.sites.maps.get(mist_session, site_id)["result"]
    for xmap in new_maps:
        if xmap["name"] in maps_ids:
            maps_ids[xmap["name"]]["new_id"] = xmap["id"]
    return xmap

def _find_new_map_id_by_old_id(map_id_dict, old_id):
    for xmap in map_id_dict:
        if xmap["old_id"] == old_id:
            return xmap["new_id"]
    add_missing_object_by_old_id("maps", map_id_dict, old_id)
    return None

def _find_new_site_id_by_name(map_id_dict, map_name):
    if "new_id" in map_id_dict[map_name]:
        return map_id_dict[map_name]["new_id"]
    add_missing_object_by_name("maps", map_id_dict, map_name)
    return None

## device profiles
def _link_deviceprofiles_ids(mist_session, org_id, deviceprofiles_ids):
    new_deviceprofiles = mist_lib.requests.orgs.deviceprofiles.get(mist_session, org_id)["result"]
    for deviceprofile in new_deviceprofiles:
        if deviceprofile["name"] in deviceprofiles_ids:
            deviceprofiles_ids[deviceprofile["name"]]["new_id"] = deviceprofile["id"]
    return deviceprofiles_ids

def _find_new_deviceprofile_id_by_old_id(deviceprofile_id_dict, old_id, site_name=None):
    for deviceprofile in deviceprofile_id_dict:
        if deviceprofile["old_id"] == old_id:
            return deviceprofile["new_id"]
    add_missing_object_by_old_id("deviceprofiles", deviceprofile_id_dict, old_id)
    return None

def _find_new_deviceprofile_id_by_name(deviceprofile_id_dict, deviceprofile_name):
    if "new_id" in deviceprofile_id_dict[deviceprofile_name]:
        return deviceprofile_id_dict[deviceprofile_name]["new_id"]
    add_missing_object_by_name("deviceprofiles", deviceprofile_id_dict, deviceprofile_name)
    return None


## commons
def add_missing_object_by_old_id(object_name, object_id_dict, old_id):
    for o in object_id_dict:
        if o["old_id"] == old_id:
            missing_ids[object_name].append("%s (old id: %s" %(o, old_id))
def add_missing_object_by_name(object_name, object_id_dict, name):
    missing_ids[object_name].append("%s (old id: %s)" %(name, object_id_dict[name]["old_id"]))

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
    image_name = "%s_org_%s_device_%s_image_%s.png" %(file_prefix, org_id, device_id, i)    
    if os.path.isfile(image_name):
        console.info("Image %s will be restored to device %s" %(image_name, device_id))
        return True
    else:
        console.error("Image %s not found for device id %s" %(image_name, device_id))
        return False

def _restore_devices(new_site_id, deviceprofile_id_dict, map_id_dict, devices):
    for device in devices:
        device = _clean_ids(device)

        if device["deviceprofile_id"]:
            device["deviceprofile_id"] = _find_new_deviceprofile_id_by_old_id(deviceprofile_id_dict, device["deviceprofile_id"]) 

        if device["map_id"]:
            device["map_id"] = _find_new_map_id_by_old_id(map_id_dict, device["map_id"]) 

        device["site_id"] = new_site_id  

        i=1
        image_exists = True
        while image_exists:
            image_exists = _restore_device_image(org_id, new_site_id, device["id"], i)
            i+=1


#### SCRIPT ENTRYPOINT ####
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
                console.error("    - %s" %(missing_site))
        if len(missing_ids["maps"]) > 0:
            console.error("Missing maps:")
            for missing_map in missing_ids["maps"]:
                console.error("    - %s" %(missing_map))
        if len(missing_ids["deviceprofiles"]) > 0:
            console.error("Missing deviceprofiles:")
            for missing_deviceprofile in missing_ids["deviceprofiles"]:
                console.error("    - %s" %(missing_deviceprofile))
    print("")

def _precheck(mist_session, dest_org_id, backup, site_name = None):
    print(""" 

    This script is still in BETA. It won't hurt your original
    organization, but the restoration may partially fail. 
    It's your responsability to validate the importation result!


    """)
    deviceprofile_id_dict = _link_deviceprofiles_ids(mist_session, dest_org_id, backup["deviceprofiles_ids"])
    site_id_dict = _link_sites_ids(mist_session, dest_org_id, backup["sites_ids"])

    for restore_site_name in backup["sites"]:
        if not site_name or restore_site_name == site_name:
            site = backup["sites"][restore_site_name]
            print("Restoring Site %s" %(restore_site_name))

            new_site_id = _find_new_site_id_by_name(site_id_dict, restore_site_name) 
            print(new_site_id)
            if new_site_id == None:
                if new_site_id in missing_ids["sites"]: 
                    missing_ids["sites"].append(new_site_id)
            else:              
                map_id_dict = _link_maps_id(mist_session, new_site_id, site["maps_ids"]) 
                _restore_devices(new_site_id, deviceprofile_id_dict, map_id_dict, site["devices"])
    
    _result(backup)


def _go_to_backup_folder(source_org_name=None):
    os.chdir(backup_directory)
    i = 0
    folders = []
    for entry in os.listdir("./"):
        if os.path.isdir(os.path.join("./", entry)):
            folders.append(entry)
            print("%s) %s" %(i, entry))
            i+=1
    try:
        os.chdir(source_org_name)
    except:
        print("Backup folder for organization %s not found. Please select a folder in the following list." %(source_org_name))
        folder = None
        while folder == None:
            resp = input("Which backup do you want to restore (0-%s, or x or exit)? "  %i)
            if resp.lower() == "x":
                console.warning("Interruption... Exiting...")
            try:
                respi = int(resp)
                if respi >= 0 and respi <= i:
                    folder = folders[respi]
                else:
                    print("The entry value \"%s\" is not valid. Please try again...")
            except:
                print("Only numbers are allowed. Please try again...")
        os.chdir(folder)

def start_precheck(mist_session, org_id, org_name, source_org_name=None, site_name=None):
    try:
        _go_to_backup_folder(source_org_name)
        with open(backup_file) as f:
            backup = json.load(f)
        console.info("File %s loaded succesfully." %backup_file)
        _precheck(mist_session, org_id, backup["org"], site_name)
    except:
        return 255

def start(mist_session, org_id=None, site_name=None):
    if org_id == "":
        org_id = cli.select_org(mist_session)
    org_name = mist_lib.requests.orgs.info.get(mist_session, org_id)["result"]["name"]
    start_precheck(mist_session, org_id, org_name, site_name)


#### SCRIPT ENTRYPOINT ####


if __name__ == "__main__":
    mist_session = mist_lib.Mist_Session(session_file)
    start(mist_session, org_id)


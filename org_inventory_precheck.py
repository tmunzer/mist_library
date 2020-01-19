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

#### IMPORTS ####

import mlib as mist_lib
from mlib.__debug import Console
from mlib import cli
from tabulate import tabulate
import json
import os.path
console = Console(6)
backup_file = "./org_inventory_file.json"
file_prefix = ".".join(backup_file.split(".")[:-1])
session_file = None

org_id = ""

with open(backup_file) as f:
    backup = json.load(f)

#### CONSTANTS ####


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

def find_missing_object(object_id, object_list):
    for o in object_list:
        if object_list[o] == object_id: return o

def sync_sites_id():
    old_site_id_dict = backup["org"]["site_id_dict"]
    new_sites = mist_lib.requests.orgs.sites.get(mist_session, org_id)["result"]
    for site in new_sites:
        sync_maps_id(site["id"])
        if site["name"] in old_site_id_dict:
            old_id = old_site_id_dict[site["name"]]
            site_id_dict[old_id] = site["id"]

def sync_maps_id(site_id):
    old_map_id_dict = backup["org"]["map_id_dict"]
    new_maps = mist_lib.requests.sites.maps.get(mist_session, site_id)["result"]
    for xmap in new_maps:
        if xmap["name"] in old_map_id_dict:
            old_id = old_map_id_dict[xmap["name"]]
            map_id_dict[old_id] = xmap["id"]

def sync_deviceprofiles_id():
    old_deviceprofile_id_dict = backup["org"]["deviceprofile_id_dict"]
    new_deviceprofiles = mist_lib.requests.orgs.deviceprofiles.get(mist_session, org_id)["result"]
    for deviceprofile in new_deviceprofiles:
        if deviceprofile["name"] in old_deviceprofile_id_dict:
            old_id = old_deviceprofile_id_dict[deviceprofile["name"]]
            deviceprofile_id_dict[old_id] = deviceprofile["id"]

def get_new_id(old_id, new_ids_dict):
    if old_id in new_ids_dict:
        new_id = new_ids_dict[old_id]
        console.notice("Replacing id %s with id %s" %(old_id, new_id))
        return new_id
    else:
        console.warning("Unable to replace id %s" %old_id)
        return None

def replace_id(old_ids_list, new_ids_dict):
    if old_ids_list == None:
        return None
    if old_ids_list == {}:
        return {}
    elif type(old_ids_list) == str:
        return get_new_id(old_ids_list, new_ids_dict)
    elif type(old_ids_list) == list:
        new_ids_list = []
        for old_id in old_ids_list:
            new_ids_list.append(get_new_id(old_id, new_ids_dict))
        return new_ids_list
    else:
        console.error("Unable to replace ids: %s" % old_ids_list)


def clean_ids(data):
    if "org_id" in data:
        del data["org_id"]
    if "modified_time" in data:
        del data["modified_time"]
    if "created_time" in data:
        del data["created_time"]
    return data

def restore_device_image(org_id, site_id, device_id, i):
    image_name = "%s_org_%s_device_%s_image_%s.png" %(file_prefix, org_id, device_id, i)    
    if os.path.isfile(image_name):
        console.info("Image %s will be restored to device %s" %(image_name, device_id))
        return True
    else:
        console.info("Image %s not found for device id %s" %(image_name, device_id))
        return False

def restore_devices(devices):
    sync_sites_id()
    sync_deviceprofiles_id()
    for device in devices:
        device = clean_ids(device)

        if not device["deviceprofile_id"] == None:
            deviceprofile_id = replace_id(device["deviceprofile_id"], deviceprofile_id_dict) 
            if deviceprofile_id == None and not device["deviceprofile_id"] in missing_ids["deviceprofiles"]: 
                missing_ids["deviceprofiles"].append(device["deviceprofile_id"])
            else:
                device["deviceprofile_id"] = deviceprofile_id

        if not device["map_id"] == None:
            map_id = replace_id(device["map_id"], map_id_dict) 
            if deviceprofile_id == None and not device["map_id"] in missing_ids["maps"]: 
                missing_ids["maps"].append(device["map_id"])
            else:
                device["map_id"] = map_id

        site_id = replace_id(device["site_id"], site_id_dict) 
        if site_id == None and not device["site_id"] in missing_ids["sites"]: 
            missing_ids["sites"].append(device["site_id"])
        else:
            device["site_id"] = site_id
        device["site_id"] = site_id  

        i=1
        image_exists = True
        while image_exists:
            image_exists = restore_device_image(org_id, site_id, device["id"], i)
            i+=1
        
#### SCRIPT ENTRYPOINT ####

mist_session = mist_lib.Mist_Session(session_file)
if org_id == "":
    org_id = cli.select_org(mist_session)

print(""" 

This script is still in BETA. It won't hurt your original
organization, but the restoration may partially fail. 
It's your responsability to validate the importation result!


""")

sync_deviceprofiles_id()
sync_sites_id()    
restore_devices(backup["org"]["devices"])
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
        for missing_id in missing_ids["sites"]:
            console.error("    - %s" %find_missing_object(missing_id, backup["org"]["site_id_dict"]))
    if len(missing_ids["maps"]) > 0:
        console.error("Missing maps:")
        for missing_id in missing_ids["maps"]:
            console.error("    - %s" %find_missing_object(missing_id, backup["org"]["map_id_dict"]))
    if len(missing_ids["deviceprofiles"]) > 0:
        console.error("Missing deviceprofiles:")
        for missing_id in missing_ids["deviceprofiles"]:
            console.error("    - %s" %find_missing_object(missing_id, backup["org"]["deviceprofile_id_dict"]))
print("")

exit(0)

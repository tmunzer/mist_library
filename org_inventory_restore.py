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


#### FUNCTIONS ####


def _sync_sites_id():
    old_site_id_dict = backup["org"]["site_id_dict"]
    new_sites = mist_lib.requests.orgs.sites.get(mist_session, org_id)["result"]
    for site in new_sites:
        _sync_maps_id(site["id"])
        if site["name"] in old_site_id_dict:
            old_id = old_site_id_dict[site["name"]]
            site_id_dict[old_id] = site["id"]

def _sync_maps_id(site_id):
    old_map_id_dict = backup["org"]["map_id_dict"]
    new_maps = mist_lib.requests.sites.maps.get(mist_session, site_id)["result"]
    for xmap in new_maps:
        if xmap["name"] in old_map_id_dict:
            old_id = old_map_id_dict[xmap["name"]]
            map_id_dict[old_id] = xmap["id"]

def _sync_deviceprofiles_id():
    old_deviceprofile_id_dict = backup["org"]["deviceprofile_id_dict"]
    new_deviceprofiles = mist_lib.requests.orgs.deviceprofiles.get(mist_session, org_id)["result"]
    for deviceprofile in new_deviceprofiles:
        if deviceprofile["name"] in old_deviceprofile_id_dict:
            old_id = old_deviceprofile_id_dict[deviceprofile["name"]]
            deviceprofile_id_dict[old_id] = deviceprofile["id"]

def _get_new_id(old_id, new_ids_dict):
    if old_id in new_ids_dict:
        new_id = new_ids_dict[old_id]
        console.notice("Replacing id %s with id %s" %(old_id, new_id))
        return new_id
    else:
        console.notice("Unable to replace id %s" %old_id)
        return None

def _replace_id(old_ids_list, new_ids_dict):
    if old_ids_list == None:
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
        console.error("Unable to replace ids: %s" % old_ids_list)


def _clean_ids(data):
    if "org_id" in data:
        del data["org_id"]
    if "modified_time" in data:
        del data["modified_time"]
    if "created_time" in data:
        del data["created_time"]
    return data

def _restore_device_image(org_id, site_id, device_id, i):
    image_name = "%s_org_%s_device_%s_image_%s.png" %(file_prefix, org_id, device_id, i)    
    if os.path.isfile(image_name):
        console.info("Image %s will be restored to device %s" %(image_name, device_id))
        mist_lib.requests.sites.devices.add_image(mist_session, site_id, device_id, i, image_name)
        return True
    else:
        console.info("No image found for device id %s" % device_id)
        return False


def _restore_inventory(inventory):
    mist_lib.requests.orgs.inventory.add(mist_session, org_id, inventory)

def _restore_site_assign(site_assignment):
    for old_site_id in site_assignment:
        new_site_id = _replace_id(old_site_id, site_id_dict)
        macs = site_assignment[new_site_id]
        mist_lib.requests.orgs.inventory.assign_macs_to_site(mist_session, org_id, new_site_id, macs)

def _restore_devices(devices):
    _sync_sites_id()
    _sync_deviceprofiles_id()
    for device in devices:
        device = _clean_ids(device)
        device["deviceprofile_id"] = _replace_id(device["deviceprofile_id"], deviceprofile_id_dict) 
## add image
        device["map_id"] = _replace_id(device["map_id"], map_id_dict) 
        site_id = _replace_id(device["site_id"], site_id_dict) 
        device["site_id"] = site_id
        mist_lib.requests.sites.devices.set_device_conf(mist_session, site_id, device["id"], device)
        i=1
        image_exists = True
        while image_exists:
            image_exists = _restore_device_image(org_id, site_id, device["id"], i)
            i+=1
        
def _select_backup_folder(folders):   
    i = 0
    print("Available backups:")
    while i < len(folders):
        print("%s) %s" %(i, folders[i]))
        i += 1
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

def _go_to_backup_folder(source_org_name=None):
    os.chdir(backup_directory)
    folders = []
    for entry in os.listdir("./"):
        if os.path.isdir(os.path.join("./", entry)):
            folders.append(entry)
    if source_org_name in folders:
        print("Backup found for organization %s." %(source_org_name))
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
        print("Backup folder for organization %s not found. Please select a folder in the following list." %(source_org_name))
        _select_backup_folder(folders)
#### SCRIPT ENTRYPOINT ####

mist_session = mist_lib.Mist_Session(session_file)
if org_id == "":
    org_id = cli.select_org(mist_session)

print(""" 
__          __     _____  _   _ _____ _   _  _____ 
\ \        / /\   |  __ \| \ | |_   _| \ | |/ ____|
 \ \  /\  / /  \  | |__) |  \| | | | |  \| | |  __ 
  \ \/  \/ / /\ \ |  _  /| . ` | | | | . ` | | |_ |
   \  /\  / ____ \| | \ \| |\  |_| |_| |\  | |__| |
    \/  \/_/    \_\_|  \_\_| \_|_____|_| \_|\_____|

This script is still in BETA. It won't hurt your original
organization, but the restoration may partially fail. 
It's your responsability to validate the importation result!


""")
resp = "x"
while not resp in ["y", "n", ""]:
    resp = input("Do you want to continue to import the configuration into the organization %s (y/N)? " %org_id).lower()

if resp == "y":
    _sync_deviceprofiles_id()
    _sync_sites_id()    
    _restore_inventory(backup["org"]["inventory"])
    _restore_site_assign(backup["org"]["site_assignment"])
    _restore_devices(backup["org"]["devices"])
    print('')
    console.info("Restoration succeed!")
else:
    console.warning("Interruption... Exiting...")
exit(0)

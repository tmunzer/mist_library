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

## devices

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
            console.error("Unable to find the new id for the %s with old id %s" %(obj, old_id))
            missing_ids[object_name].append("%s (old_id id: %s" %(obj, old_id))


def _missing_name_object(object_name, object_id_dict, name):
    missing_ids[object_name].append("%s (old id: %s)" %(name, object_id_dict[name]["old_id"]))


## restore
def _restore_device_image(mist_session, source_org_id, org_id, site_id, device_serial, device_id, i):
    image_name = "%s_org_%s_device_%s_image_%s.png" %(file_prefix, source_org_id, device_serial, i)    
    if os.path.isfile(image_name):
        console.info("Image %s will be restored to device %s" %(image_name, device_serial))
        mist_lib.requests.sites.devices.add_image(mist_session, site_id, device_id, i, image_name)
        return True
    else:
        console.debug("Image %s not found for device id %s" %(image_name, device_serial))
        return False


def _restore_devices(mist_session, source_org_id, dest_org_id, new_site_id, site_name, map_id_dict, devices, inventory, ap_mac_filter):
    for device in devices:
        if not ap_mac_filter or device["mac"] in ap_mac_filter:
            console.info("SITE %s > DEVICE SERIAL %s > Images Restoration in progress" %(site_name, device["serial"]))  
            image_exists = True
            i = 1
            while image_exists:
                image_exists = _restore_device_image(mist_session, source_org_id, org_id, new_site_id, device["serial"], device["id"], i)
                i+=1
            console.info("SITE %s > DEVICE SERIAL %s > Restoration finished" %(site_name, device["serial"]))  


#TODO
def _restore_inventory(mist_session, dest_org_id, backup, sites_list, source_org_id, source_mist_session=None, ap_mac_filter=None):
    site_id_dict = _link_sites_ids(mist_session, dest_org_id, backup["sites_ids"])
    for restore_site_name in sites_list:
        site = backup["sites"][restore_site_name]
        console.notice("Restoring Site %s" %(restore_site_name))

        new_site_id = _find_new_site_id_by_name(site_id_dict, restore_site_name) 
        
        if new_site_id == None:
            if new_site_id in missing_ids["sites"]: 
                missing_ids["sites"].append(new_site_id)
        else:              
            map_id_dict = _link_maps_id(mist_session, new_site_id, site["maps_ids"]) 
            _restore_devices(mist_session, source_org_id, dest_org_id, new_site_id, restore_site_name, map_id_dict, site["devices"], backup["inventory"], ap_mac_filter)
        console.notice("Site %s restored" %(restore_site_name))
    _result(backup)

## backup folder selection
def _select_backup_folder(folders):   
    i = 0
    print("Available backups:")
    while i < len(folders):
        print("%s) %s" %(i, folders[i]))
        i += 1
    folder = None
    while folder == None:
        resp = input("Which backup do you want to restore (0-%s, or x to exit)? "  %i)
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
    print()

def _go_to_backup_folder(org_name=None):
    os.chdir(backup_directory)
    folders = []
    for entry in os.listdir("./"):
        if os.path.isdir(os.path.join("./", entry)):
            folders.append(entry)
    if org_name in folders:
        print("Backup found for organization %s." %(org_name))
        loop = True
        while loop:
            resp = input("Do you want to use this backup (y/n)? ")
            if resp.lower() == "y":
                print()
                loop = False    
                try:
                    os.chdir(org_name)
                except:
                    _select_backup_folder(folders)
            elif resp.lower() == "n":
                print()
                loop = False    
                _select_backup_folder(folders)
    else:
        print("Backup folder for organization %s not found. Please select a folder in the following list." %(org_name))
        _select_backup_folder(folders)


def _select_one_site(sites_names):
    print("Available sites:")
    i=0
    for site in sites_names:
        print("%s) %s" %(i, site))
        i+=1
    loop = True
    while loop:
        resp = input("Which site do you want to restore (0-%s)? " %(i))
        try:
            iresp = int(resp)
            if iresp >= 0 and iresp < i:
                loop = False
                return [sites_names[iresp]]
            else:
                print("Only number between 0 and %s are allowed..." %(i - 1))
        except:
            print("Only numbers are allowed...")

def _select_sites(sites_names):
    print("By default, this script will restore all the devices assigned to sites listed in the \"sites_names\" variable inside the backup file, but you can select a specific site to restore")
    loop = True
    while loop:
        resp = input("Do you want to select a specific site to restore (y/n)? ")
        if resp.lower() == "n":
            loop = False
            return sites_names
        elif resp.lower() == "y":
            loop = False
            return _select_one_site(sites_names)

# starting functions
def _display_warning(message):
    resp = "x"
    while not resp.lower() in ["y", "n", ""]:
        print()
        resp = input(message)
    if not resp.lower()=="y":
        console.warning("Interruption... Exiting...")
        exit(0)

def _y_or_n_question(message):
    resp = "x"
    while not resp.lower() in ["y", "n"]:
        print()
        resp = input(message)
    if resp.lower()=="y":
        return True
    elif resp.lower() == "n":
        return False

def _print_warning():
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

def _check_org_name(org_name):
    while True:
        print()
        resp = input("To avoid any error, please confirm the current destination orgnization name: ")
        if resp == org_name:
            print()
            return True
        else:
            console.warning("The orgnization names do not match... Please try again...")

def start_restore_inventory(mist_session, dest_org_id, dest_org_name, source_mist_session=None, source_org_name=None, source_org_id=None, sites_list=None, check_org_name=True, in_backup_folder=False, ap_mac=None):
    if check_org_name: _check_org_name(dest_org_name)
    if not in_backup_folder: _go_to_backup_folder(source_org_name)
    try:
        with open(backup_file) as f:
            backup = json.load(f)
    except: 
        print("unable to load the file backup %s" %(backup_file))
    finally:
        if backup:
            console.info("File %s loaded succesfully." %backup_file)
            source_org_id = backup["org"]["id"]
        
            if sites_list == None:
                sites_list = _select_sites(backup["org"]["sites_names"])
            _display_warning("Are you sure about this? Do you want to import the inventory into the organization %s with the id %s (y/N)? " %(dest_org_name, dest_org_id))

            _restore_inventory(mist_session, dest_org_id, backup["org"], sites_list, source_org_id, source_mist_session, ap_mac)
            print()
            console.notice("Restoration process finished...")



def start(mist_session, org_id=None, source_org_name=None, sites_list=None, ap_mac=None):
    if not org_id:
        print("***                                            ***")
        print("*** Please select the destination organization ***")
        print("***                                            ***")
        org_id = cli.select_org(mist_session)
    org_name = mist_lib.requests.orgs.info.get(mist_session, org_id)["result"]["name"]
    start_restore_inventory(mist_session, org_id, org_name, source_org_name, sites_list, ap_mac)


#### SCRIPT ENTRYPOINT ####


if __name__ == "__main__":
    mist_session = mist_lib.Mist_Session(session_file)
    start(mist_session)



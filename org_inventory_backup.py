'''
Written by: Thomas Munzer (tmunzer@juniper.net)
Github repository: https://github.com/tmunzer/Mist_library/
'''

#### PARAMETERS #####
backup_file = "./org_inventory_file.json"
file_prefix = ".".join(backup_file.split(".")[:-1])
session_file = "./session.py"
org_id = "" #optional

#### IMPORTS ####
import mlib as mist_lib
import urllib.request
from mlib import cli
from tabulate import tabulate
import json
import os

from mlib.__debug import Console
console = Console(6)

#### VARIABLES ####

backup = {
    "org" : {
        "id": "",
        "sites" : {},
        "sites_ids": {},
        "sites_names": [],
        "deviceprofiles_ids": {},
        "inventory" : []
    }
}

#### FUNCTIONS ####
def _save_site_info(site):
    backup["org"]["sites"][site["name"]] = {"id": site["id"],  "maps_ids": {}, "devices": []}
    backup["org"]["sites_ids"][site["name"]] = {"old_id": site["id"]}
    backup["org"]["sites_names"].append(site["name"])

def _backup_site_id_dict(site):
    if site["name"] in backup["org"]["sites"]:
        print("Two sites are using the same name %s!" %(site["name"]))
        print("This will cause issue during the backup and the restore process.")
        print("I recommand you to rename one of the two sites.")
        loop = True
        while loop:
            resp = input("Do you want to continur anyway (y/N)? ")
            if resp.lower == "y": 
                loop = False
                _save_site_info(site)
            elif resp.lower == "n" or resp == "":
                loop = False
                exit(200)
    else:
        _save_site_info(site)

def _backup_site_maps(mist_session, site):
    backup_maps = mist_lib.requests.sites.maps.get(mist_session, site["id"])["result"]
    maps_ids = {}
    for xmap in backup_maps:
        if xmap["name"] in maps_ids:
            print("Two maps are using the same name %s in the same site %s!" %(xmap["name"], site["name"]))
            print("This will cause issue during the backup and the restore process.")
            print("I recommand you to rename one of the two maps.")
            loop = True
            while loop:
                resp = input("Do you want to continur anyway (y/N)? ")
                if resp.lower == "y": 
                    loop = False
                    ["maps"].append({xmap["name"]: xmap["id"]}) 
                    ["maps_ids"][xmap["name"]] = xmap["id"]
                elif resp.lower == "n" or resp == "":
                    loop = False
                    exit(200)
        else:            
            maps_ids[xmap["name"]] = {"old_id": xmap["id"]}
    return maps_ids

def _backup_inventory(mist_session, org_id, org_name=None):
    backup["org"]["id"] = org_id
    console.notice("ORG %s > Backup processing..." %(org_name))

    console.info("ORG %s > Backuping inventory" %(org_name))
    inventory = mist_lib.requests.orgs.inventory.get(mist_session, org_id)["result"]
    for data in inventory:
        if not data["magic"] == "":
            backup["org"]["inventory"].append({"serial": data["serial"], "magic": data["magic"]})

    console.info("ORG %s > Backuping device profiles ids" %(org_name))
    deviceprofiles = mist_lib.requests.orgs.deviceprofiles.get(mist_session, org_id)["result"]
    for deviceprofile in deviceprofiles:
       backup["org"]["deviceprofiles_ids"][deviceprofile["name"]] = {"old_id": deviceprofile["id"]}

    console.info("ORG %s > Backuping devices" %(org_name))
    sites = mist_lib.requests.orgs.sites.get(mist_session, org_id)['result']
    for site in sites:
        console.info("ORG %s > SITE %s > Backuping devices" %(org_name, site["name"]))
        _backup_site_id_dict(site)
        maps_ids = _backup_site_maps(mist_session, site)
        backup["org"]["sites"][site["name"]]["maps_ids"] = maps_ids
        devices = mist_lib.requests.sites.devices.get(mist_session, site["id"])["result"]
        backup["org"]["sites"][site["name"]]["devices"] = devices
        for device in devices:
            i = 1
            while "image%s_url"%i in device:
                url = device["image%s_url"%i]
                image_name = "%s_org_%s_device_%s_image_%s.png" %(file_prefix, org_id, device["serial"], i)
                urllib.request.urlretrieve(url, image_name)
                i+=1

    
    console.notice("ORG %s > Backup done" %(org_name))

def _save_to_file(backup_file, backup):
    print("saving to file...")
    with open(backup_file, "w") as f:
        json.dump(backup, f)

def start_inventory_backup(mist_session, org_id, org_name, in_backup_folder=False):    
    if not in_backup_folder:
        if not os.path.exists("org_backup"):
            os.mkdir("org_backup")
        os.chdir("org_backup")
        if not os.path.exists(org_name):
            os.mkdir(org_name)
        os.chdir(org_name)

    _backup_inventory(mist_session, org_id, org_name)
    _save_to_file(backup_file, backup)

    print("Inventory from organisation %s with id %s saved!" %(org_name, org_id))
    

def start(mist_session, org_id):
    if org_id == "":
        org_id = cli.select_org(mist_session)[0]
    org_name = mist_lib.orgs.info.get(mist_session, org_id)["result"]["name"]
    start_inventory_backup(mist_session, org_id, org_name)


if __name__ == "__main__":
    mist_session = mist_lib.Mist_Session(session_file)
    start(mist_session, org_id)
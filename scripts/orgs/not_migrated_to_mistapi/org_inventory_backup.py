'''
Written by: Thomas Munzer (tmunzer@juniper.net)
Github repository: https://github.com/tmunzer/Mist_library/
'''

#### IMPORTS ####
import logging
import sys
import os
import json
from mlib import cli
import urllib.request
import mlib as mist_lib


#### PARAMETERS #####
backup_file = "./org_inventory_file.json"
log_file = "./org_inventory_backup.log"
file_prefix = ".".join(backup_file.split(".")[:-1])
session_file = "./session.py"
org_id = ""  # optional


#### LOGS ####
logger = logging.getLogger(__name__)


#### VARIABLES ####

backup = {
    "org": {
        "id": "",
        "sites": {},
        "sites_ids": {},
        "sites_names": [],
        "deviceprofiles_ids": {},
        "inventory": []
    }
}

#### FUNCTIONS ####
def log_message(message):
    print(f"{message}".ljust(79, '.'), end="", flush=True)

def log_success(message):
    print("\033[92m\u2714\033[0m")
    logger.info(f"{message}: Success")

def log_failure(message):
    logger.exception(f"{message}: Failure")
    print('\033[31m\u2716\033[0m')


def _save_site_info(site):
    backup["org"]["sites"][site["name"]] = {
        "id": site["id"],  "maps_ids": {}, "devices": []}
    backup["org"]["sites_ids"][site["name"]] = {"old_id": site["id"]}
    backup["org"]["sites_names"].append(site["name"])


def _backup_site_id_dict(site):
    if site["name"] in backup["org"]["sites"]:
        print(f"Two sites are using the same name {site['name']}!")
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
                sys.exit(200)
    else:
        _save_site_info(site)


def _backup_site_maps(mist_session, site):
    backup_maps = mistapi.api.v1.sites.maps.get(
        mist_session, site["id"])["result"]
    maps_ids = {}
    for xmap in backup_maps:
        if xmap["name"] in maps_ids:
            print(
                f"Two maps are using the same name {xmap['name']} in the same site {site['name']}!")
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
                    sys.exit(200)
        else:
            maps_ids[xmap["name"]] = {"old_id": xmap["id"]}
    return maps_ids


def _backup_inventory(mist_session, org_id, org_name=None):
    print()
    print(f" Backuping Org {org_name} Elements ".center(80, "_"))

    backup["org"]["id"] = org_id

    ################################################
    ##  Backuping inventory
    message=f"Backuping inventory "
    log_message(message)
    try:
        inventory = mistapi.api.v1.orgs.inventory.get(mist_session, org_id)[
            "result"]
        for data in inventory:
            if not data["magic"] == "":
                backup["org"]["inventory"].append(
                    {"serial": data["serial"], "magic": data["magic"]})
        log_success(message)
    except Exception as e:
        log_failure(message)
        logger.error("Exception occurred", exc_info=True)

    ################################################
    ##  Retrieving device profiles
    message=f"Backuping Device Profiles "
    log_message(message)
    try:
        deviceprofiles = mistapi.api.v1.orgs.deviceprofiles.get(mist_session, org_id)[
            "result"]
        for deviceprofile in deviceprofiles:
            backup["org"]["deviceprofiles_ids"][deviceprofile["name"]] = {
                "old_id": deviceprofile["id"]}
        log_success(message)
    except Exception as e:
        log_failure(message)
        logger.error("Exception occurred", exc_info=True)

    ################################################
    ##  Retrieving Sites list
    message=f"Retrieving Sites list "
    log_message(message)
    try:
        sites = mistapi.api.v1.orgs.sites.get(mist_session, org_id)['result']
        log_success(message)
    except Exception as e:
        log_failure(message)
        logger.error("Exception occurred", exc_info=True)

    ################################################
    ## Backuping Sites Devices
    for site in sites:
        print(f" Backuping Site {site['name']} ".center(80, "_"))
        message=f"Devices List "
        log_message(message)
        try:
            _backup_site_id_dict(site)
            maps_ids = _backup_site_maps(mist_session, site)
            backup["org"]["sites"][site["name"]]["maps_ids"] = maps_ids
            devices = mistapi.api.v1.sites.devices.get(
                mist_session, site["id"], device_type="all")["result"]
            backup["org"]["sites"][site["name"]]["devices"] = devices
            log_success(message)
        except Exception as e:
            log_failure(message)
            logger.error("Exception occurred", exc_info=True)
        ################################################
        ## Backuping Site Devices Images
        for device in devices:
            message=f"Backuping {device['type'].upper()} {device['serial']} images "
            log_message(message)
            try:
                i = 1
                while f"image{i}_url" in device:
                    url = device[f"image{i}_url"]
                    image_name = f"{file_prefix}_org_{org_id}_device_{device['serial']}_image_{i}.png"
                    urllib.request.urlretrieve(url, image_name)
                    i += 1
                log_success(message)
            except Exception as e:
                log_failure(message)
                logger.error("Exception occurred", exc_info=True)
    
    ################################################
    ## End
    print(f" Backup Done ".center(80, "_"))



def _save_to_file(backup_file, org_name, backup):
    backup_path = f"./org_backup/{org_name}/{backup_file.replace('./','')}"
    message=f"Saving to file {backup_path} "
    log_message(message)
    try:
        with open(backup_file, "w") as f:
            json.dump(backup, f)
        log_success(message)
    except Exception as e:
        log_failure(message)
        logger.error("Exception occurred", exc_info=True)


def start_inventory_backup(mist_session, org_id, org_name, in_backup_folder=False, parent_log_file=None):
    if parent_log_file:
        logging.basicConfig(filename=log_file, filemode='a')
        logger.setLevel(logging.DEBUG)
    if not in_backup_folder:
        if not os.path.exists("org_backup"):
            os.mkdir("org_backup")
        os.chdir("org_backup")
        if not os.path.exists(org_name):
            os.makedirs(org_name)
        os.chdir(org_name)

    _backup_inventory(mist_session, org_id, org_name)
    _save_to_file(backup_file, org_name, backup)


def start(mist_session, org_id):
    if org_id == "":
        org_id = cli.select_org(mist_session)[0]
    org_name = mist_lib.orgs.info.get(mist_session, org_id)["result"]["name"]
    start_inventory_backup(mist_session, org_id, org_name)


if __name__ == "__main__":
    #### LOGS ####
    logging.basicConfig(filename=log_file, filemode='w')
    logger.setLevel(logging.DEBUG)

    mist_session = mistapi.APISession(session_file)
    start(mist_session, org_id)

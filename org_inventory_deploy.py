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

from mlib.requests.sites import devices


#### PARAMETERS #####
dry_run = False
backup_file = "./org_inventory_file.json"
file_prefix = ".".join(backup_file.split(".")[:-1])
backup_directory = "./org_backup/"
log_file = "./org_inventory_deploy.log"
session_file = "./session.py"


#### CONSTANTS ####

#### GLOBAL VARS ####
missing_magic = []
magic_batch_size = 50
missing_ids = {
    "sites": [],
    "maps": [],
    "deviceprofiles": []
}


#### LOGS ####
logger = logging.getLogger(__name__)


#### FUNCTIONS ####
def log_title(message):
    print(f" {message} ".center(80, "_"))
    logger.warning(f"{message}")


def log_message(message):
    print(f"{message} ".ljust(79, '.'), end="", flush=True)


def log_debug(message):
    logger.debug(f"{message} ")


def log_error(message):
    logger.error(f"{message} ")


def log_success(message):
    print("\033[92m\u2714\033[0m")
    logger.info(f"{message}: Success")


def log_failure(message):
    print('\033[31m\u2716\033[0m')
    logger.exception(f"{message}: Failure")

# Final tests


def _find_name_by_old_id(object_id_dict, old_object_id):
    for name in object_id_dict:
        if object_id_dict["old_id"] == old_object_id:
            return name


def _result(backup):
    print('')
    if len(missing_ids["sites"]) == 0 and len(missing_ids["maps"]) == 0 and len(missing_ids["deviceprofiles"]) == 0 and len(missing_magic) == 0:
        print("Inventory deployed !")
    else:
        print(f" Warning ".center(80, "_"))
        print("Pre check validation failed!")
        print("Please create the following object to the new org before restoring the devices.")
        print("")
        if len(missing_ids["sites"]) > 0:
            print("Missing sites:")
            for missing_site in missing_ids["sites"]:
                print(f"    - {missing_site}")
        if len(missing_ids["maps"]) > 0:
            print("Missing maps:")
            for missing_map in missing_ids["maps"]:
                print(f"    - {missing_map}")
        if len(missing_ids["deviceprofiles"]) > 0:
            print("Missing deviceprofiles:")
            for missing_deviceprofile in missing_ids["deviceprofiles"]:
                print(f"    - {missing_deviceprofile}")
        if len(missing_magic):
            print("""The following devices where not claimed to the new org because they were adopted
to the previous org (no known claim code):""")
            for magic in missing_magic:
                print(f" - {magic}")
    print("")
# site id


def _link_sites_ids(mist_session, org_id, sites_ids):
    new_sites = mist_lib.requests.orgs.sites.get(
        mist_session, org_id)["result"]
    return _link_objects_ids(new_sites, sites_ids)


def _find_new_site_id_by_old_id(site_id_dict, old_id):
    return _find_new_object_id_by_old_id("sites", site_id_dict, old_id)


def _find_new_site_id_by_name(site_id_dict, site_name):
    if "new_id" in site_id_dict[site_name]:
        return site_id_dict[site_name]["new_id"]
    _missing_name_object("sites", site_id_dict, site_name)
    return None

# map id


def _link_maps_id(mist_session, site_id, maps_ids):
    new_maps = mist_lib.requests.sites.maps.get(
        mist_session, site_id)["result"]
    return _link_objects_ids(new_maps, maps_ids)


def _find_new_map_id_by_old_id(map_id_dict, old_id):
    return _find_new_object_id_by_old_id("maps", map_id_dict, old_id)


def _find_new_site_id_by_name(map_id_dict, map_name):
    if "new_id" in map_id_dict[map_name]:
        return map_id_dict[map_name]["new_id"]
    _missing_name_object("maps", map_id_dict, map_name)
    return None

# device profiles


def _link_deviceprofiles_ids(mist_session, org_id, deviceprofiles_ids):
    new_deviceprofiles = mist_lib.requests.orgs.deviceprofiles.get(
        mist_session, org_id)["result"]
    return _link_objects_ids(new_deviceprofiles, deviceprofiles_ids)


def _find_new_deviceprofile_id_by_old_id(deviceprofile_id_dict, old_id):
    return _find_new_object_id_by_old_id("deviceprofiles", deviceprofile_id_dict, old_id)


def _find_new_deviceprofile_id_by_name(deviceprofile_id_dict, deviceprofile_name):
    if "new_id" in deviceprofile_id_dict[deviceprofile_name]:
        return deviceprofile_id_dict[deviceprofile_name]["new_id"]
    _missing_name_object(
        "deviceprofiles", deviceprofile_id_dict, deviceprofile_name)
    return None

# devices


def _add_magic(mist_session, org_id, magics):
    i = 0
    while i * magic_batch_size < len(magics):
        magic_start = i*magic_batch_size
        magic_end = (i+1)*magic_batch_size
        if magic_end > len(magics):
            magic_end = len(magics)
        current_magics = magics[magic_start:magic_end]
        message = f"Claiming magics from {magic_start} to {magic_end}"
        log_message(message)
        try:
            if not dry_run:
                mist_lib.requests.orgs.inventory.add(
                    mist_session, org_id, current_magics)
            log_success(message)
        except Exception as e:
            log_failure(message)
            logger.error("Exception occurred", exc_info=True)
        i += 1


def _restore_device_to_site_assignment(mist_session, org_id, new_site_id, devices_mac):
    message = f"Assigning {len(devices_mac)} devices to site {new_site_id}"
    log_message(message)
    log_debug(f"MAC Addresse: {devices_mac}")
    try:
        if not dry_run:
            mist_lib.requests.orgs.inventory.assign_macs_to_site(
                mist_session, org_id, new_site_id, devices_mac)
        log_success(message)
    except Exception as e:
        log_failure(message)
        logger.error("Exception occurred", exc_info=True)


def _unclaim_devices(mist_session, org_id, devices):
    message = f"Unclaiming {len(devices)} devices from org {org_id}"
    log_message(message)
    try:
        if not dry_run:
            mist_lib.requests.orgs.inventory.delete_multiple(
                mist_session, org_id, macs=devices)
        log_success(message)
    except Exception as e:
        log_failure(message)
        logger.error("Exception occurred", exc_info=True)

# commons


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
            log_error(
                f"Unable to find the new id for the {obj} with old id {old_id}")
            missing_ids[object_name].append(f"{obj} (old_id id: {old_id}")


def _missing_name_object(object_name, object_id_dict, name):
    missing_ids[object_name].append(
        f"{name} (old id: {object_id_dict[name]['old_id']})")


def _clean_ids(data):
    if "org_id" in data:
        del data["org_id"]
    if "modified_time" in data:
        del data["modified_time"]
    if "created_time" in data:
        del data["created_time"]
    return data

# restore


def _restore_device_image(mist_session, source_org_id, site_id, device, i):
    image_name = f"{file_prefix}_org_{source_org_id}_device_{device['serial']}_image_{i}.png"
    if os.path.isfile(image_name):
        message = f"{device.get('type', 'device').upper()} {device['serial']}: Restoration Device Image #{i}"
        log_message(message)
        try:
            if not dry_run:
                mist_lib.requests.sites.devices.add_image(
                    mist_session, site_id, device["id"], i, image_name)
            log_success(message)
            return True
        except Exception as e:
            log_failure(message)
            logger.error("Exception occurred", exc_info=True)
    else:
        log_debug(
            f"Image {image_name} not found for device id {device['serial']}")
        return False


def _auto_unclaim_devices(source_mist_session, source_org_id, devices, ap_mac_filter, magics):
    mac_addresses = []
    for device in devices:
        if not ap_mac_filter or device["mac"] in ap_mac_filter:
            if device["serial"] not in missing_magic:
                mac_addresses.append(device["mac"])
    _unclaim_devices(source_mist_session, source_org_id, mac_addresses)


def _restore_device_configuration(mist_session, source_org_id, new_site_id, device, deviceprofile_id_dict, map_id_dict):
    stop = False
    ################################
    # Updating IDs
    message = f"{device.get('type', 'device').upper()} {device['serial']}: Updating IDs"
    log_message(message)
    try:
        device = _clean_ids(device)
        if device["deviceprofile_id"]:
            device["deviceprofile_id"] = _find_new_deviceprofile_id_by_old_id(
                deviceprofile_id_dict, device["deviceprofile_id"])
        if device["map_id"]:
            device["map_id"] = _find_new_map_id_by_old_id(
                map_id_dict, device["map_id"])
        device["site_id"] = new_site_id
        log_success(message)
    except Exception as e:
        log_failure(message)
        logger.error("Exception occurred", exc_info=True)

    if not stop:
        ################################
        # Deploy Config
        message = f"{device.get('type', 'device').upper()} {device['serial']}: Restore Device Configuration"
        log_message(message)
        try:
            if not dry_run:
                mist_lib.requests.sites.devices.set_device_conf(
                    mist_session, new_site_id, device["id"], device)
            log_success(message)
        except Exception as e:
            log_failure(message)
            logger.error("Exception occurred", exc_info=True)

        ################################
        # Deploy Images
        i = 1
        image_exists = True
        while image_exists:
            image_exists = _restore_device_image(
                mist_session, source_org_id, new_site_id, device, i)
            i += 1


def _migrate_devices(mist_session, source_mist_session, auto_unclaim, source_org_id, dest_org_id, new_site_id, deviceprofile_id_dict, map_id_dict, devices, inventory, ap_mac_filter):
    magics = []
    mac_addresses = []

    ################################
    # Magics managmenet
    # for each backuped device, get the magic
    for device in devices:
        if not ap_mac_filter or device["mac"] in ap_mac_filter:
            magic = [i for i in inventory if i["serial"] == device["serial"]]
            if len(magic) == 0:
                missing_magic.append(device["serial"])
            else:
                magics.append(magic[0]["magic"])
                mac_addresses.append(device["mac"])

    if auto_unclaim and source_org_id and source_mist_session:
        _auto_unclaim_devices(source_mist_session, source_org_id, devices, ap_mac_filter, magics)

    _add_magic(mist_session, dest_org_id, magics)

    _restore_device_to_site_assignment(
        mist_session, dest_org_id, new_site_id, mac_addresses)

    ################################
    # Devices management
    for device in devices:
        if not ap_mac_filter or device["mac"] in ap_mac_filter and not device["serial"] in missing_magic:
            _restore_device_configuration(mist_session, source_org_id, new_site_id, device, deviceprofile_id_dict, map_id_dict)

        


# TODO
def _restore_inventory(mist_session, dest_org_id, backup, sites_list, auto_unclaim=False, source_org_id=None, source_mist_session=None, ap_mac_filter=None):
    deviceprofile_id_dict = _link_deviceprofiles_ids(
        mist_session, dest_org_id, backup["deviceprofiles_ids"])
    site_id_dict = _link_sites_ids(
        mist_session, dest_org_id, backup["sites_ids"])
    for restore_site_name in sites_list:
        site = backup["sites"][restore_site_name]
        log_title(f" Restoring Devices on site {restore_site_name}")

        new_site_id = _find_new_site_id_by_name(
            site_id_dict, restore_site_name)

        if not new_site_id:
            if new_site_id in missing_ids["sites"]:
                missing_ids["sites"].append(new_site_id)
        else:
            map_id_dict = _link_maps_id(
                mist_session, new_site_id, site["maps_ids"])
            _migrate_devices(
                mist_session, source_mist_session, auto_unclaim,
                source_org_id, dest_org_id, new_site_id,
                deviceprofile_id_dict, map_id_dict, site["devices"],
                backup["inventory"], ap_mac_filter)
    _result(backup)

# backup folder selection


def _select_backup_folder(folders):
    i = 0
    print("Available backups:")
    while i < len(folders):
        print(f"{i}) {folders[i]}")
        i += 1
    folder = None
    while not folder:
        resp = input(
            f"Which backup do you want to restore (0-{i}, or q to quit)? ")
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
    print()


def _go_to_backup_folder(org_name=None):
    os.chdir(backup_directory)
    folders = []
    for entry in os.listdir("./"):
        if os.path.isdir(os.path.join("./", entry)):
            folders.append(entry)
    if org_name in folders:
        print(f"Backup found for organization {org_name}.")
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
        print(
            f"Backup folder for organization {org_name} not found. Please select a folder in the following list.")
        _select_backup_folder(folders)


def _select_one_site(sites_names):
    print("Available sites:")
    i = 0
    for site in sites_names:
        print(f"{i}) {site}")
        i += 1
    loop = True
    while loop:
        resp = input(f"Which site do you want to restore (0-{i})? ")
        try:
            iresp = int(resp)
            if iresp >= 0 and iresp < i:
                loop = False
                return [sites_names[iresp]]
            else:
                print(f"Only number between 0 and {i - 1} are allowed...")
        except:
            print("Only numbers are allowed...")


def _select_sites(sites_names):
    print("By default, this script will restore all the devices assigned to sites listed in the \"sites_names\" variable inside the backup file, but you can select a specific site to restore")
    loop = True
    while loop:
        resp = input(
            "Do you want to select a specific site to restore (y/n)? ")
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
    if not resp.lower() == "y":
        print()
        print("Interruption... Exiting...")
        sys.exit(0)


def _y_or_n_question(message, default=None):
    resp = "x"
    accepted = ["y", "n"]
    if default:
        accepted.append("")
    while not resp.lower() in accepted:
        print()
        resp = input(message)
    if resp == "":
        resp = default
    return resp.lower() == "y"


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


*******     IMPORTANT INFORMATION     *********

The current version of the script will not migrate APs
that are not assigned to a site!

*******     IMPORTANT INFORMATION     *********
""")


def _check_org_name(org_name):
    while True:
        print()
        resp = input(
            "To avoid any error, please confirm the current destination orgnization name: ")
        if resp == org_name:
            print()
            return True
        else:
            print()
            print("The orgnization names do not match... Please try again...")


def start_deploy_inventory(mist_session, dest_org_id, dest_org_name, source_mist_session=None, source_org_name=None, source_org_id=None, sites_list=None, check_org_name=True, in_backup_folder=False, ap_mac=None, parent_log_file=None):
    if parent_log_file:
        logging.basicConfig(filename=log_file, filemode='a')
        logger.setLevel(logging.DEBUG)
    if check_org_name:
        _check_org_name(dest_org_name)
    if not in_backup_folder:
        _go_to_backup_folder(source_org_name)
    try:
        message = "Loading Backup File "
        log_message(message)
        with open(backup_file) as f:
            backup = json.load(f)
        log_success(message)    
    except Exception as e:
        log_failure(message)
        logger.error("Exception occurred", exc_info=True)
        sys.exit(0)

    if backup:
        print()
        auto_unclaim = _y_or_n_question(
            f"Do you want to automatically unclaim devices from the source organization {source_org_name} (y/N)? ", "n")
        if auto_unclaim:
            if not source_mist_session:
                print("".center(80,'*'))
                print(" Please select the source organization ".center(80,'*'))
                print("".center(80,'*'))                
                source_mist_session = mist_lib.Mist_Session()
            if not source_org_id:
                source_org_id = cli.select_org(source_mist_session)[0]
                source_org_name = mist_lib.requests.orgs.info.get(
                    source_mist_session, source_org_id)["result"]["name"]
                _check_org_name(source_org_name)

        if source_org_id is None:
            source_org_id = backup["org"]["id"]
        if sites_list is None:
            sites_list = _select_sites(backup["org"]["sites_names"])
        _display_warning(
            f"Are you sure about this? Do you want to import the inventory into the organization {dest_org_name} with the id {dest_org_id} (y/N)? ")

        # TODO: Migrate magics for APs not assigned to sites
        _restore_inventory(mist_session, dest_org_id,
                           backup["org"], sites_list, auto_unclaim, source_org_id, source_mist_session, ap_mac)
        print()
        print("Restoration process finished...")


def start(mist_session, org_id=None, source_org_name=None, sites_list=None, ap_mac=None):
    if not org_id:
        print("".center(80,'*'))
        print(" Please select the destination organization ".center(80,'*'))
        print("".center(80,'*'))
        org_id = cli.select_org(mist_session)[0]
    org_name = mist_lib.requests.orgs.info.get(
        mist_session, org_id)["result"]["name"]
    start_deploy_inventory(mist_session, org_id, org_name,
                            source_org_name, sites_list, ap_mac)


#### SCRIPT ENTRYPOINT ####


if __name__ == "__main__":
    #### LOGS ####
    logging.basicConfig(filename=log_file, filemode='w')
    logger.setLevel(logging.DEBUG)

    mist_session = mist_lib.Mist_Session(session_file)
    start(mist_session)

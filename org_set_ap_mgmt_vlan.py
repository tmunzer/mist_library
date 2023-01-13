'''
Written by Thomas Munzer (tmunzer@juniper.net)
Github repository: https://github.com/tmunzer/Mist_library/

Python script reconfigure Mist APs with a tagged managed VL

You can run the script with the command "python3 org_set_ap_mgmt_vlan.py"

The script has 3 different steps:
1) admin login
2) select the organisation/sites where you want to reconfigure the APs
3) enter the requried management VLAN ID
'''

#### PARAMETERS #####

log_file = "./org_set_ap_mgmt_vlan.log"
org_id = ""
site_ids = []
vlan_id = 0

#### IMPORTS ####
import sys
import logging
from datetime import datetime
import mlib as mist_lib
from mlib import cli

#### LOGS ####
logging.basicConfig(filename=log_file, filemode='a')
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.info(f"NEW RUN: {datetime.now()}")
#### GLOBAL VARIABLES ####
out=sys.stdout

#### FUNCTIONS ####

def _get_device_ids(mist, site_name, site_id):
    logger.info(f"{site_id}: Retrieving devices list")
    device_ids = []
    try:
        out.write(f"Retrieving devices list from {site_name}\r")
        out.flush()
        device_ids = []
        devices = mist_lib.requests.sites.devices.get(mist, site_id=site_id, device_type="ap")["result"]
        for device in devices:
            device_ids.append(device["id"])
    except:
        logger.error(f"{site_id}: Unable to retrieve devices list")
        print(f"Unable to retrieve devices list from site {site_name}")
    finally:
        logger.info(f"{site_id}: device_ids are {device_ids}")
        return device_ids

def _update_vlan_id(ip_config, vlan_id):
    if vlan_id > 0:
        ip_config["vlan_id"] = vlan_id
    elif ip_config.get("vlan_id", None) is not None:
        del ip_config["vlan_id"]
    return ip_config


def _update_devices(mist, site_name, site_id, vlan_id):
    logger.info(f"{site_id}: Processing devices")
    device_ids = _get_device_ids(mist, site_name, site_id)
    if len(device_ids) == 0:
        logger.info(f"{site_id}: no devices to process")
    else:
        count = len(device_ids)
        size = 58
        i = 0
        def show(j):
            x = int(size*j/count)
            out.write(f"{site_name}".ljust(12))
            out.write(f"[{'█'*x}{'.'*(size-x)}]")
            out.write(f"{j}/{count}\r".rjust(9))
            out.flush()
        show(i)
        for device_id in device_ids:
            logger.info(f"{site_id}: device {device_id} started")
            try:
                device_settings = mist_lib.requests.sites.devices.get_details(mist, site_id=site_id, device_id=device_id)["result"]
                logger.debug(device_settings)
                ip_config = device_settings.get("ip_config", {})
                logger.debug(f"ip_config before change: {ip_config}")
                ip_config = _update_vlan_id(ip_config, vlan_id)
                logger.debug(f"ip_config after change: {ip_config}")
                device_settings["ip_config"] = ip_config
                mist_lib.requests.sites.devices.set_device_conf(mist, site_id, device_id, device_settings)
                logger.info(f"{site_id}: device {device_id} updated")
            except:
                logger.error(f"{site_id}: device {device_id} failed")
                print(f"{site_name}: Failed for device with MAC {device_settings['mac']} (S/N {device_settings['serial']})".ljust(80))
            finally:
                i += 1
                show(i)
        out.write("\n")
        out.flush()


def _enter_vlan_id():
    vid = -1
    while vid < 0 or vid > 4095:
        print("")    
        resp = input("Management VLAN ID (0 for untagged): ")
        try:
            resp = int(resp)
            if resp < 0 or resp > 4095:
                print("Please enter a number between 0 and 4095")
            else: 
                vid = resp
        except:
            print("Please enter a number between 0 and 4095")
    return vid
        
def _split_site_name(site_name):
    if len(site_name) > 10:
        site_name = f"{site_name[:7]}..."
    return site_name

def process_sites(mist, site_ids, vlan_id):
    print()
    for site_id in site_ids:
        logger.info(f"{site_id}: Processing site")
        site_info = mist_lib.requests.sites.info.get(mist, site_id)["result"]
        site_name = _split_site_name(site_info["name"])
        logger.info(f"{site_id}: name is {site_name}")
        _update_devices(mist, site_name, site_id, vlan_id)



#### SCRIPT ENTRYPOINT ####

if __name__ == "__main__":
    mist = mist_lib.Mist_Session()

    org_id = cli.select_org(mist, allow_many=False)[0]
    logger.info(f"Org ID  : {org_id}")
    site_ids = cli.select_site(mist, org_id=org_id, allow_many=True)
    logger.info(f"Site IDs: {site_ids}")
    vlan_id = _enter_vlan_id()
    logger.info(f"VLAN ID : {vlan_id}")
    process_sites(mist, site_ids, vlan_id)

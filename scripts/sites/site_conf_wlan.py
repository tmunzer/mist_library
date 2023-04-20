'''
Written by Thomas Munzer (tmunzer@juniper.net)
Github repository: https://github.com/tmunzer/Mist_library/

This script can be used to list/add/delete an SSID from Org/Site
'''

#### IMPORTS ####
import mistapi
import json
import sys
import logging
#### PARAMETERS #####
csv_separator = ","
log_file = "./sites_scripts.log"
default_wlan_file = "./site_conf_wlan_settings.json"
env_file = "./.env"
#### LOGS ####
logger = logging.getLogger(__name__)


def add_wlan(apisession, site_id):
    wlan_file = input(f"Path to the WLAN configuration JSON file (default: {default_wlan_file}): ")
    if wlan_file == "": 
        wlan_file = default_wlan_file
    try:
        with open(wlan_file, "r") as f:
            wlan  = json.load(f)       
    except:
        print("Error while loading the configuration file... exiting...")
        sys.exit(255)
    try:
        wlan_json = json.dumps(wlan)
    except:
        print("Error while loading the wlan settings from the file... exiting...")
        sys.exit(255)
    mistapi.api.v1.sites.wlans.createSiteWlan(apisession, site_id, wlan_json)

def remove_wlan(apisession, site_id):
    wlans = mistapi.api.v1.sites.wlans.listSiteWlans(apisession, site_id).data
    resp = -1
    while True:    
        print()    
        print("Available WLANs:")
        i = 0
        for wlan in wlans:
            print(f"{i}) {wlan['ssid']} (id: {wlan['id']})")
            i+=1
        print()        
        resp = input(f"Which WLAN do you want to delete (0-{i-1}, or q to quit)? ")
        if resp.lower() == "q":
            sys.exit(0)
        else:
            try:
                resp_num = int(resp)
                if resp_num >= 0 and resp_num <= i:
                    wlan = wlans[resp_num]
                    print()    
                    confirmation = input(f"Are you sure you want to delete WLAN {wlan['ssid']} (y/N)? ")
                    if confirmation.lower() == "y":
                        break
                else:
                    print(f"{resp_num} is not part of the possibilities.")
            except:
                print("Only numbers are allowed.")
    mistapi.api.v1.sites.wlans.deleteSiteWlan(apisession, site_id, wlan["id"])    


def display_wlan(apisession, site_id):
    fields = ["id","ssid", "enabled", "auth", "auth_servers", "acct_servers", "band", "interface", "vlan_id", "dynamic_vlan", "hide_ssid"]
    site_wlans = mistapi.api.v1.sites.wlans.getSiteWlanDerived(apisession, site_id).data 
    mistapi.cli.display_list_of_json_as_table(site_wlans, fields)

def start_site_conf_wlan(apisession, site_id):
    while True:
        print()    
        print(" ===================")
        print(" == CURRENT WLANS ==")
        display_wlan(apisession, site_id)
        print(" ===================")
        print()
        actions = ["add WLAN", "remove WLAN"]
        print("What do you want to do:")
        i = -1
        for action in actions:
            i+= 1
            print(f"{i}) {action}")
        print()    
        resp = input(f"Choice (0-{i}, q to quit): ")
        if resp.lower() == "q":
            sys.exit(0)
        else:
            try:
                resp_num = int(resp)
            except:
                print("Only numbers are allowed.")
            if resp_num >= 0 and resp_num <= i:
                if actions[resp_num] == "add WLAN": 
                    add_wlan(apisession, site_id)
                    print()    
                    print(" ========================")
                    print(" == WLANS AFTER CHANGE ==")
                    display_wlan(apisession, site_id)
                    print(" ========================")              
                    break
                elif actions[resp_num] == "remove WLAN":
                    remove_wlan(apisession, site_id)
                    print()    
                    print(" ========================")
                    print(" == WLANS AFTER CHANGE ==")
                    display_wlan(apisession, site_id)
                    print(" ========================")
                    break
            else:
                print(f"{resp_num} is not part of the possibilities.")

def start(apisession):
    org_id = mistapi.cli.select_org(apisession)[0]
    site_id = mistapi.cli.select_site(apisession, org_id=org_id, allow_many=False)[0]
    start_site_conf_wlan(apisession, site_id)

##### ENTRY POINT ####

if __name__ == "__main__":
    #### LOGS ####
    logging.basicConfig(filename=log_file, filemode='w')
    logger.setLevel(logging.DEBUG)
    ### START ###
    apisession = mistapi.APISession(env_file=env_file)
    apisession.login()
    start(apisession)
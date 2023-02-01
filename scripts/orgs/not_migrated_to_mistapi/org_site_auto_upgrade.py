'''
Written by Thomas Munzer (tmunzer@juniper.net)
Github repository: https://github.com/tmunzer/Mist_library/
'''

#### PARAMETERS #####

import sys
from mlib import cli
import mlib as mist_lib
auto_site_assignment = {
    "enable": True,
    "rules": []
}

#### IMPORTS #####

#### GLOBAL VARIABLES ####
# auto_upgrade_rule = {
#     "enabled": True,
#     "version": "custom",
#     "time_of_day": "02:00",
#     "custom_versions": {
#         "AP32": "0.10.24028",
#         "AP32E": "0.8.21602"
#     },
#     "day_of_week": "sun"
# }
auto_upgrade_rule= {
        "enabled": False
        }
#### FUNCTIONS ####


def get_site_setting(mist, site_id):
    print("Retrieving current settings for site {0} ".format(site_id).ljust(79, " "), end="", flush=True)
    try:
        current_auto_upgrade_rule = mistapi.api.v1.sites.settings.get(mist, site_id)["result"]["auto_upgrade"]
        update_site_setting(mist, site_id, current_auto_upgrade_rule)
        print("\033[92m\u2714\033[0m")
    except:        
        print('\033[31m\u2716\033[0m')

def update_site_setting(mist, site_id, current_auto_upgrade_rule):
    parameters = ["enabled", "version", "time_of_day", "day_of_week", "custom_versions"]
    for param in parameters:
        try:
            current_auto_upgrade_rule[param]= auto_upgrade_rule[param]
        except:
            pass
    print("Updating settings for site {0} ".format(site_id).ljust(79, " "), end="", flush=True)
    try:
        mistapi.api.v1.sites.settings.update(mist, site_id, {"auto_upgrade": current_auto_upgrade_rule})
        print("\033[92m\u2714\033[0m")
    except:        
        print('\033[31m\u2716\033[0m')
    
def confirm_action(mist, site_ids):
    while True:
        print("New Auto Upgrade Configuration".center(80, "-"))
        print(auto_upgrade_rule)
        print("".center(80, "-"))
        print()
        resp = input(
            "Are you sure you want to update the selected sites with the configuration above (y/N)?")
        if resp.lower() == 'n' or resp == "":
            sys.exit(0)
        elif resp.lower() == "y":
            for site_id in site_ids:
                get_site_setting(mist, site_id)
            break


def get_site_ids(mist, org_id):
    site_ids = []
    sites = mistapi.api.v1.orgs.sites.get(mist, org_id)["result"]
    for site in sites:
        site_ids.append(site["id"])
    return site_ids
####### ENTRY POINT #######


mist = mistapi.APISession()
org_id = cli.select_org(mist)[0]

while True:
    resp = input(
        "Do you want to update the auto-upgrade settings on all the sites (y/N)?")
    if resp.lower() == 'n' or resp == "":
        site_id = cli.select_site(mist, org_id)
        confirm_action(mist, [site_id])
        break
    elif resp.lower() == "y":
        site_ids = get_site_ids(mist, org_id)
        confirm_action(mist, site_ids)
        break

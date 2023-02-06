'''
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script update the Mist AP Auto_upgrade parameters in the site settings

Requireements:
mistapi: https://pypi.org/project/mistapi/

Usage:
This script can be run as is (without parameters). 
The "auto_upgrade_rule" settings must be defined in the "PARAMETERS" section
below.
The site(s) to update will be selected during the script execution.

It is recomended to use an environment file to store the required information
to request the Mist Cloud (see https://pypi.org/project/mistapi/ for more 
information about the available parameters).

Examples:
python3 ./org_site_auto_upgrade.py

'''

#### IMPORTS #####
import sys
import logging
try:
    import mistapi
except:
    print("""
Critical: 
\"mistapi\" package is missing. Please use the pip command to install it.

# Linux/macOS
python3 -m pip install mistapi

# Windows
py -m pip install mistapi
    """)
    sys.exit(2)

#### PARAMETERS #####

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

log_file = "./script.log"
env_file = "~/.mist_env"

#### LOGS ####
logger = logging.getLogger(__name__)

#### FUNCTIONS ####


def get_site_setting(mist_session, site_id):
    print("Retrieving current settings for site {0} ".format(site_id).ljust(79, " "), end="", flush=True)
    try:
        current_auto_upgrade_rule = mistapi.api.v1.sites.setting.getSiteSetting(mist_session, site_id).data["auto_upgrade"]
        print("\033[92m\u2714\033[0m")
        update_site_setting(mist_session, site_id, current_auto_upgrade_rule)
    except:        
        print('\033[31m\u2716\033[0m')

def update_site_setting(mist_session, site_id, current_auto_upgrade_rule):
    parameters = ["enabled", "version", "time_of_day", "day_of_week", "custom_versions"]
    for param in parameters:
        try:
            current_auto_upgrade_rule[param]= auto_upgrade_rule[param]
        except:
            pass
    print("Updating settings for site {0} ".format(site_id).ljust(79, " "), end="", flush=True)
    try:
        mistapi.api.v1.sites.setting.updateSiteSettings(mist_session, site_id, {"auto_upgrade": current_auto_upgrade_rule})
        print("\033[92m\u2714\033[0m")
    except:        
        print('\033[31m\u2716\033[0m')
    
def confirm_action(mist_session, site_ids):
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
                get_site_setting(mist_session, site_id)
            break


def get_site_ids(mist_session, org_id):
    site_ids = []
    sites = mistapi.api.v1.orgs.sites.getOrgSites(mist_session, org_id)["result"]
    for site in sites:
        site_ids.append(site["id"])
    return site_ids
####### ENTRY POINT #######


if __name__ == "__main__":
    #### LOGS ####
    logging.basicConfig(filename=log_file, filemode='w')
    logger.setLevel(logging.DEBUG)
    ### MIST SESSION ###
    mist_session = mistapi.APISession(env_file=env_file)
    mist_session.login()

    org_id = mistapi.cli.select_org(mist_session)[0]

while True:
    resp = input(
        "Do you want to update the auto-upgrade settings on all the sites (y/N)?")
    if resp.lower() == 'n' or resp == "":
        site_id = mistapi.cli.select_site(mist_session, org_id)[0]
        confirm_action(mist_session, [site_id])
        break
    elif resp.lower() == "y":
        site_ids = get_site_ids(mist_session, org_id)
        confirm_action(mist_session, site_ids)
        break

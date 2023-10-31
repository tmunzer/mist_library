"""
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to backup a whole site.
You can use the script "site_conf_deploy.py" to restore the generated backup files to an
existing organization (empty or not) or to a new one.

This script will not change/create/delete/touch any existing objects. It will just
retrieve every single object from the organization.

-------
Requirements:
mistapi: https://pypi.org/project/mistapi/

-------
Usage:
This script can be run as is (without parameters), or with the options below.
If no options are defined, or if options are missing, the missing options will
be asked by the script or the default values will be used.

It is recomended to use an environment file to store the required information
to request the Mist Cloud (see https://pypi.org/project/mistapi/ for more 
information about the available parameters).

-------
Script Parameters:
-h, --help              display this help
-o, --org_id=           Set the org_id (required to backup templates assigned to the site)
-s, --site_ids          Set the list of site_ids to backup, comma separated 
                        If the site_ids is not providced, the script will propose to
                        select the site to backup
-b, --backup_folder=    Path to the folder where to save the org backup (a subfolder
                        will be created with the org name)
                        default is "./org_backup"
-l, --log_file=         define the filepath/filename where to write the logs
                        default is "./script.log"
-e, --env=              define the env file to use (see mistapi env file documentation 
                        here: https://pypi.org/project/mistapi/)
                        default is "~/.mist_env"

-------
Examples:
python3 ./site_conf_backup.py
python3 ./site_conf_backup.py --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 -s a39d0e91-xxxx-xxxx-xxxx-42df868c5a0b

"""

#### IMPORTS ####
import logging
import json
import urllib.request
import os
import sys
import getopt

MISTAPI_MIN_VERSION = "0.44.1"

try:
    import mistapi
    from mistapi.__logger import console
except:
    print(
        """
        Critical: 
        \"mistapi\" package is missing. Please use the pip command to install it.

        # Linux/macOS
        python3 -m pip install mistapi

        # Windows
        py -m pip install mistapi
        """
    )
    sys.exit(2)


#####################################################################
#### PARAMETERS #####
BACKUP_FOLDER = "./site_backup"
BACKUP_FILE = "site_conf_file.json"
LOG_FILE = "./script.log"
FILE_PREFIX = ".".join(BACKUP_FILE.split(".")[:-1])
ENV_FILE = "~/.mist_env"

#####################################################################
#### LOGS ####
LOGGER = logging.getLogger(__name__)


#####################################################################
# BACKUP OBJECTS REFS
ORG_STEPS = {
    "alarmtemplate": {
        "mistapi_function": mistapi.api.v1.orgs.alarmtemplates.listOrgAlarmTemplates,
        "text": "Org alarmtemplates",
    },
    "rftemplate": {
        "mistapi_function": mistapi.api.v1.orgs.rftemplates.listOrgRfTemplates,
        "text": "Org rftemplates",
    },
    "networktemplate": {
        "mistapi_function": mistapi.api.v1.orgs.networktemplates.listOrgNetworkTemplates,
        "text": "Org networktemplates",
    },
    "secpolicy": {
        "mistapi_function": mistapi.api.v1.orgs.secpolicies.listOrgSecPolicies,
        "text": "Org secpolicies",
    },
}
SITE_STEPS = {
    "info": {
        "mistapi_function": mistapi.api.v1.sites.sites.getSiteInfo,
        "text": "Site info",
    },
    "settings": {
        "mistapi_function": mistapi.api.v1.sites.setting.getSiteSetting,
        "text": "Site settings",
    },
    "assets": {
        "mistapi_function": mistapi.api.v1.sites.assets.listSiteAssets,
        "text": "Site assets",
    },
    "assetfilters": {
        "mistapi_function": mistapi.api.v1.sites.assetfilters.listSiteAssetFilters,
        "text": "Site assetfilters",
    },
    "beacons": {
        "mistapi_function": mistapi.api.v1.sites.beacons.listSiteBeacons,
        "text": "Site beacons",
    },
    "maps": {
        "mistapi_function": mistapi.api.v1.sites.maps.listSiteMaps,
        "text": "Site maps",
    },
    "psks": {
        "mistapi_function": mistapi.api.v1.sites.psks.listSitePsks,
        "text": "Site psks",
    },
    "rssizones": {
        "mistapi_function": mistapi.api.v1.sites.rssizones.listSiteRssiZones,
        "text": "Site rssizones",
    },
    "vbeacons": {
        "mistapi_function": mistapi.api.v1.sites.vbeacons.listSiteVBeacons,
        "text": "Site vbeacons",
    },
    "webhooks": {
        "mistapi_function": mistapi.api.v1.sites.webhooks.listSiteWebhooks,
        "text": "Site webhooks",
    },
    "wlans": {
        "mistapi_function": mistapi.api.v1.sites.wlans.listSiteWlans,
        "text": "Site wlans",
    },
    "wxrules": {
        "mistapi_function": mistapi.api.v1.sites.wxrules.listSiteWxRules,
        "text": "Site wxrules",
    },
    "wxtags": {
        "mistapi_function": mistapi.api.v1.sites.wxtags.listSiteWxTags,
        "text": "Site wxtags",
    },
    "wxtunnels": {
        "mistapi_function": mistapi.api.v1.sites.wxtunnels.listSiteWxTunnels,
        "text": "Site wxtunnels",
    },
    "zones": {
        "mistapi_function": mistapi.api.v1.sites.zones.listSiteZones,
        "text": "Site zones",
    },
}


#####################################################################
#### BACKUP FUNCTIONS ####
def log_message(message):
    print(f"{message}".ljust(79, "."), end="", flush=True)


def log_success(message):
    print("\033[92m\u2714\033[0m")
    LOGGER.info(f"{message}: Success")


def log_failure(message):
    print("\033[31m\u2716\033[0m")
    LOGGER.exception(f"{message}: Failure")


def _do_backup(
    mist_session, backup_function, scope_id, message, request_type: str = None
):
    try:
        log_message(message)
        if request_type:
            response = backup_function(mist_session, scope_id, type=request_type)
        else:
            response = backup_function(mist_session, scope_id)
        data = mistapi.get_all(mist_session, response)
        log_success(message)
        return data
    except Exception as e:
        log_failure(message)
        LOGGER.error("Exception occurred", exc_info=True)
        return None


def _backup_wlan_portal(org_id, site_id, wlans):
    for wlan in wlans:
        if not site_id:
            portal_file_name = f"{FILE_PREFIX}_wlan_{wlan['id']}.json"
            portal_image = f"{FILE_PREFIX}_wlan_{wlan['id']}.png"
        else:
            portal_file_name = f"{FILE_PREFIX}_site_{site_id}_wlan_{wlan['id']}.json"
            portal_image = f"{FILE_PREFIX}_site_{site_id}_wlan_{wlan['id']}.png"

        if "portal_template_url" in wlan:
            print(
                f"Backuping portal template for WLAN {wlan['ssid']} ".ljust(79, "."),
                end="",
                flush=True,
            )
            try:
                urllib.request.urlretrieve(
                    wlan["portal_template_url"], portal_file_name
                )
                print("\033[92m\u2714\033[0m")
            except:
                print("\033[31m\u2716\033[0m")
        if "portal_image" in wlan:
            print(
                f"Backuping portal image for WLAN {wlan['ssid']} ".ljust(79, "."),
                end="",
                flush=True,
            )
            try:
                urllib.request.urlretrieve(wlan["portal_image"], portal_image)
                print("\033[92m\u2714\033[0m")
            except:
                print("\033[31m\u2716\033[0m")


#####################################################################
#### BACKUP SITE ####
def _backup_site(apisession, site_id, site_name, org_id):
    print()
    console.info(f"Backup: processing site {site_name} ...")
    print()
    site_backup = {
        "site": {
            "info": {},
            "settings": {},
            "assetfilters": {},
            "assets": {},
            "beacons": {},
            "maps": {},
            "psks": {},
            "rssizones": {},
            "vbeacons": {},
            "webhooks": {},
            "wlans": {},
            "wxrules": {},
            "wxtags": {},
            "wxtunnels": {},
            "zones": {},
        },
        "rftemplate": {},
        "secpolicy": {},
        "alarmtemplate": {},
        "networktemplate": {},
        "sitegroup_names": [],
    }

    for step_name in SITE_STEPS:
        step = SITE_STEPS[step_name]
        site_backup["site"][step_name] = _do_backup(
            apisession, step["mistapi_function"], site_id, step["text"]
        )

    _backup_wlan_portal(org_id, site_id, site_backup["site"]["wlans"])

    for step_name in ORG_STEPS:
        if site_backup["site"].get(f"{step_name}_id"):
            site_backup[step_name] = _do_backup(
                apisession, step["mistapi_function"], org_id, step["text"]
            )

    if site_backup["site"].get("sitegroup_ids"):
        for sitegroup_id in site_backup["site"]["sitegroup_ids"]:
            sitegroup_info = mistapi.api.v1.orgs.sitegroups.getOrgSiteGroup(
                apisession, org_id, sitegroup_id
            ).data
            if "name" in sitegroup_info:
                site_backup["sitegroup_names"].append(sitegroup_info["name"])

    for xmap in site_backup["site"]["maps"]:
        if "url" in xmap:
            print(
                f"Backuping image for map {xmap['name']} ".ljust(79, "."),
                end="",
                flush=True,
            )
            try:
                url = xmap["url"]
                image_name = f"{FILE_PREFIX}_site_{site_id}_map_{xmap['id']}.png"
                urllib.request.urlretrieve(url, image_name)
                print("\033[92m\u2714\033[0m")
            except:
                print("\033[31m\u2716\033[0m")

    return site_backup


#####################################################################
#### SAVING FUNCTIONS ####
def _save_to_file(site_name, backup):
    print(f"Saving backup to {site_name}/{BACKUP_FILE} file...".ljust(79, "."), end="", flush=True)
    try:
        with open(BACKUP_FILE, "w") as f:
            json.dump(backup, f)
        print("\033[92m\u2714\033[0m")
    except:
        print("\033[31m\u2716\033[0m")


def _goto_folder(folder_name):
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
    os.chdir(folder_name)


def start_site_backup(apisession, org_id, org_name, site_ids, backup_folder):
    _goto_folder(backup_folder)
    _goto_folder(org_name)

    for site_id in site_ids:
        site_name = mistapi.api.v1.sites.sites.getSiteInfo(apisession, site_id).data[
            "name"
        ]
        _goto_folder(site_name)

        backup = _backup_site(apisession, site_id, site_name, org_id)
        _save_to_file(site_name, backup)
        print()
        console.info(f"Backup done for site {site_name}")
        print()

        os.chdir("..")


def start(
    apisession: mistapi.APISession, org_id: str, site_ids: list, backup_folder: str):
    if not org_id:
        org_id = mistapi.cli.select_org(apisession)[0]
    if not site_ids:
        site_ids = mistapi.cli.select_site(apisession, org_id, allow_many=True)
    else:
        org_name = mistapi.api.v1.orgs.orgs.getOrg(apisession, org_id).data["name"]
        response = mistapi.api.v1.orgs.sites.listOrgSites(apisession, org_id)
        org_sites = mistapi.get_all(apisession, response)
        org_site_ids = []

        for site in org_sites:
            org_site_ids.append(site["id"])

        for site_id in site_ids:
            if  site_id in org_site_ids:
                LOGGER.info(f"site ID {site_id} belong to the org {org_name}")
            else:
                console.critical(f"Site ID {site_id} does not belong to the Org {org_name}. Exiting...")
                sys.exit(255)

    current_folder = os.getcwd()
    if not backup_folder:
        backup_folder = BACKUP_FOLDER
    start_site_backup(apisession, org_id, org_name, site_ids, backup_folder)
    os.chdir(current_folder)


#####################################################################
##### USAGE ####
def usage():
    print(
        """
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to backup a whole site.
You can use the script "site_conf_deploy.py" to restore the generated backup files to an
existing organization (empty or not) or to a new one.

This script will not change/create/delete/touch any existing objects. It will just
retrieve every single object from the organization.

-------
Requirements:
mistapi: https://pypi.org/project/mistapi/

-------
Usage:
This script can be run as is (without parameters), or with the options below.
If no options are defined, or if options are missing, the missing options will
be asked by the script or the default values will be used.

It is recomended to use an environment file to store the required information
to request the Mist Cloud (see https://pypi.org/project/mistapi/ for more 
information about the available parameters).

-------
Script Parameters:
-h, --help              display this help
-o, --org_id=           Set the org_id (required to backup templates assigned to the site)
-s, --site_ids          Set the list of site_ids to backup, comma separated 
                        If the site_ids is not providced, the script will propose to
                        select the site to backup
-b, --backup_folder=    Path to the folder where to save the org backup (a subfolder
                        will be created with the org name)
                        default is "./org_backup"
-l, --log_file=         define the filepath/filename where to write the logs
                        default is "./script.log"
-e, --env=              define the env file to use (see mistapi env file documentation 
                        here: https://pypi.org/project/mistapi/)
                        default is "~/.mist_env"

-------
Examples:
python3 ./site_conf_backup.py
python3 ./site_conf_backup.py --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 -s a39d0e91-xxxx-xxxx-xxxx-42df868c5a0b

"""
    )
    sys.exit(0)


#####################################################################
##### ENTRY POINT ####
if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(
            sys.argv[1:],
            "ho:s:e:l:b:",
            ["help", "org_id=", "site_ids=", "env=", "log_file=", "backup_folder="],
        )
    except getopt.GetoptError as err:
        console.error(err)
        usage()

    ORG_ID = None
    SITE_IDS = None
    for o, a in opts:
        if o in ["-h", "--help"]:
            usage()
        elif o in ["-o", "--org_id"]:
            ORG_ID = a
        elif o in ["-s", "--site_ids"]:
            SITE_IDS = a.split(",")
        elif o in ["-e", "--env"]:
            ENV_FILE = a
        elif o in ["-l", "--log_file"]:
            LOG_FILE = a
        elif o in ["-b", "--backup_folder"]:
            BACKUP_FOLDER = a
        else:
            assert False, "unhandled option"

    #### LOGS ####
    logging.basicConfig(filename=LOG_FILE, filemode="w")
    LOGGER.setLevel(logging.DEBUG)
    ### START ###
    APISESSION = mistapi.APISession(env_file=ENV_FILE)
    APISESSION.login()
    start(APISESSION, ORG_ID, SITE_IDS, BACKUP_FOLDER)

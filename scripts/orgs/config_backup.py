'''
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to backup a whole organization.
You can use the script "config_restore.py" to restore the generated backup files to an
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
-o, --org_id=           Set the org_id
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
python3 ./config_backup.py -f ./my_new_sites.csv                 
python3 ./config_backup.py --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 

'''


#### IMPORTS ####
import logging
import json
import urllib.request
import os
import sys
import getopt

try:
    import mistapi
    from mistapi.__logger import console
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

#####################################################################
#### PARAMETERS #####
backup_folder = "./org_backup"
backup_file = "org_conf_file.json"
log_file = "./org_conf_backup.log"
file_prefix = ".".join(backup_file.split(".")[:-1])
env_file = "~/.mist_env"

#####################################################################
#### LOGS ####
logger = logging.getLogger(__name__)

#####################################################################
# BACKUP OBJECTS REFS
org_steps = {
    "data": {"mistapi_function": mistapi.api.v1.orgs.orgs.getOrgInfo, "text": "Org info"},
    "sites": {"mistapi_function": mistapi.api.v1.orgs.sites.getOrgSites, "text": "Org Sites"},
    "settings": {"mistapi_function": mistapi.api.v1.orgs.setting.getOrgSettings, "text": "Org settings"},
    "webhooks": {"mistapi_function": mistapi.api.v1.orgs.webhooks.getOrgWebhooks, "text": "Org webhooks"},
    "assetfilters": {"mistapi_function": mistapi.api.v1.orgs.assetfilters.getOrgAssetFilters, "text": "Org assetfilters"},
    "alarmtemplates": {"mistapi_function": mistapi.api.v1.orgs.alarmtemplates.getOrgAlarmTemplates, "text": "Org alarmtemplates"},
    "deviceprofiles": {"mistapi_function": mistapi.api.v1.orgs.deviceprofiles.getOrgDeviceProfiles, "text": "Org deviceprofiles"},
    "hubprofiles": {"mistapi_function": mistapi.api.v1.orgs.deviceprofiles.getOrgDeviceProfiles, "text": "Org hubprofiles", "request_type":"gateway"},
    "mxclusters": {"mistapi_function": mistapi.api.v1.orgs.mxclusters.getOrgMxEdgeClusters, "text": "Org mxclusters"},
    "mxtunnels": {"mistapi_function": mistapi.api.v1.orgs.mxtunnels.getOrgMxTunnels, "text": "Org mxtunnels"},
    "psks": {"mistapi_function": mistapi.api.v1.orgs.psks.getOrgPsks, "text": "Org psks"},
    "pskportals": {"mistapi_function": mistapi.api.v1.orgs.pskportals.getOrgPskPortals, "text": "Org pskportals"},
    "rftemplates": {"mistapi_function": mistapi.api.v1.orgs.rftemplates.getOrgRfTemplates, "text": "Org rftemplates"},
    "networktemplates": {"mistapi_function": mistapi.api.v1.orgs.networktemplates.getOrgNetworkTemplates, "text": "Org networktemplates"},
    "evpn_topologies": {"mistapi_function": mistapi.api.v1.orgs.evpn_topologies.getOrgEvpnTopologies, "text": "Org evpn_topologies"},
    "services": {"mistapi_function": mistapi.api.v1.orgs.services.getOrgServices, "text": "Org services"},
    "networks": {"mistapi_function": mistapi.api.v1.orgs.networks.getOrgNetworks, "text": "Org networks"},
    "gatewaytemplates": {"mistapi_function": mistapi.api.v1.orgs.gatewaytemplates.getOrgGatewayTemplates, "text": "Org gatewaytemplates"},
    "vpns": {"mistapi_function": mistapi.api.v1.orgs.vpns.getOrgsVpns, "text": "Org vpns"},
    "secpolicies": {"mistapi_function": mistapi.api.v1.orgs.secpolicies.getOrgSecPolicies, "text": "Org secpolicies"},
    "sitegroups": {"mistapi_function": mistapi.api.v1.orgs.sitegroups.getOrgSiteGroups, "text": "Org sitegroups"},
    "ssos": {"mistapi_function": mistapi.api.v1.orgs.ssos.getOrgSsos, "text": "Org ssos"},
    "ssoroles": {"mistapi_function": mistapi.api.v1.orgs.ssoroles.getOrgSsoRoles, "text": "Org ssoroles"},
    "templates": {"mistapi_function": mistapi.api.v1.orgs.templates.getOrgTemplates, "text": "Org templates"},
    "wxrules": {"mistapi_function": mistapi.api.v1.orgs.wxrules.getOrgWxRules, "text": "Org wxrules"},
    "wxtags": {"mistapi_function": mistapi.api.v1.orgs.wxtags.getOrgWxTags, "text": "Org wxtags"},
    "wxtunnels": {"mistapi_function": mistapi.api.v1.orgs.wxtunnels.getOrgWxTunnels, "text": "Org wxtunnels"},
    "nactags": {"mistapi_function": mistapi.api.v1.orgs.nactags.getOrgNacTags, "text": "Org nactags"},
    "nacrules": {"mistapi_function": mistapi.api.v1.orgs.nacrules.getOrgNacRules, "text": "Org nacrules"},
    "wlans": {"mistapi_function": mistapi.api.v1.orgs.wlans.getOrgWlans, "text": "Org wlans"}
}
site_steps = {        
    "assets": {"mistapi_function": mistapi.api.v1.sites.assets.getSiteAssets, "text": "Site assets"},
    "assetfilters": {"mistapi_function": mistapi.api.v1.sites.assetfilters.getSiteAssetFilters, "text": "Site assetfilters"},
    "beacons": {"mistapi_function": mistapi.api.v1.sites.beacons.getSiteBeacons, "text": "Site beacons"},
    "maps": {"mistapi_function": mistapi.api.v1.sites.maps.getSiteMaps, "text": "Site maps"},
    "psks": {"mistapi_function": mistapi.api.v1.sites.psks.getSitePsks, "text": "Site psks"},
    "rssizones": {"mistapi_function": mistapi.api.v1.sites.rssizones.getSiteRssiZones, "text": "Site rssizones"},
    "settings": {"mistapi_function": mistapi.api.v1.sites.setting.getSiteSetting, "text": "Site settings"},
    "vbeacons": {"mistapi_function": mistapi.api.v1.sites.vbeacons.getSiteVBeacons, "text": "Site vbeacons"},
    "webhooks": {"mistapi_function": mistapi.api.v1.sites.webhooks.getSiteWebhooks, "text": "Site webhooks"},
    "wlans": {"mistapi_function": mistapi.api.v1.sites.wlans.getSiteWlans, "text": "Site wlans"},
    "wxrules": {"mistapi_function": mistapi.api.v1.sites.wxrules.getSiteWxRules, "text": "Site wxrules"},
    "wxtags": {"mistapi_function": mistapi.api.v1.sites.wxtags.getSiteWxTags, "text": "Site wxtags"},
    "wxtunnels": {"mistapi_function": mistapi.api.v1.sites.wxtunnels.getSiteWxTunnels, "text": "Site wxtunnels"},
    "zones": {"mistapi_function": mistapi.api.v1.sites.zones.getSiteZones, "text": "Site zones"}
}

#####################################################################
#### FUNCTIONS ####

def log_message(message):
    print(f"{message}".ljust(79, '.'), end="", flush=True)

def log_success(message):
    print("\033[92m\u2714\033[0m")
    logger.info(f"{message}: Success")

def log_failure(message):
    print('\033[31m\u2716\033[0m')
    logger.exception(f"{message}: Failure")


def _backup_wlan_portal(org_id, site_id, wlans):
    for wlan in wlans:
        wlan_id = wlan["id"]
        if not site_id:
            portal_file_name = f"{file_prefix}_org_{org_id}_wlan_{wlan_id}.json"
            portal_image = f"{file_prefix}_org_{org_id}_wlan_{wlan_id}.png"
        else:
            portal_file_name = f"{file_prefix}_org_{org_id}_site_{site_id}_wlan_{wlan_id}.json"
            portal_image = f"{file_prefix}_org_{org_id}_site_{site_id}_wlan_{wlan_id}.png"
        if "portal_template_url" in wlan and wlan["portal_template_url"]:
            try:
                message=f"portal template for wlan {wlan_id} "
                log_message(message)
                urllib.request.urlretrieve(
                    wlan["portal_template_url"], portal_file_name)
                log_success(message)
            except Exception as e:
                log_failure(message)
                logger.error("Exception occurred", exc_info=True)
        if "portal_image" in wlan and wlan["portal_image"]:
            try:
                message=f"portal image for wlan {wlan_id} "
                log_message(message)
                urllib.request.urlretrieve(wlan["portal_image"], portal_image)
                log_success(message)
            except Exception as e:
                log_failure(message)
                logger.error("Exception occurred", exc_info=True)


def _do_backup(mist_session, backup_function, scope_id, message, request_type:str=None):
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
        logger.error("Exception occurred", exc_info=True)
        return None

#### BACKUP ####
def _backup_full_org(mist_session, org_id, org_name):
    print()
    print(f" Backuping Org {org_name} ".center(80, "_"))
    backup = {}
    backup["org"] = {"id": org_id}

    ### ORG BACKUP
    for step_name in org_steps:
        step = org_steps[step_name]
        request_type = step.get("request_type")
        backup["org"][step_name] = _do_backup(mist_session, step["mistapi_function"], org_id, step["text"], request_type)
    _backup_wlan_portal(org_id, None, backup["org"]["wlans"])
    
    ### SITES BACKUP
    for site in backup["org"]["sites"]:
        site_id = site["id"]
        site_name = site["name"]
        print(f" Backuping Site {site_name} ".center(80, "_"))

        for step_name in site_steps:
            step = site_steps[step_name]
            site[step_name] = _do_backup(mist_session, step["mistapi_function"], site_id, step["text"])

        if site["wlans"]:
            _backup_wlan_portal(org_id, site_id, site["wlans"])

        message="Site map images "
        log_message(message)
        try:
            for xmap in site["maps"]:
                url = None
                if "url" in xmap:
                    url = xmap["url"]
                    xmap_id = xmap["id"]
                if url:
                    image_name = f"{file_prefix}_org_{org_id}_site_{site_id}_map_{xmap_id}.png"
                    urllib.request.urlretrieve(url, image_name)
            log_success(message)
        except Exception as e:
            log_failure(message)
            logger.error("Exception occurred", exc_info=True)

    print(" Backup Done ".center(80, "_"))
    logger.info(f"ORG {org_name} > Backup done")
    return backup


def _save_to_file(backup_file, backup, org_name):
    backup_path = os.path.join(backup_folder, org_name, backup_file)
    message=f"Saving to file {backup_path} "
    log_message(message)
    try:
        with open(backup_file, "w") as f:
            json.dump(backup, f)
        log_success(message)
    except Exception as e:
        log_failure(message)
        logger.error("Exception occurred", exc_info=True)


def start_org_backup(mist_session, org_id, org_name, parent_log_file=None):
    if parent_log_file:
        logging.basicConfig(filename=log_file, filemode='a')
        logger.setLevel(logging.DEBUG)
    try:
        if not os.path.exists(backup_folder):
            os.makedirs(backup_folder)
        os.chdir(backup_folder)
        if not os.path.exists(org_name):
            os.makedirs(org_name)
        os.chdir(org_name)

        backup = _backup_full_org(mist_session, org_id, org_name)
        _save_to_file(backup_file, backup, org_name)
    except Exception as e:
        print(e)
        logger.error("Exception occurred", exc_info=True)


def start(mist_session:mistapi.APISession, org_id:str, backup_folder_param:str=None):
    if backup_folder_param:
        global backup_folder 
        backup_folder = backup_folder_param
    if not org_id: org_id = mistapi.cli.select_org(mist_session)[0]
    org_name = mistapi.api.v1.orgs.orgs.getOrgInfo(mist_session, org_id).data["name"]
    start_org_backup(mist_session, org_id, org_name)


#####################################################################
# USAGE
def usage():
    print('''
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to backup a whole organization.
You can use the script "config_restore.py" to restore the generated backup files to an
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
-o, --org_id=           Set the org_id
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
python3 ./config_backup.py -f ./my_new_sites.csv                 
python3 ./config_backup.py --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 

'''
)


#####################################################################
##### ENTRY POINT ####
if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(sys.argv[1:], "ho:e:l:b:", [
                                   "help", "org_id=", "env=", "log_file=", "backup_folder="])
    except getopt.GetoptError as err:
        console.error(err)
        usage()

    org_id = None
    for o, a in opts:
        if o in ["-h", "--help"]:
            usage()
        elif o in ["-o", "--org_id"]:
            org_id = a      
        elif o in ["-e", "--env"]:
            env_file = a
        elif o in ["-l", "--log_file"]:
            log_file = a
        elif o in ["-b", "--backup_folder"]:
            backup_folder = a
        else:
            assert False, "unhandled option"

    #### LOGS ####
    logging.basicConfig(filename=log_file, filemode='w')
    logger.setLevel(logging.DEBUG)
    ### START ###
    apisession = mistapi.APISession(env_file=env_file)
    apisession.login()
    start(apisession, org_id, backup_folder)

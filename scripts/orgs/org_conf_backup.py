'''
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to backup a whole organization.
You can use the script "org_conf_deploy.py" to restore the generated backup 
files to an existing organization (empty or not) or to a new one.

This script will not change/create/delete/touch any existing objects. It will 
just retrieve every single object from the organization.

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
-b, --backup_folder=    Path to the folder where to save the org backup (a 
                        subfolder will be created with the org name)
                        default is "./org_backup"
-l, --log_file=         define the filepath/filename where to write the logs
                        default is "./script.log"
-e, --env=              define the env file to use (see mistapi env file 
                        documentation here: https://pypi.org/project/mistapi/)
                        default is "~/.mist_env"

-------
Examples:
python3 ./org_conf_backup.py     
python3 ./org_conf_backup.py --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 

'''


#### IMPORTS ####
import logging
import json
import urllib.request
import os
import signal
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
log_file = "./script.log"
file_prefix = ".".join(backup_file.split(".")[:-1])
env_file = "~/.mist_env"

#####################################################################
#### LOGS ####
logger = logging.getLogger(__name__)

#####################################################################
#### GLOBALS #####
sys_exit=False
def sigint_handler(signal, frame):
    global sys_exit
    sys_exit = True
    ('[Ctrl C],KeyboardInterrupt exception occured.')
signal.signal(signal.SIGINT, sigint_handler)
#####################################################################
# BACKUP OBJECTS REFS
org_steps = {
    "data": {"mistapi_function": mistapi.api.v1.orgs.orgs.getOrgInfo, "text": "Org info", "check_next":False},
    "settings": {"mistapi_function": mistapi.api.v1.orgs.setting.getOrgSettings, "text": "Org settings", "check_next":False},
    "sites": {"mistapi_function": mistapi.api.v1.orgs.sites.listOrgSites, "text": "Org Sites", "check_next":True},
    "webhooks": {"mistapi_function": mistapi.api.v1.orgs.webhooks.listOrgWebhooks, "text": "Org webhooks", "check_next":True},
    "assetfilters": {"mistapi_function": mistapi.api.v1.orgs.assetfilters.listOrgAssetFilters, "text": "Org assetfilters", "check_next":True},
    "alarmtemplates": {"mistapi_function": mistapi.api.v1.orgs.alarmtemplates.listOrgAlarmTemplates, "text": "Org alarmtemplates", "check_next":True},
    "deviceprofiles": {"mistapi_function": mistapi.api.v1.orgs.deviceprofiles.listOrgDeviceProfiles, "text": "Org deviceprofiles", "check_next":True},
    "hubprofiles": {"mistapi_function": mistapi.api.v1.orgs.deviceprofiles.listOrgDeviceProfiles, "text": "Org hubprofiles", "request_type":"gateway", "check_next":True},
    "mxclusters": {"mistapi_function": mistapi.api.v1.orgs.mxclusters.listOrgMxEdgeClusters, "text": "Org mxclusters", "check_next":True},
    "mxtunnels": {"mistapi_function": mistapi.api.v1.orgs.mxtunnels.listOrgMxTunnels, "text": "Org mxtunnels", "check_next":True},
    "psks": {"mistapi_function": mistapi.api.v1.orgs.psks.listOrgPsks, "text": "Org psks", "check_next":True},
    "pskportals": {"mistapi_function": mistapi.api.v1.orgs.pskportals.listOrgPskPortals, "text": "Org pskportals", "check_next":True},
    "rftemplates": {"mistapi_function": mistapi.api.v1.orgs.rftemplates.listOrgRfTemplates, "text": "Org rftemplates", "check_next":True},
    "networktemplates": {"mistapi_function": mistapi.api.v1.orgs.networktemplates.listOrgNetworkTemplates, "text": "Org networktemplates", "check_next":True},
    "evpn_topologies": {"mistapi_function": mistapi.api.v1.orgs.evpn_topologies.listOrgEvpnTopologies, "text": "Org evpn_topologies", "check_next":True},
    "services": {"mistapi_function": mistapi.api.v1.orgs.services.listOrgServices, "text": "Org services", "check_next":True},
    "networks": {"mistapi_function": mistapi.api.v1.orgs.networks.listOrgNetworks, "text": "Org networks", "check_next":True},
    "gatewaytemplates": {"mistapi_function": mistapi.api.v1.orgs.gatewaytemplates.listOrgGatewayTemplates, "text": "Org gatewaytemplates", "check_next":True},
    "vpns": {"mistapi_function": mistapi.api.v1.orgs.vpns.listOrgsVpns, "text": "Org vpns", "check_next":True},
    "secpolicies": {"mistapi_function": mistapi.api.v1.orgs.secpolicies.listOrgSecPolicies, "text": "Org secpolicies", "check_next":True},
    "servicepolicies": {"mistapi_function": mistapi.api.v1.orgs.servicepolicies.listOrgServicePolicies, "text": "Org servicepolicies", "check_next":True},
    "sitegroups": {"mistapi_function": mistapi.api.v1.orgs.sitegroups.listOrgSiteGroups, "text": "Org sitegroups", "check_next":True},
    "sitetemplates": {"mistapi_function": mistapi.api.v1.orgs.sitetemplates.listOrgSiteTemplates, "text": "Org sitetemplates", "check_next":True},
    "ssos": {"mistapi_function": mistapi.api.v1.orgs.ssos.listOrgSsos, "text": "Org ssos", "check_next":True},
    "ssoroles": {"mistapi_function": mistapi.api.v1.orgs.ssoroles.listOrgSsoRoles, "text": "Org ssoroles", "check_next":True},
    "templates": {"mistapi_function": mistapi.api.v1.orgs.templates.listOrgTemplates, "text": "Org templates", "check_next":True},
    "wxrules": {"mistapi_function": mistapi.api.v1.orgs.wxrules.listOrgWxRules, "text": "Org wxrules", "check_next":True},
    "wxtags": {"mistapi_function": mistapi.api.v1.orgs.wxtags.listOrgWxTags, "text": "Org wxtags", "check_next":True},
    "wxtunnels": {"mistapi_function": mistapi.api.v1.orgs.wxtunnels.listOrgWxTunnels, "text": "Org wxtunnels", "check_next":True},
    "nactags": {"mistapi_function": mistapi.api.v1.orgs.nactags.listOrgNacTags, "text": "Org nactags", "check_next":True},
    "nacrules": {"mistapi_function": mistapi.api.v1.orgs.nacrules.listOrgNacRules, "text": "Org nacrules", "check_next":True},
    "wlans": {"mistapi_function": mistapi.api.v1.orgs.wlans.listOrgWlans, "text": "Org wlans", "check_next":True}
}
site_steps = {        
    "assets": {"mistapi_function": mistapi.api.v1.sites.assets.listSiteAssets, "text": "Site assets", "check_next":True},
    "assetfilters": {"mistapi_function": mistapi.api.v1.sites.assetfilters.listSiteAssetFilters, "text": "Site assetfilters", "check_next":True},
    "beacons": {"mistapi_function": mistapi.api.v1.sites.beacons.listSiteBeacons, "text": "Site beacons", "check_next":True},
    "maps": {"mistapi_function": mistapi.api.v1.sites.maps.listSiteMaps, "text": "Site maps", "check_next":True},
    "psks": {"mistapi_function": mistapi.api.v1.sites.psks.listSitePsks, "text": "Site psks", "check_next":True},
    "rssizones": {"mistapi_function": mistapi.api.v1.sites.rssizones.listSiteRssiZones, "text": "Site rssizones", "check_next":True},
    "settings": {"mistapi_function": mistapi.api.v1.sites.setting.getSiteSetting, "text": "Site settings", "check_next":False},
    "vbeacons": {"mistapi_function": mistapi.api.v1.sites.vbeacons.listSiteVBeacons, "text": "Site vbeacons", "check_next":True},
    "webhooks": {"mistapi_function": mistapi.api.v1.sites.webhooks.listSiteWebhooks, "text": "Site webhooks", "check_next":True},
    "wlans": {"mistapi_function": mistapi.api.v1.sites.wlans.listSiteWlans, "text": "Site wlans", "check_next":True},
    "wxrules": {"mistapi_function": mistapi.api.v1.sites.wxrules.listSiteWxRules, "text": "Site wxrules", "check_next":True},
    "wxtags": {"mistapi_function": mistapi.api.v1.sites.wxtags.listSiteWxTags, "text": "Site wxtags", "check_next":True},
    "wxtunnels": {"mistapi_function": mistapi.api.v1.sites.wxtunnels.listSiteWxTunnels, "text": "Site wxtunnels", "check_next":True},
    "zones": {"mistapi_function": mistapi.api.v1.sites.zones.listSiteZones, "text": "Site zones", "check_next":True}
}

#####################################################################
# PROGRESS BAR AND DISPLAY
class ProgressBar():
    def __init__(self):        
        self.steps_total = 0
        self.steps_count = 0

    def _pb_update(self, size:int=80):   
        if self.steps_count > self.steps_total: 
            self.steps_count = self.steps_total

        percent = self.steps_count/self.steps_total
        delta = 17
        x = int((size-delta)*percent)
        print(f"Progress: ", end="")
        print(f"[{'█'*x}{'.'*(size-delta-x)}]", end="")
        print(f"{int(percent*100)}%".rjust(5), end="")

    def _pb_new_step(self, message:str, result:str, inc:bool=False, size:int=80, display_pbar:bool=True):
        if inc: self.steps_count += 1
        text = f"\033[A\033[F{message}"
        print(f"{text} ".ljust(size + 4, "."), result)
        print("".ljust(80))
        if display_pbar: self._pb_update(size)

    def _pb_title(self, text:str, size:int=80, end:bool=False, display_pbar:bool=True):
        print("\033[A")
        print(f" {text} ".center(size, "-"),"\n")
        if not end and display_pbar: 
            print("".ljust(80))
            self._pb_update(size)

    def set_steps_total(self, steps_total:int):
        self.steps_total = steps_total

    def log_message(self, message, display_pbar:bool=True):
        self._pb_new_step(message, " ", display_pbar=display_pbar)

    def log_success(self, message, inc:bool=False, display_pbar:bool=True):
        logger.info(f"{message}: Success")
        self._pb_new_step(message, "\033[92m\u2714\033[0m\n", inc=inc, display_pbar=display_pbar)

    def log_failure(self, message, inc:bool=False, display_pbar:bool=True):
        logger.error(f"{message}: Failure")    
        self._pb_new_step(message, '\033[31m\u2716\033[0m\n', inc=inc, display_pbar=display_pbar)

    def log_title(self, message, end:bool=False, display_pbar:bool=True):
        logger.info(message)
        self._pb_title(message, end=end, display_pbar=display_pbar)

pb = ProgressBar()
#####################################################################
#### FUNCTIONS ####
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
                message=f"portal template for wlan {wlan_id}"
                pb.log_message(message)
                urllib.request.urlretrieve(
                    wlan["portal_template_url"], portal_file_name)
                pb.log_success(message)
            except Exception as e:
                pb.log_failure(message)
                logger.error("Exception occurred", exc_info=True)
        if "portal_image" in wlan and wlan["portal_image"]:
            try:
                message=f"portal image for wlan {wlan_id}"
                pb.log_message(message)
                urllib.request.urlretrieve(wlan["portal_image"], portal_image)
                pb.log_success(message)
            except Exception as e:
                pb.log_failure(message)
                logger.error("Exception occurred", exc_info=True)


def _do_backup(mist_session, backup_function, check_next, scope_id, message, request_type:str=None):
    if sys_exit: sys.exit(0)
    try:
        pb.log_message(message)
        if request_type:
            response = backup_function(mist_session, scope_id, type=request_type)
        else:
            response = backup_function(mist_session, scope_id)

        if check_next:
            data = mistapi.get_all(mist_session, response)
        else:
            data = response.data
        pb.log_success(message, True)
        return data
    except Exception as e:
        pb.log_failure(message, True)
        logger.error("Exception occurred", exc_info=True)
        return None

#### BACKUP ####
def _backup_full_org(mist_session, org_id, org_name):
    pb.log_title(f"Backuping Org {org_name}")
    backup = {}
    backup["org"] = {"id": org_id}

    ### ORG BACKUP
    for step_name in org_steps:
        step = org_steps[step_name]
        request_type = step.get("request_type")
        backup["org"][step_name] = _do_backup(mist_session, step["mistapi_function"], step["check_next"], org_id, step["text"], request_type)
    _backup_wlan_portal(org_id, None, backup["org"]["wlans"])
    
    ### SITES BACKUP
    backup["sites"]={}
    for site in backup["org"]["sites"]:
        site_id = site["id"]
        site_name = site["name"]
        site_backup = {}
        pb.log_title(f"Backuping Site {site_name}")
        for step_name in site_steps:
            step = site_steps[step_name]
            site_backup[step_name] = _do_backup(mist_session, step["mistapi_function"], step["check_next"], site_id, step["text"])
        backup["sites"][site_id] = site_backup

        if site_backup["wlans"]:
            _backup_wlan_portal(org_id, site_id, site_backup["wlans"])

        message="Site map images"
        pb.log_message(message)
        try:
            for xmap in site_backup["maps"]:
                url = None
                if "url" in xmap:
                    url = xmap["url"]
                    xmap_id = xmap["id"]
                if url:
                    image_name = f"{file_prefix}_org_{org_id}_site_{site_id}_map_{xmap_id}.png"
                    urllib.request.urlretrieve(url, image_name)
            pb.log_success(message)
        except Exception as e:
            pb.log_failure(message)
            logger.error("Exception occurred", exc_info=True)
        
    pb.log_title("Backup Done", end=True)
    return backup


def _save_to_file(backup_file, backup, org_name):
    backup_path = os.path.join(backup_folder, org_name, backup_file)
    message=f"Saving to file {backup_path} "
    print(f"{message}".ljust(79, "."), end="", flush=True)
    try:
        with open(backup_file, "w") as f:
            json.dump(backup, f)
        print("\033[92m\u2714\033[0m\n")
    except Exception as e:
        print("\033[31m\u2716\033[0m\n")
        logger.error("Exception occurred", exc_info=True)


def _start_org_backup(mist_session, org_id, org_name) -> bool:
    # FOLDER
    try:
        if not os.path.exists(backup_folder):
            os.makedirs(backup_folder)
        os.chdir(backup_folder)
        if not os.path.exists(org_name):
            os.makedirs(org_name)
        os.chdir(org_name)
    except Exception as e:
        print(e)
        logger.error("Exception occurred", exc_info=True)
        return False

    # PREPARE PROGRESS BAR
    try:
        response = mistapi.api.v1.orgs.sites.listOrgSites(mist_session, org_id)
        sites = mistapi.get_all(mist_session, response)
        pb.set_steps_total(len(org_steps) + len(sites) * len(site_steps))
    except Exception as e:
        print(e)
        logger.error("Exception occurred", exc_info=True)
        return False

    # BACKUP
    try:
        backup = _backup_full_org(mist_session, org_id, org_name)
        _save_to_file(backup_file, backup, org_name)
    except Exception as e:
        print(e)
        logger.error("Exception occurred", exc_info=True)
        return False

    return True

def start(mist_session:mistapi.APISession, org_id:str, backup_folder_param:str=None):
    '''
    Start the process to deploy a backup/template

    PARAMS
    -------
    :param  mistapi.APISession  apisession          - mistapi session, already logged in
    :param  str                 org_id              - only if the destination org already exists. org_id where to deploy the configuration
    :param  str                 backup_folder_param - Path to the folder where to save the org backup (a subfolder will be created with the org name). default is "./org_backup"
    
    RETURNS
    -------
    :return bool                success status of the backup process. Returns False if the process didn't ended well
    '''
    current_folder = os.getcwd()
    if backup_folder_param:
        global backup_folder 
        backup_folder = backup_folder_param
    if not org_id: org_id = mistapi.cli.select_org(mist_session)[0]
    org_name = mistapi.api.v1.orgs.orgs.getOrgInfo(mist_session, org_id).data["name"]
    success = _start_org_backup(mist_session, org_id, org_name)    
    os.chdir(current_folder)
    return success

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
You can use the script "org_conf_deploy.py" to restore the generated backup 
files to an existing organization (empty or not) or to a new one.

This script will not change/create/delete/touch any existing objects. It will 
just retrieve every single object from the organization.

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
-b, --backup_folder=    Path to the folder where to save the org backup (a 
                        subfolder will be created with the org name)
                        default is "./org_backup"
-l, --log_file=         define the filepath/filename where to write the logs
                        default is "./script.log"
-e, --env=              define the env file to use (see mistapi env file 
                        documentation here: https://pypi.org/project/mistapi/)
                        default is "~/.mist_env"

-------
Examples:
python3 ./org_conf_backup.py
python3 ./org_conf_backup.py --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 

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
    backup_folder_param = None
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
            backup_folder_param = a
        else:
            assert False, "unhandled option"

    #### LOGS ####
    logging.basicConfig(filename=log_file, filemode='w')
    logger.setLevel(logging.DEBUG)
    ### START ###
    apisession = mistapi.APISession(env_file=env_file)
    apisession.login()
    start(apisession, org_id, backup_folder_param)

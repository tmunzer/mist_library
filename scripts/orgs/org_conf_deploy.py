"""
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to deploy organization backup/template file.
You can use the script "org_conf_backup.py" to generate the backup file from an
existing organization.

This script will not overide existing objects. If you already configured objects in the
destination organisation, new objects will be created. If you want to "reset" the
destination organization, you can use the script "org_conf_zeroise.py".
This script is trying to maintain objects integrity as much as possible. To do so, when
an object is referencing another object by its ID, the script will replace be ID from
the original organization by the corresponding ID from the destination org.

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
-o, --org_id=           Only if the destination org already exists. org_id where to
                        deploy the configuration
-n, --org_name=         Org name where to deploy the configuration:
                            - if org_id is provided (existing org), used to validate
                            the destination org
                            - if org_id is not provided (new org), the script will
                            create a new org and name it with the org_name value
-f, --backup_folder=    Path to the folder where to save the org backup (a subfolder
                        will be created with the org name)
                        default is "./org_backup"
-b, --source_backup=    Name of the backup/template to deploy. This is the name of
                        the folder where all the backup files are stored.
-l, --log_file=         define the filepath/filename where to write the logs
                        default is "./script.log"
-e, --env=              define the env file to use (see mistapi env file documentation
                        here: https://pypi.org/project/mistapi/)
                        default is "~/.mist_env"

-------
Examples:
python3 ./org_conf_deploy.py
python3 ./org_conf_deploy.py --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 -n "my test org"

"""

#### IMPORTS ####
import logging
import json
import os
import sys
import re
import getopt
import signal
from typing import Callable

MISTAPI_MIN_VERSION = "0.52.0"

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
BACKUP_FOLDER = "./org_backup"
BACKUP_FILE = "org_conf_file.json"
LOG_FILE = "./script.log"
FILE_PREFIX = ".".join(BACKUP_FILE.split(".")[:-1])
ENV_FILE = "~/.mist_env"

#####################################################################
#### LOGS ####
LOGGER = logging.getLogger(__name__)

#####################################################################
#### GLOBALS #####
SYS_EXIT = False


def sigint_handler(signal, frame):
    global SYS_EXIT
    SYS_EXIT = True
    ("[Ctrl C],KeyboardInterrupt exception occured.")


signal.signal(signal.SIGINT, sigint_handler)

#####################################################################
# DEPLOY OBJECTS REFS
ORG_STEPS = {
    "assetfilters": {
        "mistapi_function": mistapi.api.v1.orgs.assetfilters.createOrgAssetFilters,
        "text": "Org assetfilters",
    },
    "deviceprofiles": {
        "mistapi_function": mistapi.api.v1.orgs.deviceprofiles.createOrgDeviceProfiles,
        "text": "Org deviceprofiles",
    },
    "switchprofiles": {
        "mistapi_function": mistapi.api.v1.orgs.deviceprofiles.createOrgDeviceProfiles,
        "text": "Org switchprofiles",
        "request_type": "switch",
        "check_next": True,
    },
    "hubprofiles": {
        "mistapi_function": mistapi.api.v1.orgs.deviceprofiles.createOrgDeviceProfiles,
        "text": "Org hubprofiles",
    },
    "evpn_topologies": {
        "mistapi_function": mistapi.api.v1.orgs.evpn_topologies.createOrgEvpnTopology,
        "text": "Org evpn_topologies",
    },
    "secpolicies": {
        "mistapi_function": mistapi.api.v1.orgs.secpolicies.createOrgSecPolicies,
        "text": "Org secpolicies",
    },
    "aptempaltes": {
        "mistapi_function": mistapi.api.v1.orgs.aptemplates.createOrgAptemplate,
        "text": "Org aptemplates",
    },
    "networktemplates": {
        "mistapi_function": mistapi.api.v1.orgs.networktemplates.createOrgNetworkTemplate,
        "text": "Org networktemplates",
    },
    "networks": {
        "mistapi_function": mistapi.api.v1.orgs.networks.createOrgNetwork,
        "text": "Org networks",
    },
    "services": {
        "mistapi_function": mistapi.api.v1.orgs.services.createOrgService,
        "text": "Org services",
    },
    "servicepolicies": {
        "mistapi_function": mistapi.api.v1.orgs.servicepolicies.createOrgServicePolicy,
        "text": "Org servicepolicies",
    },
    "vpns": {
        "mistapi_function": mistapi.api.v1.orgs.vpns.createOrgVpns,
        "text": "Org vpns",
    },
    "gatewaytemplates": {
        "mistapi_function": mistapi.api.v1.orgs.gatewaytemplates.createOrgGatewayTemplate,
        "text": "Org gatewaytemplates",
    },
    "alarmtemplates": {
        "mistapi_function": mistapi.api.v1.orgs.alarmtemplates.createOrgAlarmTemplate,
        "text": "Org alarmtemplates",
    },
    "rftemplates": {
        "mistapi_function": mistapi.api.v1.orgs.rftemplates.createOrgRfTemplate,
        "text": "Org rftemplates",
    },
    "webhooks": {
        "mistapi_function": mistapi.api.v1.orgs.webhooks.createOrgWebhook,
        "text": "Org webhooks",
    },
    "mxclusters": {
        "mistapi_function": mistapi.api.v1.orgs.mxclusters.createOrgMxEdgeCluster,
        "text": "Org mxclusters",
    },
    "mxtunnels": {
        "mistapi_function": mistapi.api.v1.orgs.mxtunnels.createOrgMxTunnel,
        "text": "Org mxtunnels",
    },
    "wxtunnels": {
        "mistapi_function": mistapi.api.v1.orgs.wxtunnels.createOrgWxTunnel,
        "text": "Org wxtunnels",
    },
    "sitetemplates": {
        "mistapi_function": mistapi.api.v1.orgs.sitetemplates.createOrgSiteTemplates,
        "text": "Org sitetemplates",
    },
    "sitegroups": {
        "mistapi_function": mistapi.api.v1.orgs.sitegroups.createOrgSiteGroup,
        "text": "Org sitegroups",
    },
    "sites": {
        "mistapi_function": mistapi.api.v1.orgs.sites.createOrgSite,
        "text": "Org Sites",
    },
    "templates": {
        "mistapi_function": mistapi.api.v1.orgs.templates.createOrgTemplate,
        "text": "Org templates",
    },
    "wlans": {
        "mistapi_function": mistapi.api.v1.orgs.wlans.createOrgWlan,
        "text": "Org wlans",
    },
    "wxtags": {
        "mistapi_function": mistapi.api.v1.orgs.wxtags.createOrgWxTag,
        "text": "Org wxtags",
    },
    "wxrules": {
        "mistapi_function": mistapi.api.v1.orgs.wxrules.createOrgWxRule,
        "text": "Org wxrules",
    },
    "pskportals": {
        "mistapi_function": mistapi.api.v1.orgs.pskportals.createOrgPskPortal,
        "text": "Org pskportals",
    },
    "psks": {
        "mistapi_function": mistapi.api.v1.orgs.psks.importOrgPsks,
        "text": "Org psks",
    },
    "nactags": {
        "mistapi_function": mistapi.api.v1.orgs.nactags.createOrgNacTag,
        "text": "Org nactags",
    },
    "nacrules": {
        "mistapi_function": mistapi.api.v1.orgs.nacrules.createOrgNacRule,
        "text": "Org nacrules",
    },
    "ssos": {
        "mistapi_function": mistapi.api.v1.orgs.ssos.createOrgSso,
        "text": "Org ssos",
    },
    "ssoroles": {
        "mistapi_function": mistapi.api.v1.orgs.ssoroles.createOrgSsoRole,
        "text": "Org ssoroles",
    },
}
SITE_STEPS = {
    "settings": {
        "mistapi_function": mistapi.api.v1.sites.setting.updateSiteSettings,
        "text": "Site settings",
    },
    "maps": {
        "mistapi_function": mistapi.api.v1.sites.maps.createSiteMap,
        "text": "Site maps",
    },
    "zones": {
        "mistapi_function": mistapi.api.v1.sites.zones.createSiteZone,
        "text": "Site zones",
    },
    "rssizones": {
        "mistapi_function": mistapi.api.v1.sites.rssizones.createSiteRssiZone,
        "text": "Site rssizones",
    },
    "assets": {
        "mistapi_function": mistapi.api.v1.sites.assets.createSiteAsset,
        "text": "Site assets",
    },
    "assetfilters": {
        "mistapi_function": mistapi.api.v1.sites.assetfilters.createSiteAssetFilters,
        "text": "Site assetfilters",
    },
    "beacons": {
        "mistapi_function": mistapi.api.v1.sites.beacons.createSiteBeacon,
        "text": "Site beacons",
    },
    "psks": {
        "mistapi_function": mistapi.api.v1.sites.psks.importSitePsks,
        "text": "Site psks",
    },
    "vbeacons": {
        "mistapi_function": mistapi.api.v1.sites.vbeacons.createSiteVBeacon,
        "text": "Site vbeacons",
    },
    "evpn_topologies": {
        "mistapi_function": mistapi.api.v1.sites.evpn_topologies.createSiteEvpnTopology,
        "text": "Site EVPN Topologies",
    },
    "webhooks": {
        "mistapi_function": mistapi.api.v1.sites.webhooks.createSiteWebhook,
        "text": "Site webhooks",
    },
    "wxtunnels": {
        "mistapi_function": mistapi.api.v1.sites.wxtunnels.createSiteWxTunnel,
        "text": "Site wxtunnels",
    },
    "wlans": {
        "mistapi_function": mistapi.api.v1.sites.wlans.createSiteWlan,
        "text": "Site wlans",
    },
    "wxtags": {
        "mistapi_function": mistapi.api.v1.sites.wxtags.createSiteWxTag,
        "text": "Site wxtags",
    },
    "wxrules": {
        "mistapi_function": mistapi.api.v1.sites.wxrules.createSiteWxRule,
        "text": "Site wxrules",
    },
}


##########################################################################################
# CLASS TO MANAGE UUIDS UPDATES (replace UUIDs from source org to the newly created ones)
class UUIDM:
    """
    CLASS TO MANAGE UUIDS UPDATES (replace UUIDs from source org to the newly created ones)
    """

    def __init__(self):
        self.uuids = {}
        self.requests_to_replay = []

    def add_uuid(self, new: str, old: str):
        if new and old:
            LOGGER.debug(f"add_uuid: old_id {old} matching new_id {new}")
            self.uuids[old] = new
        else:
            LOGGER.warning(f"add_uuid: old_id {old} matching new_id {new}")

    def get_new_uuid(self, old: str):
        return self.uuids.get(old)

    def add_replay(
        self, mistapi_function: Callable, scope_id: str, object_type: str, data: dict
    ):
        self.requests_to_replay.append(
            {
                "mistapi_function": mistapi_function,
                "scope_id": scope_id,
                "data": data,
                "object_type": object_type,
                "retry": 0,
            }
        )

    def get_replay(self):
        return self.requests_to_replay

    def _uuid_string(self, obj_str: str, missing_uuids: list):
        #        uuid_re = '"[a-zA-Z_-]*": "[0-9a-f]{8}-[0-9a-f]{4}-[0-5][0-9a-f]{3}-[089ab][0-9a-f]{3}-[0-9a-f]{12}"'
        uuid_re = r"\"[a-zA-Z_-]*\": \"[0-9a-f]{8}-[0-9a-f]{4}-[0-5][0-9a-f]{3}-[089ab][0-9a-f]{3}-[0-9a-f]{12}\""
        uuids_to_replace = re.findall(uuid_re, obj_str)
        if uuids_to_replace:
            for uuid in uuids_to_replace:
                uuid_key = uuid.replace('"', "").split(":")[0].strip()
                uuid_val = uuid.replace('"', "").split(":")[1].strip()
                if self.get_new_uuid(uuid_val):
                    obj_str = obj_str.replace(uuid_val, self.get_new_uuid(uuid_val))
                elif uuid_key not in [
                    "issuer",
                    "idp_sso_url",
                    "custom_logout_url",
                    "sso_issuer",
                    "sso_idp_sso_url",
                    "ibeacon_uuid",
                ]:
                    missing_uuids.append({uuid_key: uuid_val})
        return obj_str, missing_uuids

    def _uuid_list(self, obj_str: str, missing_uuids: list):
        #        uuid_list_re = '("[a-zA-Z_-]*": \["[0-9a-f]{8}-[0-9a-f]{4}-[0-5][0-9a-f]{3}-[089ab][0-9a-f]{3}-[0-9a-f]{12}"[^\]]*)\]'
        uuid_list_re = r"(\"[a-zA-Z_-]*\": \[\"[0-9a-f]{8}-[0-9a-f]{4}-[0-5][0-9a-f]{3}-[089ab][0-9a-f]{3}-[0-9a-f]{12}\"[^\]]*)\]"

        uuid_lists_to_replace = re.findall(uuid_list_re, obj_str)
        if uuid_lists_to_replace:
            for uuid_list in uuid_lists_to_replace:
                uuid_key = uuid_list.replace('"', "").split(":")[0].strip()
                uuids = (
                    uuid_list.replace('"', "")
                    .replace("[", "")
                    .replace("]", "")
                    .split(":")[1]
                    .split(",")
                )
                for uuid in uuids:
                    uuid_val = uuid.strip()
                    if self.get_new_uuid(uuid_val):
                        obj_str = obj_str.replace(uuid_val, self.get_new_uuid(uuid_val))
                    else:
                        missing_uuids.append({uuid_key: uuid_val})
        return obj_str, missing_uuids

    def find_and_replace(self, obj: dict, object_type: str):
        # REMOVE READONLY FIELDS
        ids_to_remove = [
            "id",
            "msp_id",
            "org_id",
            "site_id",
            "site_ids",
            "url",
            "bg_image_url",
            "portal_template_url",
            "portal_sso_url",
            "thumbnail_url",
            "template_url",
            "ui_url",
        ]

        for id_name in ids_to_remove:
            if not object_type == "webhooks" or not id_name == "url":
                if id_name in obj:
                    del obj[id_name]
        if "service_policies" in obj:
            for service_policy in obj.get("service_policies", []):
                if "id" in service_policy:
                    del service_policy["id"]

        # REPLACE REMAINING IDS
        obj_str = json.dumps(obj)
        obj_str, missing_uuids = self._uuid_string(obj_str, [])
        obj_str, missing_uuids = self._uuid_list(obj_str, missing_uuids)
        obj = json.loads(obj_str)

        return obj, missing_uuids


UUID_MATCHING = UUIDM()


#####################################################################
# PROGRESS BAR AND DISPLAY
class ProgressBar:
    """
    PROGRESS BAR AND DISPLAY
    """

    def __init__(self):
        self.steps_total = 0
        self.steps_count = 0

    def _pb_update(self, size: int = 80):
        if self.steps_count > self.steps_total:
            self.steps_count = self.steps_total

        percent = self.steps_count / self.steps_total
        delta = 17
        x = int((size - delta) * percent)
        print(f"Progress: ", end="")
        print(f"[{'█'*x}{'.'*(size-delta-x)}]", end="")
        print(f"{int(percent*100)}%".rjust(5), end="")

    def _pb_new_step(
        self,
        message: str,
        result: str,
        inc: bool = False,
        size: int = 80,
        display_pbar: bool = True,
    ):
        if inc:
            self.steps_count += 1
        text = f"\033[A\033[F{message}"
        print(f"{text} ".ljust(size + 4, "."), result)
        print("".ljust(80))
        if display_pbar:
            self._pb_update(size)

    def _pb_title(
        self, text: str, size: int = 80, end: bool = False, display_pbar: bool = True
    ):
        print("\033[A")
        print(f" {text} ".center(size, "-"), "\n")
        if not end and display_pbar:
            print("".ljust(80))
            self._pb_update(size)

    def set_steps_total(self, steps_total: int):
        self.steps_total = steps_total

    def log_message(self, message, display_pbar: bool = True):
        self._pb_new_step(message, " ", display_pbar=display_pbar)

    def log_debug(self, message):
        LOGGER.debug(f"{message}")

    def log_success(self, message, inc: bool = False, display_pbar: bool = True):
        LOGGER.info(f"{message}: Success")
        self._pb_new_step(
            message, "\033[92m\u2714\033[0m\n", inc=inc, display_pbar=display_pbar
        )

    def log_warning(self, message, inc: bool = False, display_pbar: bool = True):
        LOGGER.warning(f"{message}")
        self._pb_new_step(
            message, "\033[93m\u2B58\033[0m\n", inc=inc, display_pbar=display_pbar
        )

    def log_failure(self, message, inc: bool = False, display_pbar: bool = True):
        LOGGER.error(f"{message}: Failure")
        self._pb_new_step(
            message, "\033[31m\u2716\033[0m\n", inc=inc, display_pbar=display_pbar
        )

    def log_title(self, message, end: bool = False, display_pbar: bool = True):
        LOGGER.info(message)
        self._pb_title(message, end=end, display_pbar=display_pbar)


PB = ProgressBar()


##########################################################################################
##########################################################################################
# DEPLOY FUNCTIONS
##########################################################################################
# COMMON FUNCTION
def _common_deploy(
    apisession: mistapi.APISession,
    mistapi_function: Callable,
    scope_id: str,
    object_type: str,
    data: dict,
    retry: bool = False,
):
    LOGGER.debug("conf_deploy:_common_deploy")
    if SYS_EXIT:
        sys.exit(0)
    old_id = None
    new_id = None
    object_name = ""
    if "name" in data:
        object_name = f"\"{data.get('name', '<unknown>')}\""
    elif "ssid" in data:
        object_name = f"\"{data.get('ssid', '<unknown>')}\""
    if "id" in data:
        old_id = data["id"]
    else:
        old_id = None

    message = f"Creating {object_type} {object_name}"
    PB.log_message(message)
    data, missing_uuids = UUID_MATCHING.find_and_replace(data, object_type)

    if missing_uuids and not retry:        
        UUID_MATCHING.add_replay(mistapi_function, scope_id, object_type, data)
        PB.log_warning(message, inc=True)
    else:
        try:
            response = mistapi_function(apisession, scope_id, data)
            if response.status_code == 200:
                new_id = response.data.get("id")
                PB.log_success(message, inc=True)
            else:
                PB.log_failure(message, inc=True)
        except:
            PB.log_failure(message, inc=True)
        UUID_MATCHING.add_uuid(new_id, old_id)
        return new_id
    return None


##########################################################################################
# COMMON FUNCTION
def _import_psks(
    apisession: mistapi.APISession,
    mistapi_function: Callable,
    scope_id: str,
    data: dict,
):
    LOGGER.debug("conf_deploy:_import_psks")
    if SYS_EXIT:
        sys.exit(0)

    message = f"Importing PSKs"
    PB.log_message(message)

    try:
        response = mistapi_function(apisession, scope_id, data)
        if response.status_code == 200:
            PB.log_success(message, inc=True)
        else:
            PB.log_failure(message, inc=True)
    except:
        PB.log_failure(message, inc=True)
    return None


##########################################################################################
# WLAN FUNCTIONS
def _deploy_wlan(
    apisession: mistapi.APISession,
    mistapi_function: Callable,
    scope_id: str,
    data: dict,
    old_org_id: str,
    old_site_id: str = None,
):
    LOGGER.debug("conf_deploy:_deploy_wlan")
    if SYS_EXIT:
        sys.exit(0)
    old_wlan_id = data["id"]
    new_wlan_id = _common_deploy(apisession, mistapi_function, scope_id, "wlans", data)
    UUID_MATCHING.add_uuid(new_wlan_id, old_wlan_id)
    _deploy_wlan_portal(
        apisession,
        old_org_id,
        old_site_id,
        old_wlan_id,
        scope_id,
        new_wlan_id,
        data.get("ssid"),
    )


def _deploy_wlan_portal(
    apisession: mistapi.APISession,
    old_org_id: str,
    old_site_id: str,
    old_wlan_id: str,
    scope_id: str,
    new_wlan_id: str,
    wlan_name: str,
):
    LOGGER.debug("conf_deploy:_deploy_wlan_portal")
    portal_file_name = ""
    if SYS_EXIT:
        sys.exit(0)
    elif not old_site_id:
        portal_file_name = f"{FILE_PREFIX}_org_{old_org_id}_wlan_{old_wlan_id}.json"
        portal_image = f"{FILE_PREFIX}_org_{old_org_id}_wlan_{old_wlan_id}.png"
        upload_image_function = mistapi.api.v1.orgs.wlans.uploadOrgWlanPortalImageFile
        update_template_function = mistapi.api.v1.orgs.wlans.updateOrgWlanPortalTemplate
    else:
        portal_file_name = (
            f"{FILE_PREFIX}_org_{old_org_id}_site_{old_site_id}_wlan_{old_wlan_id}.json"
        )
        portal_image = (
            f"{FILE_PREFIX}_org_{old_org_id}_site_{old_site_id}_wlan_{old_wlan_id}.png"
        )
        upload_image_function = mistapi.api.v1.sites.wlans.uploadSiteWlanPortalImageFile
        update_template_function = (
            mistapi.api.v1.sites.wlans.updateSiteWlanPortalTemplate
        )

    if os.path.isfile(portal_file_name):
        message = f'Creating Portal Template for WLAN "{wlan_name}" '
        PB.log_message(message)
        try:
            template = open(portal_file_name, "r")
        except Exception as e:
            PB.log_failure(f'Unable to open the template file "{portal_file_name}" ')
            LOGGER.error("Exception occurred", exc_info=True)
            return
        try:
            template = json.load(template)
        except Exception as e:
            PB.log_failure(f'Unable to read the template file "{portal_file_name}" ')
            LOGGER.error("Exception occurred", exc_info=True)
            return
        try:
            update_template_function(apisession, scope_id, new_wlan_id, template)
            PB.log_success(message)
        except Exception as e:
            PB.log_failure(f'Unable to upload the template "{portal_file_name}" ')
            LOGGER.error("Exception occurred", exc_info=True)

    else:
        PB.log_debug(f'No Portal template found for WLAN "{wlan_name}"')

    if os.path.isfile(portal_image):
        message = f'Uploading Portal image for WLAN "{wlan_name}" '
        try:
            upload_image_function(apisession, scope_id, new_wlan_id, portal_image)
            PB.log_success(message)
        except Exception as e:
            PB.log_failure(message)
            LOGGER.error("Exception occurred", exc_info=True)
    else:
        PB.log_debug(f"No Portal Template image found for WLAN {wlan_name} ")


##########################################################################################
# SITE FUNCTIONS
def _deploy_site_maps(
    apisession: mistapi.APISession,
    old_org_id: str,
    old_site_id: str,
    new_site_id: str,
    data: dict,
):
    LOGGER.debug("conf_deploy:_deploy_site_maps")
    if SYS_EXIT:
        sys.exit(0)
    old_map_id = data["id"]

    for area in data.get("intended_coverage_areas", []):
        LOGGER.info(f"_deploy_site_maps:removing ids from intended_coverage_areas")
        del area["id"]
        del area["map_id"]
    if data.get("sitesurvey_path"):
        LOGGER.info(f"_deploy_site_maps:removing sitesurvey_path")
        del data["sitesurvey_path"]

    new_map_id = _common_deploy(
        apisession, SITE_STEPS["maps"]["mistapi_function"], new_site_id, "maps", data
    )

    if not new_map_id:
        LOGGER.warning(f"new id not returned for old_id {old_map_id}, trying to find a match")
        new_map_id = UUID_MATCHING.get_new_uuid(old_map_id)
    if not new_map_id:
        LOGGER.error(f"no match for old_id {old_map_id}")
    image_name = (
        f"{FILE_PREFIX}_org_{old_org_id}_site_{old_site_id}_map_{old_map_id}.png"
    )
    if os.path.isfile(image_name):
        message = f"Uploading image floorplan  \"{data['name']}\""
        PB.log_message(message)
        try:
            mistapi.api.v1.sites.maps.addSiteMapImageFile(
                apisession, new_site_id, new_map_id, image_name
            )
            PB.log_success(message)
        except:
            PB.log_failure(message)
    else:
        PB.log_debug(f"No image found for \"{data['name']}\"")


def _deploy_site(
    apisession: mistapi.APISession,
    org_id: str,
    old_org_id: str,
    site_info: dict,
    sites_backup: dict,
):
    LOGGER.debug("conf_deploy:_deploy_site")
    if SYS_EXIT:
        sys.exit(0)
    old_site_id = site_info["id"]
    site_data = sites_backup.get(old_site_id, {})

    PB.log_title(f" Deploying Site {site_info['name']} ".center(80, "_"))
    new_site_id = _common_deploy(
        apisession, ORG_STEPS["sites"]["mistapi_function"], org_id, "sites", site_info
    )
    LOGGER.debug(
        f"conf_deploy:_deploy_site:site {site_info['name']}, old id={old_site_id}, new id={new_site_id}"
    )
    for step_name, step in SITE_STEPS.items():
        if not site_data.get(step_name):
            LOGGER.debug(f"{site_info['name']} > {step_name}: nothing to process")
        else:
            LOGGER.debug(f"{site_info['name']} > {step_name}: processing")
            if step_name == "settings":
                step_data = site_data.get(step_name, {})
                _common_deploy(
                    apisession,
                    step["mistapi_function"],
                    new_site_id,
                    step_name,
                    step_data
                )
            elif step_name == "psks":
                step_data = site_data.get(step_name)
                if step_data:
                    _import_psks(
                        apisession,
                        step["mistapi_function"],
                        new_site_id,
                        step_data
                    )
            elif step_name == "maps":
                for step_data in site_data.get(step_name, []):
                    _deploy_site_maps(
                        apisession,
                        old_org_id,
                        old_site_id,
                        new_site_id,
                        step_data
                    )
            elif step_name == "wlans":
                for step_data in site_data.get(step_name, []):
                    _deploy_wlan(
                        apisession,
                        step["mistapi_function"],
                        new_site_id,
                        step_data,
                        old_org_id,
                        old_site_id,
                    )
            else:
                for step_data in site_data.get(step_name, []):
                    _common_deploy(
                        apisession,
                        step["mistapi_function"],
                        new_site_id,
                        step_name,
                        step_data,
                    )


##########################################################################################
#  ORG FUNCTIONS
def _deploy_org(
    apisession: mistapi.APISession, org_id: str, org_name: str, backup: dict
):
    LOGGER.debug("conf_deploy:_deploy_org")
    PB.log_title(f"Deploying Org {org_name}")

    ####################
    ####  ORG MAIN  ####
    org_backup = backup["org"]
    sites_backup = backup["sites"]

    org_data = org_backup["data"]
    old_org_id = org_data["id"]
    UUID_MATCHING.add_uuid(org_id, old_org_id)

    message = "Org Info "
    PB.log_message(message)
    try:
        org_data["name"] = org_name
        mistapi.api.v1.orgs.orgs.updateOrg(apisession, org_id, org_data)
        PB.log_success(message, inc=True)
    except Exception as e:
        PB.log_failure(message, inc=True)
        LOGGER.error("Exception occurred", exc_info=True)

    ########################
    ####  ORG SETTINGS  ####
    message = "Org Settings "
    org_settings = org_backup["settings"]
    PB.log_message(message)
    try:
        mistapi.api.v1.orgs.setting.updateOrgSettings(apisession, org_id, org_settings)
        PB.log_success(message, inc=True)
    except Exception as e:
        PB.log_failure(message, inc=True)
        LOGGER.error("Exception occurred", exc_info=True)

    #######################
    ####  ORG OBJECTS  ####
    PB.log_title(f"Deploying Common Org Objects")
    for step_name, step in ORG_STEPS.items():
        if step_name in org_backup:
            if step_name == "psks":
                step_data = org_backup.get("psks")
                if step_data:
                    _import_psks(
                        apisession, step["mistapi_function"], org_id, step_data
                    )
            else:
                for step_data in org_backup[step_name]:
                    if step_name == "sites":
                        _deploy_site(
                            apisession, org_id, old_org_id, step_data, sites_backup
                        )
                    elif step_name == "wlans":
                        _deploy_wlan(
                            apisession,
                            step["mistapi_function"],
                            org_id,
                            step_data,
                            old_org_id,
                        )
                    else:
                        _common_deploy(
                            apisession,
                            step["mistapi_function"],
                            org_id,
                            step_name,
                            step_data,
                        )

    PB.log_title(f"Retrying missing objects")
    for replay in UUID_MATCHING.get_replay():
        _common_deploy(
            apisession,
            replay["mistapi_function"],
            replay["scope_id"],
            replay["object_type"],
            replay["data"],
            True,
        )

    PB.log_title("Deployment Done", end=True)


def _start_deploy_org(
    apisession: mistapi.APISession,
    org_id: str,
    org_name: str,
    backup_folder: str,
    src_org_name: str = None,
    source_backup: str = None,
):
    LOGGER.debug("conf_deploy:_start_deploy_org")
    _go_to_backup_folder(backup_folder, src_org_name, source_backup)
    print()
    try:
        message = f"Loading template/backup file {BACKUP_FILE} "
        PB.log_message(message, display_pbar=False)
        with open(BACKUP_FILE) as f:
            backup = json.load(f)
        PB.log_success(message, display_pbar=False)
    except:
        PB.log_failure(message, display_pbar=False)
        console.critical("Unable to load the template/bakup")
        LOGGER.error("Exception occurred", exc_info=True)
        sys.exit(1)

    try:
        message = f"Analyzing template/backup file {BACKUP_FILE} "
        PB.log_message(message, display_pbar=False)
        steps_total = 2
        for step_name in ORG_STEPS:
            if step_name in backup["org"]:
                steps_total += len(backup["org"][step_name])
        for site_id in backup["sites"]:
            for step_name in SITE_STEPS:
                if step_name == "settings":
                    steps_total += 1
                elif backup["sites"][site_id].get("step_name"):
                    steps_total += len(backup["sites"][site_id].get("step_name", []))
        PB.set_steps_total(steps_total)
        PB.log_success(message, display_pbar=False)
        console.info(f"The process will deploy {steps_total} new objects")
    except:
        PB.log_failure(message, display_pbar=False)
        console.critical("Unable to parse the template/backup file")
        LOGGER.error("Exception occurred", exc_info=True)
        sys.exit(1)
    if backup:
        _display_warning(
            f"Are you sure about this? Do you want to import the configuration "
            f"into the organization {org_name} with the id {org_id} (y/N)? "
        )
        _deploy_org(apisession, org_id, org_name, backup)


#####################################################################
#### MENUS ####
def _chdir(path: str):
    try:
        os.chdir(path)
        return True
    except FileNotFoundError:
        console.error("Le chemin spécifié n'existe pas.")
        return False
    except NotADirectoryError:
        console.error("Le chemin spécifié n'est pas un répertoire.")
        return False
    except PermissionError:
        console.error(
            "Vous n'avez pas les autorisations nécessaires "
            "pour accéder au répertoire spécifié."
        )
        return False
    except Exception as e:
        console.error(f"Une erreur s'est produite : {e}")
        return False


def _display_warning(message):
    resp = "x"
    while resp.lower() not in ["y", "n", ""]:
        print()
        resp = input(message)
    if resp.lower() != "y":
        console.error("Interruption... Exiting...")
        LOGGER.error("Interruption... Exiting...")
        sys.exit(0)


def _select_backup_folder(folders):
    i = 0
    print("Available Templates/Backups:")
    while i < len(folders):
        print(f"{i}) {folders[i]}")
        i += 1
    folder = None
    while folder is None:
        resp = input(
            f"Which template/backup do you want to deploy (0-{i - 1}, or q to quit)? "
        )
        if resp.lower() == "q":
            console.error("Interruption... Exiting...")
            LOGGER.error("Interruption... Exiting...")
            sys.exit(0)
        try:
            respi = int(resp)
            if respi >= 0 and respi <= i:
                folder = folders[respi]
            else:
                print(f'The entry value "{respi}" is not valid. Please try again...')
        except:
            print("Only numbers are allowed. Please try again...")
    _chdir(folder)


def _go_to_backup_folder(
    backup_folder: str, src_org_name: str = None, source_backup: str = None
):
    print()
    print(" Source Backup/Template ".center(80, "-"))
    print()
    _chdir(backup_folder)
    folders = []
    for entry in os.listdir("./"):
        if os.path.isdir(os.path.join("./", entry)):
            folders.append(entry)
    folders = sorted(folders, key=str.casefold)
    if source_backup in folders and _chdir(source_backup):
        print(f"Template/Backup {source_backup} found. It will be automatically used.")
    elif src_org_name in folders:
        print(f"Template/Backup found for organization {src_org_name}.")
        loop = True
        while loop:
            resp = input("Do you want to use this template/backup (y/N)? ")
            if resp.lower() in ["y", "n", " "]:
                loop = False
                if resp.lower() == "y" and _chdir(src_org_name):
                    pass
                else:
                    _select_backup_folder(folders)
    else:
        print(
            f"No Template/Backup found for organization {src_org_name}. "
            f"Please select a folder in the following list."
        )
        _select_backup_folder(folders)


def _check_org_name_in_script_param(
    apisession: mistapi.APISession, org_id: str, org_name: str = None
):
    response = mistapi.api.v1.orgs.orgs.getOrg(apisession, org_id)
    if response.status_code != 200:
        console.critical(f"Unable to retrieve the org information: {response.data}")
        sys.exit(3)
    org_name_from_mist = response.data["name"]
    return org_name == org_name_from_mist


def _check_org_name(apisession: mistapi.APISession, org_id: str, org_name: str = None):
    if not org_name:
        org_name = mistapi.api.v1.orgs.orgs.getOrg(apisession, org_id).data["name"]
    while True:
        print()
        resp = input(
            "To avoid any error, please confirm the current destination orgnization name: "
        )
        if resp == org_name:
            return org_id, org_name
        else:
            print()
            print("The orgnization names do not match... Please try again...")


def _create_org(apisession: mistapi.APISession, custom_dest_org_name: str = None):
    while True:
        if not custom_dest_org_name:
            custom_dest_org_name = input("Organization name? ")
        if custom_dest_org_name:
            org = {"name": custom_dest_org_name}
            print("")
            print("")
            message = f'Creating the organisation "{custom_dest_org_name}" on {apisession.get_cloud()} '
            PB.log_message(message, display_pbar=False)
            try:
                PB.log_success(message, display_pbar=False)
            except Exception as e:
                PB.log_failure(message, display_pbar=False)
                LOGGER.error("Exception occurred", exc_info=True)
                sys.exit(10)
            org_id = mistapi.api.v1.orgs.orgs.createOrg(apisession, org).data["id"]
            print(f"New Org id: {org_id}")
            return org_id, custom_dest_org_name


def _select_dest_org(apisession: mistapi.APISession):
    print()
    print(" Destination Org ".center(80, "-"))
    print()
    while True:
        res = input(
            "Do you want to create a (n)ew organisation or (r)estore to an existing one, (q)uit ? "
        )
        if res.lower() == "q":
            sys.exit(0)
        elif res.lower() == "r":
            org_id = mistapi.cli.select_org(apisession)[0]
            org_name = mistapi.api.v1.orgs.orgs.getOrg(apisession, org_id).data["name"]
            if _check_org_name(apisession, org_id, org_name):
                return org_id, org_name
        elif res.lower() == "n":
            return _create_org(apisession)


#####################################################################
#### START ####
def start(
    apisession: mistapi.APISession,
    org_id: str = None,
    org_name: str = None,
    backup_folder_param: str = None,
    src_org_name: str = None,
    source_backup: str = None,
):
    """
    Start the process to deploy a backup/template

    PARAMS
    -------
    apisession : mistapi.APISession
        mistapi session, already logged in
    org_id : str
        only if the destination org already exists. org_id where to deploy the configuration
    org_name : str
        Org name where to deploy the configuration:
        * if org_id is provided (existing org), used to validate the destination org
        * if org_id is not provided (new org), the script will create a new org and name it with
        the org_name value
    backup_folder_param : str
        Path to the folder where to save the org backup (a subfolder will be created with the org
        name). default is "./org_backup"
    src_org_name : str
        Name of the backup/template to deploy. This is the name of the folder where all the backup
        files are stored. If the backup is found, the script will ask for a confirmation to use it
    source_backup : str
        Name of the backup/template to deploy. This is the name of the folder where all the backup
        files are stored. If the backup is found, the script will NOT ask for a confirmation to use
        it
    """
    current_folder = os.getcwd()
    if not backup_folder_param:
        backup_folder_param = BACKUP_FOLDER

    if org_id and org_name:
        if not _check_org_name_in_script_param(apisession, org_id, org_name):
            console.critical(f"Org name {org_name} does not match the org {org_id}")
            sys.exit(0)
    elif org_id and not org_name:
        org_id, org_name = _check_org_name(apisession, org_id)
    elif not org_id and org_name:
        org_id, name = _create_org(apisession, org_name)
    elif not org_id and not org_name:
        org_id, org_name = _select_dest_org(apisession)
    else:  # should not since we covered all the possibilities...
        sys.exit(0)

    _start_deploy_org(
        apisession, org_id, org_name, backup_folder_param, src_org_name, source_backup
    )
    os.chdir(current_folder)


#####################################################################
#### USAGE ####
def usage():
    print(
        """
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to deploy organization backup/template file.
You can use the script "org_conf_backup.py" to generate the backup file from an
existing organization.

This script will not overide existing objects. If you already configured objects in the
destination organisation, new objects will be created. If you want to "reset" the
destination organization, you can use the script "org_conf_zeroise.py".
This script is trying to maintain objects integrity as much as possible. To do so, when
an object is referencing another object by its ID, the script will replace be ID from
the original organization by the corresponding ID from the destination org.

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
-o, --org_id=           Only if the destination org already exists. org_id where to
                        deploy the configuration
-n, --org_name=         Org name where to deploy the configuration:
                            - if org_id is provided (existing org), used to validate
                            the destination org
                            - if org_id is not provided (new org), the script will
                            create a new org and name it with the org_name value
-f, --backup_folder=    Path to the folder where to save the org backup (a subfolder
                        will be created with the org name)
                        default is "./org_backup"
-b, --source_backup=    Name of the backup/template to deploy. This is the name of
                        the folder where all the backup files are stored.
-l, --log_file=         define the filepath/filename where to write the logs
                        default is "./script.log"
-e, --env=              define the env file to use (see mistapi env file documentation
                        here: https://pypi.org/project/mistapi/)
                        default is "~/.mist_env"

-------
Examples:
python3 ./org_conf_deploy.py
python3 ./org_conf_deploy.py --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 -n "my test org"

"""
    )
    sys.exit(0)


def check_mistapi_version():
    if mistapi.__version__ < MISTAPI_MIN_VERSION:
        LOGGER.critical(
            f'"mistapi" package version {MISTAPI_MIN_VERSION} is required, '
            f"you are currently using version {mistapi.__version__}."
        )
        LOGGER.critical(f"Please use the pip command to updated it.")
        LOGGER.critical("")
        LOGGER.critical(f"    # Linux/macOS")
        LOGGER.critical(f"    python3 -m pip install --upgrade mistapi")
        LOGGER.critical("")
        LOGGER.critical(f"    # Windows")
        LOGGER.critical(f"    py -m pip install --upgrade mistapi")
        print(
            f"""
    Critical:
    \"mistapi\" package version {MISTAPI_MIN_VERSION} is required, you are currently using version {mistapi.__version__}.
    Please use the pip command to updated it.

    # Linux/macOS
    python3 -m pip install --upgrade mistapi

    # Windows
    py -m pip install --upgrade mistapi
        """
        )
        sys.exit(2)
    else:
        LOGGER.info(
            f'"mistapi" package version {MISTAPI_MIN_VERSION} is required, '
            f"you are currently using version {mistapi.__version__}."
        )


#####################################################################
#### SCRIPT ENTRYPOINT ####
if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(
            sys.argv[1:],
            "ho:n:e:l:f:b:",
            [
                "help",
                "org_id=",
                "org_name=",
                "env=",
                "log_file=",
                "backup_folder=",
                "source_backup=",
            ],
        )
    except getopt.GetoptError as err:
        console.error(err)
        usage()

    ORG_ID = None
    ORG_NAME = None
    BACKUP_FOLDER_PARAM = None
    SOURCE_BACKUP = None
    for o, a in opts:
        if o in ["-h", "--help"]:
            usage()
        elif o in ["-o", "--org_id"]:
            ORG_ID = a
        elif o in ["-n", "--org_name"]:
            ORG_NAME = a
        elif o in ["-e", "--env"]:
            ENV_FILE = a
        elif o in ["-l", "--log_file"]:
            LOG_FILE = a
        elif o in ["-f", "--backup_folder"]:
            BACKUP_FOLDER_PARAM = a
        elif o in ["-b", "--source_backup"]:
            SOURCE_BACKUP = a
        else:
            assert False, "unhandled option"

    #### LOGS ####
    logging.basicConfig(filename=LOG_FILE, filemode="w")
    LOGGER.setLevel(logging.DEBUG)
    check_mistapi_version()
    ### START ###
    APISESSION = mistapi.APISession(env_file=ENV_FILE)
    APISESSION.login()
    start(
        APISESSION, ORG_ID, ORG_NAME, BACKUP_FOLDER_PARAM, source_backup=SOURCE_BACKUP
    )

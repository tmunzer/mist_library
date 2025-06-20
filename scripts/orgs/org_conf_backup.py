"""
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

It is recommended to use an environment file to store the required information
to request the Mist Cloud (see https://pypi.org/project/mistapi/ for more
information about the available parameters).

-------
Script Parameters:
-h, --help              display this help
-o, --org_id=           Set the org_id
-b, --backup_folder=    Path to the folder where to save the org backup (a
                        subfolder will be created with the org name)
                        default is "./org_backup"

-d, --datetime          append the current date and time (ISO format) to the
                        backup name
-t, --timestamp         append the current timestamp to the backup

-l, --log_file=         define the filepath/filename where to write the logs
                        default is "./script.log"
-e, --env=              define the env file to use (see mistapi env file
                        documentation here: https://pypi.org/project/mistapi/)
                        default is "~/.mist_env"

-------
Examples:
python3 ./org_conf_backup.py
python3 ./org_conf_backup.py --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4

"""

#### IMPORTS ####
import logging
import json
import datetime
import urllib.request
import os
import signal
import sys
import argparse

MISTAPI_MIN_VERSION = "0.55.6"

try:
    import mistapi
    from mistapi.__logger import console
except ImportError:
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
DEFAULT_BACKUP_FOLDER = "./org_backup"
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


def sigint_handler(signal, frame) -> None:
    """
    Handle the SIGINT signal (Ctrl+C) to exit gracefully.
    """
    global SYS_EXIT
    SYS_EXIT = True
    print("[Ctrl C],KeyboardInterrupt exception occurred.")


signal.signal(signal.SIGINT, sigint_handler)
#####################################################################
# BACKUP OBJECTS REFS
class Step:
    """
    Class to define a step in the backup process.
    """

    def __init__(self, mistapi_function, text, check_next, request_type: str = ""):
        self.mistapi_function = mistapi_function
        self.text = text
        self.check_next = check_next
        self.request_type = request_type
        
ORG_STEPS:dict[str, Step] = {
    "data": Step(
        mistapi_function=mistapi.api.v1.orgs.orgs.getOrg,
        text="Org info",
        check_next=False,
    ),
    "settings": Step(
        mistapi_function=mistapi.api.v1.orgs.setting.getOrgSettings,
        text="Org settings",
        check_next=False,
    ),
    "sites": Step(
        mistapi_function=mistapi.api.v1.orgs.sites.listOrgSites,
        text="Org Sites",
        check_next=True,
    ),
    "webhooks": Step(
        mistapi_function=mistapi.api.v1.orgs.webhooks.listOrgWebhooks,
        text="Org webhooks",
        check_next=True,
    ),
    "assetfilters": Step(
        mistapi_function=mistapi.api.v1.orgs.assetfilters.listOrgAssetFilters,
        text="Org assetfilters",
        check_next=True,
    ),
    "alarmtemplates": Step(
        mistapi_function=mistapi.api.v1.orgs.alarmtemplates.listOrgAlarmTemplates,
        text="Org alarmtemplates",
        check_next=True,
    ),
    "deviceprofiles": Step(
        mistapi_function=mistapi.api.v1.orgs.deviceprofiles.listOrgDeviceProfiles,
        text="Org deviceprofiles",
        check_next=True,
    ),
    "switchprofiles": Step(
        mistapi_function=mistapi.api.v1.orgs.deviceprofiles.listOrgDeviceProfiles,
        text="Org switchprofiles",
        request_type="switch",
        check_next=True,
    ),
    "hubprofiles": Step(
        mistapi_function=mistapi.api.v1.orgs.deviceprofiles.listOrgDeviceProfiles,
        text="Org hubprofiles",
        request_type="gateway",
        check_next=True,
    ),
    "mxclusters": Step(
        mistapi_function=mistapi.api.v1.orgs.mxclusters.listOrgMxEdgeClusters,
        text="Org mxclusters",
        check_next=True,
    ),
    "mxtunnels": Step(
        mistapi_function=mistapi.api.v1.orgs.mxtunnels.listOrgMxTunnels,
        text="Org mxtunnels",
        check_next=True,
    ),
    "psks": Step(
        mistapi_function=mistapi.api.v1.orgs.psks.listOrgPsks,
        text="Org psks",
        check_next=True,
    ),
    "pskportals": Step(
        mistapi_function=mistapi.api.v1.orgs.pskportals.listOrgPskPortals,
        text="Org pskportals",
        check_next=True,
    ),
    "rftemplates": Step(
        mistapi_function=mistapi.api.v1.orgs.rftemplates.listOrgRfTemplates,
        text="Org rftemplates",
        check_next=True,
    ),
    "networktemplates": Step(
        mistapi_function=mistapi.api.v1.orgs.networktemplates.listOrgNetworkTemplates,
        text="Org networktemplates",
        check_next=True,
    ),
    "evpn_topologies": Step(
        mistapi_function=mistapi.api.v1.orgs.evpn_topologies.listOrgEvpnTopologies,
        text="Org evpn_topologies",
        check_next=True,
    ),
    "services": Step(
        mistapi_function=mistapi.api.v1.orgs.services.listOrgServices,
        text="Org services",
        check_next=True,
    ),
    "networks": Step(
        mistapi_function=mistapi.api.v1.orgs.networks.listOrgNetworks,
        text="Org networks",
        check_next=True,
    ),
    "gatewaytemplates": Step(
        mistapi_function=mistapi.api.v1.orgs.gatewaytemplates.listOrgGatewayTemplates,
        text="Org gatewaytemplates",
        check_next=True,
    ),
    "vpns": Step(
        mistapi_function=mistapi.api.v1.orgs.vpns.listOrgVpns,
        text="Org vpns",
        check_next=True,
    ),
    "secpolicies": Step(
        mistapi_function=mistapi.api.v1.orgs.secpolicies.listOrgSecPolicies,
        text="Org secpolicies",
        check_next=True,
    ),
    "servicepolicies": Step(
        mistapi_function=mistapi.api.v1.orgs.servicepolicies.listOrgServicePolicies,
        text="Org servicepolicies",
        check_next=True,
    ),
    "sitegroups": Step(
        mistapi_function=mistapi.api.v1.orgs.sitegroups.listOrgSiteGroups,
        text="Org sitegroups",
        check_next=True,
    ),
    "sitetemplates": Step(
        mistapi_function=mistapi.api.v1.orgs.sitetemplates.listOrgSiteTemplates,
        text="Org sitetemplates",
        check_next=True,
    ),
    "ssos": Step(
        mistapi_function=mistapi.api.v1.orgs.ssos.listOrgSsos,
        text="Org ssos",
        check_next=True,
    ),
    "ssoroles": Step(
        mistapi_function=mistapi.api.v1.orgs.ssoroles.listOrgSsoRoles,
        text="Org ssoroles",
        check_next=True,
    ),
    "templates": Step(
        mistapi_function=mistapi.api.v1.orgs.templates.listOrgTemplates,
        text="Org templates",
        check_next=True,
    ),
    "wxrules": Step(
        mistapi_function=mistapi.api.v1.orgs.wxrules.listOrgWxRules,
        text="Org wxrules",
        check_next=True,
    ),
    "wxtags": Step(
        mistapi_function=mistapi.api.v1.orgs.wxtags.listOrgWxTags,
        text="Org wxtags",
        check_next=True,
    ),
    "wxtunnels": Step(
        mistapi_function=mistapi.api.v1.orgs.wxtunnels.listOrgWxTunnels,
        text="Org wxtunnels",
        check_next=True,
    ),
    "nactags": Step(
        mistapi_function=mistapi.api.v1.orgs.nactags.listOrgNacTags,
        text="Org nactags",
        check_next=True,
    ),
    "nacrules": Step(
        mistapi_function=mistapi.api.v1.orgs.nacrules.listOrgNacRules,
        text="Org nacrules",
        check_next=True,
    ),
    "usermacs": Step(
        mistapi_function=mistapi.api.v1.orgs.usermacs.searchOrgUserMacs,
        text="Org usermacs",
        check_next=True,
    ),
    "wlans": Step(
        mistapi_function=mistapi.api.v1.orgs.wlans.listOrgWlans,
        text="Org wlans",
        check_next=True,
    ),
}
SITE_STEPS:dict[str, Step] = {
    "assets": Step(
        mistapi_function=mistapi.api.v1.sites.assets.listSiteAssets,
        text="Site assets",
        check_next=True,
    ),
    "assetfilters": Step(
        mistapi_function=mistapi.api.v1.sites.assetfilters.listSiteAssetFilters,
        text="Site assetfilters",
        check_next=True,
    ),
    "beacons": Step(
        mistapi_function=mistapi.api.v1.sites.beacons.listSiteBeacons,
        text="Site beacons",
        check_next=True,
    ),
    "maps": Step(
        mistapi_function=mistapi.api.v1.sites.maps.listSiteMaps,
        text="Site maps",
        check_next=True,
    ),
    "psks": Step(
        mistapi_function=mistapi.api.v1.sites.psks.listSitePsks,
        text="Site psks",
        check_next=True,
    ),
    "evpn_topologies": Step(
        mistapi_function=mistapi.api.v1.sites.evpn_topologies.listSiteEvpnTopologies,
        text="Site EVPN Topologies",
        check_next=True,
    ),
    "rssizones": Step(
        mistapi_function=mistapi.api.v1.sites.rssizones.listSiteRssiZones,
        text="Site rssizones",
        check_next=True,
    ),
    "settings": Step(
        mistapi_function=mistapi.api.v1.sites.setting.getSiteSetting,
        text="Site settings",
        check_next=False,
    ),
    "vbeacons": Step(
        mistapi_function=mistapi.api.v1.sites.vbeacons.listSiteVBeacons,
        text="Site vbeacons",
        check_next=True,
    ),
    "webhooks": Step(
        mistapi_function=mistapi.api.v1.sites.webhooks.listSiteWebhooks,
        text="Site webhooks",
        check_next=True,
    ),
    "wlans": Step(
        mistapi_function=mistapi.api.v1.sites.wlans.listSiteWlans,
        text="Site wlans",
        check_next=True,
    ),
    "wxrules": Step(
        mistapi_function=mistapi.api.v1.sites.wxrules.listSiteWxRules,
        text="Site wxrules",
        check_next=True,
    ),
    "wxtags": Step(
        mistapi_function=mistapi.api.v1.sites.wxtags.listSiteWxTags,
        text="Site wxtags",
        check_next=True,
    ),
    "wxtunnels": Step(
        mistapi_function=mistapi.api.v1.sites.wxtunnels.listSiteWxTunnels,
        text="Site wxtunnels",
        check_next=True,
    ),
    "zones": Step(
        mistapi_function=mistapi.api.v1.sites.zones.listSiteZones,
        text="Site zones",
        check_next=True,
    ),
}


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
        print("Progress: ", end="")
        print(f"[{'█' * x}{'.' * (size - delta - x)}]", end="")
        print(f"{int(percent * 100)}%".rjust(5), end="")

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

    def set_steps_total(self, steps_total: int) -> None:
        """
        Set the total number of steps for the progress bar.
        :param steps_total: The total number of steps
        """
        self.steps_total = steps_total

    def log_message(self, message, display_pbar: bool = True) -> None:
        """
        Log a message in the progress bar.
        :param message: The message to log
        :param display_pbar: If True, the progress bar will be displayed after the message
        """
        self._pb_new_step(message, " ", display_pbar=display_pbar)

    def log_debug(self, message) -> None:
        """
        Log a debug message.
        :param message: The debug message to log
        """
        LOGGER.debug(message)

    def log_success(
        self, message, inc: bool = False, display_pbar: bool = True
    ) -> None:
        """
        Log a success message in the progress bar.
        :param message: The success message to log
        :param inc: If True, the step count will be incremented
        :param display_pbar: If True, the progress bar will be displayed after the success
        """
        LOGGER.info("%s: Success", message)
        self._pb_new_step(
            message, "\033[92m\u2714\033[0m\n", inc=inc, display_pbar=display_pbar
        )

    def log_warning(
        self, message, inc: bool = False, display_pbar: bool = True
    ) -> None:
        """
        Log a warning message in the progress bar.
        :param message: The warning message to log
        :param inc: If True, the step count will be incremented
        :param display_pbar: If True, the progress bar will be displayed after the warning
        """
        LOGGER.warning(message)
        self._pb_new_step(
            message, "\033[93m\u2b58\033[0m\n", inc=inc, display_pbar=display_pbar
        )

    def log_failure(
        self, message, inc: bool = False, display_pbar: bool = True
    ) -> None:
        """
        Log a failure message in the progress bar.
        :param message: The failure message to log
        :param inc: If True, the step count will be incremented
        :param display_pbar: If True, the progress bar will be displayed after the failure
        """
        LOGGER.error("%s: Failure", message)
        self._pb_new_step(
            message, "\033[31m\u2716\033[0m\n", inc=inc, display_pbar=display_pbar
        )

    def log_title(self, message, end: bool = False, display_pbar: bool = True) -> None:
        """
        Log a title message in the progress bar.
        :param message: The title message to log
        :param end: If True, the progress bar will not be displayed after the title
        :param display_pbar: If True, the progress bar will be displayed after the title
        """
        LOGGER.info(message)
        self._pb_title(message, end=end, display_pbar=display_pbar)


PB = ProgressBar()


#####################################################################
#### FUNCTIONS ####
def _backup_wlan_portal(org_id, site_id, wlans) -> None:
    for wlan in wlans:
        wlan_id = wlan["id"]
        if not site_id:
            portal_file_name = f"{FILE_PREFIX}_org_{org_id}_wlan_{wlan_id}.json"
            portal_image = f"{FILE_PREFIX}_org_{org_id}_wlan_{wlan_id}.png"
        else:
            portal_file_name = (
                f"{FILE_PREFIX}_org_{org_id}_site_{site_id}_wlan_{wlan_id}.json"
            )
            portal_image = (
                f"{FILE_PREFIX}_org_{org_id}_site_{site_id}_wlan_{wlan_id}.png"
            )
        if "portal_template_url" in wlan and wlan["portal_template_url"]:
            try:
                message = f"portal template for wlan {wlan_id}"
                PB.log_message(message)
                urllib.request.urlretrieve(
                    wlan["portal_template_url"], portal_file_name
                )
                PB.log_success(message)
            except Exception:
                PB.log_failure(message)
                LOGGER.error("Exception occurred", exc_info=True)
        if "portal_image" in wlan and wlan["portal_image"]:
            try:
                message = f"portal image for wlan {wlan_id}"
                PB.log_message(message)
                urllib.request.urlretrieve(wlan["portal_image"], portal_image)
                PB.log_success(message)
            except Exception:
                PB.log_failure(message)
                LOGGER.error("Exception occurred", exc_info=True)


def _backup_evpn_topology(mist_session, evpn_topologies) -> None:
    for evpn_topology in evpn_topologies:
        evpn_topology_id = evpn_topology["id"]
        org_id = evpn_topology.get("org_id")
        site_id = evpn_topology.get("site_id", "00000000-0000-0000-0000-000000000000")
        data = {}
        if (
            evpn_topology.get("for_site")
            and site_id != "00000000-0000-0000-0000-000000000000"
        ):
            LOGGER.info(
                "_backup_evpn_topology: retrieving EVPN Data for Site EVPN Topology %s",
                evpn_topology_id,
            )
            resp = mistapi.api.v1.sites.evpn_topologies.getSiteEvpnTopology(
                mist_session, site_id, evpn_topology_id
            )
            if resp.status_code == 200 and resp.data:
                data = resp.data
            else:
                LOGGER.error(
                    "_backup_evpn_topology: Unable to retrieve EVPN Topology data: %s / %s",
                    resp.status_code,
                    resp.raw_data,
                )
                continue
        else:
            LOGGER.info(
                "_backup_evpn_topology: retrieving EVPN Data for Org EVPN Topology %s",
                evpn_topology_id,
            )
            resp = mistapi.api.v1.orgs.evpn_topologies.getOrgEvpnTopology(
                mist_session, org_id, evpn_topology_id
            )
            if resp.status_code == 200 and resp.data:
                data = resp.data
            else:
                LOGGER.error(
                    "_backup_evpn_topology: Unable to retrieve EVPN Topology data: %s / %s",
                    resp.status_code,
                    resp.raw_data,
                )
                continue
        evpn_topology["switches"] = []
        for switch in data.get("switches", []):
            evpn_topology["switches"].append(
                {
                    "mac": switch.get("mac"),
                    "role": switch.get("role"),
                    "pod": switch.get("pod"),
                }
            )


def _do_backup(
    mist_session,
    step_name,
    backup_function,
    check_next,
    scope_id,
    message,
    request_type: str = "",
) -> list:
    if SYS_EXIT:
        sys.exit(0)
    try:
        PB.log_message(message)
        if request_type:
            response = backup_function(mist_session, scope_id, type=request_type)
        else:
            response = backup_function(mist_session, scope_id)

        if check_next:
            data = mistapi.get_all(mist_session, response)
        else:
            data = response.data

        if step_name == "evpn_topologies":
            _backup_evpn_topology(mist_session, data)

        PB.log_success(message, True)
        return data
    except Exception:
        PB.log_failure(message, True)
        LOGGER.error("Exception occurred", exc_info=True)
        return []


#### BACKUP ####
def _backup_full_org(mist_session, org_id, org_name) -> dict:
    PB.log_title(f"Backuping Org {org_name}")
    backup = {}
    backup["org"] = {"id": org_id}

    ### ORG BACKUP
    for step_name, step in ORG_STEPS.items():
        request_type:str = step.request_type
        backup["org"][step_name] = _do_backup(
            mist_session,
            step_name,
            step.mistapi_function,
            step.check_next,
            org_id,
            step.text,
            request_type,
        )
    _backup_wlan_portal(org_id, None, backup["org"]["wlans"])

    ### SITES BACKUP
    backup["sites"] = {}
    for site in backup["org"]["sites"]:
        site_id = site["id"]
        site_name = site["name"]
        site_backup = {}
        PB.log_title(f"Backuping Site {site_name}")
        for step_name, step in SITE_STEPS.items():
            site_backup[step_name] = _do_backup(
                mist_session,
                step_name,
                step.mistapi_function,
                step.check_next,
                site_id,
                step.text,
            )
        backup["sites"][site_id] = site_backup

        if site_backup["wlans"]:
            _backup_wlan_portal(org_id, site_id, site_backup["wlans"])

        message = "Site map images"
        PB.log_message(message)
        try:
            for xmap in site_backup["maps"]:
                url = None
                xmap_id = None
                if "url" in xmap:
                    url = xmap["url"]
                    xmap_id = xmap["id"]
                if url and xmap_id:
                    image_name = (
                        f"{FILE_PREFIX}_org_{org_id}_site_{site_id}_map_{xmap_id}.png"
                    )
                    urllib.request.urlretrieve(url, image_name)
            PB.log_success(message)
        except Exception:
            PB.log_failure(message)
            LOGGER.error("Exception occurred", exc_info=True)

    PB.log_title("Backup Done", end=True)
    return backup


def _save_to_file(backup: dict, backup_folder: str, backup_name: str):
    backup_path = os.path.join(backup_folder, backup_name, BACKUP_FILE)
    message = f"Saving to file {backup_path} "
    PB.log_title(message, end=True, display_pbar=False)
    try:
        with open(BACKUP_FILE, "w") as f:
            json.dump(backup, f)
        PB.log_success(message, display_pbar=False)
    except Exception:
        PB.log_failure(message, display_pbar=False)
        LOGGER.error("Exception occurred", exc_info=True)


def _start_org_backup(
    mist_session: mistapi.APISession,
    org_id: str,
    org_name: str,
    backup_folder: str,
    backup_name: str,
) -> bool:
    # FOLDER
    try:
        if not os.path.exists(backup_folder):
            os.makedirs(backup_folder)
        os.chdir(backup_folder)
        if not os.path.exists(backup_name):
            os.makedirs(backup_name)
        os.chdir(backup_name)
    except Exception as e:
        print(e)
        LOGGER.error("Exception occurred", exc_info=True)
        return False

    # PREPARE PROGRESS BAR
    try:
        response = mistapi.api.v1.orgs.sites.listOrgSites(mist_session, org_id)
        sites = mistapi.get_all(mist_session, response)
        PB.set_steps_total(len(ORG_STEPS) + len(sites) * len(SITE_STEPS))
    except Exception as e:
        print(e)
        LOGGER.error("Exception occurred", exc_info=True)
        return False

    # BACKUP
    try:
        backup = _backup_full_org(mist_session, org_id, org_name)
        _save_to_file(backup, backup_folder, backup_name)
    except Exception as e:
        print(e)
        LOGGER.error("Exception occurred", exc_info=True)
        return False

    return True


def start(
    mist_session: mistapi.APISession,
    org_id: str,
    backup_folder_param: str = "",
    backup_name: str = "",
    backup_name_date: bool = False,
    backup_name_ts: bool = False,
):
    """
    Start the process to deploy a backup/template

    PARAMS
    -------
    apisession : mistapi.APISession
        mistapi session, already logged in
    org_id : str
        only if the destination org already exists. org_id where to deploy the
        configuration
    backup_folder_param : str
        Path to the folder where to save the org backup (a subfolder will be
        created with the org name).
        default is "./org_backup"
    backup_name : str
        Name of the subfolder where the the backup files will be saved
        default is the org name
    backup_name_date : bool, default = False
        if `backup_name_date`==`True`, append the current date and time (ISO
        format) to the backup name
    backup_name_ts : bool, default = False
        if `backup_name_ts`==`True`, append the current timestamp to the backup
        name

    RETURNS
    -------
    bool
        success status of the backup process. Returns False if the process
        didn't ended well
    """
    LOGGER.debug("org_conf_backup:start")
    LOGGER.debug("org_conf_backup:start:parameters:org_id: %s", org_id)
    LOGGER.debug(
        "org_conf_backup:start:parameters:backup_folder_param: %s", backup_folder_param
    )
    LOGGER.debug("org_conf_backup:start:parameters:backup_name: %s", backup_name)
    LOGGER.debug(
        "org_conf_backup:start:parameters:backup_name_date: %s", backup_name_date
    )
    LOGGER.debug("org_conf_backup:start:parameters:backup_name_ts: %s", backup_name_ts)
    current_folder = os.getcwd()
    if not backup_folder_param:
        backup_folder_param = DEFAULT_BACKUP_FOLDER
    if not org_id:
        org_id = mistapi.cli.select_org(mist_session)[0]
    org_name = mistapi.api.v1.orgs.orgs.getOrg(mist_session, org_id).data["name"]

    if not backup_name:
        backup_name = org_name
    if backup_name_date:
        backup_name = f"{backup_name}_{datetime.datetime.isoformat(datetime.datetime.now()).split('.')[0].replace(':', '.')}"
    elif backup_name_ts:
        backup_name = f"{backup_name}_{round(datetime.datetime.timestamp(datetime.datetime.now()))}"

    success = _start_org_backup(
        mist_session, org_id, org_name, backup_folder_param, backup_name
    )
    os.chdir(current_folder)
    return success


#####################################################################
# USAGE
def usage(error_message: str = "") -> None:
    """
    Print the usage information and exit the script.
    :param error_message: Optional error message to display
    """
    print(
        """
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

It is recommended to use an environment file to store the required information
to request the Mist Cloud (see https://pypi.org/project/mistapi/ for more 
information about the available parameters).

-------
Script Parameters:
-h, --help              display this help
-o, --org_id=           Set the org_id
-b, --backup_folder=    Path to the folder where to save the org backup (a 
                        subfolder will be created with the org name)
                        default is "./org_backup"

-d, --datetime          append the current date and time (ISO format) to the
                        backup name 
-t, --timestamp         append the current timestamp to the backup 

-l, --log_file=         define the filepath/filename where to write the logs
                        default is "./script.log"
-e, --env=              define the env file to use (see mistapi env file 
                        documentation here: https://pypi.org/project/mistapi/)
                        default is "~/.mist_env"

-------
Examples:
python3 ./org_conf_backup.py
python3 ./org_conf_backup.py --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 

"""
    )
    if error_message:
        console.critical(error_message)
    sys.exit(0)


def check_mistapi_version():
    """Check if the installed mistapi version meets the minimum requirement."""

    current_version = mistapi.__version__.split(".")
    required_version = MISTAPI_MIN_VERSION.split(".")

    try:
        for i, req in enumerate(required_version):
            if current_version[int(i)] > req:
                break
            if current_version[int(i)] < req:
                raise ImportError(
                    f'"mistapi" package version {MISTAPI_MIN_VERSION} is required '
                    f"but version {mistapi.__version__} is installed."
                )
    except ImportError as e:
        LOGGER.critical(str(e))
        LOGGER.critical("Please use the pip command to update it.")
        LOGGER.critical("")
        LOGGER.critical("    # Linux/macOS")
        LOGGER.critical("    python3 -m pip install --upgrade mistapi")
        LOGGER.critical("")
        LOGGER.critical("    # Windows")
        LOGGER.critical("    py -m pip install --upgrade mistapi")
        print(
            f"""
Critical:\r\n
{e}\r\n
Please use the pip command to update it.
# Linux/macOS
python3 -m pip install --upgrade mistapi
# Windows
py -m pip install --upgrade mistapi
            """
        )
        sys.exit(2)
    finally:
        LOGGER.info(
            '"mistapi" package version %s is required, '
            "you are currently using version %s.",
            MISTAPI_MIN_VERSION,
            mistapi.__version__,
        )


#####################################################################
##### ENTRY POINT ####
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Python script to backup a whole organization.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
python3 ./org_conf_backup.py
python3 ./org_conf_backup.py --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4
        """,
    )

    parser.add_argument("-o", "--org_id", help="Set the org_id")
    parser.add_argument(
        "-e", "--env", default=ENV_FILE, help="define the env file to use"
    )
    parser.add_argument(
        "-l",
        "--log_file",
        default=LOG_FILE,
        help="define the filepath/filename where to write the logs",
    )
    parser.add_argument(
        "-b",
        "--backup_folder",
        default=DEFAULT_BACKUP_FOLDER,
        help="Path to the folder where to save the org backup",
    )

    timestamp_group = parser.add_mutually_exclusive_group()
    timestamp_group.add_argument(
        "-d",
        "--datetime",
        action="store_true",
        help="append the current date and time (ISO format) to the backup name",
    )
    timestamp_group.add_argument(
        "-t",
        "--timestamp",
        action="store_true",
        help="append the current timestamp to the backup",
    )

    args = parser.parse_args()

    ORG_ID = args.org_id
    BACKUP_FOLDER = args.backup_folder
    BACKUP_NAME = ""
    BACKUP_NAME_DATE = args.datetime
    BACKUP_NAME_TS = args.timestamp
    ENV_FILE = args.env
    LOG_FILE = args.log_file

    #### LOGS ####
    logging.basicConfig(filename=LOG_FILE, filemode="w")
    LOGGER.setLevel(logging.DEBUG)
    check_mistapi_version()
    ### START ###
    APISESSION = mistapi.APISession(env_file=ENV_FILE)
    APISESSION.login()

    ### START ###
    start(
        APISESSION, ORG_ID, BACKUP_FOLDER, BACKUP_NAME, BACKUP_NAME_DATE, BACKUP_NAME_TS
    )

"""
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to deploy organization backup/template file.
You can use the script "org_conf_backup.py" to generate the backup file from an
existing organization.

This script will not override existing objects. If you already configured objects in the
destination organization, new objects will be created. If you want to "reset" the
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

It is recommended to use an environment file to store the required information
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
import argparse
import signal
from typing import Callable

MISTAPI_MIN_VERSION = "0.55.5"

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
    print("[Ctrl C],KeyboardInterrupt exception occurred.")


signal.signal(signal.SIGINT, sigint_handler)


#####################################################################
# DEPLOY OBJECTS REFS
class Step:
    """
    Class to define a step in the backup process.
    """

    def __init__(self, create_mistapi_function, update_mistapi_function=None, text=""):
        self.create_mistapi_function = create_mistapi_function
        self.update_mistapi_function = update_mistapi_function
        self.text = text


ORG_STEPS = {
    "assetfilters": Step(
        create_mistapi_function=mistapi.api.v1.orgs.assetfilters.createOrgAssetFilter,
        update_mistapi_function=mistapi.api.v1.orgs.assetfilters.updateOrgAssetFilter,
        text="Org assetfilters",
    ),
    "deviceprofiles": Step(
        create_mistapi_function=mistapi.api.v1.orgs.deviceprofiles.createOrgDeviceProfile,
        update_mistapi_function=mistapi.api.v1.orgs.deviceprofiles.updateOrgDeviceProfile,
        text="Org deviceprofiles",
    ),
    "switchprofiles": Step(
        create_mistapi_function=mistapi.api.v1.orgs.deviceprofiles.createOrgDeviceProfile,
        update_mistapi_function=mistapi.api.v1.orgs.deviceprofiles.updateOrgDeviceProfile,
        text="Org switchprofiles",
    ),
    "hubprofiles": Step(
        create_mistapi_function=mistapi.api.v1.orgs.deviceprofiles.createOrgDeviceProfile,
        update_mistapi_function=mistapi.api.v1.orgs.deviceprofiles.updateOrgDeviceProfile,
        text="Org hubprofiles",
    ),
    "evpn_topologies": Step(
        create_mistapi_function=mistapi.api.v1.orgs.evpn_topologies.createOrgEvpnTopology,
        update_mistapi_function=mistapi.api.v1.orgs.evpn_topologies.updateOrgEvpnTopology,
        text="Org evpn_topologies",
    ),
    "secpolicies": Step(
        create_mistapi_function=mistapi.api.v1.orgs.secpolicies.createOrgSecPolicy,
        update_mistapi_function=mistapi.api.v1.orgs.secpolicies.updateOrgSecPolicy,
        text="Org secpolicies",
    ),
    "aptemplates": Step(
        create_mistapi_function=mistapi.api.v1.orgs.aptemplates.createOrgAptemplate,
        update_mistapi_function=mistapi.api.v1.orgs.aptemplates.updateOrgAptemplate,
        text="Org aptemplates",
    ),
    "networktemplates": Step(
        create_mistapi_function=mistapi.api.v1.orgs.networktemplates.createOrgNetworkTemplate,
        update_mistapi_function=mistapi.api.v1.orgs.networktemplates.updateOrgNetworkTemplate,
        text="Org networktemplates",
    ),
    "networks": Step(
        create_mistapi_function=mistapi.api.v1.orgs.networks.createOrgNetwork,
        update_mistapi_function=mistapi.api.v1.orgs.networks.updateOrgNetwork,
        text="Org networks",
    ),
    "services": Step(
        create_mistapi_function=mistapi.api.v1.orgs.services.createOrgService,
        update_mistapi_function=mistapi.api.v1.orgs.services.updateOrgService,
        text="Org services",
    ),
    "servicepolicies": Step(
        create_mistapi_function=mistapi.api.v1.orgs.servicepolicies.createOrgServicePolicy,
        update_mistapi_function=mistapi.api.v1.orgs.servicepolicies.updateOrgServicePolicy,
        text="Org servicepolicies",
    ),
    "vpns": Step(
        create_mistapi_function=mistapi.api.v1.orgs.vpns.createOrgVpn,
        update_mistapi_function=mistapi.api.v1.orgs.vpns.updateOrgVpn,
        text="Org vpns",
    ),
    "gatewaytemplates": Step(
        create_mistapi_function=mistapi.api.v1.orgs.gatewaytemplates.createOrgGatewayTemplate,
        update_mistapi_function=mistapi.api.v1.orgs.gatewaytemplates.updateOrgGatewayTemplate,
        text="Org gatewaytemplates",
    ),
    "alarmtemplates": Step(
        create_mistapi_function=mistapi.api.v1.orgs.alarmtemplates.createOrgAlarmTemplate,
        update_mistapi_function=mistapi.api.v1.orgs.alarmtemplates.updateOrgAlarmTemplate,
        text="Org alarmtemplates",
    ),
    "rftemplates": Step(
        create_mistapi_function=mistapi.api.v1.orgs.rftemplates.createOrgRfTemplate,
        update_mistapi_function=mistapi.api.v1.orgs.rftemplates.updateOrgRfTemplate,
        text="Org rftemplates",
    ),
    "webhooks": Step(
        create_mistapi_function=mistapi.api.v1.orgs.webhooks.createOrgWebhook,
        update_mistapi_function=mistapi.api.v1.orgs.webhooks.updateOrgWebhook,
        text="Org webhooks",
    ),
    "mxclusters": Step(
        create_mistapi_function=mistapi.api.v1.orgs.mxclusters.createOrgMxEdgeCluster,
        update_mistapi_function=mistapi.api.v1.orgs.mxclusters.updateOrgMxEdgeCluster,
        text="Org mxclusters",
    ),
    "mxtunnels": Step(
        create_mistapi_function=mistapi.api.v1.orgs.mxtunnels.createOrgMxTunnel,
        update_mistapi_function=mistapi.api.v1.orgs.mxtunnels.updateOrgMxTunnel,
        text="Org mxtunnels",
    ),
    "wxtunnels": Step(
        create_mistapi_function=mistapi.api.v1.orgs.wxtunnels.createOrgWxTunnel,
        update_mistapi_function=mistapi.api.v1.orgs.wxtunnels.updateOrgWxTunnel,
        text="Org wxtunnels",
    ),
    "sitetemplates": Step(
        create_mistapi_function=mistapi.api.v1.orgs.sitetemplates.createOrgSiteTemplate,
        update_mistapi_function=mistapi.api.v1.orgs.sitetemplates.updateOrgSiteTemplate,
        text="Org sitetemplates",
    ),
    "sitegroups": Step(
        create_mistapi_function=mistapi.api.v1.orgs.sitegroups.createOrgSiteGroup,
        update_mistapi_function=mistapi.api.v1.orgs.sitegroups.updateOrgSiteGroup,
        text="Org sitegroups",
    ),
    "sites": Step(
        create_mistapi_function=mistapi.api.v1.orgs.sites.createOrgSite,
        update_mistapi_function=mistapi.api.v1.sites.sites.updateSiteInfo,
        text="Org Sites",
    ),
    "templates": Step(
        create_mistapi_function=mistapi.api.v1.orgs.templates.createOrgTemplate,
        update_mistapi_function=mistapi.api.v1.orgs.templates.updateOrgTemplate,
        text="Org templates",
    ),
    "wlans": Step(
        create_mistapi_function=mistapi.api.v1.orgs.wlans.createOrgWlan,
        update_mistapi_function=mistapi.api.v1.orgs.wlans.updateOrgWlan,
        text="Org wlans",
    ),
    "wxtags": Step(
        create_mistapi_function=mistapi.api.v1.orgs.wxtags.createOrgWxTag,
        update_mistapi_function=mistapi.api.v1.orgs.wxtags.updateOrgWxTag,
        text="Org wxtags",
    ),
    "wxrules": Step(
        create_mistapi_function=mistapi.api.v1.orgs.wxrules.createOrgWxRule,
        update_mistapi_function=mistapi.api.v1.orgs.wxrules.updateOrgWxRule,
        text="Org wxrules",
    ),
    "pskportals": Step(
        create_mistapi_function=mistapi.api.v1.orgs.pskportals.createOrgPskPortal,
        update_mistapi_function=mistapi.api.v1.orgs.pskportals.updateOrgPskPortal,
        text="Org pskportals",
    ),
    "psks": Step(
        create_mistapi_function=mistapi.api.v1.orgs.psks.importOrgPsks,
        text="Org psks",
    ),
    "nactags": Step(
        create_mistapi_function=mistapi.api.v1.orgs.nactags.createOrgNacTag,
        update_mistapi_function=mistapi.api.v1.orgs.nactags.updateOrgNacTag,
        text="Org nactags",
    ),
    "nacrules": Step(
        create_mistapi_function=mistapi.api.v1.orgs.nacrules.createOrgNacRule,
        update_mistapi_function=mistapi.api.v1.orgs.nacrules.updateOrgNacRule,
        text="Org nacrules",
    ),
    "usermacs": Step(
        create_mistapi_function=mistapi.api.v1.orgs.usermacs.importOrgUserMacs,
        text="Org nacendpoints",
    ),
    "ssos": Step(
        create_mistapi_function=mistapi.api.v1.orgs.ssos.createOrgSso,
        update_mistapi_function=mistapi.api.v1.orgs.ssos.updateOrgSso,
        text="Org ssos",
    ),
    "ssoroles": Step(
        create_mistapi_function=mistapi.api.v1.orgs.ssoroles.createOrgSsoRole,
        update_mistapi_function=mistapi.api.v1.orgs.ssoroles.updateOrgSsoRole,
        text="Org ssoroles",
    ),
}
SITE_STEPS = {
    "settings": Step(
        create_mistapi_function=mistapi.api.v1.sites.setting.updateSiteSettings,
        update_mistapi_function=mistapi.api.v1.sites.setting.updateSiteSettings,
        text="Site settings",
    ),
    "maps": Step(
        create_mistapi_function=mistapi.api.v1.sites.maps.createSiteMap,
        update_mistapi_function=mistapi.api.v1.sites.maps.updateSiteMap,
        text="Site maps",
    ),
    "zones": Step(
        create_mistapi_function=mistapi.api.v1.sites.zones.createSiteZone,
        update_mistapi_function=mistapi.api.v1.sites.zones.updateSiteZone,
        text="Site zones",
    ),
    "rssizones": Step(
        create_mistapi_function=mistapi.api.v1.sites.rssizones.createSiteRssiZone,
        update_mistapi_function=mistapi.api.v1.sites.rssizones.updateSiteRssiZone,
        text="Site rssizones",
    ),
    "assets": Step(
        create_mistapi_function=mistapi.api.v1.sites.assets.createSiteAsset,
        update_mistapi_function=mistapi.api.v1.sites.assets.updateSiteAsset,
        text="Site assets",
    ),
    "assetfilters": Step(
        create_mistapi_function=mistapi.api.v1.sites.assetfilters.createSiteAssetFilter,
        update_mistapi_function=mistapi.api.v1.sites.assetfilters.updateSiteAssetFilter,
        text="Site assetfilters",
    ),
    "beacons": Step(
        create_mistapi_function=mistapi.api.v1.sites.beacons.createSiteBeacon,
        update_mistapi_function=mistapi.api.v1.sites.beacons.updateSiteBeacon,
        text="Site beacons",
    ),
    "psks": Step(
        create_mistapi_function=mistapi.api.v1.sites.psks.importSitePsks,
        update_mistapi_function=mistapi.api.v1.sites.psks.updateSitePsk,
        text="Site psks",
    ),
    "vbeacons": Step(
        create_mistapi_function=mistapi.api.v1.sites.vbeacons.createSiteVBeacon,
        update_mistapi_function=mistapi.api.v1.sites.vbeacons.updateSiteVBeacon,
        text="Site vbeacons",
    ),
    "evpn_topologies": Step(
        create_mistapi_function=mistapi.api.v1.sites.evpn_topologies.createSiteEvpnTopology,
        update_mistapi_function=mistapi.api.v1.sites.evpn_topologies.updateSiteEvpnTopology,
        text="Site EVPN Topologies",
    ),
    "webhooks": Step(
        create_mistapi_function=mistapi.api.v1.sites.webhooks.createSiteWebhook,
        update_mistapi_function=mistapi.api.v1.sites.webhooks.updateSiteWebhook,
        text="Site webhooks",
    ),
    "wxtunnels": Step(
        create_mistapi_function=mistapi.api.v1.sites.wxtunnels.createSiteWxTunnel,
        update_mistapi_function=mistapi.api.v1.sites.wxtunnels.updateSiteWxTunnel,
        text="Site wxtunnels",
    ),
    "wlans": Step(
        create_mistapi_function=mistapi.api.v1.sites.wlans.createSiteWlan,
        update_mistapi_function=mistapi.api.v1.sites.wlans.updateSiteWlan,
        text="Site wlans",
    ),
    "wxtags": Step(
        create_mistapi_function=mistapi.api.v1.sites.wxtags.createSiteWxTag,
        update_mistapi_function=mistapi.api.v1.sites.wxtags.updateSiteWxTag,
        text="Site wxtags",
    ),
    "wxrules": Step(
        create_mistapi_function=mistapi.api.v1.sites.wxrules.createSiteWxRule,
        update_mistapi_function=mistapi.api.v1.sites.wxrules.updateSiteWxRule,
        text="Site wxrules",
    ),
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

    def add_uuid(self, new: str | None, old: str | None) -> None:
        """
        Add a new UUID mapping to the dictionary.
        :param new: The new UUID to be added.
        :param old: The old UUID that the new UUID replaces.
        """
        if new and old:
            LOGGER.debug("add_uuid: old_id %s matching new_id %s", old, new)
            self.uuids[old] = new
        else:
            LOGGER.warning("add_uuid: old_id %s matching new_id %s", old, new)

    def get_new_uuid(self, old: str) -> str:
        """
        Get the new UUID that replaces the old UUID.
        :param old: The old UUID to be replaced.
        :return: The new UUID if it exists, otherwise None.
        """
        return self.uuids.get(old, "")

    def add_replay(
        self,
        create_mistapi_function: Callable,
        update_mistapi_function: Callable | None,
        scope_id: str,
        object_id: str,
        object_type: str,
        data: dict,
    ) -> None:
        """
        Add a request to the replay list.
        :param create_mistapi_function: The function to create the object.
        :param update_mistapi_function: The function to update the object.
        :param scope_id: The scope ID where the object is located.
        :param object_id: The ID of the object to be created or updated.
        :param object_type: The type of the object (e.g., "wlans", "sites").
        :param data: The data to be used for creating or updating the object.
        """
        self.requests_to_replay.append(
            {
                "create_mistapi_function": create_mistapi_function,
                "update_mistapi_function": update_mistapi_function,
                "scope_id": scope_id,
                "object_id": object_id,
                "data": data,
                "object_type": object_type,
                "retry": 0,
            }
        )

    def get_replay(self) -> list:
        """
        Get the list of requests to replay.
        :return: A list of requests to replay.
        """
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

    def find_and_replace(self, obj: dict, object_type: str) -> tuple:
        """
        Find and replace UUIDs in the given object.
        :param obj: The object to process.
        :param object_type: The type of the object (e.g., "wlans", "sites").
        :return: A tuple containing the processed object and a list of missing UUIDs.
        """
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


##########################################################################################
##########################################################################################
# DEPLOY FUNCTIONS
##########################################################################################
# COMMON FUNCTION
def _common_deploy(
    apisession: mistapi.APISession,
    create_mistapi_function: Callable,
    update_mistapi_function: Callable | None,
    scope_id: str,
    object_type: str,
    data: dict,
    retry: bool = False,
) -> str:
    LOGGER.debug("conf_deploy:_common_deploy")
    if SYS_EXIT:
        sys.exit(0)
    old_id = None
    new_id = ""
    object_name = ""
    if "name" in data:
        object_name = f'"{data.get("name", "<unknown>")}"'
    elif "ssid" in data:
        object_name = f'"{data.get("ssid", "<unknown>")}"'
    if "id" in data:
        old_id = data["id"]
    else:
        old_id = None

    if object_type == "evpn_topologies":
        data["overwrite"] = True

    message = f"Creating {object_type} {object_name}"
    PB.log_message(message)
    data, missing_uuids = UUID_MATCHING.find_and_replace(data, object_type)

    try:
        response = create_mistapi_function(apisession, scope_id, data)
        if response.status_code == 200:
            new_id = response.data.get("id")
            if not missing_uuids:
                PB.log_success(message, inc=True)
            elif not retry:
                UUID_MATCHING.add_replay(
                    create_mistapi_function,
                    update_mistapi_function,
                    scope_id,
                    new_id,
                    object_type,
                    data,
                )
                PB.log_warning(message, inc=True)
        else:
            PB.log_failure(message, inc=True)
    except Exception:
        PB.log_failure(message, inc=True)
        LOGGER.error("Exception occurred", exc_info=True)
    UUID_MATCHING.add_uuid(new_id, old_id)
    return new_id


def _common_update(
    apisession: mistapi.APISession,
    update_mistapi_function: Callable,
    scope_id: str,
    object_id: str,
    object_type: str,
    data: dict,
) -> str | None:
    LOGGER.debug("conf_deploy:_common_update")
    if SYS_EXIT:
        sys.exit(0)
    old_id = None
    new_id = None
    object_name = ""
    if "name" in data:
        object_name = f'"{data.get("name", "<unknown>")}"'
    elif "ssid" in data:
        object_name = f'"{data.get("ssid", "<unknown>")}"'
    if "id" in data:
        old_id = data["id"]
    else:
        old_id = None

    if object_type == "evpn_topologies":
        data["overwrite"] = True

    message = f"Updating {object_type} {object_name} (id: {object_id})"
    PB.log_message(message)
    data, _ = UUID_MATCHING.find_and_replace(data, object_type)

    try:
        response = update_mistapi_function(apisession, scope_id, object_id, data)
        if response.status_code == 200:
            new_id = response.data.get("id")
            PB.log_success(message, inc=True)
        else:
            PB.log_failure(message, inc=True)
    except Exception:
        PB.log_failure(message, inc=True)
        LOGGER.error("Exception occurred", exc_info=True)
    UUID_MATCHING.add_uuid(new_id, old_id)
    return new_id


##########################################################################################
# BULK IMPORT
def _import_psks(
    apisession: mistapi.APISession,
    mistapi_function: Callable,
    scope_id: str,
    data: dict,
) -> None:
    LOGGER.debug("conf_deploy:_import_psks")
    if SYS_EXIT:
        sys.exit(0)

    message = "Importing PSKs"
    PB.log_message(message)

    try:
        response = mistapi_function(apisession, scope_id, data)
        if response.status_code == 200:
            PB.log_success(message, inc=True)
        else:
            PB.log_failure(message, inc=True)
    except Exception:
        PB.log_failure(message, inc=True)
        LOGGER.error("Exception occurred", exc_info=True)
    return None


def _import_usermacs(
    apisession: mistapi.APISession,
    mistapi_function: Callable,
    scope_id: str,
    data: dict,
) -> None:
    LOGGER.debug("conf_deploy:_deploy_wlan")
    message = "Importing Usermacs "
    PB.log_message(message)
    try:
        response = mistapi_function(apisession, scope_id, data)
        if response.status_code == 200:
            PB.log_success(message, inc=True)
        else:
            PB.log_failure(message, inc=True)
    except Exception:
        PB.log_failure(message, inc=True)
        LOGGER.error("Exception occurred", exc_info=True)


##########################################################################################
# WLAN FUNCTIONS
def _deploy_wlan(
    apisession: mistapi.APISession,
    create_mistapi_function: Callable,
    update_mistapi_function: Callable | None,
    scope_id: str,
    data: dict,
    old_org_id: str,
    old_site_id: str = "",
) -> None:
    LOGGER.debug("conf_deploy:_deploy_wlan")
    if SYS_EXIT:
        sys.exit(0)
    old_wlan_id = data["id"]
    new_wlan_id = _common_deploy(
        apisession,
        create_mistapi_function,
        update_mistapi_function,
        scope_id,
        "wlans",
        data,
    )
    UUID_MATCHING.add_uuid(new_wlan_id, old_wlan_id)
    _deploy_wlan_portal(
        apisession,
        old_org_id,
        old_site_id,
        old_wlan_id,
        scope_id,
        new_wlan_id,
        data.get("ssid", "<unknown>"),
    )


def _deploy_wlan_portal(
    apisession: mistapi.APISession,
    old_org_id: str,
    old_site_id: str,
    old_wlan_id: str,
    scope_id: str,
    new_wlan_id: str | None,
    wlan_name: str,
) -> None:
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

    if os.path.isfile(portal_file_name) and new_wlan_id:
        message = f'Creating Portal Template for WLAN "{wlan_name}" '
        PB.log_message(message)
        try:
            template = open(portal_file_name, "r")
        except Exception:
            PB.log_failure(f'Unable to open the template file "{portal_file_name}" ')
            LOGGER.error("Exception occurred", exc_info=True)
            return
        try:
            template = json.load(template)
        except Exception:
            PB.log_failure(f'Unable to read the template file "{portal_file_name}" ')
            LOGGER.error("Exception occurred", exc_info=True)
            return
        try:
            update_template_function(apisession, scope_id, new_wlan_id, template)
            PB.log_success(message)
        except Exception:
            PB.log_failure(f'Unable to upload the template "{portal_file_name}" ')
            LOGGER.error("Exception occurred", exc_info=True)

    else:
        PB.log_debug(f'No Portal template found for WLAN "{wlan_name}"')

    if os.path.isfile(portal_image) and new_wlan_id:
        message = f'Uploading Portal image for WLAN "{wlan_name}" '
        try:
            upload_image_function(apisession, scope_id, new_wlan_id, portal_image)
            PB.log_success(message)
        except Exception:
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
) -> None:
    LOGGER.debug("conf_deploy:_deploy_site_maps")
    if SYS_EXIT:
        sys.exit(0)
    old_map_id = data["id"]

    for area in data.get("intended_coverage_areas", []):
        LOGGER.info("_deploy_site_maps:removing ids from intended_coverage_areas")
        del area["id"]
        del area["map_id"]
    if data.get("sitesurvey_path"):
        LOGGER.info("_deploy_site_maps:removing sitesurvey_path")
        del data["sitesurvey_path"]

    new_map_id = _common_deploy(
        apisession,
        SITE_STEPS["maps"].create_mistapi_function,
        SITE_STEPS["maps"].update_mistapi_function,
        new_site_id,
        "maps",
        data,
    )

    if not new_map_id:
        LOGGER.warning(
            "new id not returned for old_id %s, trying to find a match", old_map_id
        )
        new_map_id = UUID_MATCHING.get_new_uuid(old_map_id)
    if not new_map_id:
        LOGGER.error("no match for old_id %s", old_map_id)
    image_name = (
        f"{FILE_PREFIX}_org_{old_org_id}_site_{old_site_id}_map_{old_map_id}.png"
    )
    if os.path.isfile(image_name):
        message = f'Uploading image floorplan  "{data.get("name", "map name unknown")}"'
        PB.log_message(message)
        try:
            mistapi.api.v1.sites.maps.addSiteMapImageFile(
                apisession, new_site_id, new_map_id, image_name
            )
            PB.log_success(message)
        except Exception:
            PB.log_failure(message)
            LOGGER.error("Exception occurred", exc_info=True)
    else:
        PB.log_debug(f'No image found for "{data.get("name", "map name unknown")}"')


def _deploy_site(
    apisession: mistapi.APISession,
    org_id: str,
    old_org_id: str,
    site_info: dict,
    sites_backup: dict,
) -> None:
    LOGGER.debug("conf_deploy:_deploy_site")
    if SYS_EXIT:
        sys.exit(0)
    old_site_id = site_info["id"]
    site_data = sites_backup.get(old_site_id, {})

    PB.log_title(f" Deploying Site {site_info['name']} ".center(80, "_"))
    new_site_id = _common_deploy(
        apisession,
        ORG_STEPS["sites"].create_mistapi_function,
        ORG_STEPS["sites"].update_mistapi_function,
        org_id,
        "sites",
        site_info,
    )
    LOGGER.debug(
        "conf_deploy:_deploy_site:site %s, old id=%s, new id=%s",
        site_info["name"],
        old_site_id,
        new_site_id,
    )
    for step_name, step in SITE_STEPS.items():
        if not site_data.get(step_name):
            LOGGER.debug("%s > %s: nothing to process", site_info["name"], step_name)
        else:
            LOGGER.debug("%s > %s: processing", site_info["name"], step_name)
            if step_name == "settings":
                step_data = site_data.get(step_name, {})
                _common_deploy(
                    apisession,
                    step.create_mistapi_function,
                    step.update_mistapi_function,
                    new_site_id,
                    step_name,
                    step_data,
                )
            elif step_name == "psks":
                step_data = site_data.get(step_name)
                if step_data:
                    _import_psks(
                        apisession,
                        step.create_mistapi_function,
                        new_site_id,
                        step_data,
                    )
            elif step_name == "maps":
                for step_data in site_data.get(step_name, []):
                    _deploy_site_maps(
                        apisession, old_org_id, old_site_id, new_site_id, step_data
                    )
            elif step_name == "wlans":
                for step_data in site_data.get(step_name, []):
                    _deploy_wlan(
                        apisession,
                        step.create_mistapi_function,
                        step.update_mistapi_function,
                        new_site_id,
                        step_data,
                        old_org_id,
                        old_site_id,
                    )
            else:
                for step_data in site_data.get(step_name, []):
                    _common_deploy(
                        apisession,
                        step.create_mistapi_function,
                        step.update_mistapi_function,
                        new_site_id,
                        step_name,
                        step_data,
                    )


##########################################################################################
#  ORG FUNCTIONS
def _deploy_org(
    apisession: mistapi.APISession, org_id: str, org_name: str, backup: dict
) -> None:
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
    except Exception:
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
    except Exception:
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
                        apisession, step.create_mistapi_function, org_id, step_data
                    )
            elif step_name == "usermacs":
                step_data = org_backup.get("usermacs")
                if step_data:
                    _import_usermacs(
                        apisession, step.create_mistapi_function, org_id, step_data
                    )
            else:
                for step_data in org_backup[step_name]:
                    if step_name == "sites":
                        _deploy_site(
                            apisession, org_id, old_org_id, step_data, sites_backup
                        )
                        PB.log_title(" Deploying Other Org Objects ".center(80, "_"))
                    elif step_name == "wlans":
                        _deploy_wlan(
                            apisession,
                            step.create_mistapi_function,
                            step.update_mistapi_function,
                            org_id,
                            step_data,
                            old_org_id,
                        )
                    else:
                        _common_deploy(
                            apisession,
                            step.create_mistapi_function,
                            step.update_mistapi_function,
                            org_id,
                            step_name,
                            step_data,
                        )

    PB.log_title("Retrying missing objects")
    for replay in UUID_MATCHING.get_replay():
        if replay.get("object_id"):
            _common_update(
                apisession,
                replay["update_mistapi_function"],
                replay["scope_id"],
                replay["object_id"],
                replay["object_type"],
                replay["data"],
            )
        else:
            _common_deploy(
                apisession,
                replay["create_mistapi_function"],
                replay["update_mistapi_function"],
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
    src_org_name: str = "",
    source_backup: str = "",
) -> None:
    LOGGER.debug("conf_deploy:_start_deploy_org")
    _go_to_backup_folder(backup_folder, src_org_name, source_backup)
    print()
    try:
        message = f"Loading template/backup file {BACKUP_FILE} "
        PB.log_message(message, display_pbar=False)
        with open(BACKUP_FILE) as f:
            backup = json.load(f)
        PB.log_success(message, display_pbar=False)
    except Exception:
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
    except Exception:
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
def _chdir(path: str) -> bool:
    try:
        os.chdir(path)
        return True
    except FileNotFoundError:
        console.error("The specified path does not exist.")
        return False
    except NotADirectoryError:
        console.error("The specified path is not a directory.")
        return False
    except PermissionError:
        console.error(
            "You do not have the necessary permissions "
            "to access the specified directory."
        )
        return False
    except Exception as e:
        console.error(f"An error occurred: {e}")
        return False


def _display_warning(message) -> None:
    resp = "x"
    while resp.lower() not in ["y", "n", ""]:
        print()
        resp = input(message)
    if resp.lower() != "y":
        console.error("Interruption... Exiting...")
        LOGGER.error("Interruption... Exiting...")
        sys.exit(0)


def _select_backup_folder(folders) -> None:
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
        except Exception:
            print("Only numbers are allowed. Please try again...")
    _chdir(folder)


def _go_to_backup_folder(
    backup_folder: str, src_org_name: str = "", source_backup: str = ""
) -> None:
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
    apisession: mistapi.APISession, org_id: str, org_name: str = ""
):
    response = mistapi.api.v1.orgs.orgs.getOrg(apisession, org_id)
    if response.status_code != 200:
        console.critical(f"Unable to retrieve the org information: {response.data}")
        sys.exit(3)
    org_name_from_mist = response.data["name"]
    return org_name == org_name_from_mist


def _check_org_name(apisession: mistapi.APISession, org_id: str, org_name: str = ""):
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


def _create_org(apisession: mistapi.APISession, custom_dest_org_name: str = ""):
    while True:
        if not custom_dest_org_name:
            custom_dest_org_name = input("Organization name? ")
        if custom_dest_org_name:
            org = {"name": custom_dest_org_name}
            print("")
            print("")
            message = f'Creating the organization "{custom_dest_org_name}" on {apisession.get_cloud()} '
            PB.log_message(message, display_pbar=False)
            try:
                PB.log_success(message, display_pbar=False)
            except Exception:
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
            "Do you want to create a (n)ew organization or (r)estore to an existing one, (q)uit ? "
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
    org_id: str = "",
    org_name: str = "",
    backup_folder_param: str = "",
    src_org_name: str = "",
    source_backup: str = "",
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
        org_id, _ = _create_org(apisession, org_name)
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

This script will not override existing objects. If you already configured objects in the
destination organization, new objects will be created. If you want to "reset" the
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

It is recommended to use an environment file to store the required information
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
#### SCRIPT ENTRYPOINT ####
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Deploy organization backup/template file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
python3 ./org_conf_deploy.py
python3 ./org_conf_deploy.py --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 -n "my test org"
        """,
    )

    parser.add_argument(
        "-o",
        "--org_id",
        help="Only if the destination org already exists. org_id where to deploy the configuration",
    )
    parser.add_argument(
        "-n", "--org_name", help="Org name where to deploy the configuration"
    )
    parser.add_argument(
        "-e",
        "--env",
        default=ENV_FILE,
        help="define the env file to use (default: ~/.mist_env)",
    )
    parser.add_argument(
        "-l",
        "--log_file",
        default=LOG_FILE,
        help="define the filepath/filename where to write the logs (default: ./script.log)",
    )
    parser.add_argument(
        "-f",
        "--backup_folder",
        help="Path to the folder where to save the org backup (default: ./org_backup)",
    )
    parser.add_argument(
        "-b", "--source_backup", help="Name of the backup/template to deploy"
    )

    args = parser.parse_args()

    ORG_ID = args.org_id
    ORG_NAME = args.org_name
    BACKUP_FOLDER_PARAM = args.backup_folder
    SOURCE_BACKUP = args.source_backup
    ENV_FILE = args.env
    LOG_FILE = args.log_file

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

"""
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to deploy organization backup/template file.
You can use the script "org_conf_backup.py" to generate the backup file from an
existing organization.

This script will not override existing objects by default but this behavior can be
changed with the parameter "--merge_action":
* --merge_action=skip (default): existing objects will be skipped
* --merge_action=rename: new objects will be created with a modified name
* --merge_action=replace: existing objects will be replaced by the new configuration

If you want to "reset" the destination organization, you can use the script "org_conf_zeroise.py".

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
                            
-m, --merge_action=     Action to perform when an object already exists in the
                        destination org: 
                        - skip: do not import the object
                        - replace: replace the existing object with the backup payload
                        - rename: create a new object with a modified name
                        default is "skip"  
                                         
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

    def __init__(
        self,
        create_mistapi_function: Callable,
        list_mistapi_function: Callable | None = None,
        update_mistapi_function: Callable | None = None,
        list_type_query_param: str | None = None,
        text: str = "",
        attr_name: str = "name",
    ):
        self.list_mistapi_function = list_mistapi_function
        self.list_type_query_param = list_type_query_param
        self.create_mistapi_function = create_mistapi_function
        self.update_mistapi_function = update_mistapi_function
        self.text = text
        self.attr_name = attr_name
        self.existing_objects = []

    def load_existing_objects(self, apisession, org_id):
        """
        Load existing objects from the destination organization.

        :param apisession: The Mist API session.
        :param org_id: The organization ID.
        """
        LOGGER.debug("Loading existing objects for step: %s", self.text)
        message = f"Loading existing objects for {self.text}..."
        PB.log_message(message, display_pbar=False)
        try:
            if self.list_mistapi_function and self.list_type_query_param:
                resp = self.list_mistapi_function(
                    apisession,
                    org_id,
                    type=self.list_type_query_param,
                    limit=1000,
                    page=1,
                )
                self.existing_objects = mistapi.get_all(apisession, resp)
            elif self.list_mistapi_function:
                resp = self.list_mistapi_function(
                    apisession, org_id, limit=1000, page=1
                )
                self.existing_objects = mistapi.get_all(apisession, resp)
            else:
                self.existing_objects = []
            PB.log_success(message, display_pbar=False, inc=False)
        except Exception as e:
            PB.log_failure(message, display_pbar=False, inc=False)
            LOGGER.error("Error loading existing objects for step %s: %s", self.text, e)
            self.existing_objects = []

    def search_existing_object(
        self, obj: dict, obj_name: str, action: str
    ):
        """
        Search for an existing object by name.

        :param obj: The object to search for.
        :param obj_name: The name of the object to search for.
        :param action: The action to take if the object exists ("skip", "replace", "rename").
        :return: A tuple (proceed: bool, obj: dict | None, existing_obj_id: str | None)
        """
        LOGGER.debug("Searching for existing object %s with name %s", self.text, obj_name)
        LOGGER.debug("merge action: %s", action)
        for existing_obj in self.existing_objects:
            if existing_obj.get(self.attr_name, "") == obj_name:
                if action == "skip":
                    LOGGER.debug(
                        "Object %s with name %s already exists, skipping...",
                        self.text,
                        obj_name,
                    )
                    UUID_MATCHING.add_uuid(existing_obj["id"], obj["id"])
                    return False, None, existing_obj["id"]
                elif action == "replace":
                    LOGGER.debug(
                        "Object %s with name %s already exists, replacing...",
                        self.text,
                        obj_name,
                    )
                    UUID_MATCHING.add_uuid(existing_obj["id"], obj["id"])
                    obj["id"] = existing_obj["id"]
                    return False, obj, existing_obj["id"]
                elif action == "rename":
                    new_name = f"{obj_name}_copy"
                    LOGGER.debug(
                        "Object %s with name %s already exists, renaming to %s...",
                        self.text,
                        obj_name,
                        new_name,
                    )
                    obj[self.attr_name] = new_name
                    return True, obj, existing_obj["id"]
        LOGGER.debug(
            "Object %s with name %s does not exist, proceeding...",
            self.text,
            obj_name,
        )
        return True, obj, None


ORG_STEPS = {
    "assetfilters": Step(
        list_mistapi_function=mistapi.api.v1.orgs.assetfilters.listOrgAssetFilters,
        create_mistapi_function=mistapi.api.v1.orgs.assetfilters.createOrgAssetFilter,
        update_mistapi_function=mistapi.api.v1.orgs.assetfilters.updateOrgAssetFilter,
        text="Org assetfilters",
    ),
    "deviceprofiles": Step(
        list_mistapi_function=mistapi.api.v1.orgs.deviceprofiles.listOrgDeviceProfiles,
        list_type_query_param="ap",
        create_mistapi_function=mistapi.api.v1.orgs.deviceprofiles.createOrgDeviceProfile,
        update_mistapi_function=mistapi.api.v1.orgs.deviceprofiles.updateOrgDeviceProfile,
        text="Org deviceprofiles",
    ),
    "switchprofiles": Step(
        list_mistapi_function=mistapi.api.v1.orgs.deviceprofiles.listOrgDeviceProfiles,
        list_type_query_param="switch",
        create_mistapi_function=mistapi.api.v1.orgs.deviceprofiles.createOrgDeviceProfile,
        update_mistapi_function=mistapi.api.v1.orgs.deviceprofiles.updateOrgDeviceProfile,
        text="Org switchprofiles",
    ),
    "hubprofiles": Step(
        list_mistapi_function=mistapi.api.v1.orgs.deviceprofiles.listOrgDeviceProfiles,
        list_type_query_param="gateway",
        create_mistapi_function=mistapi.api.v1.orgs.deviceprofiles.createOrgDeviceProfile,
        update_mistapi_function=mistapi.api.v1.orgs.deviceprofiles.updateOrgDeviceProfile,
        text="Org hubprofiles",
    ),
    "evpn_topologies": Step(
        list_mistapi_function=mistapi.api.v1.orgs.evpn_topologies.listOrgEvpnTopologies,
        create_mistapi_function=mistapi.api.v1.orgs.evpn_topologies.createOrgEvpnTopology,
        update_mistapi_function=mistapi.api.v1.orgs.evpn_topologies.updateOrgEvpnTopology,
        text="Org evpn_topologies",
    ),
    "secpolicies": Step(
        list_mistapi_function=mistapi.api.v1.orgs.secpolicies.listOrgSecPolicies,
        create_mistapi_function=mistapi.api.v1.orgs.secpolicies.createOrgSecPolicy,
        update_mistapi_function=mistapi.api.v1.orgs.secpolicies.updateOrgSecPolicy,
        text="Org secpolicies",
    ),
    "aptemplates": Step(
        list_mistapi_function=mistapi.api.v1.orgs.aptemplates.listOrgAptemplates,
        create_mistapi_function=mistapi.api.v1.orgs.aptemplates.createOrgAptemplate,
        update_mistapi_function=mistapi.api.v1.orgs.aptemplates.updateOrgAptemplate,
        text="Org aptemplates",
    ),
    "networktemplates": Step(
        list_mistapi_function=mistapi.api.v1.orgs.networktemplates.listOrgNetworkTemplates,
        create_mistapi_function=mistapi.api.v1.orgs.networktemplates.createOrgNetworkTemplate,
        update_mistapi_function=mistapi.api.v1.orgs.networktemplates.updateOrgNetworkTemplate,
        text="Org networktemplates",
    ),
    "networks": Step(
        list_mistapi_function=mistapi.api.v1.orgs.networks.listOrgNetworks,
        create_mistapi_function=mistapi.api.v1.orgs.networks.createOrgNetwork,
        update_mistapi_function=mistapi.api.v1.orgs.networks.updateOrgNetwork,
        text="Org networks",
    ),
    "services": Step(
        list_mistapi_function=mistapi.api.v1.orgs.services.listOrgServices,
        create_mistapi_function=mistapi.api.v1.orgs.services.createOrgService,
        update_mistapi_function=mistapi.api.v1.orgs.services.updateOrgService,
        text="Org services",
    ),
    "servicepolicies": Step(
        list_mistapi_function=mistapi.api.v1.orgs.servicepolicies.listOrgServicePolicies,
        create_mistapi_function=mistapi.api.v1.orgs.servicepolicies.createOrgServicePolicy,
        update_mistapi_function=mistapi.api.v1.orgs.servicepolicies.updateOrgServicePolicy,
        text="Org servicepolicies",
    ),
    "vpns": Step(
        list_mistapi_function=mistapi.api.v1.orgs.vpns.listOrgVpns,
        create_mistapi_function=mistapi.api.v1.orgs.vpns.createOrgVpn,
        update_mistapi_function=mistapi.api.v1.orgs.vpns.updateOrgVpn,
        text="Org vpns",
    ),
    "gatewaytemplates": Step(
        list_mistapi_function=mistapi.api.v1.orgs.gatewaytemplates.listOrgGatewayTemplates,
        create_mistapi_function=mistapi.api.v1.orgs.gatewaytemplates.createOrgGatewayTemplate,
        update_mistapi_function=mistapi.api.v1.orgs.gatewaytemplates.updateOrgGatewayTemplate,
        text="Org gatewaytemplates",
    ),
    "alarmtemplates": Step(
        list_mistapi_function=mistapi.api.v1.orgs.alarmtemplates.listOrgAlarmTemplates,
        create_mistapi_function=mistapi.api.v1.orgs.alarmtemplates.createOrgAlarmTemplate,
        update_mistapi_function=mistapi.api.v1.orgs.alarmtemplates.updateOrgAlarmTemplate,
        text="Org alarmtemplates",
    ),
    "rftemplates": Step(
        list_mistapi_function=mistapi.api.v1.orgs.rftemplates.listOrgRfTemplates,
        create_mistapi_function=mistapi.api.v1.orgs.rftemplates.createOrgRfTemplate,
        update_mistapi_function=mistapi.api.v1.orgs.rftemplates.updateOrgRfTemplate,
        text="Org rftemplates",
    ),
    "webhooks": Step(
        list_mistapi_function=mistapi.api.v1.orgs.webhooks.listOrgWebhooks,
        create_mistapi_function=mistapi.api.v1.orgs.webhooks.createOrgWebhook,
        update_mistapi_function=mistapi.api.v1.orgs.webhooks.updateOrgWebhook,
        text="Org webhooks",
    ),
    "mxclusters": Step(
        list_mistapi_function=mistapi.api.v1.orgs.mxclusters.listOrgMxEdgeClusters,
        create_mistapi_function=mistapi.api.v1.orgs.mxclusters.createOrgMxEdgeCluster,
        update_mistapi_function=mistapi.api.v1.orgs.mxclusters.updateOrgMxEdgeCluster,
        text="Org mxclusters",
    ),
    "mxtunnels": Step(
        list_mistapi_function=mistapi.api.v1.orgs.mxtunnels.listOrgMxTunnels,
        create_mistapi_function=mistapi.api.v1.orgs.mxtunnels.createOrgMxTunnel,
        update_mistapi_function=mistapi.api.v1.orgs.mxtunnels.updateOrgMxTunnel,
        text="Org mxtunnels",
    ),
    "wxtunnels": Step(
        list_mistapi_function=mistapi.api.v1.orgs.wxtunnels.listOrgWxTunnels,
        create_mistapi_function=mistapi.api.v1.orgs.wxtunnels.createOrgWxTunnel,
        update_mistapi_function=mistapi.api.v1.orgs.wxtunnels.updateOrgWxTunnel,
        text="Org wxtunnels",
    ),
    "sitetemplates": Step(
        list_mistapi_function=mistapi.api.v1.orgs.sitetemplates.listOrgSiteTemplates,
        create_mistapi_function=mistapi.api.v1.orgs.sitetemplates.createOrgSiteTemplate,
        update_mistapi_function=mistapi.api.v1.orgs.sitetemplates.updateOrgSiteTemplate,
        text="Org sitetemplates",
    ),
    "sitegroups": Step(
        list_mistapi_function=mistapi.api.v1.orgs.sitegroups.listOrgSiteGroups,
        create_mistapi_function=mistapi.api.v1.orgs.sitegroups.createOrgSiteGroup,
        update_mistapi_function=mistapi.api.v1.orgs.sitegroups.updateOrgSiteGroup,
        text="Org sitegroups",
    ),
    "sites": Step(
        list_mistapi_function=mistapi.api.v1.orgs.sites.listOrgSites,
        create_mistapi_function=mistapi.api.v1.orgs.sites.createOrgSite,
        update_mistapi_function=mistapi.api.v1.sites.sites.updateSiteInfo,
        text="Org Sites",
    ),
    "templates": Step(
        list_mistapi_function=mistapi.api.v1.orgs.templates.listOrgTemplates,
        create_mistapi_function=mistapi.api.v1.orgs.templates.createOrgTemplate,
        update_mistapi_function=mistapi.api.v1.orgs.templates.updateOrgTemplate,
        text="Org templates",
    ),
    "wlans": Step(
        list_mistapi_function=mistapi.api.v1.orgs.wlans.listOrgWlans,
        create_mistapi_function=mistapi.api.v1.orgs.wlans.createOrgWlan,
        update_mistapi_function=mistapi.api.v1.orgs.wlans.updateOrgWlan,
        text="Org wlans",
        attr_name = "ssid",
    ),
    "wxtags": Step(
        list_mistapi_function=mistapi.api.v1.orgs.wxtags.listOrgWxTags,
        create_mistapi_function=mistapi.api.v1.orgs.wxtags.createOrgWxTag,
        update_mistapi_function=mistapi.api.v1.orgs.wxtags.updateOrgWxTag,
        text="Org wxtags",
    ),
    "wxrules": Step(
        list_mistapi_function=mistapi.api.v1.orgs.wxrules.listOrgWxRules,
        create_mistapi_function=mistapi.api.v1.orgs.wxrules.createOrgWxRule,
        update_mistapi_function=mistapi.api.v1.orgs.wxrules.updateOrgWxRule,
        text="Org wxrules",
        attr_name = "order",
    ),
    "pskportals": Step(
        list_mistapi_function=mistapi.api.v1.orgs.pskportals.listOrgPskPortals,
        create_mistapi_function=mistapi.api.v1.orgs.pskportals.createOrgPskPortal,
        update_mistapi_function=mistapi.api.v1.orgs.pskportals.updateOrgPskPortal,
        text="Org pskportals",
    ),
    "psks": Step(
        list_mistapi_function=mistapi.api.v1.orgs.psks.listOrgPsks,
        create_mistapi_function=mistapi.api.v1.orgs.psks.importOrgPsks,
        text="Org psks",
    ),
    "nacportals": Step(
        list_mistapi_function=mistapi.api.v1.orgs.nacportals.listOrgNacPortals,
        create_mistapi_function=mistapi.api.v1.orgs.nacportals.createOrgNacPortal,
        update_mistapi_function=mistapi.api.v1.orgs.nacportals.updateOrgNacPortal,
        text="Org nacportals",
    ),
    "nactags": Step(
        list_mistapi_function=mistapi.api.v1.orgs.nactags.listOrgNacTags,
        create_mistapi_function=mistapi.api.v1.orgs.nactags.createOrgNacTag,
        update_mistapi_function=mistapi.api.v1.orgs.nactags.updateOrgNacTag,
        text="Org nactags",
    ),
    "nacrules": Step(
        list_mistapi_function=mistapi.api.v1.orgs.nacrules.listOrgNacRules,
        create_mistapi_function=mistapi.api.v1.orgs.nacrules.createOrgNacRule,
        update_mistapi_function=mistapi.api.v1.orgs.nacrules.updateOrgNacRule,
        text="Org nacrules",
    ),
    "usermacs": Step(
        list_mistapi_function=mistapi.api.v1.orgs.usermacs.searchOrgUserMacs,
        create_mistapi_function=mistapi.api.v1.orgs.usermacs.importOrgUserMacs,
        text="Org nacendpoints",
    ),
    "ssos": Step(
        list_mistapi_function=mistapi.api.v1.orgs.ssos.listOrgSsos,
        create_mistapi_function=mistapi.api.v1.orgs.ssos.createOrgSso,
        update_mistapi_function=mistapi.api.v1.orgs.ssos.updateOrgSso,
        text="Org ssos",
    ),
    "ssoroles": Step(
        list_mistapi_function=mistapi.api.v1.orgs.ssoroles.listOrgSsoRoles,
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
        list_mistapi_function=mistapi.api.v1.sites.maps.listSiteMaps,
        create_mistapi_function=mistapi.api.v1.sites.maps.createSiteMap,
        update_mistapi_function=mistapi.api.v1.sites.maps.updateSiteMap,
        text="Site maps",
    ),
    "zones": Step(
        list_mistapi_function=mistapi.api.v1.sites.zones.listSiteZones,
        create_mistapi_function=mistapi.api.v1.sites.zones.createSiteZone,
        update_mistapi_function=mistapi.api.v1.sites.zones.updateSiteZone,
        text="Site zones",
    ),
    "rssizones": Step(
        list_mistapi_function=mistapi.api.v1.sites.rssizones.listSiteRssiZones,
        create_mistapi_function=mistapi.api.v1.sites.rssizones.createSiteRssiZone,
        update_mistapi_function=mistapi.api.v1.sites.rssizones.updateSiteRssiZone,
        text="Site rssizones",
    ),
    "assets": Step(
        list_mistapi_function=mistapi.api.v1.sites.assets.listSiteAssets,
        create_mistapi_function=mistapi.api.v1.sites.assets.createSiteAsset,
        update_mistapi_function=mistapi.api.v1.sites.assets.updateSiteAsset,
        text="Site assets",
    ),
    "assetfilters": Step(
        list_mistapi_function=mistapi.api.v1.sites.assetfilters.listSiteAssetFilters,
        create_mistapi_function=mistapi.api.v1.sites.assetfilters.createSiteAssetFilter,
        update_mistapi_function=mistapi.api.v1.sites.assetfilters.updateSiteAssetFilter,
        text="Site assetfilters",
    ),
    "beacons": Step(
        list_mistapi_function=mistapi.api.v1.sites.beacons.listSiteBeacons,
        create_mistapi_function=mistapi.api.v1.sites.beacons.createSiteBeacon,
        update_mistapi_function=mistapi.api.v1.sites.beacons.updateSiteBeacon,
        text="Site beacons",
    ),
    "psks": Step(
        list_mistapi_function=mistapi.api.v1.sites.psks.listSitePsks,
        create_mistapi_function=mistapi.api.v1.sites.psks.importSitePsks,
        update_mistapi_function=mistapi.api.v1.sites.psks.updateSitePsk,
        text="Site psks",
    ),
    "vbeacons": Step(
        list_mistapi_function=mistapi.api.v1.sites.vbeacons.listSiteVBeacons,
        create_mistapi_function=mistapi.api.v1.sites.vbeacons.createSiteVBeacon,
        update_mistapi_function=mistapi.api.v1.sites.vbeacons.updateSiteVBeacon,
        text="Site vbeacons",
    ),
    "evpn_topologies": Step(
        list_mistapi_function=mistapi.api.v1.sites.evpn_topologies.listSiteEvpnTopologies,
        create_mistapi_function=mistapi.api.v1.sites.evpn_topologies.createSiteEvpnTopology,
        update_mistapi_function=mistapi.api.v1.sites.evpn_topologies.updateSiteEvpnTopology,
        text="Site EVPN Topologies",
    ),
    "webhooks": Step(
        list_mistapi_function=mistapi.api.v1.sites.webhooks.listSiteWebhooks,
        create_mistapi_function=mistapi.api.v1.sites.webhooks.createSiteWebhook,
        update_mistapi_function=mistapi.api.v1.sites.webhooks.updateSiteWebhook,
        text="Site webhooks",
    ),
    "wxtunnels": Step(
        list_mistapi_function=mistapi.api.v1.sites.wxtunnels.listSiteWxTunnels,
        create_mistapi_function=mistapi.api.v1.sites.wxtunnels.createSiteWxTunnel,
        update_mistapi_function=mistapi.api.v1.sites.wxtunnels.updateSiteWxTunnel,
        text="Site wxtunnels",
    ),
    "wlans": Step(
        list_mistapi_function=mistapi.api.v1.sites.wlans.listSiteWlans,
        create_mistapi_function=mistapi.api.v1.sites.wlans.createSiteWlan,
        update_mistapi_function=mistapi.api.v1.sites.wlans.updateSiteWlan,
        text="Site wlans",
        attr_name = "ssid",
    ),
    "wxtags": Step(
        list_mistapi_function=mistapi.api.v1.sites.wxtags.listSiteWxTags,
        create_mistapi_function=mistapi.api.v1.sites.wxtags.createSiteWxTag,
        update_mistapi_function=mistapi.api.v1.sites.wxtags.updateSiteWxTag,
        text="Site wxtags",
    ),
    "wxrules": Step(
        list_mistapi_function=mistapi.api.v1.sites.wxrules.listSiteWxRules,
        create_mistapi_function=mistapi.api.v1.sites.wxrules.createSiteWxRule,
        update_mistapi_function=mistapi.api.v1.sites.wxrules.updateSiteWxRule,
        text="Site wxrules",
        attr_name = "order",
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
        mist_step: Step,
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
                "mist_step": mist_step,
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
def _common_process(
    apisession: mistapi.APISession,
    scope_id: str,
    data: list,
    step: Step,
    step_name: str,
    merge: bool,
    merge_action: str,
):
    LOGGER.debug("conf_deploy:_common_process: step_name %s, merge action: %s", step_name, merge_action)
    if merge:
        step.load_existing_objects(apisession, scope_id)
    for step_data in data:
        create, object_to_deploy, _ = step.search_existing_object(
            step_data, step_data[step.attr_name], merge_action
        )
        if object_to_deploy and create:
            _common_deploy(
                apisession,
                step,
                scope_id,
                step_name,
                object_to_deploy,
            )
        elif object_to_deploy:
            _common_update(
                apisession,
                step,
                scope_id,
                object_to_deploy["id"],
                step_name,
                object_to_deploy,
            )
        else:
            PB.steps_count += 1


def _common_deploy(
    apisession: mistapi.APISession,
    mist_step: Step,
    scope_id: str,
    object_type: str,
    data: dict,
    retry: bool = False,
) -> str:
    LOGGER.debug("conf_deploy:_common_deploy")
    if SYS_EXIT:
        sys.exit(0)
    if not mist_step.create_mistapi_function:
        LOGGER.error(
            "conf_deploy:_common_deploy: No create function provided for object type %s",
            object_type,
        )
        return ""

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
        response = mist_step.create_mistapi_function(apisession, scope_id, data)
        if response.status_code == 200:
            new_id = response.data.get("id")
            if not missing_uuids:
                PB.log_success(message, inc=True)
            elif not retry:
                UUID_MATCHING.add_replay(
                    mist_step,
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
    mist_step: Step,
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
        if mist_step.update_mistapi_function is None:
            LOGGER.error(
                "conf_deploy:_common_update: No update function provided for object type %s",
                object_type,
            )
            return None
        response = mist_step.update_mistapi_function(
            apisession, scope_id, object_id, data
        )
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
def _bulk_import_process(
    apisession: mistapi.APISession,
    scope_id: str,
    step_name: str,
    step_data: dict,
    step: Step,
) -> None:
    if step_name == "psks" and step_data:
        _import_psks(apisession, step.create_mistapi_function, scope_id, step_data)
    elif step_name == "usermacs" and step_data:
        _import_usermacs(apisession, step.create_mistapi_function, scope_id, step_data)


def _import_psks(
    apisession: mistapi.APISession,
    mistapi_function: Callable | None,
    scope_id: str,
    data: dict,
) -> None:
    LOGGER.debug("conf_deploy:_import_psks")
    if SYS_EXIT:
        sys.exit(0)
    if not mistapi_function:
        LOGGER.error("conf_deploy:_import_psks: No import function provided for PSKs")
        return None

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
    mistapi_function: Callable | None,
    scope_id: str,
    data: dict,
) -> None:
    LOGGER.debug("conf_deploy:_import_usermacs")
    if SYS_EXIT:
        sys.exit(0)
    if not mistapi_function:
        LOGGER.error(
            "conf_deploy:_import_usermacs: No import function provided for User Macs"
        )
        return None

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
def _wlan_process(
    apisession: mistapi.APISession,
    scope_id: str,
    old_scope_id: str,
    data: list,
    step: Step,
    merge: bool,
    merge_action: str,
):
    if merge:
        step.load_existing_objects(apisession, scope_id)
    for step_data in data:
        create, object_to_deploy, _ = step.search_existing_object(
            step_data, step_data["ssid"], merge_action
        )
        if object_to_deploy and create:
            _deploy_wlan(
                apisession,
                step,
                scope_id,
                object_to_deploy,
                old_scope_id,
            )
        elif object_to_deploy:
            _update_wlan(
                apisession,
                step,
                scope_id,
                object_to_deploy,
                old_scope_id,
            )
        else:
            PB.steps_count += 1


def _deploy_wlan(
    apisession: mistapi.APISession,
    mist_step: Step,
    scope_id: str,
    data: dict,
    old_org_id: str,
    old_site_id: str = "",
) -> None:
    LOGGER.debug("conf_deploy:_deploy_wlan")
    if SYS_EXIT:
        sys.exit(0)
    if not mist_step.create_mistapi_function:
        LOGGER.error("conf_deploy:_deploy_wlan: No create function provided for WLANs")
        return None

    old_wlan_id = data["id"]
    new_wlan_id = _common_deploy(
        apisession,
        mist_step,
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


def _update_wlan(
    apisession: mistapi.APISession,
    mist_step: Step,
    scope_id: str,
    data: dict,
    old_org_id: str,
    old_site_id: str = "",
) -> None:
    LOGGER.debug("conf_deploy:_deploy_wlan")
    if SYS_EXIT:
        sys.exit(0)
    if not mist_step.create_mistapi_function:
        LOGGER.error("conf_deploy:_deploy_wlan: No create function provided for WLANs")
        return None

    old_wlan_id = data["id"]
    new_wlan_id = _common_update(
        apisession,
        mist_step,
        scope_id,
        old_wlan_id,
        "wlans",
        data,
    )

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
            template = open(portal_file_name, "r", encoding="utf-8")
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
        SITE_STEPS["maps"],
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
    merge: bool,
    merge_action: str,
) -> None:
    LOGGER.debug("conf_deploy:_deploy_site - merge action: %s", merge_action)
    if SYS_EXIT:
        sys.exit(0)

    PB.log_title(f" Deploying Site {site_info['name']} ".center(80, "_"))
    create, object_to_deploy, new_site_id = ORG_STEPS["sites"].search_existing_object(
        site_info, site_info["name"], merge_action
    )
    LOGGER.debug(
        "conf_deploy:_deploy_site: create=%s, object_to_deploy=%s, new_site_id=%s",
        create,
        object_to_deploy,
        new_site_id,
    )

    old_site_id = site_info["id"]
    update_site_settings = False

    if object_to_deploy and create:
        update_site_settings = True
        new_site_id = _common_deploy(
            apisession,
            ORG_STEPS["sites"],
            org_id,
            "sites",
            site_info,
        )
    elif object_to_deploy:
        new_site_id = _common_update(
            apisession,
            ORG_STEPS["sites"],
            org_id,
            object_to_deploy["id"],
            "sites",
            site_info,
        )

    if not new_site_id:
        LOGGER.error(
            "conf_deploy:_deploy_site: Unable to create or update site %s",
            site_info["name"],
        )
        return

    site_data = sites_backup.get(old_site_id, {})
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
                if update_site_settings:
                    step_data = site_data.get(step_name, {})
                    _common_deploy(
                        apisession,
                        step,
                        new_site_id,
                        step_name,
                        step_data,
                    )
            elif step_name in ["psks"]:
                step_data = site_data.get(step_name)
                _bulk_import_process(
                    apisession,
                    new_site_id,
                    step_name,
                    step_data,
                    step,
                )
            elif step_name == "maps":
                if merge:
                    step.load_existing_objects(apisession, new_site_id)
                for step_data in site_data.get(step_name, []):
                    create, object_to_deploy, _ = step.search_existing_object(
                        step_data, step_data[step.attr_name], merge_action
                    )
                    if object_to_deploy and create:
                        _deploy_site_maps(
                            apisession, old_org_id, old_site_id, new_site_id, step_data
                        )
            elif step_name == "wlans":
                _wlan_process(
                    apisession,
                    new_site_id,
                    old_site_id,
                    site_data.get(step_name, []),
                    step,
                    merge,
                    merge_action,
                )
            else:
                _common_process(
                    apisession,
                    new_site_id,
                    site_data.get(step_name, []),
                    step,
                    step_name,
                    merge,
                    merge_action,
                )


##########################################################################################
#  ORG FUNCTIONS
def _deploy_org(
    apisession: mistapi.APISession,
    org_id: str,
    org_name: str,
    backup: dict,
    merge: bool,
    merge_action: str,
) -> None:
    LOGGER.debug("conf_deploy:_deploy_org - merge action: %s", merge_action)
    PB.log_title(f"Deploying Org {org_name}")

    ####################
    ####  ORG MAIN  ####
    org_backup = backup["org"]
    sites_backup = backup["sites"]

    org_data = org_backup["data"]
    old_org_id = org_data["id"]
    UUID_MATCHING.add_uuid(org_id, old_org_id)

    if not merge:
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
            mistapi.api.v1.orgs.setting.updateOrgSettings(
                apisession, org_id, org_settings
            )
            PB.log_success(message, inc=True)
        except Exception:
            PB.log_failure(message, inc=True)
            LOGGER.error("Exception occurred", exc_info=True)

    #######################
    ####  ORG OBJECTS  ####
    PB.log_title("Deploying Common Org Objects")
    for step_name, step in ORG_STEPS.items():
        if step_name in org_backup:
            if step_name in ["psks", "usermacs"]:
                step_data = org_backup.get(step_name)
                _bulk_import_process(
                    apisession,
                    org_id,
                    step_name,
                    step_data,
                    step,
                )

            elif step_name == "sites":
                if merge:
                    step.load_existing_objects(apisession, org_id)
                for step_data in org_backup[step_name]:
                    _deploy_site(
                        apisession,
                        org_id,
                        old_org_id,
                        step_data,
                        sites_backup,
                        merge,
                        merge_action,
                    )
                    PB.log_title(" Deploying Other Org Objects ".center(80, "_"))

            elif step_name == "wlans":
                _wlan_process(
                    apisession,
                    org_id,
                    old_org_id,
                    org_backup[step_name],
                    step,
                    merge,
                    merge_action,
                )
            else:
                _common_process(
                    apisession,
                    org_id,
                    org_backup[step_name],
                    step,
                    step_name,
                    merge,
                    merge_action,
                )

    PB.log_title("Retrying missing objects")
    for replay in UUID_MATCHING.get_replay():
        if replay.get("object_id"):
            _common_update(
                apisession,
                replay["mist_step"],
                replay["scope_id"],
                replay["object_id"],
                replay["object_type"],
                replay["data"],
            )
        else:
            _common_deploy(
                apisession,
                replay["mist_step"],
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
    merge: bool,
    merge_action: str,
    src_org_name: str = "",
    source_backup: str = "",
) -> None:
    LOGGER.debug("conf_deploy:_start_deploy_org")
    _go_to_backup_folder(backup_folder, src_org_name, source_backup)
    print()
    try:
        message = f"Loading template/backup file {BACKUP_FILE} "
        PB.log_message(message, display_pbar=False)
        with open(BACKUP_FILE, "r", encoding="utf-8") as f:
            backup = json.load(f)
        PB.log_success(message, display_pbar=False)
    except Exception:
        PB.log_failure(message, display_pbar=False)
        console.critical("Unable to load the template/backup")
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
        _deploy_org(apisession, org_id, org_name, backup, merge, merge_action)


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
            "To avoid any error, please confirm the current destination organization name: "
        )
        if resp == org_name:
            return org_id, org_name
        else:
            print()
            print("The organization names do not match... Please try again...")


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
                return True, org_id, org_name
        elif res.lower() == "n":
            return False, *_create_org(apisession)


#####################################################################
#### START ####
def start(
    apisession: mistapi.APISession,
    org_id: str = "",
    org_name: str = "",
    backup_folder_param: str = "",
    src_org_name: str = "",
    source_backup: str = "",
    merge_action: str = "skip",
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
    merge = True
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
        merge = False
    elif not org_id and not org_name:
        merge, org_id, org_name = _select_dest_org(apisession)
    else:  # should not since we covered all the possibilities...
        sys.exit(0)

    _start_deploy_org(
        apisession, org_id, org_name, backup_folder_param, merge, merge_action, src_org_name, source_backup
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

This script will not override existing objects by default but this behavior can be
changed with the parameter "--merge_action":
* --merge_action=skip (default): existing objects will be skipped
* --merge_action=rename: new objects will be created with a modified name
* --merge_action=replace: existing objects will be replaced by the new configuration

If you want to "reset" the destination organization, you can use the script "org_conf_zeroise.py".

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
                            
-m, --merge_action=     Action to perform when an object already exists in the
                        destination org: 
                        - skip: do not import the object
                        - replace: replace the existing object with the backup payload
                        - rename: create a new object with a modified name
                        default is "skip"  
                                                  
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
    parser.add_argument(
        "-k",
        "--keyring_service",
        help="Keyring service name to retrieve the Mist API cloud and API token or username/password",
        default=None,
    )
    parser.add_argument(
        "-m", "--merge_action",
        help="Action to perform when an object already exists in the destination org: skip, replace, rename",
        default="skip",
        choices=["skip", "replace", "rename"],
    )

    args = parser.parse_args()

    ORG_ID = args.org_id
    ORG_NAME = args.org_name
    BACKUP_FOLDER_PARAM = args.backup_folder
    SOURCE_BACKUP = args.source_backup
    ENV_FILE = args.env
    LOG_FILE = args.log_file
    KEYRING_SERVICE = args.keyring_service
    MERGE_ACTION = args.merge_action
    if KEYRING_SERVICE:
        ENV_FILE = None

    #### LOGS ####
    logging.basicConfig(filename=LOG_FILE, filemode="w")
    LOGGER.setLevel(logging.DEBUG)
    check_mistapi_version()
    ### START ###
    APISESSION = mistapi.APISession(env_file=ENV_FILE, keyring_service=KEYRING_SERVICE)
    APISESSION.login()
    LOGGER.info("Logged in to Mist Cloud %s", APISESSION.get_cloud())
    LOGGER.info("Using env file: %s", ENV_FILE if ENV_FILE else "keyring")
    LOGGER.info("Log file: %s", LOG_FILE)
    LOGGER.info("Backup folder: %s", BACKUP_FOLDER_PARAM)
    LOGGER.info("Source backup: %s", SOURCE_BACKUP if SOURCE_BACKUP else "ask user")
    LOGGER.info("Destination Org ID: %s", ORG_ID if ORG_ID else "ask user")
    LOGGER.info("Destination Org Name: %s", ORG_NAME if ORG_NAME else "ask user")
    LOGGER.info("Merge action: %s", MERGE_ACTION)
    start(
        APISESSION, ORG_ID, ORG_NAME, BACKUP_FOLDER_PARAM, SOURCE_BACKUP, merge_action=MERGE_ACTION
    )

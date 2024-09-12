"""
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
            __          __     _____  _   _ _____ _   _  _____ 
            \ \        / /\   |  __ \| \ | |_   _| \ | |/ ____|
             \ \  /\  / /  \  | |__) |  \| | | | |  \| | |  __ 
              \ \/  \/ / /\ \ |  _  /| . ` | | | | . ` | | |_ |
               \  /\  / ____ \| | \ \| |\  |_| |_| |\  | |__| |
                \/  \/_/    \_\_|  \_\_| \_|_____|_| \_|\_____|
            THIS SCRIPT IS DESIGNED TO REMOVE ALL THE OBJECT IN 
              A SPECIFIC ORGANIZATION! THESE CHANGES CAN'T BE 
               REVERT BACK. USE THIS SCRIPT AS YOUR OWN RISK


Python script to zeroise an organization. This scrip will remove all the 
configuration, all the sites and all the objects from the organization.
                    
Use it with extreme precaution, there is no way to revert the action if
you didn't backed up the organization.

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
-n, --org_name=         Org name to reset, for validation
-l, --log_file=         define the filepath/filename where to write the logs
                        default is "./script.log"
-e, --env=              define the env file to use (see mistapi env file documentation 
                        here: https://pypi.org/project/mistapi/)
                        default is "~/.mist_env"

-------
Examples:
python3 ./org_conf_zeroise.py     
python3 ./org_conf_zeroise.py --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 -n my_test_org

"""

#####################################################################
#### IMPORTS ####
import sys
import getopt
import logging

MISTAPI_MIN_VERSION = "0.44.1"

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
ids_to_not_delete = []
log_file = "./script.log"
env_file = "~/.mist_env"

#####################################################################
#### LOGS ####
logger = logging.getLogger(__name__)

#####################################################################
#### GLOBAL VARS ####

get_org_steps = {
    "sites": {
        "mistapi_function": mistapi.api.v1.orgs.sites.listOrgSites,
        "text": "Org Sites",
        "check_next": True,
    },
    "webhooks": {
        "mistapi_function": mistapi.api.v1.orgs.webhooks.listOrgWebhooks,
        "text": "Org webhooks",
        "check_next": True,
    },
    "assetfilters": {
        "mistapi_function": mistapi.api.v1.orgs.assetfilters.listOrgAssetFilters,
        "text": "Org assetfilters",
        "check_next": True,
    },
    "alarmtemplates": {
        "mistapi_function": mistapi.api.v1.orgs.alarmtemplates.listOrgAlarmTemplates,
        "text": "Org alarmtemplates",
        "check_next": True,
    },
    "deviceprofiles": {
        "mistapi_function": mistapi.api.v1.orgs.deviceprofiles.listOrgDeviceProfiles,
        "text": "Org deviceprofiles",
        "check_next": True,
    },
    "hubprofiles": {
        "mistapi_function": mistapi.api.v1.orgs.deviceprofiles.listOrgDeviceProfiles,
        "text": "Org hubprofiles",
        "request_type": "gateway",
        "check_next": True,
    },
    "mxclusters": {
        "mistapi_function": mistapi.api.v1.orgs.mxclusters.listOrgMxEdgeClusters,
        "text": "Org mxclusters",
        "check_next": True,
    },
    "mxtunnels": {
        "mistapi_function": mistapi.api.v1.orgs.mxtunnels.listOrgMxTunnels,
        "text": "Org mxtunnels",
        "check_next": True,
    },
    "psks": {
        "mistapi_function": mistapi.api.v1.orgs.psks.listOrgPsks,
        "text": "Org psks",
        "check_next": True,
    },
    "pskportals": {
        "mistapi_function": mistapi.api.v1.orgs.pskportals.listOrgPskPortals,
        "text": "Org pskportals",
        "check_next": True,
    },
    "rftemplates": {
        "mistapi_function": mistapi.api.v1.orgs.rftemplates.listOrgRfTemplates,
        "text": "Org rftemplates",
        "check_next": True,
    },
    "networktemplates": {
        "mistapi_function": mistapi.api.v1.orgs.networktemplates.listOrgNetworkTemplates,
        "text": "Org networktemplates",
        "check_next": True,
    },
    "evpn_topologies": {
        "mistapi_function": mistapi.api.v1.orgs.evpn_topologies.listOrgEvpnTopologies,
        "text": "Org evpn_topologies",
        "check_next": True,
    },
    "services": {
        "mistapi_function": mistapi.api.v1.orgs.services.listOrgServices,
        "text": "Org services",
        "check_next": True,
    },
    "servicepolicies": {
        "mistapi_function": mistapi.api.v1.orgs.servicepolicies.listOrgServicePolicies,
        "text": "Org servicepolicies",
        "check_next": True,
    },
    "networks": {
        "mistapi_function": mistapi.api.v1.orgs.networks.listOrgNetworks,
        "text": "Org networks",
        "check_next": True,
    },
    "gatewaytemplates": {
        "mistapi_function": mistapi.api.v1.orgs.gatewaytemplates.listOrgGatewayTemplates,
        "text": "Org gatewaytemplates",
        "check_next": True,
    },
    "vpns": {
        "mistapi_function": mistapi.api.v1.orgs.vpns.listOrgsVpns,
        "text": "Org vpns",
        "check_next": True,
    },
    "secpolicies": {
        "mistapi_function": mistapi.api.v1.orgs.secpolicies.listOrgSecPolicies,
        "text": "Org secpolicies",
        "check_next": True,
    },
    "sitegroups": {
        "mistapi_function": mistapi.api.v1.orgs.sitegroups.listOrgSiteGroups,
        "text": "Org sitegroups",
        "check_next": True,
    },
    "sitetemplates": {
        "mistapi_function": mistapi.api.v1.orgs.sitetemplates.listOrgSiteTemplates,
        "text": "Org sitetemplates",
        "check_next": True,
    },
    "ssos": {
        "mistapi_function": mistapi.api.v1.orgs.ssos.listOrgSsos,
        "text": "Org ssos",
        "check_next": True,
    },
    "ssoroles": {
        "mistapi_function": mistapi.api.v1.orgs.ssoroles.listOrgSsoRoles,
        "text": "Org ssoroles",
        "check_next": True,
    },
    "templates": {
        "mistapi_function": mistapi.api.v1.orgs.templates.listOrgTemplates,
        "text": "Org templates",
        "check_next": True,
    },
    "wxrules": {
        "mistapi_function": mistapi.api.v1.orgs.wxrules.listOrgWxRules,
        "text": "Org wxrules",
        "check_next": True,
    },
    "wxtags": {
        "mistapi_function": mistapi.api.v1.orgs.wxtags.listOrgWxTags,
        "text": "Org wxtags",
        "check_next": True,
    },
    "wxtunnels": {
        "mistapi_function": mistapi.api.v1.orgs.wxtunnels.listOrgWxTunnels,
        "text": "Org wxtunnels",
        "check_next": True,
    },
    "nactags": {
        "mistapi_function": mistapi.api.v1.orgs.nactags.listOrgNacTags,
        "text": "Org nactags",
        "check_next": True,
    },
    "nacrules": {
        "mistapi_function": mistapi.api.v1.orgs.nacrules.listOrgNacRules,
        "text": "Org nacrules",
        "check_next": True,
    },
    "wlans": {
        "mistapi_function": mistapi.api.v1.orgs.wlans.listOrgWlans,
        "text": "Org wlans",
        "check_next": True,
    },
}
delete_steps = {
    "assetfilters": {
        "mistapi_function": mistapi.api.v1.orgs.assetfilters.deleteOrgAssetFilter,
        "text": "Org assetfilters",
    },
    "deviceprofiles": {
        "mistapi_function": mistapi.api.v1.orgs.deviceprofiles.deleteOrgDeviceProfile,
        "text": "Org deviceprofiles",
    },
    "hubprofiles": {
        "mistapi_function": mistapi.api.v1.orgs.deviceprofiles.deleteOrgDeviceProfile,
        "text": "Org hubprofiles",
    },
    "evpn_topologies": {
        "mistapi_function": mistapi.api.v1.orgs.evpn_topologies.deleteOrgEvpnTopology,
        "text": "Org evpn_topologies",
    },
    "secpolicies": {
        "mistapi_function": mistapi.api.v1.orgs.secpolicies.deleteOrgSecPolicy,
        "text": "Org secpolicies",
    },
    "aptempaltes": {
        "mistapi_function": mistapi.api.v1.orgs.aptemplates.deleteOrgAptemplate,
        "text": "Org aptemplates",
    },
    "networktemplates": {
        "mistapi_function": mistapi.api.v1.orgs.networktemplates.deleteOrgNetworkTemplate,
        "text": "Org networktemplates",
    },
    "gatewaytemplates": {
        "mistapi_function": mistapi.api.v1.orgs.gatewaytemplates.deleteOrgGatewayTemplate,
        "text": "Org gatewaytemplates",
    },
    "alarmtemplates": {
        "mistapi_function": mistapi.api.v1.orgs.alarmtemplates.deleteOrgAlarmTemplate,
        "text": "Org alarmtemplates",
    },
    "rftemplates": {
        "mistapi_function": mistapi.api.v1.orgs.rftemplates.deleteOrgRfTemplate,
        "text": "Org rftemplates",
    },
    "sitetemplates": {
        "mistapi_function": mistapi.api.v1.orgs.sitetemplates.deleteOrgSiteTemplate,
        "text": "Org sitetemplates",
    },
    "sitegroups": {
        "mistapi_function": mistapi.api.v1.orgs.sitegroups.deleteOrgSiteGroup,
        "text": "Org sitegroups",
    },
    "templates": {
        "mistapi_function": mistapi.api.v1.orgs.templates.deleteOrgTemplate,
        "text": "Org templates",
    },
    "webhooks": {
        "mistapi_function": mistapi.api.v1.orgs.webhooks.deleteOrgWebhook,
        "text": "Org webhooks",
    },
    "networks": {
        "mistapi_function": mistapi.api.v1.orgs.networks.deleteOrgNetwork,
        "text": "Org networks",
    },
    "services": {
        "mistapi_function": mistapi.api.v1.orgs.services.deleteOrgService,
        "text": "Org services",
    },
    "servicepolicies": {
        "mistapi_function": mistapi.api.v1.orgs.servicepolicies.deleteOrgServicePolicy,
        "text": "Org services",
    },
    "vpns": {
        "mistapi_function": mistapi.api.v1.orgs.vpns.deleteOrgVpn,
        "text": "Org vpns",
    },
    "wlans": {
        "mistapi_function": mistapi.api.v1.orgs.wlans.deleteOrgWlan,
        "text": "Org wlans",
    },
    "wxtags": {
        "mistapi_function": mistapi.api.v1.orgs.wxtags.deleteOrgWxTag,
        "text": "Org wxtags",
    },
    "wxrules": {
        "mistapi_function": mistapi.api.v1.orgs.wxrules.deleteOrgWxRule,
        "text": "Org wxrules",
    },
    "mxclusters": {
        "mistapi_function": mistapi.api.v1.orgs.mxclusters.deleteOrgMxEdgeCluster,
        "text": "Org mxclusters",
    },
    "mxtunnels": {
        "mistapi_function": mistapi.api.v1.orgs.mxtunnels.deleteOrgMxTunnel,
        "text": "Org mxtunnels",
    },
    "wxtunnels": {
        "mistapi_function": mistapi.api.v1.orgs.wxtunnels.deleteOrgWxTunnel,
        "text": "Org wxtunnels",
    },
    "psks": {
        "mistapi_function": mistapi.api.v1.orgs.psks.deleteOrgPsk,
        "text": "Org psks",
    },
    "pskportals": {
        "mistapi_function": mistapi.api.v1.orgs.pskportals.deleteOrgPskPortal,
        "text": "Org pskportals",
    },
    "nactags": {
        "mistapi_function": mistapi.api.v1.orgs.nactags.deleteOrgNacTag,
        "text": "Org nactags",
    },
    "nacrules": {
        "mistapi_function": mistapi.api.v1.orgs.nacrules.deleteOrgNacRule,
        "text": "Org nacrules",
    },
    "ssos": {
        "mistapi_function": mistapi.api.v1.orgs.ssos.deleteOrgSso,
        "text": "Org ssos",
    },
    "ssoroles": {
        "mistapi_function": mistapi.api.v1.orgs.ssoroles.deleteOrgSsoRole,
        "text": "Org ssoroles",
    },
}


##########################################################################################
#### FUNCTIONS ####
def log_message(message):
    print(f"{message}".ljust(79, "."), end="", flush=True)


def log_debug(message):
    logger.debug(f"{message}")


def log_error(message):
    logger.error(f"{message}")


def log_success(message):
    print("\033[92m\u2714\033[0m")
    logger.info(f"{message}: Success")


def log_failure(message):
    print("\033[31m\u2716\033[0m")
    logger.exception(f"{message}: Failure")


def display_warning(message, expected_response: str = "y"):
    resp = "x"
    print()
    resp = input(message)
    if not resp.lower() == expected_response.lower():
        console.warning("User Interruption... Exiting...")
        sys.exit(0)


##########################################################################################
# COMMON FUNCTIONS
def start_delete(apisession, org_id):
    for step_name in get_org_steps:
        step = get_org_steps[step_name]
        response = step["mistapi_function"](apisession, org_id)
        if step["check_next"]:
            data = mistapi.get_all(apisession, response)
        else:
            data = response.data
        for entry in data:
            if not entry["id"] in ids_to_not_delete:
                try:
                    message = f"Deleting {step_name} with ID {entry['id']} "
                    log_message(message)
                    if step_name == "sites":
                        mistapi.api.v1.sites.sites.deleteSite(apisession, entry["id"])
                    else:
                        delete_steps[step_name]["mistapi_function"](
                            apisession, org_id, entry["id"]
                        )
                    log_success(message)
                except:
                    log_failure(message)


def create_primary_site(apisession, org_id):
    primary_site = {
        "name": "Primary Site",
    }
    primary_site = mistapi.api.v1.orgs.sites.createOrgSite(
        apisession, org_id, primary_site
    ).data
    ids_to_not_delete.append(primary_site["id"])


##########################################################################################
# SCRIPT FUNCTIONS
def check_org_name(org_name):
    while True:
        print()
        resp = input(
            "To avoid any error, please confirm the orgnization name you want to reset: "
        )
        if resp == org_name:
            return True
        else:
            console.warning("The orgnization names do not match... Please try again...")


def start(apisession, org_id, org_name_from_user):
    if not org_id:
        org_id = mistapi.cli.select_org(apisession)[0]
    org_name_from_mist = mistapi.api.v1.orgs.orgs.getOrg(apisession, org_id).data[
        "name"
    ]

    if org_name_from_mist == org_name_from_user:
        console.info("Org name validated from script parameters")
    else:
        check_org_name(org_name_from_mist)
    display_warning(
        f"Are you sure about this? Do you want to remove all the objects from the org {org_name_from_mist} with the id {org_id} (y/N)? "
    )
    display_warning(
        f'Do you understant you won\'t be able to revert changes done on the org {org_name_from_mist} with id {org_id} (Please type "I understand")? ',
        "I understand",
    )

    print()
    start_delete(apisession, org_id)
    create_primary_site(apisession, org_id)

    print()
    console.info(
        f"All objects removed... Organization {org_name_from_mist} is back to default..."
    )


def usage():
    print(
        """
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
            __          __     _____  _   _ _____ _   _  _____ 
            \ \        / /\   |  __ \| \ | |_   _| \ | |/ ____|
             \ \  /\  / /  \  | |__) |  \| | | | |  \| | |  __ 
              \ \/  \/ / /\ \ |  _  /| . ` | | | | . ` | | |_ |
               \  /\  / ____ \| | \ \| |\  |_| |_| |\  | |__| |
                \/  \/_/    \_\_|  \_\_| \_|_____|_| \_|\_____|
            THIS SCRIPT IS DESIGNED TO REMOVE ALL THE OBJECT IN 
              A SPECIFIC ORGANIZATION! THESE CHANGES CAN'T BE 
               REVERT BACK. USE THIS SCRIPT AS YOUR OWN RISK


Python script to zeroise an organization. This scrip will remove all the 
configuration, all the sites and all the objects from the organization.
                    
Use it with extreme precaution, there is no way to revert the action if
you didn't backed up the organization.

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
-n, --org_name=         Org name to reset, for validation
-l, --log_file=         define the filepath/filename where to write the logs
                        default is "./script.log"
-e, --env=              define the env file to use (see mistapi env file documentation 
                        here: https://pypi.org/project/mistapi/)
                        default is "~/.mist_env"

-------
Examples:
python3 ./org_conf_zeroise.py     
python3 ./org_conf_zeroise.py --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 -n my_test_org

"""
    )
    sys.exit(0)


def warning():
    print(
        """ 
__          __     _____  _   _ _____ _   _  _____ 
\ \        / /\   |  __ \| \ | |_   _| \ | |/ ____|
 \ \  /\  / /  \  | |__) |  \| | | | |  \| | |  __ 
  \ \/  \/ / /\ \ |  _  /| . ` | | | | . ` | | |_ |
   \  /\  / ____ \| | \ \| |\  |_| |_| |\  | |__| |
    \/  \/_/    \_\_|  \_\_| \_|_____|_| \_|\_____|

 THIS SCRIPT IS DESIGNED TO REMOVE ALL THE OBJECT IN 
  A SPECIFIC ORGANIZATION! THESE CHANGES CAN'T BE 
   REVERT BACK. USE THIS SCRIPT AS YOUR OWN RISK

"""
    )

def check_mistapi_version():
    if mistapi.__version__ < MISTAPI_MIN_VERSION:
        logger.critical(f"\"mistapi\" package version {MISTAPI_MIN_VERSION} is required, you are currently using version {mistapi.__version__}.")
        logger.critical(f"Please use the pip command to updated it.")
        logger.critical("")
        logger.critical(f"    # Linux/macOS")
        logger.critical(f"    python3 -m pip install --upgrade mistapi")
        logger.critical("")
        logger.critical(f"    # Windows")
        logger.critical(f"    py -m pip install --upgrade mistapi")
        print(f"""
    Critical: 
    \"mistapi\" package version {MISTAPI_MIN_VERSION} is required, you are currently using version {mistapi.__version__}. 
    Please use the pip command to updated it.

    # Linux/macOS
    python3 -m pip install --upgrade mistapi

    # Windows
    py -m pip install --upgrade mistapi
        """)
        sys.exit(2)
    else: 
        logger.info(f"\"mistapi\" package version {MISTAPI_MIN_VERSION} is required, you are currently using version {mistapi.__version__}.")


#####################################################################
#### SCRIPT ENTRYPOINT ####
if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(
            sys.argv[1:],
            "ho:n:e:l:",
            ["help", "org_id=", "org_name=", "env=", "log_file="],
        )
    except getopt.GetoptError as err:
        console.error(err)
        usage()

    org_id = None
    org_name = None
    backup_folder_param = None
    source_backup_org_name = None
    for o, a in opts:
        if o in ["-h", "--help"]:
            usage()
        elif o in ["-o", "--org_id"]:
            org_id = a
        elif o in ["-n", "--org_name"]:
            org_name = a
        elif o in ["-e", "--env"]:
            env_file = a
        elif o in ["-l", "--log_file"]:
            log_file = a
        else:
            assert False, "unhandled option"

    #### LOGS ####
    logging.basicConfig(filename=log_file, filemode="w")
    logger.setLevel(logging.DEBUG)
    check_mistapi_version()
    ### START ###
    warning()
    apisession = mistapi.APISession(env_file=env_file)
    apisession.login()
    start(apisession, org_id, org_name)

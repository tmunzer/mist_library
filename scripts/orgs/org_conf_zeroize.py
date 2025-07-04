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

It is recommended to use an environment file to store the required information
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

MISTAPI_MIN_VERSION = "0.56.1"

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
LOG_FILE = "./script.log"
ENV_FILE = "~/.mist_env"

#####################################################################
#### LOGS ####
LOGGER = logging.getLogger(__name__)

#####################################################################
#### GLOBAL VARS ####

get_org_steps = {
    "sites": {
        "get_mistapi_function": mistapi.api.v1.orgs.sites.listOrgSites,
        "delete_mistapi_function": mistapi.api.v1.sites.sites.deleteSite,
        "text": "Org Sites",
        "check_next": True,
    },
    "webhooks": {
        "get_mistapi_function": mistapi.api.v1.orgs.webhooks.listOrgWebhooks,
        "delete_mistapi_function": mistapi.api.v1.orgs.webhooks.deleteOrgWebhook,
        "text": "Org webhooks",
        "check_next": True,
    },
    "assetfilters": {
        "get_mistapi_function": mistapi.api.v1.orgs.assetfilters.listOrgAssetFilters,
        "delete_mistapi_function": mistapi.api.v1.orgs.assetfilters.deleteOrgAssetFilter,
        "text": "Org assetfilters",
        "check_next": True,
    },
    "alarmtemplates": {
        "get_mistapi_function": mistapi.api.v1.orgs.alarmtemplates.listOrgAlarmTemplates,
        "delete_mistapi_function": mistapi.api.v1.orgs.alarmtemplates.deleteOrgAlarmTemplate,
        "text": "Org alarmtemplates",
        "check_next": True,
    },
    "deviceprofiles": {
        "get_mistapi_function": mistapi.api.v1.orgs.deviceprofiles.listOrgDeviceProfiles,
        "delete_mistapi_function": mistapi.api.v1.orgs.deviceprofiles.deleteOrgDeviceProfile,
        "text": "Org deviceprofiles",
        "check_next": True,
    },
    "hubprofiles": {
        "get_mistapi_function": mistapi.api.v1.orgs.deviceprofiles.listOrgDeviceProfiles,
        "delete_mistapi_function": mistapi.api.v1.orgs.deviceprofiles.deleteOrgDeviceProfile,
        "text": "Org hubprofiles",
        "get_options": {"type":"gateway"},
        "check_next": True,
    },
    "switchprofiles": {
        "get_mistapi_function": mistapi.api.v1.orgs.deviceprofiles.listOrgDeviceProfiles,
        "delete_mistapi_function": mistapi.api.v1.orgs.deviceprofiles.deleteOrgDeviceProfile,
        "text": "Org switchprofiles",
        "get_options": {"type":"switch"},
        "check_next": True,
    },
    "mxclusters": {
        "get_mistapi_function": mistapi.api.v1.orgs.mxclusters.listOrgMxEdgeClusters,
        "delete_mistapi_function": mistapi.api.v1.orgs.mxclusters.deleteOrgMxEdgeCluster,
        "text": "Org mxclusters",
        "check_next": True,
    },
    "mxtunnels": {
        "get_mistapi_function": mistapi.api.v1.orgs.mxtunnels.listOrgMxTunnels,
        "delete_mistapi_function": mistapi.api.v1.orgs.mxtunnels.deleteOrgMxTunnel,
        "text": "Org mxtunnels",
        "check_next": True,
    },
    "psks": {
        "get_mistapi_function": mistapi.api.v1.orgs.psks.listOrgPsks,
        "delete_mistapi_function": mistapi.api.v1.orgs.psks.deleteOrgPsk,
        "text": "Org psks",
        "check_next": True,
    },
    "pskportals": {
        "get_mistapi_function": mistapi.api.v1.orgs.pskportals.listOrgPskPortals,
        "delete_mistapi_function": mistapi.api.v1.orgs.pskportals.deleteOrgPskPortal,
        "text": "Org pskportals",
        "check_next": True,
    },
    "rftemplates": {
        "get_mistapi_function": mistapi.api.v1.orgs.rftemplates.listOrgRfTemplates,
        "delete_mistapi_function": mistapi.api.v1.orgs.rftemplates.deleteOrgRfTemplate,
        "text": "Org rftemplates",
        "check_next": True,
    },
    "networktemplates": {
        "get_mistapi_function": mistapi.api.v1.orgs.networktemplates.listOrgNetworkTemplates,
        "delete_mistapi_function": mistapi.api.v1.orgs.networktemplates.deleteOrgNetworkTemplate,
        "text": "Org networktemplates",
        "check_next": True,
    },
    "evpn_topologies": {
        "get_mistapi_function": mistapi.api.v1.orgs.evpn_topologies.listOrgEvpnTopologies,
        "delete_mistapi_function": mistapi.api.v1.orgs.evpn_topologies.deleteOrgEvpnTopology,
        "text": "Org evpn_topologies",
        "check_next": True,
    },
    "services": {
        "get_mistapi_function": mistapi.api.v1.orgs.services.listOrgServices,
        "delete_mistapi_function": mistapi.api.v1.orgs.services.deleteOrgService,
        "text": "Org services",
        "check_next": True,
    },
    "servicepolicies": {
        "get_mistapi_function": mistapi.api.v1.orgs.servicepolicies.listOrgServicePolicies,
        "delete_mistapi_function": mistapi.api.v1.orgs.servicepolicies.deleteOrgServicePolicy,
        "text": "Org servicepolicies",
        "check_next": True,
    },
    "networks": {
        "get_mistapi_function": mistapi.api.v1.orgs.networks.listOrgNetworks,
        "delete_mistapi_function": mistapi.api.v1.orgs.networks.deleteOrgNetwork,
        "text": "Org networks",
        "check_next": True,
    },
    "gatewaytemplates": {
        "get_mistapi_function": mistapi.api.v1.orgs.gatewaytemplates.listOrgGatewayTemplates,
        "delete_mistapi_function": mistapi.api.v1.orgs.gatewaytemplates.deleteOrgGatewayTemplate,
        "text": "Org gatewaytemplates",
        "check_next": True,
    },
    "vpns": {
        "get_mistapi_function": mistapi.api.v1.orgs.vpns.listOrgVpns,
        "delete_mistapi_function": mistapi.api.v1.orgs.vpns.deleteOrgVpn,
        "text": "Org vpns",
        "check_next": True,
    },
    "secpolicies": {
        "get_mistapi_function": mistapi.api.v1.orgs.secpolicies.listOrgSecPolicies,
        "delete_mistapi_function": mistapi.api.v1.orgs.secpolicies.deleteOrgSecPolicy,
        "text": "Org secpolicies",
        "check_next": True,
    },
    "sitegroups": {
        "get_mistapi_function": mistapi.api.v1.orgs.sitegroups.listOrgSiteGroups,
        "delete_mistapi_function": mistapi.api.v1.orgs.sitegroups.deleteOrgSiteGroup,
        "text": "Org sitegroups",
        "check_next": True,
    },
    "sitetemplates": {
        "get_mistapi_function": mistapi.api.v1.orgs.sitetemplates.listOrgSiteTemplates,
        "delete_mistapi_function": mistapi.api.v1.orgs.sitetemplates.deleteOrgSiteTemplate,
        "text": "Org sitetemplates",
        "check_next": True,
    },
    "ssos": {
        "get_mistapi_function": mistapi.api.v1.orgs.ssos.listOrgSsos,
        "delete_mistapi_function": mistapi.api.v1.orgs.ssos.deleteOrgSso,
        "text": "Org ssos",
        "check_next": True,
    },
    "ssoroles": {
        "get_mistapi_function": mistapi.api.v1.orgs.ssoroles.listOrgSsoRoles,
        "delete_mistapi_function": mistapi.api.v1.orgs.ssoroles.deleteOrgSsoRole,
        "text": "Org ssoroles",
        "check_next": True,
    },
    "templates": {
        "get_mistapi_function": mistapi.api.v1.orgs.templates.listOrgTemplates,
        "delete_mistapi_function": mistapi.api.v1.orgs.templates.deleteOrgTemplate,
        "text": "Org templates",
        "check_next": True,
    },
    "wxrules": {
        "get_mistapi_function": mistapi.api.v1.orgs.wxrules.listOrgWxRules,
        "delete_mistapi_function": mistapi.api.v1.orgs.wxrules.deleteOrgWxRule,
        "text": "Org wxrules",
        "check_next": True,
    },
    "wxtags": {
        "get_mistapi_function": mistapi.api.v1.orgs.wxtags.listOrgWxTags,
        "delete_mistapi_function": mistapi.api.v1.orgs.wxtags.deleteOrgWxTag,
        "text": "Org wxtags",
        "check_next": True,
    },
    "wxtunnels": {
        "get_mistapi_function": mistapi.api.v1.orgs.wxtunnels.listOrgWxTunnels,
        "delete_mistapi_function": mistapi.api.v1.orgs.wxtunnels.deleteOrgWxTunnel,
        "text": "Org wxtunnels",
        "check_next": True,
    },
    "nactags": {
        "get_mistapi_function": mistapi.api.v1.orgs.nactags.listOrgNacTags,
        "delete_mistapi_function": mistapi.api.v1.orgs.nactags.deleteOrgNacTag,
        "text": "Org nactags",
        "check_next": True,
    },
    "nacrules": {
        "get_mistapi_function": mistapi.api.v1.orgs.nacrules.listOrgNacRules,
        "delete_mistapi_function": mistapi.api.v1.orgs.nacrules.deleteOrgNacRule,
        "text": "Org nacrules",
        "check_next": True,
    },
    "usermacs": {
        "get_mistapi_function": mistapi.api.v1.orgs.usermacs.searchOrgUserMacs,
        "delete_mistapi_function": mistapi.api.v1.orgs.usermacs.deleteOrgUserMac,
        "text": "Org usermacs",
        "check_next": True,
    },
    "wlans": {
        "get_mistapi_function": mistapi.api.v1.orgs.wlans.listOrgWlans,
        "delete_mistapi_function": mistapi.api.v1.orgs.wlans.deleteOrgWlan,
        "text": "Org wlans",
        "check_next": True,
    },
    "aamwprofiles": {
        "get_mistapi_function": mistapi.api.v1.orgs.aamwprofiles.listOrgAAMWProfiles,
        "delete_mistapi_function": mistapi.api.v1.orgs.aamwprofiles.deleteOrgAAMWProfile,
        "text": "Org Advanced Anti-Malware Profiles",
        "check_next": True,
    },
    "antivirus": {
        "get_mistapi_function": mistapi.api.v1.orgs.avprofiles.listOrgAntivirusProfiles,
        "delete_mistapi_function": mistapi.api.v1.orgs.avprofiles.deleteOrgAntivirusProfile,
    }
}



##########################################################################################
#### FUNCTIONS ####
def log_message(message):
    print(f"{message}".ljust(79, "."), end="", flush=True)


def log_debug(message):
    LOGGER.debug(f"{message}")


def log_error(message):
    LOGGER.error(f"{message}")


def log_success(message):
    print("\033[92m\u2714\033[0m")
    LOGGER.info(f"{message}: Success")


def log_failure(message):
    print("\033[31m\u2716\033[0m")
    LOGGER.exception(f"{message}: Failure")


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
    for step_name, step in get_org_steps.items():
        options = step.get("get_options", {})
        response = step["get_mistapi_function"](apisession, org_id, **options)
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
                        step["delete_mistapi_function"](apisession, entry["id"])
                    else:
                        step["delete_mistapi_function"](apisession, org_id, entry["id"])
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
            "To avoid any error, please confirm the organization name you want to reset: "
        )
        if resp == org_name:
            return True
        else:
            console.warning("The organization names do not match... Please try again...")


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
        f'Do you understand you won\'t be able to revert changes done on the org {org_name_from_mist} with id {org_id} (Please type "I understand")? ',
        "I understand",
    )

    print()
    start_delete(apisession, org_id)
    create_primary_site(apisession, org_id)

    print()
    console.info(
        f"All objects removed... Organization {org_name_from_mist} is back to default..."
    )


def usage(error_message: str = "") -> None:
    """
    Print the usage information and exit the script.
    :param error_message: Optional error message to display
    """
    print(
        '''
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

It is recommended to use an environment file to store the required information
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

'''
    )
    if error_message:
        console.critical(error_message)
    sys.exit(0)


def warning():
    print(
        '''
__          __     _____  _   _ _____ _   _  _____ 
\ \        / /\   |  __ \| \ | |_   _| \ | |/ ____|
 \ \  /\  / /  \  | |__) |  \| | | | |  \| | |  __ 
  \ \/  \/ / /\ \ |  _  /| . ` | | | | . ` | | |_ |
   \  /\  / ____ \| | \ \| |\  |_| |_| |\  | |__| |
    \/  \/_/    \_\_|  \_\_| \_|_____|_| \_|\_____|

 THIS SCRIPT IS DESIGNED TO REMOVE ALL THE OBJECT IN 
  A SPECIFIC ORGANIZATION! THESE CHANGES CAN'T BE 
   REVERT BACK. USE THIS SCRIPT AS YOUR OWN RISK

'''
    )

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
            mistapi.__version__
        )


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
        console.error(err.msg)
        usage()

    ORG_ID = None
    ORG_NAME = None
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
        else:
            assert False, "unhandled option"

    #### LOGS ####
    logging.basicConfig(filename=LOG_FILE, filemode="w")
    LOGGER.setLevel(logging.DEBUG)
    check_mistapi_version()
    ### START ###
    warning()
    APISESSION = mistapi.APISession(env_file=ENV_FILE)
    APISESSION.login()
    start(APISESSION, ORG_ID, ORG_NAME)

'''
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to update the org auto assignment rules. The script is displaying 
options enable/disable the auto assignment, and to build the rules before 
updating the org settings

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
Options:
-h, --help          display this help
-o, --org_id=       Set the org_id (only one of the org_id or site_id can be defined)
--enable            Enable the auto assignment (additional configuration will be asked
                    by the script). Only one action enable/disable is allowed
--disable           Disable the auto assignment Only one action enable/disable is 
                    allowed              
-l, --log_file=     define the filepath/filename where to write the logs
                    default is "./script.log"
-e, --env=          define the env file to use (see mistapi env file documentation 
                    here: https://pypi.org/project/mistapi/)
                    default is "~/.mist_env"

-------
Examples:
python3 ./config_auto_site_assignment.py                  
python3 ./config_auto_site_assignment.py --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 --disable

'''

#### IMPORTS #####
import sys
import logging
import getopt

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


#### LOGS ####
LOGGER = logging.getLogger(__name__)

#### PARAMETERS #####
auto_site_assignment = {
    "enable": True,
    "rules": []
}

LOG_FILE = "./script.log"
ENV_FILE = "~/.mist_env"
#### GLOBAL VARIABLES ####
AUTO_ASSIGNMENT_RULES = ["name", "subnet", "lldp_system_name", "dns_suffix", "model" ]

#### FUNCTIONS ####
def create_rule(apisession, org_id):
    rules = []
    while True:
        rule_conf = {}
        rule_conf = select_rule_type(apisession, org_id)
        mistapi.cli.pretty_print(rule_conf)
        resp = input("Is it correct (Y/n)?")
        if resp.lower() == 'y' or resp == "":
            rules.append(rule_conf)
            while True:
                resp = input("Do you want to add a new rule (y/N)?")
                if resp.lower() == 'n' or resp == "":
                    return rules
                elif resp.lower() == 'y':
                    break

def select_rule_type(apisession, org_id):
    rule_conf = {}
    while True:
        print("Type of auto assignment rule:")
        i = -1
        for rule in AUTO_ASSIGNMENT_RULES:
            i+=1
            print(f"{i}) {rule}")
        resp = input(f"Please select the type of rule (0-{i})")
        try:
            resp_num = int(resp)
        except:
            print(f"Error. The value {resp} is not valid")
        if resp_num >= 0 and resp_num <= i:
            rule_conf['src'] = AUTO_ASSIGNMENT_RULES[resp_num]
            return configure_rule(apisession, org_id, rule_conf)
        else:
            print(f"Error: {resp_num} is not authorized")


def configure_rule(apisession, org_id, rule_conf):
    if rule_conf['src'] == "name":
        # // use device name (via Installer APIs)
        #{
        #     "src": "name",
        #     "expression": "[0:3]",           // "abcdef" -> "abc"
        #                   "split(.)[1]",     // "a.b.c" -> "b"
        #                   "split(-)[1][0:3], // "a1234-b5678-c90" -> "b56"
        #     "prefix": "XX-",
        #     "suffix": "-YY"
        # },             
        print("Expression to extract the site name from the LLDP system name")
        print("Example: \"[0:3]\",           // \"abcdef\" -> \"abc\"")
        print("         \"split(.)[1]\",     // \"a.b.c\" -> \"b\"")
        print("         \"split(-)[1][0:3]\", // \"a1234-b5678-c90\" -> \"b56\"")
        rule_conf['expression'] = input("Expression: ")
        rule_conf['prefix'] = input("Prefix (XX-): " )
        rule_conf['suffix'] = input("Suffix (-XX): ")
    elif rule_conf['src'] == "subnet":
        # // use subnet
        # {
        #     "src": "subnet",
        #     "subnet": "10.1.2.0/18",
        #     "value": "s1351"
        # },
        rule_conf['subnet'] = input("Please enter the subnet value (ex: 10.1.2.0/18): ")
        site_id = mistapi.cli.select_site(apisession, org_id=org_id)[0]
        rule_conf['value'] = mistapi.api.v1.sites.stats.getSiteStats(apisession, site_id).data['name']
    elif rule_conf['src'] == "lldp_system_name":
        # // use LLDP System Name
        # {
        #     "src": "lldp_system_name",
        #     "expression": "..." // same as above
        # },
        print("Expression to extract the site name from the LLDP system name")
        print("Example: \"[0:3]\",           // \"abcdef\" -> \"abc\"")
        print("         \"split(.)[1]\",     // \"a.b.c\" -> \"b\"")
        print("         \"split(-)[1][0:3]\", // \"a1234-b5678-c90\" -> \"b56\"")
        rule_conf['expression'] = input("Expression: ")
    elif rule_conf['src'] == "dns_suffix":
        # // use DNS Suffix
        # {
        #     "src": "dns_suffix",
        #     "expression": "..." // same as above
        # },
        print("Expression to extract the site name from the DNS suffix name")
        print("Example: \"[0:3]\",           // \"abcdef\" -> \"abc\"")
        print("         \"split(.)[1]\",     // \"a.b.c\" -> \"b\"")
        print("         \"split(-)[1][0:3]\", // \"a1234-b5678-c90\" -> \"b56\"")
        rule_conf['expression'] = input("Expression: ")
    elif rule_conf['src'] == "model":
        # {
        #     "src": "model",
        #     "model": "AP41",
        #     "value": "s1351"
        # }       
        rule_conf['model'] = input("Please enter the model of AP: ")
        site_id = mistapi.cli.select_site(apisession, org_id=org_id)[0]
        rule_conf['value'] = mistapi.api.v1.sites.stats.getSiteStats(apisession, site_id).data['name']
    return rule_conf


###############################################################################
### USAGE
def usage():
    print('''
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to update the org auto assignment rules. The script is displaying 
options enable/disable the auto assignment, and to build the rules before 
updating the org settings

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
Options:
-h, --help          display this help
-o, --org_id=       Set the org_id (only one of the org_id or site_id can be defined)
--enable            Enable the auto assignment (additional configuration will be asked
                    by the script). Only one action enable/disable is allowed
--disable           Disable the auto assignment Only one action enable/disable is 
                    allowed              
-l, --log_file=     define the filepath/filename where to write the logs
                    default is "./script.log"
-e, --env=          define the env file to use (see mistapi env file documentation 
                    here: https://pypi.org/project/mistapi/)
                    default is "~/.mist_env"

-------
Examples:
python3 ./config_auto_site_assignment.py                  
python3 ./config_auto_site_assignment.py --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 --disable

''')
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
            mistapi.__version__
        )


###############################################################################
### ENTRY POINT
if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(sys.argv[1:], "ho:e:l:", ["help", "org_id=", "env=", "log_file=", "enable", "disable"])
    except getopt.GetoptError as err:
        console.error(err)
        usage()

    ORG_ID=None
    ACTION=None
    for o, a in opts:
        if o in ["-h", "--help"]:
            usage()
        elif o in ["-o", "--org_id"]:
            ORG_ID = a
        elif o in ["-e", "--env"]:
            env_file=a
        elif o in ["-l", "--log_file"]:
            LOG_FILE = a
        elif o in ["-a", "--enable"]:
            if ACTION:
                console.error("Only one action \"enable\" or \"disable\" is allowed")
                sys.exit(0)
            ACTION ="enable"
            auto_site_assignment["enable"] = True
        elif o in ["-b", "--disable"]:
            if ACTION:
                console.error("Only one action \"enable\" or \"disable\" is allowed")
                sys.exit(0)
            ACTION ="disable"
            auto_site_assignment["enable"] = False
        else:
            assert False, "unhandled option"

    #### LOGS ####
    logging.basicConfig(filename=LOG_FILE, filemode='w')
    LOGGER.setLevel(logging.DEBUG)
    check_mistapi_version()
    ### MIST SESSION ###
    APISESSION = mistapi.APISession(env_file=ENV_FILE)
    APISESSION.login()

    if not ORG_ID:
        ORG_ID = mistapi.cli.select_org(APISESSION)

    while not ACTION:
        resp = input("Do you want to (E)nable of (D)isable auto site assignment (e/d)?")
        if resp.lower() == 'e':
            auto_site_assignment["enable"] = True
            ACTION = "enable"
        elif resp.lower() == 'd':
            auto_site_assignment["enable"] = False
            ACTION = "disable"
        else:
            console.error("Only \"e\" and \"d\" are allowed, to Enable or Disable auto site assignment")

    if auto_site_assignment["enable"] == True:
        auto_site_assignment["rules"] = create_rule(APISESSION, ORG_ID)


    print("Configuration to upload".center(80, "-"))
    mistapi.cli.pretty_print({"auto_site_assignment": auto_site_assignment})
    mistapi.api.v1.orgs.setting.updateOrgSettings(APISESSION, ORG_ID, {"auto_site_assignment": auto_site_assignment})
    print("Configuration from Mist".center(80, "-"))
    conf_from_mist = mistapi.api.v1.orgs.setting.getOrgSettings(APISESSION, ORG_ID).data["auto_site_assignment"]
    mistapi.cli.pretty_print({"auto_site_assignment": conf_from_mist})

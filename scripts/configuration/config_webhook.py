'''
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to list/add/delete Webhooks from Org/Site. Adding a webhook
requires a JSON file containing the webhook settings.


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
JSON file:
The JSON file must contains a single JSON object describing the webhook
parameters. Webhook configuration details can be found in the Mist API 
documentation

-------
JSON Example:
{
    "url": "https://myserver.local/webhooks",
    "enabled": false,
    "splunk_token": "",
    "secret": "mprzx74ACMqM",
    "name": "demo",
    "type": "http-post",
    "verify_cert": true,
    "headers": {}
}

-------
Script Parameters:
-h, --help          display this help
-f, --file=         OPTIONAL: path to the JSON file

-o, --org_id=       Set the org_id where the webhook must be create/delete/retrieved
                    This parameter cannot be used if -s/--site_id is used.
                    If no org_id and not site_id are defined, the script will show
                    a menu to select the org/the site.
-s, --site_id=      Set the site_id where the webhook must be create/delete/retrieved
                    This parameter cannot be used if -o/--org_id is used.
                    If no org_id and not site_id are defined, the script will show
                    a menu to select the org/the site.

-l, --log_file=     define the filepath/filename where to write the logs
                    default is "./script.log"
-e, --env=          define the env file to use (see mistapi env file documentation 
                    here: https://pypi.org/project/mistapi/)
                    default is "~/.mist_env"

-------
Examples:
python3 ./config_webhook.py             
python3 ./config_webhook.py \
    -f ./config_webhook.json \
    --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 

'''

#### IMPORTS ####
import json
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

#### PARAMETERS #####
LOG_FILE = "./scripts.log"
DEFAULT_WEBHOOK_FILE = "./config_webhook_settings.json"
ENV_FILE = "~/.mist_env"
FIELDS = ["id", "enabled", "name", "url", "type", "topics", "verify_cert"]
#### LOGS ####
LOGGER = logging.getLogger(__name__)

def _get_webhooks(apisession, org_id, site_id=None):
    webhooks= []
    if site_id:
        webhooks = mistapi.api.v1.sites.webhooks.listSiteWebhooks(apisession, site_id).data
    else:
        webhooks = mistapi.api.v1.orgs.webhooks.listOrgWebhooks(apisession, org_id).data
    return webhooks

def _create_webhooks(apisession, webhook_data, org_id, site_id=None):
    try:
        if site_id:
            mistapi.api.v1.sites.webhooks.createSiteWebhook(apisession, site_id, body=webhook_data)
        else:
            mistapi.api.v1.orgs.webhooks.createOrgWebhook(apisession, org_id, body=webhook_data)
    except Exception as e:
        print(e)

def _delete_webhooks(apisession, webhook_id, org_id, site_id=None):
    try:
        if site_id:
            mistapi.api.v1.sites.webhooks.deleteSiteWebhook(apisession, site_id, webhook_id=webhook_id)
        else:
            mistapi.api.v1.orgs.webhooks.deleteOrgWebhook(apisession, org_id, webhook_id=webhook_id)
    except Exception as e:
        print(e)

def _display_webhooks(apisession, org_id, site_id=None):
    webhooks = _get_webhooks(apisession, org_id, site_id)
    mistapi.cli.display_list_of_json_as_table(webhooks, FIELDS)

def _add_webhook(apisession, org_id, site_id):
    webhook_file = input(
        f"Path to the webhook configuration JSON file (default: {DEFAULT_WEBHOOK_FILE}): ")
    if webhook_file == "":
        webhook_file = DEFAULT_WEBHOOK_FILE
    try:
        with open(webhook_file, "r") as f:
            webhook = json.load(f)
    except:
        print("Error while loading the configuration file... exiting...")
        sys.exit(255)
    try:
        webhook_json = json.dumps(webhook)
    except:
        print("Error while loading the webhook settings from the file... exiting...")
        sys.exit(255)
    _create_webhooks(apisession, webhook_json, org_id, site_id)

def _remove_webhook(apisession, org_id, site_id=None):
    webhooks = _get_webhooks(apisession, org_id, site_id)
    resp = -1
    while True:
        print()
        print("Available webhooks:")
        i = 0
        for webhook in webhooks:
            print(f"{i}) {webhook.get('name')}: {webhook.get('url')} (id: {webhook.get('id')})")
            i += 1
        print()
        resp = input(
            f"Which webhook do you want to delete (0-{i-1}, or q to quit)? ")
        if resp.lower() == "q":
            sys.exit(0)
        else:
            try:
                resp_num = int(resp)
            except:
                print("Only numbers are allowed.")
            if resp_num >= 0 and resp_num <= i:
                webhook = webhooks[resp_num]
                print()
                confirmation = input(
                    f"Are you sure you want to delete webhook {webhook['name']} (y/N)? ")
                if confirmation.lower() == "y":
                    _delete_webhooks(apisession, webhook["id"], org_id, site_id)
                    break
            else:
                print(f"{resp_num} is not part of the possibilities.")

def _select_action(apisession, org_id, site_id=None):
    while True:
        actions = ["ADD Webhook", "DELETE Webhook", "LIST Webhooks"]
        print("What do you want to do:")
        i = 0
        for action in actions:
            print(f"{i}) {action}")
            i += 1
        print()
        resp = input(f"Choice (0-{i}, q to quit): ")
        if resp.lower() == "q":
            sys.exit(0)
        else:
            try:
                resp_num = int(resp)
                if resp_num >= 0 and resp_num <= i:
                    print()
                    print(" CURRENT Webhooks ".center(80, "-"))
                    _display_webhooks(apisession, org_id, site_id)
                    print()
                    if actions[resp_num] == "ADD Webhook":
                        _add_webhook(apisession, org_id, site_id)
                        print()
                        print(" Webhooks AFTER change ".center(80, "-"))
                        _display_webhooks(apisession, org_id, site_id)
                    elif actions[resp_num] == "DELETE Webhook":
                        _remove_webhook(apisession, org_id, site_id)
                        print()
                        print(" Webhooks AFTER change ".center(80, "-"))
                        _display_webhooks(apisession, org_id, site_id)
                    break
                else:
                    print(f"{resp_num} is not part of the possibilities.")
            except:
                print("Only numbers are allowed.")


def _site_webhook(apisession, org_id):
    site_id = mistapi.cli.select_site(apisession, org_id=org_id, allow_many=False)[0]
    _select_action(apisession, org_id, site_id)


def _org_webhook(apisession, org_id):
    _select_action(apisession, org_id)


def _start_webhook_conf(apisession, org_id):
    while True:
        actions = ["ORG Webhooks", "SITE Webhooks"]
        print("What do you want to do:")
        i = 0
        for action in actions:
            print(f"{i}) {action}")
            i += 1
        print()
        resp = input(f"Choice (0-{i}, q to quit): ")
        if resp.lower() == "q":
            sys.exit(0)
        else:
            try:
                resp_num = int(resp)
                if resp_num >= 0 and resp_num <= len(actions):
                    if actions[resp_num] == "ORG Webhooks":
                        _org_webhook(apisession, org_id)
                        break
                    elif actions[resp_num] == "SITE Webhooks":
                        _site_webhook(apisession, org_id)
                        break
                    else:
                        print(f"{resp_num} is not part of the possibilities.")
            except:
                print("Only numbers are allowed.")

def start(apisession, org_id:str=None, site_id:str=None):
    """
    start the script process
    """
    if org_id:
        _org_webhook(apisession, org_id)
    elif site_id:
        _select_action(apisession, None, site_id)
    else:
        org_id = mistapi.cli.select_org(apisession)[0]
        _start_webhook_conf(apisession, org_id)


###############################################################################
# USAGE
def usage(error_message:str=None):
    """
    show script usage
    """
    print('''
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to list/add/delete Webhooks from Org/Site. Adding a webhook
requires a JSON file containing the webhook settings.


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
JSON file:
The JSON file must contains a single JSON object describing the webhook
parameters. Webhook configuration details can be found in the Mist API 
documentation

-------
JSON Example:
{
    "url": "https://myserver.local/webhooks",
    "enabled": false,
    "splunk_token": "",
    "secret": "mprzx74ACMqM",
    "name": "demo",
    "type": "http-post",
    "verify_cert": true,
    "headers": {}
}

-------
Script Parameters:
-h, --help          display this help
-f, --file=         OPTIONAL: path to the JSON file

-o, --org_id=       Set the org_id where the webhook must be create/delete/retrieved
                    This parameter cannot be used if -s/--site_id is used.
                    If no org_id and not site_id are defined, the script will show
                    a menu to select the org/the site.
-s, --site_id=      Set the site_id where the webhook must be create/delete/retrieved
                    This parameter cannot be used if -o/--org_id is used.
                    If no org_id and not site_id are defined, the script will show
                    a menu to select the org/the site.

-l, --log_file=     define the filepath/filename where to write the logs
                    default is "./script.log"
-e, --env=          define the env file to use (see mistapi env file documentation 
                    here: https://pypi.org/project/mistapi/)
                    default is "~/.mist_env"

-------
Examples:
python3 ./config_webhook.py             
python3 ./config_webhook.py \
    -f ./config_webhook.json \
    --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 
''')
    if error_message:
        console.critical(error_message)
    sys.exit(0)

def check_mistapi_version():
    """
    check the current version of the mistapi package
    """
    if mistapi.__version__ < MISTAPI_MIN_VERSION:
        LOGGER.critical(f"\"mistapi\" package version {MISTAPI_MIN_VERSION} is required, you are currently using version {mistapi.__version__}.")
        LOGGER.critical(f"Please use the pip command to updated it.")
        LOGGER.critical("")
        LOGGER.critical(f"    # Linux/macOS")
        LOGGER.critical(f"    python3 -m pip install --upgrade mistapi")
        LOGGER.critical("")
        LOGGER.critical(f"    # Windows")
        LOGGER.critical(f"    py -m pip install --upgrade mistapi")
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
        LOGGER.info(f"\"mistapi\" package version {MISTAPI_MIN_VERSION} is required, you are currently using version {mistapi.__version__}.")

###############################################################################
##### ENTRY POINT ####

if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(sys.argv[1:], "ho:s:f:e:l:", [
                                   "help", "org_id=", "site_id=", "file=", "env=", "log_file="])
    except getopt.GetoptError as err:
        console.error(err)
        usage()

    ORG_ID = None
    SITE_ID = None
    CONFIG_FILE = None
    for o, a in opts:
        if o in ["-h", "--help"]:
            usage()
        elif o in ["-o", "--org_id"]:
            if not SITE_ID:
                ORG_ID = a
            else:
                usage("Inavlid Parameters: \"-o\"/\"--org_id\" and \"-s\"/\"--site_id\" are exclusive")
        elif o in ["-s", "--site_id"]:
            if not ORG_ID:
                SITE_ID = a
            else:
                usage("Inavlid Parameters: \"-o\"/\"--org_id\" and \"-s\"/\"--site_id\" are exclusive")
        elif o in ["-f", "--file"]:
            CONFIG_FILE = a
        elif o in ["-e", "--env"]:
            ENV_FILE = a
        elif o in ["-l", "--log_file"]:
            LOG_FILE = a
        else:
            assert False, "unhandled option"
    #### LOGS ####
    logging.basicConfig(filename=LOG_FILE, filemode='w')
    LOGGER.setLevel(logging.DEBUG)
    ### START ###
    APISESSION = mistapi.APISession(env_file=ENV_FILE)
    APISESSION.login()
    start(APISESSION, ORG_ID, SITE_ID)

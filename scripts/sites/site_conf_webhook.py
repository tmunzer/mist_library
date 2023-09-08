'''
Written by Thomas Munzer (tmunzer@juniper.net)
Github repository: https://github.com/tmunzer/Mist_library/

This script can be used to list/add/delete Webhooks from Org/Site
'''

#### IMPORTS ####
import json
import sys
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

#### PARAMETERS #####
csv_separator = ","
log_file = "./sites_scripts.log"
default_webhook_file = "./site_conf_webhook_settings.json"
env_file = "./.env"
fields = ["id", "enabled", "name", "url", "type", "topics", "verify_cert"]
#### LOGS ####
logger = logging.getLogger(__name__)

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
    mistapi.cli.display_list_of_json_as_table(webhooks, fields)

def add_webhook(apisession, org_id, site_id):
    webhook_file = input(
        f"Path to the webhook configuration JSON file (default: {default_webhook_file}): ")
    if webhook_file == "":
        webhook_file = default_webhook_file
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

def remove_webhook(apisession, org_id, site_id=None):
    webhooks = _get_webhooks(apisession, org_id, site_id)
    resp = -1
    while True:
        print()
        print("Available webhooks:")
        i = 0
        for webhook in webhooks:
            print(f"{i}) {webhook['name']}: {webhook['url']} (id: {webhook['id']})")
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

def select_action(apisession, org_id, site_id=None):
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
                        add_webhook(apisession, org_id, site_id)
                        print()
                        print(" Webhooks AFTER change ".center(80, "-"))
                        _display_webhooks(apisession, org_id, site_id)    
                    elif actions[resp_num] == "DELETE Webhook":
                        remove_webhook(apisession, org_id, site_id)
                        print()
                        print(" Webhooks AFTER change ".center(80, "-"))
                        _display_webhooks(apisession, org_id, site_id)    
                    break
                else:
                    print(f"{resp_num} is not part of the possibilities.")
            except:
                print("Only numbers are allowed.")


def site_webhook(apisession, org_id):
    site_id = mistapi.cli.select_site(apisession, org_id=org_id, allow_many=False)[0]
    select_action(apisession, org_id, site_id)


def org_webhook(apisession, org_id):
    select_action(apisession, org_id)


def start_webhook_conf(apisession, org_id):
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
                        org_webhook(apisession, org_id)
                        break
                    elif actions[resp_num] == "SITE Webhooks":
                        site_webhook(apisession, org_id)
                        break
                    else:
                        print(f"{resp_num} is not part of the possibilities.")
            except:
                print("Only numbers are allowed.")

def start(apisession):
    org_id = mistapi.cli.select_org(apisession)[0]
    start_webhook_conf(apisession, org_id)

##### ENTRY POINT ####

if __name__ == "__main__":
    #### LOGS ####
    logging.basicConfig(filename=log_file, filemode='w')
    logger.setLevel(logging.DEBUG)
    ### START ###
    apisession = mistapi.APISession(env_file=env_file)
    apisession.login()
    start(apisession)
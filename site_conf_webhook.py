'''
Written by Thomas Munzer (tmunzer@juniper.net)
Github repository: https://github.com/tmunzer/Mist_library/

This script can be used to list/add/delete Webhooks from Org/Site
'''

import mlib as mist_lib
from mlib import cli
import json
from tabulate import tabulate
import sys
#### PARAMETERS #####
csv_separator = ","


def add_webhook(WEBHOOKS, scope_id):
    webhook_file = input(
        "Path to the webhook configuration JSON file (default: ./site_conf_webhook_settings.json): ")
    if webhook_file == "":
        webhook_file = "./site_conf_webhook_settings.json"
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
    WEBHOOKS.create(mist, scope_id, webhook_json)


def remove_webhook(WEBHOOKS, scope_id):
    webhooks = WEBHOOKS.get(mist, scope_id)['result']
    resp = -1
    while True:
        print()
        print("Available webhooks:")
        i = 0
        for webhook in webhooks:
            i += 1
            print(f"{i}) {webhook['ssid']} (id: {webhook['id']})")
        print()
        resp = input(
            f"Which webhook do you want to delete (0-{i-1}, or q to quit)? ")
        if resp.lower() == "q":
            sys.exit(0)
        else:
            try:
                resp_num = int(resp)
                if resp_num >= 0 and resp_num <= i:
                    webhook = webhooks[resp_num]
                    print()
                    confirmation = input(
                        f"Are you sure you want to delete webhook {webhook['ssid']} (y/N)? ")
                    if confirmation.lower() == "y":
                        break
                else:
                    print(f"{resp_num} is not part of the possibilities.")
            except:
                print("Only numbers are allowed.")
    WEBHOOKS.delete(mist, scope_id, webhook["id"])


def display_webhook(WEBHOOKS, scope_id):
    fields = ["id", "enabled", "name", "url", "type", "topics", "verify_cert"]
    site_webhooks = WEBHOOKS.report(mist, scope_id, fields)
    print(tabulate(site_webhooks, fields))


def select_action(WEBHOOKS, scope_id):
    while True:
        actions = ["ADD Webhook", "DELETE Webhook", "LIST Webhooks"]
        print("What do you want to do:")
        i = -1
        for action in actions:
            i += 1
            print(f"{i}) {action}")
        print()
        resp = input(f"Choice (0-{i}, q to quit): ")
        if resp.lower() == "q":
            sys.exit(0)
        else:
            try:
                resp_num = int(resp)
                if resp_num >= 0 and resp_num <= len(actions):
                    print()
                    print(" CURRENT Webhooks ".center(80, "-"))
                    display_webhook(WEBHOOKS, scope_id)
                    print()
                    if actions[resp_num] == "ADD Webhook":
                        add_webhook(WEBHOOKS)
                        print()
                        print(" Webhooks AFTER change ".center(80, "-"))
                        display_webhook(WEBHOOKS, scope_id)

                    elif actions[resp_num] == "DELETE Webhook":
                        remove_webhook(WEBHOOKS, scope_id)
                        print()
                        print(" Webhooks AFTER change ".center(80, "-"))
                        display_webhook(WEBHOOKS, scope_id)
                    break
                else:
                    print(f"{resp_num} is not part of the possibilities.")
            except:
                print("Only numbers are allowed.")


def site_webhook():
    site_id = cli.select_site(mist, allow_many=False)[0]
    select_action(mist_lib.requests.sites.webhooks, site_id)


def org_webhook():
    org_id = cli.select_org(mist)[0]
    select_action(mist_lib.requests.orgs.webhooks,  org_id)


mist = mist_lib.Mist_Session("./session.py")
while True:
    actions = ["ORG Webhooks", "SITE Webhooks"]
    print("What do you want to do:")
    i = -1
    for action in actions:
        i += 1
        print(f"{i}) {action}")
    print()
    resp = input(f"Choice (0-{i}, q to quit): ")
    if resp.lower() == "q":
        sys.exit(0)
    else:
        # try:
        resp_num = int(resp)
        if resp_num >= 0 and resp_num <= len(actions):
            if actions[resp_num] == "ORG Webhooks":
                org_webhook()
                break
            elif actions[resp_num] == "SITE Webhooks":
                site_webhook()
                break
            else:
                print(f"{resp_num} is not part of the possibilities.")
        # except:
        #     print("Only numbers are allowed.")

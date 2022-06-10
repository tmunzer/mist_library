'''
Written by Thomas Munzer (tmunzer@juniper.net)
Github repository: https://github.com/tmunzer/Mist_library/

__          __     _____  _   _ _____ _   _  _____ 
\ \        / /\   |  __ \| \ | |_   _| \ | |/ ____|
 \ \  /\  / /  \  | |__) |  \| | | | |  \| | |  __ 
  \ \/  \/ / /\ \ |  _  /| . ` | | | | . ` | | |_ |
   \  /\  / ____ \| | \ \| |\  |_| |_| |\  | |__| |
    \/  \/_/    \_\_|  \_\_| \_|_____|_| \_|\_____|
 THIS SCRIPT IS DESIGNED TO REMOVE ALL THE OBJECT IN 
  A SPECIFIC ORGANIZATION! THESE CHANGES CAN'T BE 
   REVERT BACK. USE THIS SCRIPT AS YOUR OWN RISK


Python script to restore organization backup file.
You can use the script "org_conf_backup.py" to generate the backup file from an
existing organization.

This script will not overide existing objects. If you already configured objects in the 
destination organisation, new objects will be created. If you want to "reset" the 
destination organization, you can use the script "org_conf_zeroise.py".
This script is trying to maintain objects integrity as much as possible. To do so, when 
an object is referencing another object by its ID, the script will replace be ID from 
the original organization by the corresponding ID from the destination org.

You can run the script with the command "python3 org_admins_import.py <path_to_the_json_file>"

The script has 2 different steps:
1) admin login
2) choose the destination org
3) restore all the objects from the json file. 
'''

#### PARAMETERS #####

org_id = ""
ids_to_not_delete = []

#### IMPORTS ####
import mlib as mist_lib
from mlib import cli
from tabulate import tabulate
import json
from mlib.__debug import Console
console = Console(6)

#### FUNCTIONS ####

def delete_object(org_id, object_name, ids_to_not_delete):
    console.info("Removing all %s objects..." %object_name)
    req = mist_lib.requests.route("orgs", object_name)
    data = req.get(mist_session, org_id)["result"]
    for d in data:
        if not d["id"] in ids_to_not_delete:
            req.delete(mist_session, org_id, d["id"])

def display_warning(message):
    resp = "x"
    while not resp.lower() in ["y", "n", ""]:
        print()
        resp = input(message)
    if not resp.lower()=="y":
        console.warning("User Interruption... Exiting...")
        exit(0)

def start_delete(org_id):
    object_names = [
                "webhooks",
                "assetfilters",
                "alarmtemplates",
                "deviceprofiles",
                "evpn_topologies",
                "gatewaytemplates",
                "mxclusters",
                "mxtunnels",
                "networks",
                "networktemplates",
                "psks",
                "rftemplates",
                "secpolicies",
                "services",
                "sitegroups",
                "templates",
                "vpns",
                "wlans",
                "wxrules",
                "wxtags",
                "wxtunnels", 
                "sites"]

    for object_name in object_names:
        delete_object(org_id, object_name, ids_to_not_delete)

def create_primary_site(org_id):
    primary_site = {"name": "Primary Site",}
    primary_site = mist_lib.orgs.sites.create(mist_session, org_id, primary_site)["result"]
    ids_to_not_delete.append(primary_site["id"])

def check_org_name(org_name):
    while True:
        print()
        resp = input("To avoid any error, please confirm the orgnization name you want to reset: ")
        if resp == org_name:
            return True
        else:
            console.warning("The orgnization names do not match... Please try again...")

#### SCRIPT ENTRYPOINT ####

mist_session = mist_lib.Mist_Session()

print(""" 
__          __     _____  _   _ _____ _   _  _____ 
\ \        / /\   |  __ \| \ | |_   _| \ | |/ ____|
 \ \  /\  / /  \  | |__) |  \| | | | |  \| | |  __ 
  \ \/  \/ / /\ \ |  _  /| . ` | | | | . ` | | |_ |
   \  /\  / ____ \| | \ \| |\  |_| |_| |\  | |__| |
    \/  \/_/    \_\_|  \_\_| \_|_____|_| \_|\_____|

 THIS SCRIPT IS DESIGNED TO REMOVE ALL THE OBJECT IN 
  A SPECIFIC ORGANIZATION! THESE CHANGES CAN'T BE 
   REVERT BACK. USE THIS SCRIPT AS YOUR OWN RISK

""")


if org_id == "":
    org_id = cli.select_org(mist_session)[0]
org_name = mist_lib.requests.orgs.info.get(mist_session, org_id)["result"]["name"]

check_org_name(org_name)
display_warning(f"Are you sure about this? Do you want to remove all the objects from the org {org_name} with the id {org_id} (y/N)? ")
display_warning(f"Are you REALLY sure about this? Once accepted, you won't be able to revert changes done on the org {org_name} with id {org_id} (y/N)? ")

print()
create_primary_site(org_id)
start_delete(org_id)

print()
console.notice(f"All objects removed... Organization {org_name} is back to default...")
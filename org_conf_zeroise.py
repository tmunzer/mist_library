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

org_id = "b9953384-e443-4e71-a1c7-ed26c44f44e9"
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
    print(object_name)
    req = mist_lib.requests.route("orgs", object_name)
    data = req.get(mist_session, org_id)["result"]
    for d in data:
        if not d["id"] in ids_to_not_delete:
            req.delete(mist_session, org_id, d["id"])

def display_warning(message):
    resp = "x"
    while not resp.lower() in ["y", "n", ""]:
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
                "mxclusters",
                "mxtunnels",
                "psks",
                "rftemplates",
                "secpolicies",
                "sitegroups",
                "templates",
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
    org_id = cli.select_site(mist_session)
org_name = mist_lib.requests.orgs.info.get(mist_session, org_id)["result"]["name"]

display_warning("Are you sure about this? Do you want to remove all the objects from the org %s with the id %s (y/N)? " %(org_name, org_id))
display_warning("Are you REALLY sure about this? Once accepted, you won't be able to revert changes done on the org %s with id %s (y/N)? " %(org_name, org_id))

create_primary_site(org_id)
start_delete(org_id)

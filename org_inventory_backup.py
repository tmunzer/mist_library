import mlib as mist_lib
import urllib.request
from mlib import cli
from tabulate import tabulate
import json

backup_file = "./org_inventory_file.json"
file_prefix = ".".join(backup_file.split(".")[:-1])
session_file = "./session.py"
org_id = "" #optional

mist_session = mist_lib.Mist_Session(session_file)
if org_id == "":
    org_id = cli.select_org(mist_session)

def backup_id_dict(xobject_name, xobject):
    backup["org"]["%s_id_dict" %xobject_name][xobject["name"]] = xobject["id"]


backup = {
    "org" : {
        "deviceprofile_id_dict" : {},
        "site_id_dict" : {},
        "map_id_dict" : {},
        "inventory" : [],
        "devices" : []
    }
}

inventory = mist_lib.requests.orgs.inventory.get(mist_session, org_id)["result"]
for data in inventory:
    backup["org"]["inventory"].append(data["magic"])

deviceprofiles = mist_lib.requests.orgs.deviceprofiles.get(mist_session, org_id)["result"]
for deviceprofile in deviceprofiles:
    backup_id_dict("deviceprofile", deviceprofile)

sites = mist_lib.requests.orgs.sites.get(mist_session, org_id)['result']
for site in sites:
    backup_id_dict("site", site)
    maps = mist_lib.requests.sites.maps.get(mist_session, site["id"])["result"]
    for xmap in maps:
        backup_id_dict("map", xmap)
    devices = mist_lib.requests.sites.devices.get(mist_session, site["id"])["result"]
    backup["org"]["devices"] += devices
    for device in devices:
        i = 1
        while "image%s_url"%i in device:
            url = device["image%s_url"%i]
            image_name = "%s_org_%s_device_%s_image_%s.png" %(file_prefix, org_id, device["id"], i)
            urllib.request.urlretrieve(url, image_name)
            i+=1



cli.show(backup)
print("saving to file...")
with open(backup_file, "w") as f:
    json.dump(backup, f)

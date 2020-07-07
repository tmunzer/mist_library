'''
Python script to backup a whole organization to file/s.
You can use the script "org_conf_restore.py" to restore the generated backup file to an
existing organization (the organization can be empty, but it must exist).

This script will not change/create/delete/touch any existing objects. It will just
get every single object from the organization, and save it into a file

You can configure some parameters at the beginning of the script if you want
to change the default settings.
You can run the script with the command "python3 org_conf_backup.py"

The script has 2 different steps:
1) admin login
2) choose the  org
3) nackup all the objects to the json file. 
'''
#### PARAMETERS #####
backup_file = "./org_conf_file.json"
file_prefix = ".".join(backup_file.split(".")[:-1])
session_file = "./session.py"

#### IMPORTS ####
import mlib as mist_lib
import os
import urllib.request
from mlib import cli
from tabulate import tabulate
import json
from mlib.__debug import Console
console = Console(6)

#### FUNCTIONS ####
def _backup_wlan_portal(org_id, site_id, wlans):  
    for wlan in wlans:     
        if site_id == None:
            portal_file_name = "%s_org_%s_wlan_%s.json" %(file_prefix, org_id, wlan["id"])
            portal_image = "%s_org_%s_wlan_%s.png" %(file_prefix, org_id, wlan["id"])
        else:
            portal_file_name = "%s_org_%s_site_%s_wlan_%s.json" %(file_prefix, org_id, site_id, wlan["id"]) 
            portal_image = "%s_org_%s_site_%s_wlan_%s.png" %(file_prefix, org_id, site_id, wlan["id"])
        if "portal_template_url" in wlan: urllib.request.urlretrieve(wlan["portal_template_url"], portal_file_name)
        if "portal_image" in wlan: urllib.request.urlretrieve(wlan["portal_image"], portal_image)
    


def _backup_full_org(mist_session, org_id, org_name):
    console.notice("ORG %s > Backup processing..." %(org_name))
    backup = {}
    backup["org"] = { "id": org_id}
    console.info("ORG %s > Backuping info" %(org_name))
    backup["org"]["data"] = mist_lib.requests.orgs.info.get(mist_session, org_id)["result"]
    console.info("ORG %s > Backuping settings" %(org_name))
    backup["org"]["settings"] = mist_lib.requests.orgs.settings.get(mist_session, org_id)["result"]
    console.info("ORG %s > Backuping webhooks" %(org_name))
    backup["org"]["webhooks"] = mist_lib.requests.orgs.webhooks.get(mist_session, org_id)["result"]
    console.info("ORG %s > Backuping assetfilters" %(org_name))
    backup["org"]["assetfilters"] = mist_lib.requests.orgs.assetfilters.get(mist_session, org_id)["result"]
    console.info("ORG %s > Backuping alarmtemplates" %(org_name))
    backup["org"]["alarmtemplates"] = mist_lib.requests.orgs.alarmtemplates.get(mist_session, org_id)["result"]
    console.info("ORG %s > Backuping deviceprofiles" %(org_name))
    backup["org"]["deviceprofiles"] = mist_lib.requests.orgs.deviceprofiles.get(mist_session, org_id)["result"]
    console.info("ORG %s > Backuping mxclusters" %(org_name))
    backup["org"]["mxclusters"] = mist_lib.requests.orgs.mxclusters.get(mist_session, org_id)["result"]
    console.info("ORG %s > Backuping mxtunnels" %(org_name))
    backup["org"]["mxtunnels"] = mist_lib.requests.orgs.mxtunnels.get(mist_session, org_id)["result"]
    console.info("ORG %s > Backuping psks" %(org_name))
    backup["org"]["psks"] = mist_lib.requests.orgs.psks.get(mist_session, org_id)["result"]
    console.info("ORG %s > Backuping rftemplates" %(org_name))
    backup["org"]["rftemplates"] = mist_lib.requests.orgs.rftemplates.get(mist_session, org_id)["result"]
    console.info("ORG %s > Backuping networktemplates" %(org_name))
    backup["org"]["rftemplates"] = mist_lib.requests.orgs.networktemplates.get(mist_session, org_id)["result"]
    console.info("ORG %s > Backuping secpolicies" %(org_name))
    backup["org"]["secpolicies"] = mist_lib.requests.orgs.secpolicies.get(mist_session, org_id)["result"]
    console.info("ORG %s > Backuping sitegroups" %(org_name))
    backup["org"]["sitegroups"] = mist_lib.requests.orgs.sitegroups.get(mist_session, org_id)["result"]
    console.info("ORG %s > Backuping ssos" %(org_name))
    backup["org"]["ssos"] = mist_lib.requests.orgs.ssos.get(mist_session, org_id)["result"]
    console.info("ORG %s > Backuping ssoroles" %(org_name))
    backup["org"]["ssoroles"] = mist_lib.requests.orgs.ssoroles.get(mist_session, org_id)["result"]
    console.info("ORG %s > Backuping templates" %(org_name))
    backup["org"]["templates"] = mist_lib.requests.orgs.templates.get(mist_session, org_id)["result"]
    console.info("ORG %s > Backuping wlans" %(org_name))
    backup["org"]["wlans"] = mist_lib.requests.orgs.wlans.get(mist_session, org_id)["result"]
    console.info("ORG %s > Backuping captive web prortals" %(org_name))
    _backup_wlan_portal(org_id, None, backup["org"]["wlans"])
    console.info("ORG %s > Backuping wxrules" %(org_name))
    backup["org"]["wxrules"] = mist_lib.requests.orgs.wxrules.get(mist_session, org_id)["result"]
    console.info("ORG %s > Backuping wxtags" %(org_name))
    backup["org"]["wxtags"] = mist_lib.requests.orgs.wxtags.get(mist_session, org_id)["result"]
    console.info("ORG %s > Backuping wxtunnels" %(org_name))
    backup["org"]["wxtunnels"] = mist_lib.requests.orgs.wxtunnels.get(mist_session, org_id)["result"]

    backup["org"]["sites"] = []

    sites = mist_lib.requests.orgs.sites.get(mist_session, org_id)['result']
    for site in sites:
        console.info("ORG %s > SITE %s > Backup processing..." %(org_name, site["name"]))
        console.info("ORG %s > SITE %s > Backuping assets" %(org_name, site["name"]))
        assets = mist_lib.requests.sites.assets.get(mist_session, site["id"])["result"]
        console.info("ORG %s > SITE %s > Backuping assetfilters" %(org_name, site["name"]))
        assetfilters = mist_lib.requests.sites.assetfilters.get(mist_session, site["id"])["result"]
        console.info("ORG %s > SITE %s > Backuping beacons" %(org_name, site["name"]))
        beacons = mist_lib.requests.sites.beacons.get(mist_session, site["id"])["result"]
        console.info("ORG %s > SITE %s > Backuping maps" %(org_name, site["name"]))
        maps = mist_lib.requests.sites.maps.get(mist_session, site["id"])["result"]
        console.info("ORG %s > SITE %s > Backuping psks" %(org_name, site["name"]))
        psks = mist_lib.requests.sites.psks.get(mist_session, site["id"])["result"]
        console.info("ORG %s > SITE %s > Backuping rssizones" %(org_name, site["name"]))
        rssizones = mist_lib.requests.sites.rssizones.get(mist_session, site["id"])["result"]
        console.info("ORG %s > SITE %s > Backuping settings" %(org_name, site["name"]))
        settings = mist_lib.requests.sites.settings.get(mist_session, site["id"])["result"]
        console.info("ORG %s > SITE %s > Backuping vbeacons" %(org_name, site["name"]))
        vbeacons = mist_lib.requests.sites.vbeacons.get(mist_session, site["id"])["result"]
        console.info("ORG %s > SITE %s > Backuping webhooks" %(org_name, site["name"]))
        webhooks = mist_lib.requests.sites.webhooks.get(mist_session, site["id"])["result"]
        console.info("ORG %s > SITE %s > Backuping wlans" %(org_name, site["name"]))
        wlans = mist_lib.requests.sites.wlans.get(mist_session, site["id"])["result"]
        console.info("ORG %s > SITE %s > Backuping captive web prortals" %(org_name, site["name"]))
        _backup_wlan_portal(org_id, site["id"], wlans)
        console.info("ORG %s > SITE %s > Backuping wxrules" %(org_name, site["name"]))
        wxrules = mist_lib.requests.sites.wxrules.get(mist_session, site["id"])["result"]
        console.info("ORG %s > SITE %s > Backuping wxtags" %(org_name, site["name"]))
        wxtags = mist_lib.requests.sites.wxtags.get(mist_session, site["id"])["result"]
        console.info("ORG %s > SITE %s > Backuping wxtunnels" %(org_name, site["name"]))
        wxtunnels = mist_lib.requests.sites.wxtunnels.get(mist_session, site["id"])["result"]
        console.info("ORG %s > SITE %s > Backuping zones" %(org_name, site["name"]))
        zones = mist_lib.requests.sites.zones.get(mist_session, site["id"])["result"]
        backup["org"]["sites"].append({
            "data": site, 
            "assetfilters": assetfilters,
            "assets": assets,
            "beacons": beacons, 
            "maps": maps, 
            "psks": psks, 
            "rssizones":rssizones,
            "settings": settings,
            "vbeacons": vbeacons, 
            "webhooks": webhooks,
            "wlans": wlans, 
            "wxrules": wxrules, 
            "wxtags": wxtags, 
            "wxtunnels": wxtunnels,
            "zones": zones
            })
        console.info("ORG %s > SITE %s > Backuping map images" %(org_name, site["name"]))
        for xmap in maps:
            if 'url' in xmap:
                url = xmap["url"]
                image_name = "%s_org_%s_site_%s_map_%s.png" %(file_prefix, org_id, site["id"], xmap["id"])
                urllib.request.urlretrieve(url, image_name)
        console.notice("ORG %s > SITE %s > Backup done" %(org_name, site["name"]))

    console.notice("ORG %s > Backup done" %(org_name))
    return backup

def _save_to_file(backup_file, backup):
    print("saving to file...")
    with open(backup_file, "w") as f:
        json.dump(backup, f)

def start_org_backup(mist_session, org_id, org_name):
    #try:
    if not os.path.exists("org_backup"):
        os.mkdir("org_backup")
    os.chdir("org_backup")
    if not os.path.exists(org_name):
        os.mkdir(org_name)
    os.chdir(org_name)

    backup = _backup_full_org(mist_session, org_id, org_name)
    _save_to_file(backup_file, backup)
    
    #except:
     #   return 255


def start(mist_session):
    org_id = cli.select_org(mist_session)[0]
    org_name = mist_lib.orgs.info.get(mist_session, org_id)["result"]["name"]
    start_org_backup(mist_session, org_id, org_name)


##### ENTRY POINT ####

if __name__ == "__main__":
    mist_session = mist_lib.Mist_Session(session_file)
    start(mist_session)
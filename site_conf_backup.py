'''
Written by Thomas Munzer (tmunzer@juniper.net)
Github repository: https://github.com/tmunzer/Mist_library/

Python script to backup a whole site to file/s.
You can use the script "site_conf_restore.py" to restore the generated backup file to an
existing organization (the organization can be empty, but it must exist).

This script will not change/create/delete/touch any existing objects. It will just
get every single object from the organization, and save it into a file

You can configure some parameters at the beginning of the script if you want
to change the default settings.
You can run the script with the command "python3 org_conf_backup.py"

The script has 3 different steps:
1) admin login
2) choose the  org
3) choose the site or sites to backup
3) backup all the objects to the json file. 
'''
#### PARAMETERS #####
backup_root_folder = "site_backup"
backup_file = "./site_conf_file.json"
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
            portal_file_name = "%s_wlan_%s.json" %(file_prefix, wlan["id"])
            portal_image = "%s_wlan_%s.png" %(file_prefix, wlan["id"])
        else:
            portal_file_name = "%s_site_%s_wlan_%s.json" %(file_prefix, site_id, wlan["id"]) 
            portal_image = "%s_site_%s_wlan_%s.png" %(file_prefix, site_id, wlan["id"])
        if "portal_template_url" in wlan: urllib.request.urlretrieve(wlan["portal_template_url"], portal_file_name)
        if "portal_image" in wlan: urllib.request.urlretrieve(wlan["portal_image"], portal_image)
    


def _backup_site(mist_session, site_id, site_name, org_id):
    console.notice("Backup: processing site %s..." %(site_name))
    site_backup = {
        "site": {
            "info": {},
            "settings": {}, 
            "assetfilters": {},
            "assets": {},
            "beacons": {}, 
            "maps": {}, 
            "psks": {}, 
            "rssizones":{},
            "settings": {},
            "vbeacons": {}, 
            "webhooks": {},
            "wlans": {}, 
            "wxrules": {}, 
            "wxtags": {}, 
            "wxtunnels": {},
            "zones": {}
        },
        "rftemplate": {},
        "secpolicy": {},
        "alarmtemplate": {},
        "networktemplate": {},
        "sitegroup_names": []   
    } 

    console.info("SITE %s > Backup processing..." %(site_name))
    console.info("SITE %s > Backuping assets" %(site_name))
    site_backup["site"]["assets"] = mist_lib.requests.sites.assets.get(mist_session, site_id)["result"]

    console.info("SITE %s > Backuping assetfilters" %(site_name))
    site_backup["site"]["assetfilters"] = mist_lib.requests.sites.assetfilters.get(mist_session, site_id)["result"]

    console.info("SITE %s > Backuping beacons" %(site_name))
    site_backup["site"]["beacons"] = mist_lib.requests.sites.beacons.get(mist_session, site_id)["result"]

    console.info("SITE %s > Backuping maps" %(site_name))
    site_backup["site"]["maps"] = mist_lib.requests.sites.maps.get(mist_session, site_id)["result"]

    console.info("SITE %s > Backuping psks" %(site_name))
    site_backup["site"]["psks"] = mist_lib.requests.sites.psks.get(mist_session, site_id)["result"]

    console.info("SITE %s > Backuping rssizones" %(site_name))
    site_backup["site"]["rssizones"] = mist_lib.requests.sites.rssizones.get(mist_session, site_id)["result"]

    console.info("SITE %s > Backuping vbeacons" %(site_name))
    site_backup["site"]["vbeacons"] = mist_lib.requests.sites.vbeacons.get(mist_session, site_id)["result"]

    console.info("SITE %s > Backuping webhooks" %(site_name))
    site_backup["site"]["webhooks"] = mist_lib.requests.sites.webhooks.get(mist_session, site_id)["result"]

    console.info("SITE %s > Backuping wlans" %(site_name))
    site_backup["site"]["wlans"] = mist_lib.requests.sites.wlans.get(mist_session, site_id)["result"]

    console.info("SITE %s > Backuping captive web prortals" %(site_name))
    _backup_wlan_portal(org_id, site_id, site_backup["site"]["wlans"])

    console.info("SITE %s > Backuping wxrules" %(site_name))
    site_backup["site"]["wxrules"] = mist_lib.requests.sites.wxrules.get(mist_session, site_id)["result"]

    console.info("SITE %s > Backuping wxtags" %(site_name))
    site_backup["site"]["wxtags"] = mist_lib.requests.sites.wxtags.get(mist_session, site_id)["result"]

    console.info("SITE %s > Backuping wxtunnels" %(site_name))
    site_backup["site"]["wxtunnels"] = mist_lib.requests.sites.wxtunnels.get(mist_session, site_id)["result"]

    console.info("SITE %s > Backuping zones" %(site_name))
    site_backup["site"]["zones"] = mist_lib.requests.sites.zones.get(mist_session, site_id)["result"]

    console.info("SITE %s > Backuping settings" %(site_name))
    site_backup["site"]["settings"] = mist_lib.requests.sites.settings.get(mist_session, site_id)["result"]

    console.info("SITE %s > Backuping info" %(site_name))
    site_backup["site"]["info"] = mist_lib.requests.sites.info.get(mist_session, site_id)["result"]
    if "rftemplate_id" in site_backup["site"]["info"] and site_backup["site"]["info"]["rftemplate_id"]:
        site_backup["rftemplate"] = mist_lib.requests.orgs.rftemplates.get_by_id(mist_session, org_id, site_backup["site"]["info"]["rftemplate_id"])["result"]
        
    if "secpolicy_id" in site_backup["site"]["info"] and site_backup["site"]["info"]["secpolicy_id"]:
        site_backup["secpolicy"] = mist_lib.requests.orgs.secpolicies.get_by_id(mist_session, org_id, site_backup["site"]["info"]["secpolicy_id"])["result"]

    if "alarmtemplate_id" in site_backup["site"]["info"] and site_backup["site"]["info"]["alarmtemplate_id"]:
        site_backup["alarmtemplate"] = mist_lib.requests.orgs.alarmtemplates.get_by_id(mist_session, org_id, site_backup["site"]["info"]["alarmtemplate_id"])["result"]

    if "networktemplate_id" in site_backup["site"]["info"] and site_backup["site"]["info"]["networktemplate_id"]:
        site_backup["networktemplate"] = mist_lib.requests.orgs.networktemplates.get_by_id(mist_session, org_id, site_backup["site"]["info"]["networktemplate_id"])["result"]

    if "sitegroup_ids" in site_backup["site"]["info"] and site_backup["site"]["info"]["sitegroup_ids"]:
        for sitegroup_id in site_backup["site"]["info"]["sitegroup_ids"]:
            sitegroup_info = mist_lib.requests.orgs.sitegroups.get_by_id(mist_session, org_id, sitegroup_id)["result"]
            if "name" in sitegroup_info:
                site_backup["sitegroup_names"].append(sitegroup_info["name"])

    console.info("SITE %s > Backuping map images" %(site_name))
    for xmap in site_backup["site"]["maps"]:
        if 'url' in xmap:
            url = xmap["url"]
            image_name = "%s_site_%s_map_%s.png" %(file_prefix, site_id, xmap["id"])
            urllib.request.urlretrieve(url, image_name)
    console.notice("SITE %s > Backup done" %(site_name))

    console.notice("Backup done")
    return site_backup

def _save_to_file(backup_file, backup):
    print("saving to file...")
    with open(backup_file, "w") as f:
        json.dump(backup, f)

def _goto_folder(folder_name):
    if not os.path.exists(folder_name):
        os.mkdir(folder_name)
    os.chdir(folder_name)
    

def start_site_backup(mist_session, org_id, org_name, site_ids):
    _goto_folder(backup_root_folder)
    _goto_folder(org_name)
    
    for site_id in site_ids:
        site_name = mist_lib.sites.info.get(mist_session, site_id)["result"]["name"]
        _goto_folder(site_name)

        backup = _backup_site(mist_session, site_id, site_name, org_id)
        _save_to_file(backup_file, backup)

        os.chdir("..")



def start(mist_session):
    org_id = cli.select_org(mist_session)[0]
    org_name = mist_lib.orgs.info.get(mist_session, org_id)["result"]["name"]
    site_id = cli.select_site(mist_session, org_id=org_id, allow_many=True)
    start_site_backup(mist_session, org_id, org_name, site_id)


##### ENTRY POINT ####

if __name__ == "__main__":
    print("Written by: Thomas Munzer (tmunzer@juniper.net)")
    print("")
    mist_session = mist_lib.Mist_Session(session_file)
    start(mist_session)
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
You can run the script with the command "python3 site_conf_backup.py"

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

def _backup_obj(m_func, obj_type):
    print("Backuping {0} ".format(obj_type).ljust(79, "."), end="", flush=True)
    try: 
        res = m_func["result"]
        print('\033[92m\u2714\033[0m')
    except:
        res = None
        print('\033[31m\u2716\033[0m')
    finally:
        return res


def _backup_wlan_portal(org_id, site_id, wlans):  
    for wlan in wlans:     
        if site_id == None:
            portal_file_name = "{0}_wlan_{1}.json".format(file_prefix, wlan["id"])
            portal_image = "{0}_wlan_{1}.png".format(file_prefix, wlan["id"])
        else:
            portal_file_name = "{0}_site_{1}_wlan_{2}.json".format(file_prefix, site_id, wlan["id"]) 
            portal_image = "{0]_site_{1}_wlan_{2}.png".format(file_prefix, site_id, wlan["id"])
        
        if "portal_template_url" in wlan: 
            print("Backuping portal template for WLAN {0} ".format(wlan["ssid"]).ljust(79, "."), end="", flush=True)
            try:
                urllib.request.urlretrieve(wlan["portal_template_url"], portal_file_name)
                print('\033[92m\u2714\033[0m')
            except:
                print('\033[31m\u2716\033[0m')
        if "portal_image" in wlan: 
            print("Backuping portal image for WLAN {0} ".format(wlan["ssid"]).ljust(79, "."), end="", flush=True)
            try:
                urllib.request.urlretrieve(wlan["portal_image"], portal_image)
                print('\033[92m\u2714\033[0m')
            except:
                print('\033[31m\u2716\033[0m')
    

def _backup_site(mist_session, site_id, site_name, org_id):
    print()
    console.info("Backup: processing site {0} ...".format(site_name))
    print()
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

    site_backup["site"]["settings"] = _backup_obj(mist_lib.requests.sites.settings.get(mist_session, site_id), "site settings")

    site_backup["site"]["info"] = _backup_obj(mist_lib.requests.sites.info.get(mist_session, site_id), "site info")

    site_backup["site"]["assets"] = _backup_obj(mist_lib.requests.sites.assets.get(mist_session, site_id), "assets")
    
    site_backup["site"]["assetfilters"] = _backup_obj(mist_lib.requests.sites.assetfilters.get(mist_session, site_id), "assetfilters")

    site_backup["site"]["beacons"] = _backup_obj(mist_lib.requests.sites.beacons.get(mist_session, site_id), "beacons")

    site_backup["site"]["maps"] = _backup_obj(mist_lib.requests.sites.maps.get(mist_session, site_id), "maps")

    site_backup["site"]["psks"] = _backup_obj(mist_lib.requests.sites.psks.get(mist_session, site_id), "psks")

    site_backup["site"]["rssizones"] = _backup_obj(mist_lib.requests.sites.rssizones.get(mist_session, site_id), "rssizones")

    site_backup["site"]["vbeacons"] = _backup_obj(mist_lib.requests.sites.vbeacons.get(mist_session, site_id), "vbeacons")

    site_backup["site"]["webhooks"] = _backup_obj(mist_lib.requests.sites.webhooks.get(mist_session, site_id), "webhooks")

    site_backup["site"]["wlans"] = _backup_obj(mist_lib.requests.sites.wlans.get(mist_session, site_id), "wlans")

    _backup_wlan_portal(org_id, site_id, site_backup["site"]["wlans"])

    site_backup["site"]["wxrules"] = _backup_obj(mist_lib.requests.sites.wxrules.get(mist_session, site_id), "wxrules")

    site_backup["site"]["wxtags"] = _backup_obj(mist_lib.requests.sites.wxtags.get(mist_session, site_id), "wxtags")

    site_backup["site"]["wxtunnels"] = _backup_obj(mist_lib.requests.sites.wxtunnels.get(mist_session, site_id), "wxtunnels")

    site_backup["site"]["zones"] = _backup_obj(mist_lib.requests.sites.zones.get(mist_session, site_id), "zones")

    if "rftemplate_id" in site_backup["site"]["info"] and site_backup["site"]["info"]["rftemplate_id"]:
        site_backup["rftemplate"] = _backup_obj(mist_lib.requests.orgs.rftemplates.get_by_id(mist_session, org_id, site_backup["site"]["info"]["rftemplate_id"]), "RF Template")
        
    if "secpolicy_id" in site_backup["site"]["info"] and site_backup["site"]["info"]["secpolicy_id"]:
        site_backup["secpolicy"] = _backup_obj(mist_lib.requests.orgs.secpolicies.get_by_id(mist_session, org_id, site_backup["site"]["info"]["secpolicy_id"]), "Security Policy")

    if "alarmtemplate_id" in site_backup["site"]["info"] and site_backup["site"]["info"]["alarmtemplate_id"]:
        site_backup["alarmtemplate"] = _backup_obj(mist_lib.requests.orgs.alarmtemplates.get_by_id(mist_session, org_id, site_backup["site"]["info"]["alarmtemplate_id"]), "Alarm Template")

    if "networktemplate_id" in site_backup["site"]["info"] and site_backup["site"]["info"]["networktemplate_id"]:
        site_backup["networktemplate"] = _backup_obj(mist_lib.requests.orgs.networktemplates.get_by_id(mist_session, org_id, site_backup["site"]["info"]["networktemplate_id"]), "Network Tempalte")

    if "sitegroup_ids" in site_backup["site"]["info"] and site_backup["site"]["info"]["sitegroup_ids"]:
        for sitegroup_id in site_backup["site"]["info"]["sitegroup_ids"]:
            sitegroup_info = mist_lib.requests.orgs.sitegroups.get_by_id(mist_session, org_id, sitegroup_id)["result"]
            if "name" in sitegroup_info:
                site_backup["sitegroup_names"].append(sitegroup_info["name"])

    for xmap in site_backup["site"]["maps"]:
        if 'url' in xmap:
            print("Backuping image for map {0} ".format(xmap["name"]).ljust(79, "."), end="", flush=True) 
            try:           
                url = xmap["url"]
                image_name = "{0}_site_{1}_map_{2}.png".format(file_prefix, site_id, xmap["id"])
                urllib.request.urlretrieve(url, image_name)
                print('\033[92m\u2714\033[0m')
            except:
                print('\033[31m\u2716\033[0m')

    return site_backup

def _save_to_file(backup_file, backup):
    print("Saving backup to {0} file...".format(backup_file).ljust(79, "."), end="", flush=True)
    try:
        
        with open(backup_file, "w") as f:
            json.dump(backup, f)
        print('\033[92m\u2714\033[0m')
    except:
        print('\033[31m\u2716\033[0m')

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
        print()
        console.info("Backup done for site {0}".format(site_name))
        print()

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
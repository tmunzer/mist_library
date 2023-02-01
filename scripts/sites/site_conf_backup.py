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

#### IMPORTS ####
import mistapi
from mistapi.__logger import console
import os
import urllib.request
import json
import logging

#### PARAMETERS #####
backup_root_folder = "site_backup"
backup_file = "./site_conf_file.json"
file_prefix = ".".join(backup_file.split(".")[:-1])
log_file = "./site_conf_backup.log"
env_file = "./.env"
#### LOGS ####
logger = logging.getLogger(__name__)

#### FUNCTIONS ####

def _backup_obj(m_func, obj_type):
    print(f"Backuping {obj_type} ".ljust(79, "."), end="", flush=True)
    try: 
        res = m_func.data
        print('\033[92m\u2714\033[0m')
    except:
        res = None
        print('\033[31m\u2716\033[0m')
    finally:
        return res


def _backup_wlan_portal(org_id, site_id, wlans):  
    for wlan in wlans:     
        if not site_id:
            portal_file_name = f"{file_prefix}_wlan_{wlan['id']}.json"
            portal_image = f"{file_prefix}_wlan_{wlan['id']}.png"
        else:
            portal_file_name = f"{file_prefix}_site_{site_id}_wlan_{wlan['id']}.json"
            portal_image = f"{file_prefix}_site_{site_id}_wlan_{wlan['id']}.png"
        
        if "portal_template_url" in wlan: 
            print(f"Backuping portal template for WLAN {wlan['ssid']} ".ljust(79, "."), end="", flush=True)
            try:
                urllib.request.urlretrieve(wlan["portal_template_url"], portal_file_name)
                print('\033[92m\u2714\033[0m')
            except:
                print('\033[31m\u2716\033[0m')
        if "portal_image" in wlan: 
            print(f"Backuping portal image for WLAN {wlan['ssid']} ".ljust(79, "."), end="", flush=True)
            try:
                urllib.request.urlretrieve(wlan["portal_image"], portal_image)
                print('\033[92m\u2714\033[0m')
            except:
                print('\033[31m\u2716\033[0m')
    

def _backup_site(apisession, site_id, site_name, org_id):
    print()
    console.info(f"Backup: processing site {site_name} ...")
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

    site_backup["site"]["settings"] = _backup_obj(mistapi.api.v1.sites.setting.getSiteSetting(apisession, site_id), "site settings")

    site_backup["site"]["info"] = _backup_obj(mistapi.api.v1.sites.sites.getSiteInfo(apisession, site_id), "site info")

    site_backup["site"]["assets"] = _backup_obj(mistapi.api.v1.sites.assets.getSiteAssets(apisession, site_id), "assets")
    
    site_backup["site"]["assetfilters"] = _backup_obj(mistapi.api.v1.sites.assetfilters.getSiteAssetFilters(apisession, site_id), "assetfilters")

    site_backup["site"]["beacons"] = _backup_obj(mistapi.api.v1.sites.beacons.getSiteBeacons(apisession, site_id), "beacons")

    site_backup["site"]["maps"] = _backup_obj(mistapi.api.v1.sites.maps.getSiteMaps(apisession, site_id), "maps")

    site_backup["site"]["psks"] = _backup_obj(mistapi.api.v1.sites.psks.getSitePsks(apisession, site_id), "psks")

    site_backup["site"]["rssizones"] = _backup_obj(mistapi.api.v1.sites.rssizones.getSiteRssiZones(apisession, site_id), "rssizones")

    site_backup["site"]["vbeacons"] = _backup_obj(mistapi.api.v1.sites.vbeacons.getSiteVBeacons(apisession, site_id), "vbeacons")

    site_backup["site"]["webhooks"] = _backup_obj(mistapi.api.v1.sites.webhooks.getSiteWebhooks(apisession, site_id), "webhooks")

    site_backup["site"]["wlans"] = _backup_obj(mistapi.api.v1.sites.wlans.getSiteWlans(apisession, site_id), "wlans")

    _backup_wlan_portal(org_id, site_id, site_backup["site"]["wlans"])

    site_backup["site"]["wxrules"] = _backup_obj(mistapi.api.v1.sites.wxrules.getSiteWxRules(apisession, site_id), "wxrules")

    site_backup["site"]["wxtags"] = _backup_obj(mistapi.api.v1.sites.wxtags.getSiteWxTags(apisession, site_id), "wxtags")

    site_backup["site"]["wxtunnels"] = _backup_obj(mistapi.api.v1.sites.wxtunnels.getSiteWxTunnels(apisession, site_id), "wxtunnels")

    site_backup["site"]["zones"] = _backup_obj(mistapi.api.v1.sites.zones.getSiteZones(apisession, site_id), "zones")

    if "rftemplate_id" in site_backup["site"]["info"] and site_backup["site"]["info"]["rftemplate_id"]:
        site_backup["rftemplate"] = _backup_obj(mistapi.api.v1.orgs.rftemplates.getOrgRfTemplate(apisession, org_id, site_backup["site"]["info"]["rftemplate_id"]), "RF Template")
        
    if "secpolicy_id" in site_backup["site"]["info"] and site_backup["site"]["info"]["secpolicy_id"]:
        site_backup["secpolicy"] = _backup_obj(mistapi.api.v1.orgs.secpolicies.getOrgSecPolicy(apisession, org_id, site_backup["site"]["info"]["secpolicy_id"]), "Security Policy")

    if "alarmtemplate_id" in site_backup["site"]["info"] and site_backup["site"]["info"]["alarmtemplate_id"]:
        site_backup["alarmtemplate"] = _backup_obj(mistapi.api.v1.orgs.alarmtemplates.getOrgAlarmTemplate(apisession, org_id, site_backup["site"]["info"]["alarmtemplate_id"]), "Alarm Template")

    if "networktemplate_id" in site_backup["site"]["info"] and site_backup["site"]["info"]["networktemplate_id"]:
        site_backup["networktemplate"] = _backup_obj(mistapi.api.v1.orgs.networktemplates.getOrgNetworkTemplate(apisession, org_id, site_backup["site"]["info"]["networktemplate_id"]), "Network Tempalte")

    if "sitegroup_ids" in site_backup["site"]["info"] and site_backup["site"]["info"]["sitegroup_ids"]:
        for sitegroup_id in site_backup["site"]["info"]["sitegroup_ids"]:
            sitegroup_info = mistapi.api.v1.orgs.sitegroups.getOrgSiteGroup(apisession, org_id, sitegroup_id).data
            if "name" in sitegroup_info:
                site_backup["sitegroup_names"].append(sitegroup_info["name"])

    for xmap in site_backup["site"]["maps"]:
        if 'url' in xmap:
            print(f"Backuping image for map {xmap['name']} ".ljust(79, "."), end="", flush=True) 
            try:           
                url = xmap["url"]
                image_name = f"{file_prefix}_site_{site_id}_map_{xmap['id']}.png"
                urllib.request.urlretrieve(url, image_name)
                print('\033[92m\u2714\033[0m')
            except:
                print('\033[31m\u2716\033[0m')

    return site_backup

def _save_to_file(backup_file, backup):
    print(f"Saving backup to {backup_file} file...".ljust(79, "."), end="", flush=True)
    try:
        
        with open(backup_file, "w") as f:
            json.dump(backup, f)
        print('\033[92m\u2714\033[0m')
    except:
        print('\033[31m\u2716\033[0m')

def _goto_folder(folder_name):
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
    os.chdir(folder_name)
    

def start_site_backup(apisession, org_id, org_name, site_ids):
    _goto_folder(backup_root_folder)
    _goto_folder(org_name)
    
    for site_id in site_ids:
        site_name = mistapi.api.v1.sites.sites.getSiteInfo(apisession, site_id).data["name"]
        _goto_folder(site_name)

        backup = _backup_site(apisession, site_id, site_name, org_id)
        _save_to_file(backup_file, backup)
        print()
        console.info(f"Backup done for site {site_name}")
        print()

        os.chdir("..")



def start(apisession):
    org_id = mistapi.cli.select_org(apisession)[0]
    org_name = mistapi.api.v1.orgs.orgs.getOrgInfo(apisession, org_id=org_id).data["name"]
    site_id = mistapi.cli.select_site(apisession, org_id=org_id, allow_many=True)
    start_site_backup(apisession, org_id, org_name, site_id)


##### ENTRY POINT ####

if __name__ == "__main__":
    #### LOGS ####
    logging.basicConfig(filename=log_file, filemode='w')
    logger.setLevel(logging.DEBUG)
    ### START ###
    apisession = mistapi.APISession(env_file=env_file)
    apisession.login()
    start(apisession)

'''
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

session_file = ""
backup_directory = "./backup/"

org_id = ""
#### IMPORTS ####

import mlib as mist_lib
from mlib.__debug import Console
from mlib import cli
from tabulate import tabulate
import json
import os.path

#### CONSTANTS ####
console = Console(6)
backup_file = "./org_conf_file.json"
file_prefix = ".".join(backup_file.split(".")[:-1])


#### GLOBAL VARS ####


rftemplate_id_dict = {}
site_id_dict = {}
sitegroup_id_dict = {}
map_id_dict = {}
deviceprofile_id_dict = {}
template_id_dict = {}
mxtunnel_id_dict = {}
wxtunnel_id_dict = {}
secpolicy_id_dict = {}
wxtags_id_dict = {}
mxcluster_id_dict = {}
wlan_id_dict = {}
alarmtemplate_id_dict = {}


#### FUNCTIONS ####

def _get_new_id(old_id, new_ids_dict):
    if old_id in new_ids_dict:
        new_id = new_ids_dict[old_id]
        console.debug("Replacing id %s with id %s" %(old_id, new_id))
        return new_id
    else:
        console.debug("Unable to replace id %s" %old_id)
        return None


def _replace_id(old_ids_list, new_ids_dict):
    if old_ids_list == None:
        return None
    if old_ids_list == {}:
        return {}
    elif type(old_ids_list) == str:
        return _get_new_id(old_ids_list, new_ids_dict)
    elif type(old_ids_list) == list:
        new_ids_list = []
        for old_id in old_ids_list:
            new_ids_list.append(_get_new_id(old_id, new_ids_dict))
        return new_ids_list
    else:
        console.error("Unable to replace ids: %s" % old_ids_list)

def _clean_ssorole_privileges(user):
    cleaned_privileges = []
    for privilege in user["privileges"]:
        if "org_id" in privilege: 
            privilege["org_id"] = org_id
        if "site_id" in privilege: 
            privilege["site_id"] = _replace_id(privilege["site_id"], site_id_dict)
        if "sitegroup_id" in privilege: 
            privilege["sitegroup_id"] = _replace_id(privilege["sitegroup_id"], sitegroup_id_dict)
        cleaned_privileges.append(privilege)
    return cleaned_privileges

def _clean_ids(data):
    if "id" in data:
        del data["id"]
    if "org_id" in data:
        del data["org_id"]
    if "modified_time" in data:
        del data["modified_time"]
    if "created_time" in data:
        del data["created_time"]
    return data


def _common_restore(mist_session, org_name, site_name, level, level_id, object_name, data):
    if site_name: site_text = " SITE %s >" %(site_name)
    else: site_text = ""
    console.info("ORG %s >%s Restoring %s..." %(org_name, site_text, object_name))
    old_id = data["id"]
    data = _clean_ids(data)
    module = mist_lib.requests.route(level, object_name)
    new_id = module.create(mist_session, level_id, data)["result"]["id"]
    return {old_id: new_id}


def _wlan_restore(mist_session, org_name, site_name, level, level_id, data, old_org_id, old_site_id):
    if "template_id" in data:
        data["template_id"] = _replace_id(data["template_id"], template_id_dict)
    if "wxtunnel_id" in data:
        data["wxtunnel_id"] = _replace_id(data["wxtunnel_id"], wxtags_id_dict)
    if "mxtunnel_id" in data:
        data["mxtunnel_id"] = _replace_id(data["mxtunnel_id"], mxtunnel_id_dict)
    if "app_limit" in data and "wxtag_ids" in data["app_limit"]:
        data["app_limit"]["wxtag_ids"] = _replace_id(data["app_limit"]["wxtag_ids"], wxtags_id_dict)
    ids = _common_restore(mist_session, org_name, site_name, level, level_id, 'wlans', data)
    old_wlan_id = next(iter(ids))
    new_wlan_id = ids[old_wlan_id]
    _wlan_restore_portal(mist_session, org_name, site_name,level_id, old_org_id, old_site_id, old_wlan_id, new_wlan_id)
    wlan_id_dict.update(ids)

def _wlan_restore_portal(mist_session, org_name, site_name,level_id, old_org_id, old_site_id, old_wlan_id, new_wlan_id): 
        if old_site_id == None:
            portal_file_name = "%s_org_%s_wlan_%s.json" %(file_prefix, old_org_id, old_wlan_id)
            portal_image = "%s_org_%s_wlan_%s.png" %(file_prefix, old_org_id, old_wlan_id)
            module = mist_lib.requests.route("orgs", "wlans")
        else:
            portal_file_name = "%s_org_%s_site_%s_wlan_%s.json" %(file_prefix, old_org_id, old_site_id, old_wlan_id) 
            portal_image = "%s_org_%s_site_%s_wlan_%s.png" %(file_prefix, old_org_id, old_site_id, old_wlan_id)
            module = mist_lib.requests.route("sites", "wlans")

        if site_name: site_text = " SITE %s >" %(site_name)
        else: site_text = "" 
        if os.path.isfile(portal_file_name):
            console.info("ORG %s >%s Restoring portal template %s..." %(org_name, site_text, portal_file_name))
            template = open(portal_file_name, 'r')
            template = json.load(template)
            module.set_portal_template(mist_session, level_id, new_wlan_id, template)
        else: console.warning("ORG %s >%s Portal template %s not found" %(org_name, site_text, portal_file_name))
        if os.path.isfile(portal_image):
            console.notice("ORG %s >%s Restoring portal image %s..." %(org_name, site_text, portal_image))
            module.add_portal_image(mist_session, level_id, new_wlan_id, portal_image)
        else: console.warning("ORG %s >%s Portal image %s not found" %(org_name, site_text, portal_image))
        

def _restore_org(mist_session, org_id, org_name, org):
    ####  ORG MAIN  ####
    data = org["data"]
    old_org_id = data["id"]
    # console.debug(json.dumps(data))
    del data["id"]
    if "orggroup_ids" in data:
        del data["orggroup_ids"]
    if "msp_id" in data:
        del data["msp_id"]
    if "msp_name" in data:
        del data["msp_name"]
    mist_lib.requests.orgs.info.update(mist_session, org_id, data)

    ####  ORG SETTINGS  ####
    data = _clean_ids(org["settings"])
    mist_lib.requests.orgs.settings.update(mist_session, org_id, data)
    
    ####  ORG OBJECTS  ####
    for data in org["webhooks"]:
        _common_restore(mist_session, org_name, None, 'orgs', org_id, 'webhooks', data)

    for data in org["assetfilters"]:
        _common_restore(mist_session, org_name, None, 'orgs',  org_id, 'assetfilters', data)

    for data in org["deviceprofiles"]:
        ids = _common_restore(mist_session, org_name, None, 'orgs',  org_id, 'deviceprofiles', data)
        deviceprofile_id_dict.update(ids)

    for data in org["alarmtemplates"]:
        ids = _common_restore(mist_session, org_name, None, 'orgs',  org_id, 'alarmtemplates', data)
        deviceprofile_id_dict.update(ids)

    for data in org["mxclusters"]:
        ids = _common_restore(mist_session, org_name, None, 'orgs',  org_id, 'mxclusters', data)
        mxcluster_id_dict.update(ids)

    for data in org["mxtunnels"]:
        data["mxcluster_ids"] = _replace_id(
            data["mxcluster_ids"], mxcluster_id_dict)
        ids = _common_restore(mist_session, org_name, None, 'orgs',  org_id, 'mxtunnels', data)
        mxtunnel_id_dict.update(ids)

    for data in org["psks"]:
        _common_restore(mist_session, org_name, None, 'orgs', org_id, 'psks', data)

    for data in org["secpolicies"]:
        ids = _common_restore(mist_session, org_name, None, 'orgs', org_id, 'secpolicies', data)
        secpolicy_id_dict.update(ids)

    for data in org["rftemplates"]:
        ids = _common_restore(mist_session, org_name, None, 'orgs', org_id, 'rftemplates', data)
        rftemplate_id_dict.update(ids)

    for data in org["sitegroups"]:
        if "site_ids" in data: del data["site_ids"]
        ids = _common_restore(mist_session, org_name, None, 'orgs', org_id, 'sitegroups', data)
        sitegroup_id_dict.update(ids)    

    for data in org["wxtags"]:
        if data["match"] == "wlan_id":
            _replace_id(data["values"], wlan_id_dict)
        ids = _common_restore(mist_session, org_name, None, 'orgs', org_id, 'wxtags', data)
        wxtags_id_dict.update(ids)

    for data in org["wxrules"]:
        data["src_wxtags"] = _replace_id(data["src_wxtags"], wxtags_id_dict)
        data["dst_allow_wxtags"] = _replace_id(data["dst_allow_wxtags"], wxtags_id_dict)
        data["dst_deny_wxtags"] = _replace_id(data["dst_deny_wxtags"], wxtags_id_dict)
        _common_restore(mist_session, org_name, None, 'orgs',  org_id, 'wxrules', data)

    for data in org["wxtunnels"]:
        ids = _common_restore(mist_session, org_name, None, 'orgs', org_id, 'wxtunnels', data)
        wxtunnel_id_dict.update(ids)


    ####  SITES LOOP  ####
    for data in org["sites"]:
        ####  SITES MAIN  ####
        site = data["data"]
        old_site_id = site["id"]
        if "rftemplate_id" in site:
            site["rftemplate_id"] = _replace_id(site["rftemplate_id"], rftemplate_id_dict)
        if "secpolicy_id" in site:
            site["secpolicy_id"] = _replace_id(site["secpolicy_id"], secpolicy_id_dict)
        if "alarmtemplate_id" in site:
            site["alarmtemplate_id"] = _replace_id(site["alarmtemplate_id"], alarmtemplate_id_dict)
        if "sitegroup_ids" in site:
            site["sitegroup_ids"] = _replace_id(site["sitegroup_ids"], sitegroup_id_dict)
        ids = _common_restore(mist_session, org_name, site["name"], 'orgs',  org_id, 'sites', site)
        site_id_dict.update(ids)
        new_site_id = ids[next(iter(ids))]

        settings = _clean_ids(data["settings"])
        if "site_id" in settings: del settings["site_id"]
        mist_lib.requests.sites.settings.update(
            mist_session, new_site_id, settings)

        if "maps" in data:
            for sub_data in data["maps"]:
                sub_data["site_id"] = new_site_id
                ids = _common_restore(mist_session, org_name, site["name"], 'sites', new_site_id, 'maps', sub_data)
                map_id_dict.update(ids)

                old_map_id = next(iter(ids))
                new_map_id = ids[old_map_id]
                image_name = "%s_org_%s_site_%s_map_%s.png" %(file_prefix, old_org_id, old_site_id, old_map_id)
                if os.path.isfile(image_name):
                    console.info("Image %s will be restored to map %s" %(image_name, new_map_id))
                    mist_lib.requests.sites.maps.add_image(mist_session, new_site_id, new_map_id, image_name)
                else:
                    console.info("No image found for old map id %s" % old_map_id)


        if "assetfilters" in data:
            for sub_data in data["assetfilters"]:
                _common_restore(mist_session, org_name, site["name"], 'sites', new_site_id, 'assetfilters', sub_data)

        if "assets" in data:
            for sub_data in data["assets"]:
                _common_restore(mist_session, org_name, site["name"], 'sites', new_site_id, 'assets', sub_data)

        if "beacons" in data:
            for sub_data in data["beacons"]:
                sub_data["map_id"] = _replace_id(sub_data["map_id"], map_id_dict)
                _common_restore(mist_session, org_name, site["name"], 'sites', new_site_id, 'beacons', sub_data)

        if "psks" in data:
            for sub_data in data["psks"]:
                sub_data["site_id"] = new_site_id
                _common_restore(mist_session, org_name, site["name"], 'sites', new_site_id, 'psks', sub_data)

        if "rssizones" in data:
            for sub_data in data["rssizones"]:
                _common_restore(mist_session, org_name, site["name"], 'sites', new_site_id, 'rssizones', sub_data)

        if "vbeacons" in data:
            for sub_data in data["vbeacons"]:
                sub_data["map_id"] = _replace_id(sub_data["map_id"], map_id_dict)
                _common_restore(mist_session, org_name, site["name"], 'sites', new_site_id, 'vbeacons', sub_data)

        if "webhooks" in data:
            for sub_data in data["webhooks"]:
                _common_restore(mist_session, org_name, site["name"], 'sites', new_site_id, 'webhooks', sub_data)

        if "wxtunnels" in data:
            for sub_data in data["wxtunnels"]:
                ids = _common_restore(mist_session, org_name, site["name"], 'sites', new_site_id,'wxtunnels', sub_data)
                wxtunnel_id_dict.update(ids)

        if "zones" in data:
            for sub_data in data["zones"]:
                sub_data["map_id"] = _replace_id(sub_data["map_id"], map_id_dict)
                _common_restore(mist_session, org_name, site["name"], 'sites', new_site_id, 'zones', sub_data)
        
        if "wlans" in data:
            for sub_data in data["wlans"]:
                _wlan_restore(mist_session, org_name, site["name"], 'sites', new_site_id, sub_data, old_org_id, old_site_id)

        if "wxtags" in data:
            for sub_data in data["wxtags"]:
                if sub_data["match"] == "wlan_id":
                    _replace_id(sub_data["values"], wlan_id_dict)
                ids = _common_restore(mist_session, org_name, site["name"], 'sites', new_site_id, 'wxtags', sub_data)
                wxtags_id_dict.update(ids)

        if "wxrules" in data:
            for sub_data in data["wxrules"]:
                if "src_wxtags" in sub_data:
                    sub_data["src_wxtags"] = _replace_id(sub_data["src_wxtags"], wxtags_id_dict)
                if "dst_allow_wxtags" in sub_data:
                    sub_data["dst_allow_wxtags"] = _replace_id(sub_data["dst_allow_wxtags"], wxtags_id_dict)
                if "dst_deny_wxtags" in sub_data:
                    sub_data["dst_deny_wxtags"] = _replace_id(sub_data["dst_deny_wxtags"], wxtags_id_dict)
                _common_restore(mist_session, org_name, site["name"], 'sites', new_site_id, 'wxrules', sub_data)

    for data in org["templates"]:
        if "applies" in data:
            if "org_id" in data["applies"]:
                data["applies"]["org_id"] = org_id
            if "site_ids" in data["applies"]:
                data["applies"]["site_ids"] = _replace_id(data["applies"]["site_ids"], site_id_dict)
            if "sitegroup_ids" in data["applies"]:
                data["applies"]["sitegroup_ids"] = _replace_id(data["applies"]["sitegroup_ids"], sitegroup_id_dict)
        if "exceptions" in data:
            if "site_ids" in data["exceptions"]:
                data["exceptions"]["site_ids"] = _replace_id(data["exceptions"]["site_ids"], site_id_dict)
            if "sitegroup_ids" in data["exceptions"]:
                data["exceptions"]["sitegroup_ids"] = _replace_id(data["exceptions"]["sitegroup_ids"], sitegroup_id_dict)
        if "deviceprofile_ids" in data:
            data["deviceprofile_ids"] = _replace_id(data["deviceprofile_ids"], deviceprofile_id_dict)
        ids = _common_restore(mist_session, org_name, None, 'orgs', org_id, 'templates', data)
        template_id_dict.update(ids)

    for data in org["wlans"]:
        _wlan_restore(mist_session, org_name, None, 'orgs', org_id, data, old_org_id, None)

    for data in org["ssos"]: _common_restore(mist_session, org_name, None, 'orgs', org_id, 'ssos', data)

    for data in org["ssoroles"]:
        cleaned_data = []
        for ssorole in data:
            cleaned_data.append(_clean_ssorole_privileges(ssorole))
        _common_restore(mist_session, org_name, None, 'orgs', org_id, 'ssoroles', cleaned_data)    

def _display_warning(message):
    resp = "x"
    while not resp.lower() in ["y", "n", ""]:
        print()
        resp = input(message)
    if not resp.lower()=="y":
        console.warning("Interruption... Exiting...")
        exit(0)

def _select_backup_folder(folders):   
    i = 0
    print("Available backups:")
    while i < len(folders):
        print("%s) %s" %(i, folders[i]))
        i += 1
    folder = None
    while folder == None:
        resp = input("Which backup do you want to restore (0-%s, or x or exit)? "  %i)
        if resp.lower() == "x":
            console.warning("Interruption... Exiting...")
        try:
            respi = int(resp)
            if respi >= 0 and respi <= i:
                folder = folders[respi]
            else:
                print("The entry value \"%s\" is not valid. Please try again...")
        except:
            print("Only numbers are allowed. Please try again...")
    os.chdir(folder)

def _go_to_backup_folder(source_org_name=None):
    os.chdir(os.getcwd())
    os.chdir(backup_directory)
    folders = []
    for entry in os.listdir("./"):
        if os.path.isdir(os.path.join("./", entry)):
            folders.append(entry)
    if source_org_name in folders:
        print("Backup found for organization %s." %(source_org_name))
        loop = True
        while loop:
            resp = input("Do you want to use this backup (y/n)? ")
            if resp.lower == "y":
                loop = False    
                try:
                    os.chdir(source_org_name)
                except:
                    _select_backup_folder(folders)
            else:
                loop = False    
                _select_backup_folder(folders)
    else:
        print("Backup folder for organization %s not found. Please select a folder in the following list." %(source_org_name))
        _select_backup_folder(folders)

def _print_warning():
    print(""" 

__          __     _____  _   _ _____ _   _  _____ 
\ \        / /\   |  __ \| \ | |_   _| \ | |/ ____|
 \ \  /\  / /  \  | |__) |  \| | | | |  \| | |  __ 
  \ \/  \/ / /\ \ |  _  /| . ` | | | | . ` | | |_ |
   \  /\  / ____ \| | \ \| |\  |_| |_| |\  | |__| |
    \/  \/_/    \_\_|  \_\_| \_|_____|_| \_|\_____|

This script is still in BETA. It won't hurt your original
organization, but the restoration may partially fail. 
It's your responsability to validate the importation result!


""")

def _check_org_name(org_name):
    while True:
        print()
        resp = input("To avoid any error, please confirm the current destination orgnization name: ")
        if resp == org_name:
            return True
        else:
            console.warning("The orgnization names do not match... Please try again...")


def start_restore_org(mist_session, org_id, org_name, source_org_name, check_org_name=True, in_backup_folder=False):
    if check_org_name: _check_org_name(org_name)
    if not in_backup_folder: _go_to_backup_folder(source_org_name)
    try:
        with open(backup_file) as f:
            backup = json.load(f)
    except: 
        print("unable to load the file backup %s" %(backup_file))
    finally:
        if backup:
            console.info("File %s loaded succesfully." %backup_file)
            _display_warning("Are you sure about this? Do you want to import the configuration into the organization %s with the id %s (y/N)? " %(org_name, org_id))
            _restore_org(mist_session, org_id, org_name, backup["org"])
            print()
            console.notice("Restoration process finished...")

def start(mist_session, org_id=None):
    if org_id == "":
        org_id = cli.select_org(mist_session)
    org_name = mist_lib.requests.orgs.info.get(mist_session, org_id)["result"]["name"]
    start_restore_org(mist_session, org_id, org_name, None)


#### SCRIPT ENTRYPOINT ####


if __name__ == "__main__":
    mist_session = mist_lib.Mist_Session(session_file)
    start(mist_session, org_id)



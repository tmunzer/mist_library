'''
Written by Thomas Munzer (tmunzer@juniper.net)
Github repository: https://github.com/tmunzer/Mist_library/

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
3) backup all the objects to the json file. 
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
import json
import logging


#### LOGS ####
logging.basicConfig(filename="./script.log", filemode='w')
#logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)



#### FUNCTIONS ####
def _backup_wlan_portal(org_id, site_id, wlans):
    for wlan in wlans:
        wlan_id = wlan["id"]
        # wlan_id = wlan.id
        if site_id == None:
            portal_file_name = "{0}_org_{1}_wlan_{2}.json".format(file_prefix, org_id, wlan_id)
            portal_image = "{0}_org_{1}_wlan_{2}.png".format(file_prefix, org_id, wlan_id)
        else:
            portal_file_name = "{0}_org_{1}_site_{2}_wlan_{3}.json".format(file_prefix, org_id, site_id, wlan_id)
            portal_image = "{0}_org_{1}_site_{2}_wlan_{3}.png".format(file_prefix, org_id, site_id, wlan_id)
        if hasattr(wlan, "portal_template_url") and wlan.portal_template_url:
            try:
                print("portal template for wlan {0} ".format(wlan_id).ljust(79, '.'), end="", flush=True)
                urllib.request.urlretrieve(wlan.portal_template_url, portal_file_name)
                print("\033[92m\u2714\033[0m")
                logging.info("{0}: Success".format(message))
            except:
                print('\033[31m\u2716\033[0m')
                logging.error("{0}: Failure".format(message))
        if hasattr(wlan, "portal_image") and wlan.portal_image:
            try:
                print("portal image for wlan {0} ".format(wlan_id).ljust(79, '.'), end="", flush=True)
                urllib.request.urlretrieve(wlan.portal_image, portal_image)
                print("\033[92m\u2714\033[0m")
                logging.info("{0}: Success".format(message))
            except:
                print('\033[31m\u2716\033[0m')
                logging.error("{0}: Failure".format(message))


def _do_backup(backup_function, scope_id, message):
    try:
        print("{0} ".format(message).ljust(79, '.'), end="", flush=True)
        data = backup_function(mist_session, scope_id)
        #data = backup_function(scope_id)
        if hasattr(data, "result") or "result" in data: 
            data = data["result"]
        print("\033[92m\u2714\033[0m")
        logging.info("{0}: Success".format(message))
        return data
    except:
        logging.exception("{0}: Failure".format(message))
        print('\033[31m\u2716\033[0m')
        return None


def _backup_full_org(mist_session, org_id, org_name):
    print()
    print(" Backuping Org {0} ".format(org_name).center(80, "_"))
    backup = {}
    backup["org"] = {"id": org_id}

    backup_function = mist_lib.requests.orgs.info.get
    # backup_function = mist.orgs_api.get_org_info
    backup["org"]["data"] = _do_backup(backup_function, org_id, "Org info")

    backup_function = mist_lib.requests.orgs.settings.get
    # backup_function = mist.orgs_setting_api.get_org_settings
    backup["org"]["settings"] = _do_backup(backup_function, org_id, "Org settings")

    backup_function = mist_lib.requests.orgs.webhooks.get
    #backup_function = mist.orgs_webhooks_api.get_org_webhooks
    backup["org"]["webhooks"] = _do_backup(backup_function, org_id, "Org webhooks")

    backup_function = mist_lib.requests.orgs.assetfilters.get
    # backup_function = mist.orgs_asset_filters_api.get_org_asset_filters
    backup["org"]["assetfilters"] = _do_backup(backup_function, org_id, "Org assetfilters")

    backup_function = mist_lib.requests.orgs.alarmtemplates.get
    # backup_function = mist.orgs_alarm_templates_api.get_org_alarm_templates
    backup["org"]["alarmtemplates"] = _do_backup(backup_function, org_id, "Org alarmtemplates")

    backup_function = mist_lib.requests.orgs.deviceprofiles.get
    # backup_function = mist.orgs_device_profiles_api.get_org_device_profiles
    backup["org"]["deviceprofiles"] = _do_backup(backup_function, org_id, "Org deviceprofiles" )

    backup_function = mist_lib.requests.orgs.mxclusters.get
    # backup_function = mist.orgs_mx_clusters_api.get_org_mx_edge_clusters
    backup["org"]["mxclusters"] = _do_backup(backup_function, org_id, "Org mxclusters")

    backup_function =  mist_lib.requests.orgs.mxtunnels.get
    # backup_function = mist.orgs_mx_tunnels_api.get_org_mx_tunnels
    backup["org"]["mxtunnels"] = _do_backup(backup_function, org_id, "Org mxtunnels")

    backup_function = mist_lib.requests.orgs.psks.get
    #backup_function = mist.orgs_psks_api.get_org_psks
    backup["org"]["psks"] = _do_backup(backup_function, org_id, "Org psks")

    backup_function = mist_lib.requests.orgs.rftemplates.get
    # backup_function = mist.orgs_rf_templates_api.get_org_rf_templates
    backup["org"]["rftemplates"] = _do_backup(backup_function, org_id, "Org rftemplates")

    backup_function = mist_lib.requests.orgs.networktemplates.get
    # backup_function = mist.orgs_network_templates_api.get_org_network_templates
    backup["org"]["networktemplates"] = _do_backup(backup_function, org_id, "Org networktemplates")

    backup_function = mist_lib.requests.orgs.secpolicies.get
    # backup_function = mist.orgs_secpolicies_api.get_org_sec_policies
    backup["org"]["secpolicies"] = _do_backup(backup_function, org_id, "Org secpolicies")

    backup_function = mist_lib.requests.orgs.sitegroups.get
    # backup_function = mist.orgs_sitegroups_api.get_org_site_groups
    backup["org"]["sitegroups"] = _do_backup(backup_function, org_id, "Org sitegroups")

    backup_function = mist_lib.requests.orgs.ssos.get
    # backup_function = mist.orgs_ssos_api.get_org_ssos
    backup["org"]["ssos"] = _do_backup(backup_function, org_id, "Org ssos")

    backup_function = mist_lib.requests.orgs.ssoroles.get
    # backup_function = mist.orgs_sso_roles_api.get_org_sso_roles
    backup["org"]["ssoroles"] = _do_backup(backup_function, org_id, "Org ssoroles")

    backup_function = mist_lib.requests.orgs.templates.get
    # backup_function = mist.orgs_templates_api.get_org_templates
    backup["org"]["templates"] = _do_backup(backup_function, org_id, "Org templates")

    backup_function = mist_lib.requests.orgs.wlans.get
    # backup_function = mist.orgs_wlans_api.get_org_wlans
    backup["org"]["wlans"] = _do_backup(backup_function, org_id, "Org wlans")

    _backup_wlan_portal(org_id, None, backup["org"]["wlans"])

    backup_function = mist_lib.requests.orgs.wxrules.get
    # backup_function = mist.orgs_wx_rules_api.get_org_wx_rules
    backup["org"]["wxrules"] = _do_backup(backup_function, org_id, "Org wxrules")

    backup_function = mist_lib.requests.orgs.wxtags.get
    # backup_function = mist.orgs_wx_tags_api.get_org_wx_tags
    backup["org"]["wxtags"] = _do_backup(backup_function, org_id, "Org wxtags")

    backup_function = mist_lib.requests.orgs.wxtunnels.get
    #backup_function = mist.orgs_wx_tunnels_api.get_org_wx_tunnels
    backup["org"]["wxtunnels"] = _do_backup(backup_function, org_id, "Org wxtunnels")


    backup["org"]["sites"] = []
    sites = mist_lib.requests.orgs.sites.get(mist_session, org_id)['result']
    #sites = mist.orgs_sites_api.get_org_sites(org_id=org_id)
    for site in sites:
        site_id = site["id"]
        site_name = site["name"]
        # site_id = site.id
        # site_name = site.name
        print(" Backuping Site {0} ".format(site_name).center(80, "_"))
        backup_function = mist_lib.requests.sites.assets.get
        # backup_function = mist.sites_assets_api.get_site_assets
        assets = _do_backup(backup_function, site_id, "Site assets")

        backup_function = mist_lib.requests.sites.assetfilters.get
        # backup_function = mist.sites_asset_filters_api.get_site_asset_filters
        assetfilters = _do_backup(backup_function, site_id, "Site assetfilters")

        backup_function = mist_lib.requests.sites.beacons.get
        # backup_function = mist.sites_beacons_api.get_site_beacons
        beacons = _do_backup(backup_function, site_id, "Site beacons")

        backup_function = mist_lib.requests.sites.maps.get
        # backup_function = mist.sites_maps_api.get_site_maps
        maps = _do_backup(backup_function, site_id,"Site maps")

        backup_function = mist_lib.requests.sites.psks.get
        # backup_function = mist.sites_psks_api.get_site_psks
        psks = _do_backup(backup_function, site_id, "Site psks")

        backup_function = mist_lib.requests.sites.rssizones.get
        # backup_function = mist.sites_rssizones_api.get_site_rssi_zones
        rssizones = _do_backup(backup_function, site_id, "Site rssizones")

        backup_function = mist_lib.requests.sites.settings.get
        # backup_function = mist.sites_setting_api.get_site_setting
        settings = _do_backup(backup_function, site_id, "Site settings")

        backup_function = mist_lib.requests.sites.vbeacons.get
        # backup_function = mist.sites_v_beacons_api.get_site_v_beacons
        vbeacons = _do_backup(backup_function, site_id, "Site vbeacons")

        backup_function = mist_lib.requests.sites.webhooks.get
        # backup_function = mist.sites_webhooks_api.get_site_webhooks
        webhooks = _do_backup(backup_function, site_id, "Site webhooks")

        backup_function = mist_lib.requests.sites.wlans.get
        # backup_function = mist.sites_wlans_api.get_site_wlans
        wlans = _do_backup(backup_function, site_id, "Site wlans")
        
        _backup_wlan_portal(org_id, site_id, wlans)
        
        backup_function = mist_lib.requests.sites.wxrules.get
        # backup_function = mist.sites_wx_rules_api.get_site_wx_rules
        wxrules = _do_backup(backup_function, site_id,"Site wxrules")

        backup_function = mist_lib.requests.sites.wxtags.get
        # backup_function = mist.sites_wx_tags_api.get_site_wx_tags
        wxtags = _do_backup(backup_function, site_id,"Site wxtags")

        backup_function = mist_lib.requests.sites.wxtunnels.get
        # backup_function = mist.sites_wx_tunnels_api.get_site_wx_tunnels
        wxtunnels = _do_backup(backup_function, site_id, "Site wxtunnels")

        backup_function = mist_lib.requests.sites.zones.get
        # backup_function = mist.sites_zones_api.get_site_zones
        zones = _do_backup(backup_function, site_id,"Site zones")

        backup["org"]["sites"].append({
            "data": site,
            "assetfilters": assetfilters,
            "assets": assets,
            "beacons": beacons,
            "maps": maps,
            "psks": psks,
            "rssizones": rssizones,
            "settings": settings,
            "vbeacons": vbeacons,
            "webhooks": webhooks,
            "wlans": wlans,
            "wxrules": wxrules,
            "wxtags": wxtags,
            "wxtunnels": wxtunnels,
            "zones": zones
        })
        
        print("Site map images ".ljust(79, "."), end="", flush=True)
        try:
            for xmap in maps:
                if hasattr(xmap, 'url'):
                    url = xmap.url
                    image_name = "%s_org_%s_site_%s_map_%s.png" % (
                        file_prefix, org_id, site_id, xmap.id)
                    urllib.request.urlretrieve(url, image_name)
            print("\033[92m\u2714\033[0m")
            logging.info("ORG {0} > SITE {1} > Backuping map images: Success".format(org_name, site_name))
        except:
            print('\033[31m\u2716\033[0m')
            logging.error("ORG {0} > SITE {1} > Backuping map images: Failure".format(org_name, site_name))


    print(" Backup Done ".center(80, "_"))
    logger.info("ORG {0} > Backup done".format(org_name))
    return backup


def _save_to_file(backup_file, backup):
    print("saving to file ".ljust(79, "."), end="", flush=True)
    try:
        with open(backup_file, "w") as f:
            json.dump(backup, f)
        print("\033[92m\u2714\033[0m")
        logging.info("Backup saved to file {0} with success".format(backup_file))
    except:
        print('\033[31m\u2716\033[0m')
        logging.error("Unable to save Backup to file {0}".format(backup_file))



def start_org_backup(mist_session, org_id, org_name):
    try:
        if not os.path.exists("org_backup"):
            os.mkdir("org_backup")
        os.chdir("org_backup")
        if not os.path.exists(org_name):
            os.mkdir(org_name)
        os.chdir(org_name)

        backup = _backup_full_org(mist_session, org_id, org_name)
        _save_to_file(backup_file, backup)
    except:
        return 255


def start(mist_session):
    org_id = cli.select_org(mist_session)[0]
    org_name = mist_lib.orgs.info.get(mist_session, org_id)["result"]["name"]
    start_org_backup(mist_session, org_id, org_name)


##### ENTRY POINT ####

if __name__ == "__main__":
    mist_session = mist_lib.Mist_Session(session_file)
    start(mist_session)
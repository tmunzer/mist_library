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
#### IMPORTS ####
import logging
import json
from mlib import cli
import urllib.request
import os
import sys
import mlib as mist_lib


#### PARAMETERS #####
backup_file = "./org_conf_file.json"
log_file = "./org_conf_backup.log"
file_prefix = ".".join(backup_file.split(".")[:-1])
session_file = "./session.py"

#### LOGS ####
logger = logging.getLogger(__name__)

#### FUNCTIONS ####

def log_message(message):
    print(f"{message}".ljust(79, '.'), end="", flush=True)

def log_success(message):
    print("\033[92m\u2714\033[0m")
    logger.info(f"{message}: Success")

def log_failure(message):
    print('\033[31m\u2716\033[0m')
    logger.exception(f"{message}: Failure")


def _backup_wlan_portal(org_id, site_id, wlans):
    for wlan in wlans:
        wlan_id = wlan["id"]
        # wlan_id = wlan.id
        if site_id is None:
            portal_file_name = f"{file_prefix}_org_{org_id}_wlan_{wlan_id}.json"
            portal_image = f"{file_prefix}_org_{org_id}_wlan_{wlan_id}.png"
        else:
            portal_file_name = f"{file_prefix}_org_{org_id}_site_{site_id}_wlan_{wlan_id}.json"
            portal_image = f"{file_prefix}_org_{org_id}_site_{site_id}_wlan_{wlan_id}.png"
        if hasattr(wlan, "portal_template_url") and wlan.portal_template_url:
            try:
                message=f"portal template for wlan {wlan_id} "
                log_message(message)
                urllib.request.urlretrieve(
                    wlan.portal_template_url, portal_file_name)
                log_success(message)
            except Exception as e:
                log_failure(message)
                logger.error("Exception occurred", exc_info=True)
        if hasattr(wlan, "portal_image") and wlan.portal_image:
            try:
                message=f"portal image for wlan {wlan_id} "
                log_message(message)
                urllib.request.urlretrieve(wlan.portal_image, portal_image)
                log_success(message)
            except Exception as e:
                log_failure(message)
                logger.error("Exception occurred", exc_info=True)


def _do_backup(mist_session, backup_function, scope_id, message):
    try:
        log_message(message)
        data = backup_function(mist_session, scope_id)
        #data = backup_function(scope_id)
        if hasattr(data, "result") or "result" in data:
            data = data["result"]
        log_success(message)
        return data
    except Exception as e:
        log_failure(message)
        logger.error("Exception occurred", exc_info=True)
        return None


def _backup_full_org(mist_session, org_id, org_name):
    print()
    print(f" Backuping Org {org_name} ".center(80, "_"))
    backup = {}
    backup["org"] = {"id": org_id}

    backup_function = mistapi.api.v1.orgs.info.get
    backup["org"]["data"] = _do_backup(
        mist_session, backup_function, org_id, "Org info")

    backup_function = mistapi.api.v1.orgs.settings.get
    backup["org"]["settings"] = _do_backup(
        mist_session, backup_function, org_id, "Org settings")

    backup_function = mistapi.api.v1.orgs.webhooks.get
    backup["org"]["webhooks"] = _do_backup(
        mist_session, backup_function, org_id, "Org webhooks")

    backup_function = mistapi.api.v1.orgs.assetfilters.get
    backup["org"]["assetfilters"] = _do_backup(
        mist_session, backup_function, org_id, "Org assetfilters")

    backup_function = mistapi.api.v1.orgs.alarmtemplates.get
    backup["org"]["alarmtemplates"] = _do_backup(
        mist_session, backup_function, org_id, "Org alarmtemplates")

    backup_function = mistapi.api.v1.orgs.deviceprofiles.get
    backup["org"]["deviceprofiles"] = _do_backup(
        mist_session, backup_function, org_id, "Org deviceprofiles")

    backup_function = mistapi.api.v1.orgs.mxclusters.get
    backup["org"]["mxclusters"] = _do_backup(
        mist_session, backup_function, org_id, "Org mxclusters")

    backup_function = mistapi.api.v1.orgs.mxtunnels.get
    backup["org"]["mxtunnels"] = _do_backup(
        mist_session, backup_function, org_id, "Org mxtunnels")

    backup_function = mistapi.api.v1.orgs.psks.get
    backup["org"]["psks"] = _do_backup(
        mist_session, backup_function, org_id, "Org psks")

    backup_function = mistapi.api.v1.orgs.rftemplates.get
    backup["org"]["rftemplates"] = _do_backup(
        mist_session, backup_function, org_id, "Org rftemplates")

    backup_function = mistapi.api.v1.orgs.networktemplates.get
    backup["org"]["networktemplates"] = _do_backup(
        mist_session, backup_function, org_id, "Org networktemplates")

    backup_function = mistapi.api.v1.orgs.evpn_topologies.get
    backup["org"]["evpn_topologies"] = _do_backup(
        mist_session, backup_function, org_id, "Org evpn_topologies")

    backup_function = mistapi.api.v1.orgs.services.get
    backup["org"]["services"] = _do_backup(
        mist_session, backup_function, org_id, "Org services")

    backup_function = mistapi.api.v1.orgs.networks.get
    backup["org"]["networks"] = _do_backup(
        mist_session, backup_function, org_id, "Org networks")

    backup_function = mistapi.api.v1.orgs.gatewaytemplates.get
    backup["org"]["gatewaytemplates"] = _do_backup(
        mist_session, backup_function, org_id, "Org gatewaytemplates")

    backup_function = mistapi.api.v1.orgs.hubprofiles.get
    backup["org"]["hubprofiles"] = _do_backup(
        mist_session, backup_function, org_id, "Org hubprofiles")

    backup_function = mistapi.api.v1.orgs.vpns.get
    backup["org"]["vpns"] = _do_backup(
        mist_session, backup_function, org_id, "Org vpns")

    backup_function = mistapi.api.v1.orgs.secpolicies.get
    backup["org"]["secpolicies"] = _do_backup(
        mist_session, backup_function, org_id, "Org secpolicies")

    backup_function = mistapi.api.v1.orgs.sitegroups.get
    backup["org"]["sitegroups"] = _do_backup(
        mist_session, backup_function, org_id, "Org sitegroups")

    backup_function = mistapi.api.v1.orgs.ssos.get
    backup["org"]["ssos"] = _do_backup(
        mist_session, backup_function, org_id, "Org ssos")

    backup_function = mistapi.api.v1.orgs.ssoroles.get
    backup["org"]["ssoroles"] = _do_backup(
        mist_session, backup_function, org_id, "Org ssoroles")

    backup_function = mistapi.api.v1.orgs.templates.get
    backup["org"]["templates"] = _do_backup(
        mist_session, backup_function, org_id, "Org templates")

    backup_function = mistapi.api.v1.orgs.wlans.get
    backup["org"]["wlans"] = _do_backup(
        mist_session, backup_function, org_id, "Org wlans")

    _backup_wlan_portal(org_id, None, backup["org"]["wlans"])

    backup_function = mistapi.api.v1.orgs.wxrules.get
    backup["org"]["wxrules"] = _do_backup(
        mist_session, backup_function, org_id, "Org wxrules")

    backup_function = mistapi.api.v1.orgs.wxtags.get
    backup["org"]["wxtags"] = _do_backup(
        mist_session, backup_function, org_id, "Org wxtags")

    backup_function = mistapi.api.v1.orgs.wxtunnels.get
    backup["org"]["wxtunnels"] = _do_backup(
        mist_session, backup_function, org_id, "Org wxtunnels")

    backup["org"]["sites"] = []
    sites = mistapi.api.v1.orgs.sites.get(mist_session, org_id)['result']
    #sites = mist.orgs_sites_api.get_org_sites(org_id=org_id)
    for site in sites:
        site_id = site["id"]
        site_name = site["name"]
        # site_id = site.id
        # site_name = site.name
        print(f" Backuping Site {site_name} ".center(80, "_"))
        backup_function = mistapi.api.v1.sites.assets.get
        # backup_function = mist.sites_assets_api.get_site_assets
        assets = _do_backup(mist_session, backup_function,
                            site_id, "Site assets")

        backup_function = mistapi.api.v1.sites.assetfilters.get
        # backup_function = mist.sites_asset_filters_api.get_site_asset_filters
        assetfilters = _do_backup(
            mist_session, backup_function, site_id, "Site assetfilters")

        backup_function = mistapi.api.v1.sites.beacons.get
        # backup_function = mist.sites_beacons_api.get_site_beacons
        beacons = _do_backup(mist_session, backup_function,
                             site_id, "Site beacons")

        backup_function = mistapi.api.v1.sites.maps.get
        # backup_function = mist.sites_maps_api.get_site_maps
        maps = _do_backup(mist_session, backup_function, site_id, "Site maps")

        backup_function = mistapi.api.v1.sites.psks.get
        # backup_function = mist.sites_psks_api.get_site_psks
        psks = _do_backup(mist_session, backup_function, site_id, "Site psks")

        backup_function = mistapi.api.v1.sites.rssizones.get
        # backup_function = mist.sites_rssizones_api.get_site_rssi_zones
        rssizones = _do_backup(
            mist_session, backup_function, site_id, "Site rssizones")

        backup_function = mistapi.api.v1.sites.settings.get
        # backup_function = mist.sites_setting_api.get_site_setting
        settings = _do_backup(mist_session, backup_function,
                              site_id, "Site settings")

        backup_function = mistapi.api.v1.sites.vbeacons.get
        # backup_function = mist.sites_v_beacons_api.get_site_v_beacons
        vbeacons = _do_backup(mist_session, backup_function,
                              site_id, "Site vbeacons")

        backup_function = mistapi.api.v1.sites.webhooks.get
        # backup_function = mist.sites_webhooks_api.get_site_webhooks
        webhooks = _do_backup(mist_session, backup_function,
                              site_id, "Site webhooks")

        backup_function = mistapi.api.v1.sites.wlans.get
        # backup_function = mist.sites_wlans_api.get_site_wlans
        wlans = _do_backup(mist_session, backup_function,
                           site_id, "Site wlans")

        _backup_wlan_portal(org_id, site_id, wlans)

        backup_function = mistapi.api.v1.sites.wxrules.get
        # backup_function = mist.sites_wx_rules_api.get_site_wx_rules
        wxrules = _do_backup(mist_session, backup_function,
                             site_id, "Site wxrules")

        backup_function = mistapi.api.v1.sites.wxtags.get
        # backup_function = mist.sites_wx_tags_api.get_site_wx_tags
        wxtags = _do_backup(mist_session, backup_function,
                            site_id, "Site wxtags")

        backup_function = mistapi.api.v1.sites.wxtunnels.get
        # backup_function = mist.sites_wx_tunnels_api.get_site_wx_tunnels
        wxtunnels = _do_backup(
            mist_session, backup_function, site_id, "Site wxtunnels")

        backup_function = mistapi.api.v1.sites.zones.get
        # backup_function = mist.sites_zones_api.get_site_zones
        zones = _do_backup(mist_session, backup_function,
                           site_id, "Site zones")

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

        message="Site map images "
        log_message(message)
        try:
            for xmap in maps:
                url = None
                if hasattr(xmap, 'url'):
                    url = xmap.url
                    xmap_id = xmap.id
                elif "url" in xmap:
                    url = xmap["url"]
                    xmap_id = xmap["id"]
                if url:
                    image_name = "%s_org_%s_site_%s_map_%s.png" % (
                        file_prefix, org_id, site_id, xmap_id)
                    urllib.request.urlretrieve(url, image_name)
            log_success(message)
        except Exception as e:
            log_failure(message)
            logger.error("Exception occurred", exc_info=True)

    print(" Backup Done ".center(80, "_"))
    logger.info(f"ORG {org_name} > Backup done")
    return backup


def _save_to_file(backup_file, backup, org_name):
    backup_path = f"./org_backup/{org_name}/{backup_file.replace('./','')}"
    message=f"Saving to file {backup_path} "
    log_message(message)
    try:
        with open(backup_file, "w") as f:
            json.dump(backup, f)
        log_success(message)
    except Exception as e:
        log_failure(message)
        logger.error("Exception occurred", exc_info=True)


def start_org_backup(mist_session, org_id, org_name, parent_log_file=None):
    if parent_log_file:
        logging.basicConfig(filename=log_file, filemode='a')
        logger.setLevel(logging.DEBUG)
    try:
        if not os.path.exists("org_backup"):
            os.mkdir("org_backup")
        os.chdir("org_backup")
        if not os.path.exists(org_name):
            os.makedirs(org_name)
        os.chdir(org_name)

        backup = _backup_full_org(mist_session, org_id, org_name)
        _save_to_file(backup_file, backup, org_name)
    except:
        sys.exit(255)


def start(mist_session):
    org_id = cli.select_org(mist_session)[0]
    org_name = mist_lib.orgs.info.get(mist_session, org_id)["result"]["name"]
    start_org_backup(mist_session, org_id, org_name)


##### ENTRY POINT ####

if __name__ == "__main__":
    #### LOGS ####
    logging.basicConfig(filename=log_file, filemode='w')
    logger.setLevel(logging.DEBUG)

    mist_session = mistapi.APISession(session_file)
    start(mist_session)
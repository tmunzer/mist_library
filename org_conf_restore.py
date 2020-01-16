import mlib as mist_lib
from mlib.__debug import Console
from mlib import cli
from tabulate import tabulate
import json

console = Console(6)
backup_file = "./org_backup.json"
session_file = None

mist_session = mist_lib.Mist_Session(session_file)
org_id = "0c72cf4e-91b0-4cfd-9ba2-97a5c47e5758"#cli.select_org(mist_session)

with open(backup_file) as f:
    backup = json.load(f)
   


rftemplates_id_dict = {}
sites_id_dict={}
sitegroups_id_dict={}
maps_id_dict = {}
deviceprofiles_id_dict = {}
templates_id_dict = {}
mxtunnel_id_dict = {}
wxtunnel_id_dict = {}
secpolicy_id_dict = {}
wxtags_id_dict = {} 
mxcluster_id_dict = {}
wlan_id_dict = {}
alarmtemplate_id_dict = {}

def get_new_id(old_id, new_ids_dict):
    if old_id in new_ids_dict:
        return new_ids_dict[old_id]
    else:
        return None

def replace_id(old_ids_list, new_ids_dict):
    if old_ids_list == None:
        return None
    if old_ids_list == {}:
        return {}
    elif type(old_ids_list) == str:
        return get_new_id(old_ids_list, new_ids_dict)
    elif type(old_ids_list) == list:
        new_ids_list = []
        for old_id in old_ids_list:
            new_ids_list.append(get_new_id(old_id, new_ids_dict))
        return new_ids_list
    else:
        console.error("Unable to replace ids: %s" % old_ids_list)

def clean_ids(data):
    if "id" in data: del data["id"]
    if "irg_id" in data: del data["org_id"]
    if "modified_time" in data: del data["modified_time"]
    if "created_time" in data: del data["created_time"]
    return data

data = backup["org"]["data"]
#console.debug(json.dumps(data))
del data["id"]
if "orggroup_ids" in data: del data["orggroup_ids"]
if "msp_id" in data: del data["msp_id"]
if "msp_name" in data: del data["msp_name"]
mist_lib.requests.orgs.info.update(mist_session, org_id, data)

data = clean_ids(backup["org"]["settings"])
#console.debug(json.dumps(data))
mist_lib.requests.orgs.settings.update(mist_session, org_id, data)

for data in backup["org"]["webhooks"]:
    ##console.debug(json.dumps(data))
    webhook = clean_ids(data)
    mist_lib.requests.orgs.webhooks.create(mist_session, org_id, webhook)

for data in backup["org"]["assetfilters"]:
    #console.debug(json.dumps(data))
    assetfilter = clean_ids(data)
    mist_lib.requests.orgs.assetfilters.create(mist_session, org_id, assetfilter)

for data in backup["org"]["deviceprofiles"]:
    #console.debug(json.dumps(data))
    old_id = data["id"]
    deviceprofile = clean_ids(data)
    new_deviceprofile = mist_lib.requests.orgs.deviceprofiles.create(mist_session, org_id, deviceprofile)["result"]
    deviceprofiles_id_dict[old_id] = new_deviceprofile["id"]

for data in backup["org"]["alarmtemplates"]:
    #console.debug(json.dumps(data))
    old_id = data["id"]
    alarmtemplate = clean_ids(data)
    new_deviceprofile = mist_lib.requests.orgs.alarmtemplates.create(mist_session, org_id, alarmtemplate)["result"]
    deviceprofiles_id_dict[old_id] = new_deviceprofile["id"]

for data in backup["org"]["mxclusters"]:
    #console.debug(json.dumps(data))
    old_id = data["id"]
    mxcluster = clean_ids(data)
    new_mxcluster = mist_lib.requests.orgs.mxclusters.create(mist_session, org_id, mxcluster)["result"]
    mxcluster_id_dict[old_id] = new_mxcluster["id"]

for data in backup["org"]["mxtunnels"]:
    #console.debug(json.dumps(data))
    old_id = data["id"]
    mxtunnel = clean_ids(data)
    mxtunnel["mxcluster_ids"] = replace_id(mxtunnel["mxcluster_ids"], mxcluster_id_dict)
    new_mxtunnel = mist_lib.requests.orgs.mxtunnels.create(mist_session, org_id, mxtunnel)["result"]
    mxtunnel_id_dict[old_id] = new_mxtunnel["id"]

for data in backup["org"]["psks"]:
    #console.debug(json.dumps(data))
    psk = clean_ids(data)
    mist_lib.requests.orgs.psks.create(mist_session, org_id, psk)

for data in backup["org"]["secpolicies"]:
    #console.debug(json.dumps(data))
    old_id = data["id"]
    secpolicy = clean_ids(data)
    new_secpolicy = mist_lib.requests.orgs.secpolicies.create(mist_session, org_id, secpolicy)["result"]
    secpolicy_id_dict[old_id] = new_secpolicy["id"]

for data in backup["org"]["rftemplates"]:
    #console.debug(json.dumps(data))
    old_id = data["id"]
    rftemplate = clean_ids(data)
    new_rftemplate = mist_lib.requests.orgs.rftemplates.create(mist_session, org_id, rftemplate)["result"]
    rftemplates_id_dict[old_id] = new_rftemplate["id"]

for data in backup["org"]["sitegroups"]:
    #console.debug(json.dumps(data))
    old_id = data["id"]
    sitegroup = clean_ids(data)
    new_sitegroup = mist_lib.requests.orgs.deviceprofiles.create(mist_session, org_id, sitegroup)["result"]
    sitegroups_id_dict[old_id] = new_sitegroup["id"]

for data in backup["org"]["wxtags"]:
    #console.debug(json.dumps(data))
    old_id = data["id"]
    wxtag = clean_ids(data)
    if wxtag["match"] == "wlan_id": replace_id(wxtag["values"], wlan_id_dict)
    new_wxtag = mist_lib.requests.orgs.wxtags.create(mist_session, org_id, wxtag)["result"]
    wxtags_id_dict[old_id] = new_wxtag["id"]


for data in backup["org"]["wxrules"]:
    #console.debug(json.dumps(data))
    wxrule = clean_ids(data)
    wxrule["src_wxtags"] = replace_id(wxrule["src_wxtags"], wxtags_id_dict)
    wxrule["dst_allow_wxtags"] = replace_id(wxrule["dst_allow_wxtags"], wxtags_id_dict)
    wxrule["dst_deny_wxtags"] = replace_id(wxrule["dst_deny_wxtags"], wxtags_id_dict)
    mist_lib.requests.orgs.wxrules.create(mist_session, org_id, wxrule)


for data in backup["org"]["wxtunnels"]:
    #console.debug(json.dumps(data))
    old_id = data["id"]
    wxtunnel = clean_ids(data)
    new_wxtunnel = mist_lib.requests.orgs.wxtunnels.create(mist_session, org_id, wxtunnel)["result"]
    wxtunnel_id_dict[old_id] = new_wxtunnel["id"]


for data in backup["org"]["sites"]:
    #console.debug(json.dumps(data))
    old_id = data["data"]["id"]
    site = clean_ids(data["data"])
    if "rftemplate_id" in site: site["rftemplate_id"] = replace_id(site["rftemplate_id"], rftemplates_id_dict)
    if "secpolicy_id" in site: site["secpolicy_id"] = replace_id(site["secpolicy_id"], secpolicy_id_dict)
    if "alarmtemplate_id" in site: site["alarmtemplate_id"] = replace_id(site["alarmtemplate_id"], alarmtemplate_id_dict)
    new_site = mist_lib.requests.orgs.sites.create(mist_session, org_id, site)["result"]
    sites_id_dict[old_id] = new_site["id"]

    settings = clean_ids(data["settings"])
    mist_lib.requests.sites.settings.update(mist_session, new_site["id"], settings)

    if "maps" in data:
        for sub_data in data["maps"]:
            #console.debug(json.dumps(sub_data))
            old_map_id = sub_data["id"]
            site_map = clean_ids(sub_data)        
            site_map["site_id"] = new_site["id"]
            new_map = mist_lib.requests.sites.maps.create(mist_session, new_site["id"], site_map)["result"]
            maps_id_dict[old_map_id] = new_map["id"]

    if "assetfilters" in data:
        for sub_data in data["assetfilters"]:
            #console.debug(json.dumps(sub_data))
            assetfilter = clean_ids(sub_data)
            mist_lib.requests.sites.assetfilters.create(mist_session, new_site["id"], assetfilter)

    if "assets" in data:
        for sub_data in data["assets"]:
            #console.debug(json.dumps(sub_data))
            asset = clean_ids(sub_data)
            mist_lib.requests.sites.assets.create(mist_session, new_site["id"], asset)
        
    if "beacons" in data:
        for sub_data in data["beacons"]:
            #console.debug(json.dumps(sub_data))
            beacon = clean_ids(sub_data)
            beacon["map_id"] = replace_id(beacon["map_id"], maps_id_dict)
            mist_lib.requests.sites.beacons.create(mist_session, new_site["id"], beacon)
        
    if "psks" in data:
        for sub_data in data["psks"]:
            #console.debug(json.dumps(sub_data))
            psk = clean_ids(sub_data)
            psk["site_id"] = new_site["id"]
            mist_lib.requests.sites.psks.create(mist_session, new_site["id"], psk)
        
    if "rssizones" in data:
        for sub_data in data["rssizones"]:
            #console.debug(json.dumps(sub_data))
            rssizone = clean_ids(sub_data)
            mist_lib.requests.sites.rssizones.create(mist_session, new_site["id"], rssizone)

    if "vbeacons" in data:
        for sub_data in data["vbeacons"]:
            #console.debug(json.dumps(sub_data))
            vbeacon = clean_ids(sub_data)
            vbeacon["map_id"] = replace_id(vbeacon["map_id"], maps_id_dict)
            mist_lib.requests.sites.vbeacons.create(mist_session, new_site["id"], vbeacon)
    
    if "webhooks" in data:
        for sub_data in data["webhooks"]:
            #console.debug(json.dumps(sub_data))
            webhook = clean_ids(sub_data)
            mist_lib.requests.sites.webhooks.create(mist_session, new_site["id"], webhook)

    if "wxtunnels" in data:
        for sub_data in data["wxtunnels"]:
            #console.debug(json.dumps(sub_data))
            old_id = sub_data["id"]
            wxtunnel = clean_ids(sub_data)
            new_wxtunnel = mist_lib.requests.sites.wxtunnels.create(mist_session, new_site["id"], wxtunnel)["result"]
            wxtunnel_id_dict[old_id] = new_wxtunnel["id"]

    if "zones" in data:
        for sub_data in data["zones"]:
            #console.debug(json.dumps(sub_data))
            zone = clean_ids(sub_data)
            zone["map_id"] = replace_id(zone["map_id"], maps_id_dict)
            mist_lib.requests.sites.zones.create(mist_session, new_site["id"], zone)


for data in backup["org"]["templates"]:
    #console.debug(json.dumps(data))
    old_id = data["id"]
    template = clean_ids(data)
    if "applies" in template:
        if "org_id" in template["applies"]: 
            template["applies"]["org_id"] = org_id
        if "site_ids" in template["applies"]: 
            template["applies"]["site_ids"] = replace_id(template["applies"]["site_ids"], sites_id_dict)
        if "sitegroup_ids" in template["applies"]: 
            template["applies"]["sitegroup_ids"] = replace_id(template["applies"]["sitegroup_ids"], sitegroups_id_dict)
    if "exceptions" in template:
        if "site_ids" in template["exceptions"]: 
            template["exceptions"]["site_ids"] = replace_id(template["exceptions"]["site_ids"], sites_id_dict)
        if "sitegroup_ids" in template["exceptions"]: 
            template["exceptions"]["sitegroup_ids"] = replace_id(template["exceptions"]["sitegroup_ids"], sitegroups_id_dict)
    if "deviceprofile_ids" in template:
        template["deviceprofile_ids"] = replace_id(template["deviceprofile_ids"], deviceprofiles_id_dict)
    new_templates = mist_lib.requests.orgs.templates.create(mist_session, org_id, template)["result"]
    templates_id_dict[old_id] = new_templates["id"]


for data in backup["org"]["wlans"]:
    #console.debug(json.dumps(data))
    old_id = data["id"]
    wlan = clean_ids(data)
    if "template_id" in wlan: wlan["template_id"] = replace_id(wlan["template_id"], templates_id_dict)
    if "wxtunnel_id" in wlan: wlan["wxtunnel_id"] = replace_id(wlan["wxtunnel_id"], wxtags_id_dict)
    if "mxtunnel_id" in wlan: wlan["mxtunnel_id"] = replace_id(wlan["mxtunnel_id"], mxtunnel_id_dict)
    if "app_limit" in wlan and "wxtag_ids" in wlan["app_limit"]: wlan["app_limit"]["wxtag_ids"] = replace_id(wlan["app_limit"]["wxtag_ids"], wxtags_id_dict)
    new_wlan = mist_lib.requests.orgs.wlans.create(mist_session, org_id, wlan)["result"]
    wlan_id_dict[old_id]= new_wlan["id"]

for data in backup["org"]["sites"]:
    if "wlans" in data:
        for sub_data in data["wlans"]:
            #console.debug(json.dumps(sub_data))
            wlan = clean_ids(sub_data)
            wlan["site_id"] = replace_id(wlan["site_id"], sites_id_dict)
            if "template_id" in wlan: wlan["template_id"] = replace_id(wlan["template_id"], templates_id_dict)
            if "wxtunnel_id" in wlan: wlan["wxtunnel_id"] = replace_id(wlan["wxtunnel_id"], wxtags_id_dict)
            if "mxtunnel_id" in wlan: wlan["mxtunnel_id"] = replace_id(wlan["mxtunnel_id"], mxtunnel_id_dict)
            if "app_limit" in wlan and "wxtag_ids" in wlan["app_limit"]: wlan["app_limit"]["wxtag_ids"] = replace_id(wlan["app_limit"]["wxtag_ids"], wxtags_id_dict)
            mist_lib.requests.sites.wlans.create(mist_session, new_site["id"], wlan)["result"]
            
    if "wxtags" in data:
        for sub_data in data["wxtags"]:
            #console.debug(json.dumps(sub_data))
            old_id = sub_data["id"]
            wxtag = clean_ids(sub_data)
            if wxtag["match"] == "wlan_id": replace_id(wxtag["values"], wlan_id_dict)
            new_wxtag = mist_lib.requests.sites.wxtags.create(mist_session, new_site["id"], wxtag)["result"]
            wxtags_id_dict[old_id] = new_wxtag["id"]


    if "wxrules" in data:
        for sub_data in data["wxrules"]:
            #console.debug(json.dumps(sub_data))
            wxrule = clean_ids(sub_data)
            if "src_wxtags" in wxrule: wxrule["src_wxtags"] = replace_id(wxrule["src_wxtags"], wxtags_id_dict)
            if "dst_allow_wxtags" in wxrule: wxrule["dst_allow_wxtags"] = replace_id(wxrule["dst_allow_wxtags"], wxtags_id_dict)
            if "dst_deny_wxtags" in wxrule: wxrule["dst_deny_wxtags"] = replace_id(wxrule["dst_deny_wxtags"], wxtags_id_dict)
            mist_lib.requests.sites.wxrules.create(mist_session, new_site["id"], wxrule)

exit(0)
 
'''
Written by Thomas Munzer (tmunzer@juniper.net)
Github repository: https://github.com/tmunzer/Mist_library/

Python script to list all WLANs from orgs/sites and their parameters, and save it to a CSV file.
You can configure which fields you want to retrieve/save, and where the script will save the CSV file.

You can run the script with the command "python3 org_report_wlans.py"

The script has 2 different steps:
1) admin login
2) select the organisation/site from where you want to retrieve the information


available fields:
ssid, enabled, auth, roam_mode, auth_servers_nas_id, auth_servers_nas_ip, auth_servers_timeout, auth_servers_retries, auth_servers, acct_servers,
acct_interim_interval, dynamic_vlan, band, band_steer, band_steer_force_band5, disable_11ax, interface, vlan_enabled, vlan_id, vlan_pooling, vlan_ids,
wxtunnel_id, wxtunnel_remote_id, mxtunneL_id, hide_ssid, dtim, disable_wmm, disable_uapsd, use_eapol_v1, legacy_overds, hostname_id, isolation, arp_filter,
limit_bcast, allow_mdns, allow_ipv6_ndp, no_static_ip, no_static_dns, enable_wireless_bridging, apply_to, wxtag_ids, ap_ids, wlan_limit_up_enabled, 
wlan_limit_up, wlan_limit_down_enabled, wlan_limit_down, client_limit_up_enabled, client_limit_up, client_limit_down_enabled, client_limit_down, 
max_idletime, sle_excluded, portal_template_url, portal_image, thumbnail, portal_api_secret, portal_sso_url, portal_allowed_subnets, portal_allowed_hostnames, 
portal_denied_hostnames

not yet available fields:
dns_server_rewrite, coa_server, radsec, airwatch, cisco_cwa, rateset, schedule, qos, app_limit, app_qos, portal
'''

#### PARAMETERS #####
csv_separator = ","
fields = ["id","ssid", "enabled", "auth", "auth_servers", "acct_servers", "band", "interface", "vlan_id", "dynamic_vlan", "hide_ssid" ]
csv_file = "./report.csv"

org_ids = []
site_ids = []

#### IMPORTS ####
import mlib as mist_lib
from mlib import cli

#### GLOBAL VARIABLES ####
wlans_summarized = []

#### FUNCTIONS ####
def country_code(site):
    if "country_code" in site:
        return site["country_code"]
    else:
        return "N/A"

def wlans_from_sites(mist_session, sites, org_info, site_ids):
    for site in sites:
        if len(org_ids) > 1 or site["id"] in site_ids:     
            site_wlans = mist_lib.requests.sites.wlans.report(mist_session, site["id"], fields)            
            for site_wlan in site_wlans:     
                site_wlan.insert(0, "site")           
                site_wlan.insert(1, org_info["name"])
                site_wlan.insert(2, org_info["id"])
                site_wlan.insert(3, site["name"])
                site_wlan.insert(4, site["id"])
                site_wlan.insert(5, country_code(site))
                wlans_summarized.append(site_wlan)

def wlans_from_orgs(mist_session, org_ids, site_ids):
    for org_id in org_ids:
        org_sites = list(filter(lambda privilege: "org_id" in privilege and privilege["org_id"] == org_id, mist_session.privileges))
        # the admin only has access to the org information if he/she has this privilege 
        if len(org_sites) >= 1 and org_sites[0]["scope"] == "org":
            org_info = mist_lib.requests.orgs.info.get(mist_session, org_id)["result"]
            org_sites = mist_lib.requests.orgs.sites.get(mist_session, org_id)["result"]
            org_wlans = mist_lib.requests.orgs.wlans.report(mist_session, org_id, fields)        
            for org_wlan in org_wlans:
                if len(org_ids) > 1 or org_wlan[0] in site_ids:     
                    site = list(filter(lambda site: site['id'] == org_wlan[0], org_sites))
                    if len(site) == 1:
                        site_name = site[0]["name"]
                        site_country_code = country_code(site[0])
                    else:
                        site_name = ""
                        site_country_code = "N/A"
                    org_wlan.insert(0, "org")
                    org_wlan.insert(1, org_info["name"])
                    org_wlan.insert(2, org_info["id"])
                    org_wlan.insert(3, site_name)
                    org_wlan.insert(5, site_country_code)
                    wlans_summarized.append(org_wlan)
            wlans_from_sites(mist_session, org_sites, org_info, site_ids)        
        else:
            org_info = {
                "name":org_sites[0]["org_name"],
                "id":org_sites[0]["org_id"]
            }
            org_sites = []
            for site_id in site_ids:
                org_sites.append(mist_lib.requests.sites.info.get(mist_session, site_id)["result"])
            wlans_from_sites(mist_session, org_sites, org_info, site_ids)        


#### SCRIPT ENTRYPOINT ####

mist = mist_lib.Mist_Session()

org_ids = cli.select_org(mist, allow_many=True)
if len(org_ids) == 1:
    site_ids = cli.select_site(mist, org_id=org_ids[0], allow_many=True)

wlans_from_orgs(mist, org_ids, site_ids)

            
fields.insert(0, "origin")   
fields.insert(1, "org_name")   
fields.insert(2, "org_id")
fields.insert(3, "site_name")
fields.insert(4, "site_id")
fields.insert(5, "country_code")

cli.show(wlans_summarized, fields)

print("saving to file...")
with open(csv_file, "w") as f:
    for column in fields:
        f.write("%s," % column)
    f.write('\r\n')
    for row in wlans_summarized:
        for field in row:
            f.write(field)
            f.write(csv_separator)
        f.write('\r\n')
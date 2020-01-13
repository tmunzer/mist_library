'''
Python script to list all WLANs from orgs/sites and their parameters, and save it to a CSV file.
You can configure which fields you want to retrieve/save, and where the script will save the CSV file.

You can run the script with the command "python3 org_report_wlans.py <path_to_the_csv_file>"

The script has 2 different steps:
1) admin login
2) select the organisation/site from where you want to retrieve the information
'''

#### PARAMETERS #####
csv_separator = ","
fields = ["map_id", "id", "name", "ip", "model", "radio_stat.band_24.mac", "radio_stat.band_5.mac" ]
csv_file = "./org_report_bssids_report.csv"

org_ids = []
site_ids = []

#### IMPORTS ####
import mlib as mist_lib
from mlib import cli

#### GLOBAL VARIABLES ####
bssid_list = []

#### FUNCTIONS ####


def bssids_from_sites(mist_session, sites, org_info, site_ids):
    for site in sites:
        if len(org_ids) > 1 or site["id"] in site_ids:     
            devices = mist_lib.requests.sites.devices.get_stats_devices(mist_session, site["id"])["result"]                
            for site_device in devices:
                device_stat = []    
                device_stat.append(org_info["id"])           
                device_stat.append(org_info["name"])           
                device_stat.append(site["id"])           
                device_stat.append(site["name"])     
                for field in fields:
                    field_data = cli.extract_field(site_device, field)   
                    if (field == "radio_stat.band_24.mac" or field == "radio_stat.band_5.mac") and not field_data == "N/A":
                        mac_start = field_data
                        mac_end = field_data[:-1] + "f"
                        device_stat.append("%s to %s" %(mac_start, mac_end))
                    else:
                        device_stat.append(field_data)                      
                bssid_list.append(device_stat)

def bssids_from_orgs(mist_session, org_ids, site_ids):
    for org_id in org_ids:
        org_sites = list(filter(lambda privilege: "org_id" in privilege and privilege["org_id"] == org_id, mist_session.privileges))
        # the admin only has access to the org information if he/she has this privilege 
        if len(org_sites) >= 1 and org_sites[0]["scope"] == "org":
            org_info = mist_lib.requests.org.info.get(mist_session, org_id)["result"]
            org_sites = mist_lib.requests.org.sites.get(mist_session, org_id)["result"]
            bssids_from_sites(mist_session, org_sites, org_info, site_ids)        
        # if the admin doesn't have access to the org level, but only the sites
        elif len(org_sites) >= 1:
            org_info = {
                "name":org_sites[0]["org_name"],
                "id":org_sites[0]["org_id"]
            }
            org_sites = []
            # get the sites information
            for site_id in site_ids:
                org_sites.append(mist_lib.requests.sites.info.get(mist_session, site_id)["result"])
            bssids_from_sites(mist_session, org_sites, org_info, site_ids)        


#### SCRIPT ENTRYPOINT ####

mist = mist_lib.Mist_Session()

org_ids = cli.select_org(mist, allow_many=True)
if len(org_ids) == 1:
    site_ids = cli.select_site(mist, org_id=org_ids[0], allow_many=True)

bssids_from_orgs(mist, org_ids, site_ids)

fields.insert(0, "org_id")   
fields.insert(1, "org_name")   
fields.insert(2, "site_id")
fields.insert(3, "site_name")

cli.show(bssid_list, fields)
cli.save_to_csv(csv_file, bssid_list, fields, csv_separator)
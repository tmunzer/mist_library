'''
Written by Thomas Munzer (tmunzer@juniper.net)
Github repository: https://github.com/tmunzer/Mist_library/

Python script gerenates a Rogue AP report.
It will list all the Rogue APs based on the selected types ("r_type" variable), 
and generate a CSV file based on the selected fields ("fields" variable).

The script is requesting information for all the organisation the admin has access to.

You can run the script with the command "python3 org_report_rogue.py"
'''


#### PARAMETERS #####
csv_separator = ","
csv_file = "./report_rogues.csv"
fields = ["ssid", "bssid", "num_aps", "ap_mac", "channel", "avg_rssi", "times_heard" ]
r_types = [ "honeypot", "lan", "others", "spoof"]

#### IMPORTS #####
import mlib as mist_lib
from mlib import cli

#### GLOBAL VARIABLES ####
rogues_summarized = []

#### FUNCTIONS ####
def get_rogues(org_info, site_ids):
    for site_id in site_ids:
        for r_type in r_types:
            print(f"{org_info['name']} > {site_id} > {r_type} ".ljust(79, "."), end='', flush=True)
            rogues = []
            site_info = mist_lib.requests.sites.info.get(mist, site_id)["result"]
            site_rogues = mist_lib.requests.sites.rogues.report(mist, site_id, r_type, fields)
            for rogue in site_rogues:    
                rogue.insert(0, org_info["name"])
                rogue.insert(1, org_info["id"])
                rogue.insert(2, site_info["name"])
                rogue.insert(3, site_info["id"])
                rogue.insert(4, r_type)
                rogues_summarized.append(rogue)
            print("\033[92m\u2714\033[0m")



#### SCRIPT ENTRYPOINT ####
mist = mist_lib.Mist_Session()

org_id = cli.select_org(mist, allow_many=False)
if len(org_id) == 0:
    print("No Org selected... Exiting...")
else:
    site_ids = cli.select_site(mist, org_id[0], allow_many=True)
    if len(site_ids) <= 0:
        print("No Site selected... Exiting...")
    else:
        print(" Process Started ".center(80, '-'))
        org_info = mist_lib.requests.orgs.info.get(mist, org_id[0])["result"]
        get_rogues(org_info, site_ids)
                    
        fields.insert(0, "org_name")
        fields.insert(1, "org_id")
        fields.insert(2, "site_name")
        fields.insert(3, "site_id")
        fields.insert(4, "type")

        print(" Process Done ".center(80, '-'))
        cli.show(rogues_summarized, fields)
        cli.save_to_csv(csv_file, rogues_summarized, fields, csv_separator)



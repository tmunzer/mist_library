'''
Python script gerenates a Rogue AP report.
It will list all the Rogue APs based on the selected types ("r_type" variable), 
and generate a CSV file based on the selected fields ("fields" variable).

The script is requesting information for all the organisation the admin has access to.

You can run the script with the command "python3 org_report_rogue.py"
'''

import mlib as mist_lib
from mlib import cli
from tabulate import tabulate

#### PARAMETERS #####
csv_separator = ","
csv_file = "./report_rogues.csv"
fields = ["ssid", "bssid", "num_aps", "ap_mac", "channel", "avg_rssi", "times_heard" ]
r_types = [ "honeypot", "lan", "others", "spoof"]


mist = mist_lib.Mist_Session("./session.py")

rogues_summarized = []

for r_type in r_types:
    for entry in mist.privileges:    
        if not "site_id" in entry and "org_id" in entry and entry["org_id"] != "":
            sites = mist_lib.requests.org.sites.get(mist, entry["org_id"])["result"]
            for site in sites:
                rogues = []
                site_rogues = mist_lib.requests.sites.rogues.report(mist, site["id"], r_type, fields)
                for rogue in site_rogues:    
                    rogue.insert(0, entry["name"])
                    rogue.insert(1, entry["org_id"])
                    rogue.insert(2, site["name"])
                    rogue.insert(3, site["id"])
                    rogue.insert(4, r_type)
                    rogues_summarized.append(rogue)




            
fields.insert(0, "org_name")
fields.insert(1, "org_id")
fields.insert(2, "site_name")
fields.insert(3, "site_id")
fields.insert(4, "type")

cli.show(rogues_summarized, fields)
cli.save_to_csv(csv_file, rogues_summarized, fields, csv_separator)



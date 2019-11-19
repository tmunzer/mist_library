import mlib as mist_lib
from tabulate import tabulate

#### PARAMETERS #####
csv_separator = ","


mist = mist_lib.Mist_Session("./session.py")

rogues_summarized = []
fields = ["ssid", "bssid", "num_aps", "ap_mac", "channel", "avg_rssi", "times_heard" ]
r_types = [ "honeypot", "lan", "others", "spoof"]

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
print(tabulate(rogues_summarized, fields))

print("saving to file...")
with open("./../report_rogues.csv", "w") as f:
    for column in fields:
        f.write("%s," % column)
    f.write('\r\n')
    for row in rogues_summarized:
        for field in row:
            f.write(field)
            f.write(csv_separator)
        f.write('\r\n')
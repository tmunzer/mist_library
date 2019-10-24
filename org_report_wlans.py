import mlib as mist_lib
from tabulate import tabulate

#### PARAMETERS #####
csv_separator = ","


mist = mist_lib.Mist_Session()

wlans_summarized = []
fields = ["ssid", "enabled", "auth", "auth_servers", "acct_servers", "band", "interface", "vlan_id", "dynamic_vlan", "hide_ssid" ]
for entry in mist.privileges:
    if not "site_id" in entry and "org_id" in entry and entry["org_id"] != "":
        sites = mist_lib.requests.org.sites.get(mist, entry["org_id"])["result"]
        for site in sites:
            wlans = []
            site_wlans = mist_lib.requests.sites.wlans.report(mist, site["id"], fields)            
            for site_wlan in site_wlans:                
                site_wlan.insert(0, entry["name"])
                site_wlan.insert(1, entry["org_id"])
                site_wlan.insert(2, site["name"])
                site_wlan.insert(3, site["id"])
                if "country_code" in site:
                    site_wlan.insert(4, site["country_code"])
                else:
                    site_wlan.insert(4, "N/A")
                wlans_summarized.append(site_wlan)

            
fields.insert(0, "or_gname")
fields.insert(1, "org_id")
fields.insert(2, "site_name")
fields.insert(3, "site_id")
fields.insert(4, "country_code")
print(tabulate(wlans_summarized, fields))

print("saving to file...")
with open("./../report.csv", "w") as f:
    for column in fields:
        f.write("%s," % column)
    f.write('\r\n')
    for row in wlans_summarized:
        for field in row:
            f.write(field)
            f.write(csv_separator)
        f.write('\r\n')
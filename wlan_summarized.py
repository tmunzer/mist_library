from  Mist import Mist
from tabulate import tabulate
from getpass import getpass

email = input("Login:")
password = getpass("Password:")

a = Mist("api.mist.com", email=email, password=password)

wlans_summarized = []
for entry in a.privileges:
    if not "site_id" in entry and "org_id" in entry and entry["org_id"] != "":
        sites = a.org.Sites().mget(a, entry["org_id"])["result"]
        for site in sites:
            wlans = []
            site_wlans = a.site.Wlan().summarize(a, site["id"])            
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
            

fields = ["org_name", "org_id", "site_name", "site_id", "country_code", "ssid", "enabled", "auth", "auth_servers", "acct_servers", "band", "interface", "vlan_id", "dynamic_vlan", "hide_ssid" ]
print(tabulate(wlans_summarized, fields))

print("saving to file...")
with open("report.csv", "w") as f:
    for column in fields:
        f.write("%s," % column)
    f.write('\r\n')
    for row in wlans_summarized:
        for field in row:
            f.write(u' '.join(field).encode())
        f.write('\r\n')
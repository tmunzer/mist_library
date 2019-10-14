from  lib.mist import Mist_Session
from tabulate import tabulate

#### PARAMETERS #####
csv_separator = ","



def org_select():
    i=-1
    org_ids=[]
    print("\r\nAvailable organizations:")
    for privilege in mist.privileges:
        if privilege["scope"] == "org":
            i+=1
            org_ids.append(privilege["org_id"])
            print("%s) %s (id: %s)" % (i, privilege["name"], privilege["org_id"]))
    resp = input("\r\nSelect an Org (0 to %s, or q to exit): " %i)
    if resp == "q":
        exit(0)
    else:
        try:
            resp_num = int(resp)
            if resp_num >= 0 and resp_num <= i:
                return org_ids[resp_num]
            else:
                print("Please enter a number between 0 and %s." %i)
                return org_select()
        except:
            print("Please enter a number.")
            return org_select()

def site_select(org_id):
    i=-1
    site_ids=[]
    print("\r\nAvailable sites:")
    for privilege in mist.privileges:
        if privilege["scope"] == "site" and privilege["org_id"] == org_id:
            i+=1
            site_ids.append(privilege["site_id"])
            print("%s) %s (id: %s)" % (i, privilege["name"], privilege["site_id"]))
    resp = input("\r\nSelect a Site (0 to %s, \"0,1\" for sites 0 and 1, a for all, or q to exit): " %i)
    if resp == "q":
        exit(0)
    elif resp == "a":
        return site_ids
    else:
        try:
            resp = resp.split(",")
            resp_list = []
            for num in resp:
                resp_num = int(num)
                if resp_num >= 0 and resp_num <= i:
                    resp_list.append(site_ids[resp_num])
                else:
                    print("%s is not part of the possibilities." % resp_num)
                    return site_select(org_id)
            return resp_list
        except:
            print("Only numbers are allowed.")
            return site_select(org_id)

mist = Mist_Session()
org_id = org_select()
site_ids = site_select(org_id)

        string += "Enabled: %s\r\n" %self.enabled
        string += "honeypot_enabled: %s\r\n" %self.honeypot_enabled
        string += "min_rssi: %s\r\n" %self.min_rssi
        string += "min_duration: %s\r\n" %self.min_duration
        string += "whitelisted_ssids: %s\r\n" %self.whitelisted_ssids
        string += "whitelisted_bssids: %s\r\n" %self.whitelisted_bssids
mist.site.site.set_rogue()

exit(0)
wlans_summarized = []
fields = ["ssid", "enabled", "auth", "auth_servers", "acct_servers", "band", "interface", "vlan_id", "dynamic_vlan", "hide_ssid" ]
for entry in mist.privileges:
    if not "site_id" in entry and "org_id" in entry and entry["org_id"] != "":
        sites = mist.org.sites.get(mist, entry["org_id"])["result"]
        for site in sites:
            wlans = []
            site_wlans = mist.site.wlan.report(mist, site["id"], fields)            
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
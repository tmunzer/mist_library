'''
Github repository: https://github.com/tmunzer/Mist_library/
Written by Thomas Munzer (tmunzer@juniper.net)
'''

import mlib as mist_lib
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

mist = mist_lib.Mist_Session()
org_id = org_select()
site_ids = site_select(org_id)

  
settings = mist_lib.models.sites.Settings()
settings.rogue.cli()

for site_id in site_ids:
    mist_lib.requests.sites.settings.update(mist, site_id, settings.toJSON())
    print(mist_lib.requests.sites.settings.get(mist, site_id)['result']["rogue"])
exit(0)
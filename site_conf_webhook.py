'''
Written by Thomas Munzer (tmunzer@juniper.net)
Github repository: https://github.com/tmunzer/Mist_library/
'''

import mlib as mist_lib
from tabulate import tabulate

#### PARAMETERS #####
csv_separator = ","



def multichoices(list_title="", entries_list="", allow_all=False):
    i=-1
    ids = []
    print("\r\n%s" % list_title)
    for entry in entries_list:        
        i+=1
        ids.append(entry["id"])
        print("%s) %s (id: %s)" % (i, entry["name"], entry["id"]))
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
    site_choices = mist_lib.requests.orgs.sites.get(mist, org_id)['result']
    print("\r\nAvailable sites:")
    for site in site_choices:        
        i+=1
        site_ids.append(site["id"])
        print("%s) %s (id: %s)" % (i, site["name"], site["id"]))
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


wh = mist_lib.models.sites.webhooks.Webhook()
#wh.cli()
#print(wh)

for site_id in site_ids:
#    mist_lib.requests.sites.webhooks.create(mist, site_id, wh.toJSON())
#    print(mist_lib.requests.sites.webhooks.get(mist, site_id)['result'])


    for webhook in mist_lib.requests.sites.webhooks.get(mist, site_id)["result"]:
        mist_lib.requests.sites.webhooks.delete(mist, webhook['site_id'], webhook['id'])
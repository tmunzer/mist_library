import mlib as mist_lib
import json

def select_org(mist_session, allow_many=False):
    i=-1
    org_ids=[]
    print("\r\nAvailable organizations:")
    for privilege in mist_session.privileges:
        if privilege["scope"] == "org":
            i+=1
            org_ids.append(privilege["org_id"])
            print("%s) %s (id: %s)" % (i, privilege["name"], privilege["org_id"]))
    string = "\r\nSelect an Org (0 to %s," % i
    if allow_many == True:
        string += ""
    resp = input(" %s or q to exit): " % string)
    if resp == "q":
        exit(0)
    else:
        try:
            resp_num = int(resp)
            if resp_num >= 0 and resp_num <= i:
                return org_ids[resp_num]
            else:
                print("Please enter a number between 0 and %s." %i)
                return select_org(mist_session)
        except:
            print("Please enter a number.")
            return select_org(mist_session)

def select_site(mist_session, org_id=None, allow_many=False):
    if org_id == None:
        org_id = select_org(mist_session)
    i=-1
    site_ids=[]
    site_choices = mist_lib.requests.org.sites.get(mist_session, org_id)['result']
    print("\r\nAvailable sites:")
    for site in site_choices:        
        i+=1
        site_ids.append(site["id"])
        print("%s) %s (id: %s)" % (i, site["name"], site["id"]))
    if allow_many: resp = input("\r\nSelect a Site (0 to %s, \"0,1\" for sites 0 and 1, \"a\" for all, or q to exit): " %i)
    else: resp = input("\r\nSelect a Site (0 to %s, \"0,1\" for sites 0 and 1, or q to exit): " %i)
    if resp.lower() == "q":
        exit(0)
    elif resp.lower() == "a" and allow_many:
        return site_ids
    else:
        try:
            resp = resp.split(",")
            for num in resp:
                resp_num = int(num)
                if resp_num >= 0 and resp_num <= i:
                    return site_choices[resp_num]["id"]
                else:
                    print("%s is not part of the possibilities." % resp_num)
                    return select_site(org_id)
        except:
            print("Only numbers are allowed.")
            return select_site(mist_session, org_id, allow_many)


def display_json(data):
    print(json.dumps(data, sort_keys=True, indent=4, separators=(',', ': ')))

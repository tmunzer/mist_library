import mlib as mist_lib
from tabulate import tabulate
import sys
import csv
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
    site_choices = mist_lib.requests.org.sites.get(mist, org_id)['result']
    print("\r\nAvailable sites:")
    for site in site_choices:        
        i+=1
        site_ids.append(site["id"])
        print("%s) %s (id: %s)" % (i, site["name"], site["id"]))
    resp = input("\r\nSelect a Site (0 to %s, \"0,1\" for sites 0 and 1, or q to exit): " %i)
    if resp == "q":
        exit(0)
    else:
        try:
            resp = resp.split(",")
            for num in resp:
                resp_num = int(num)
                if resp_num >= 0 and resp_num <= i:
                    return site_choices[resp_num]["id"]
                else:
                    print("%s is not part of the possibilities." % resp_num)
                    return site_select(org_id)
        except:
            print("Only numbers are allowed.")
            return site_select(org_id)

    


mist = mist_lib.Mist_Session()
org_id = org_select()
site_id = site_select(org_id)
  
psk = mist_lib.models.sites.psks.Psk()
print("Opening CSV file %s" % sys.argv[1])
try:
    with open(sys.argv[1], 'r') as my_file:
        ppsk_file = csv.reader(my_file, delimiter=',')
        for row in ppsk_file:
            username = row[0]
            passphrase = row[1]
            ssid = "MlN"            
            print(', '.join(row))
            psk.define(name=username, passphrase=passphrase, ssid=ssid)
            mist_lib.requests.sites.psks.create(mist, site_id, psk.toJSON())
            print(psk.toJSON())
except:
    print("Error while opening the CSV file... Aborting")

psks = mist_lib.requests.sites.psks.get(mist, site_id)['result']
print(psks)
exit(0)
for psk in psks:
    mist_lib.requests.sites.psks.delete(mist, site_id, psk_id=psk['id'])
print(mist_lib.requests.sites.psks.get(mist, site_id)['result'])
import mlib as mist_lib
from tabulate import tabulate
import mlib.cli as cli
import sys
import csv
#### PARAMETERS #####
csv_separator = ","
privileges = [{ "scope":"site", "site_id": "91e219cb-8fe7-4ab7-88bb-a7dcfdfebbd5", "role": "write" }]
org_id = "ebad74f0-2614-42a8-b400-850a0f98248a"
    # "privileges": [
    #     { "scope":"org", "role": "admin" },
    #     { "scope":"site", "site_id": "d96e3952-53e8-4266-959a-45acd55f5114", "role": "admin" }
    # ]

mist = mist_lib.Mist_Session()
if privileges == []:
    org_id = cli.select_org(mist)
    permission = input("Which level of privilege at the org level (\"a\" for admin, \"w\" for write,\"r\" for read,\"h\" for helpdesk,\"i\" for installer, \"n\" for none)")
    if permission.lower() == "a":
        privileges.append()
    while True:
        all_sites = input("Do you want to select specific sites (Y/n)?")
        if all_sites.lower()=="y": 
            site_ids = cli.select_site(mist, org_id, True)
            break
        elif all_sites.lower() == "n" or all_sites == "":
            site_ids = []
            break



print("Opening CSV file %s" % sys.argv[1])
try:
    with open(sys.argv[1], 'r') as my_file:
        invite_file = csv.reader(my_file, delimiter=',')
        for row in invite_file:  
            email= row[0]
            first_name= row[1]
            last_name = row[2]        
            print(', '.join(row))
            mist_lib.requests.org.admins.create_invite(mist, org_id, email, privileges, first_name, last_name)            
except:
    print("Error while opening the CSV file... Aborting")

admins = mist_lib.requests.org.admins.get(mist, org_id)['result']
print(admins)
exit(0)

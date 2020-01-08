'''
Python script to invite/add adminsitrators from a CSV file.
The CSV file must have 3 columns: email, first name, last name

You can run the script with the command "python3 org_admins_import.py <path_to_the_csv_file>"

The script has 3 different steps:
1) admin login
2) select the organisation where you want to add/invite the admins
3) choose if you want to give access to the whole organisation, or only to specific sites
'''
#### PARAMETERS #####
csv_separator = ","
privileges = []

#### IMPORTS ####
import mlib as mist_lib
from tabulate import tabulate
import mlib.cli as cli
import sys
import csv

#### CONSTANTS ####
roles = {"s": "admin", "n": "write", "o": "read", "h":"helpdesk"}

#### FUNCTIONS ####
def define_privileges(org_id):
    '''
    Generate the privilege parameters for the specified org.
    Will ask if the privileges have to be applied to the entire org or to a specific site/s, and the privilege level.
    There is no return value, the new privileges are stored into the global "privilege" variable
    '''
    role = ""
    while role not in roles:
        role = input("Which level of privilege at the org level (\"s\" for Super Admin, \"n\" for Network Admin,\"o\" for observer,\"h\" for helpdesk)")    
    while True:
        all_sites = input("Do you want to select specific sites (y/N)?")
        if all_sites.lower()=="y": 
            site_ids = cli.select_site(mist, org_id, True)
            for site_id in site_ids:
                privileges.append({"scope": "site", "org_id": org_id, "site_id": site_id, "role":roles[role]})
            break
        elif all_sites.lower() == "n" or all_sites == "":            
            site_ids = mist_lib.org.sites.get(mist, org_id)
            site_id=""
            for site in site_ids["result"]:
                if "site_id" in site:
                    site_id = site["site_id"]
                    break
            privileges.append({"scope": "org", "org_id": org_id, "site_id":site_id, "role":roles[role]})
            break 

def import_admins(file_path, org_id):
    '''
    create all the administrators from the "file_path" file.
    '''
    print("Opening CSV file %s" % file_path)
    try:
        with open(file_path, 'r') as my_file:
            invite_file = csv.reader(my_file, delimiter=',')
            for row in invite_file:  
                email= row[0]
                first_name= row[1]
                last_name = row[2]        
                print(', '.join(row))
                mist_lib.requests.org.admins.create_invite(mist, org_id, email, privileges, first_name, last_name)            
    except:
        print("Error while opening the CSV file... Aborting")

#### SCRIPT ENTRYPOINT ####
file_path = sys.argv[1]
mist = mist_lib.Mist_Session("./session.py")

org_id = cli.select_org(mist)

if privileges == []:
    define_privileges(org_id)
import_admins(file_path, org_id)

admins = mist_lib.requests.org.admins.get(mist, org_id)['result']
print(tabulate(admins))
exit(0)

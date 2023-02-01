'''
Written by Thomas Munzer (tmunzer@juniper.net)
Github repository: https://github.com/tmunzer/Mist_library/

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
import sys
import mistapi
from mistapi.__logger import console
import csv

#### CONSTANTS ####
roles = {"s": "admin", "n": "write", "o": "read", "h":"helpdesk"}

#### FUNCTIONS ####
def define_privileges(apisession, org_id):
    '''
    Generate the privilege parameters for the specified orgs.
    Will ask if the privileges have to be applied to the entire org or to a specific site/s, and the privilege level.
    There is no return value, the new privileges are stored into the global "privilege" variable
    '''
    role = ""
    while role not in roles:
        role = input("Which level of privilege at the org level (\"s\" for Super Admin, \"n\" for Network Admin,\"o\" for observer,\"h\" for helpdesk)? ")    
    while True:
        all_sites = input("Do you want to select specific sites (y/N)? ")
        if all_sites.lower()=="y": 
            site_ids = mistapi.cli.select_site(apisession, org_id, True)
            for site_id in site_ids:
                privileges.append({"scope": "site", "org_id": org_id, "site_id": site_id, "role":roles[role]})
            break
        elif all_sites.lower() == "n" or all_sites == "":            
            site_ids = mistapi.api.v1.orgs.sites.getOrgSites(apisession, org_id)
            site_id=""
            for site in site_ids.data:
                if "site_id" in site:
                    site_id = site["site_id"]
                    break
            privileges.append({"scope": "org", "org_id": org_id, "site_id":site_id, "role":roles[role]})
            break 

def import_admins(apisession, file_path, org_id):
    '''
    create all the administrators from the "file_path" file.
    '''
    print(f"Opening CSV file {file_path}")
    try:
        with open(file_path, 'r') as my_file:
            invite_file = csv.reader(my_file, delimiter=csv_separator)
            for row in invite_file:  
                body = {
                "email": row[0],
                "first_name":row[1],
                "last_name": row[2],
                "privileges": privileges      
                }
                print(', '.join(row))
                mistapi.api.v1.orgs.invites.inviteOrgAdmin(apisession, org_id, body)
    except Exception as e:
        print("Error while opening the CSV file... Aborting")
        print(e)

#### SCRIPT ENTRYPOINT ####
if __name__ == "__main__":
    file_path = sys.argv[1]
    apisession = mistapi.APISession()
    apisession.login()

    org_id = mistapi.cli.select_org(apisession)[0]

    define_privileges(apisession, org_id)
    import_admins(apisession, file_path, org_id)

    admins = mistapi.api.v1.orgs.admins.getOrgAdmins(apisession, org_id).data
    print(admins)
    mistapi.cli.display_list_of_json_as_table(admins)
    mistapi.cli.pretty_print(admins)
    sys.exit(0)

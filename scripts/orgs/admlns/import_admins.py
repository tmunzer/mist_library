'''
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to invite/add adminsitrators from a CSV file.

It is recomended to use an environment file to store the required information
to request the Mist Cloud (see https://pypi.org/project/mistapi/ for more 
information about the available parameters).

-------
Requirements:
mistapi: https://pypi.org/project/mistapi/

-------
Usage:
This script requires one parameters pointing to the CSV file. 
The CSV file must have 3 columns: email, first name, last name.
The organization and the admin roles/scopes will be asked by the script.

-------
CSV Example:
owkenobi@unknown.com,Obi-Wan,Kenobi
pamidala@unknown.com,Padme,Amidala



-------
Example:
python3 import_admins.py <path_to_the_csv_file>"

'''
#### IMPORTS ####
import sys
import csv
import logging

MISTAPI_MIN_VERSION = "0.44.1"

try:
    import mistapi
    from mistapi.__logger import console
except:
        print("""
        Critical: 
        \"mistapi\" package is missing. Please use the pip command to install it.

        # Linux/macOS
        python3 -m pip install mistapi

        # Windows
        py -m pip install mistapi
        """)
        sys.exit(2)

#### PARAMETERS #####
csv_separator = ","
privileges = []
env_file="~/.mist_env"
log_file = "./script.log"

#####################################################################
#### LOGS ####
logger = logging.getLogger(__name__)

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
            site_ids = mistapi.api.v1.orgs.sites.listOrgSites(apisession, org_id)
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
                print(', '.join(row).ljust(80), end="", flush=True)
                try:
                    response = mistapi.api.v1.orgs.invites.inviteOrgAdmin(apisession, org_id, body)
                    if response.status_code == 200:
                        print("\033[92m\u2714\033[0m")
                    else:
                        print('\033[31m\u2716\033[0m')
                except: 
                    print('\033[31m\u2716\033[0m')
    except Exception as e:
        print("Error while opening the CSV file... Aborting")
        print(e)

def check_mistapi_version():
    if mistapi.__version__ < MISTAPI_MIN_VERSION:
        logger.critical(f"\"mistapi\" package version {MISTAPI_MIN_VERSION} is required, you are currently using version {mistapi.__version__}.")
        logger.critical(f"Please use the pip command to updated it.")
        logger.critical("")
        logger.critical(f"    # Linux/macOS")
        logger.critical(f"    python3 -m pip install --upgrade mistapi")
        logger.critical("")
        logger.critical(f"    # Windows")
        logger.critical(f"    py -m pip install --upgrade mistapi")
        print(f"""
    Critical: 
    \"mistapi\" package version {MISTAPI_MIN_VERSION} is required, you are currently using version {mistapi.__version__}. 
    Please use the pip command to updated it.

    # Linux/macOS
    python3 -m pip install --upgrade mistapi

    # Windows
    py -m pip install --upgrade mistapi
        """)
        sys.exit(2)
    else: 
        logger.info(f"\"mistapi\" package version {MISTAPI_MIN_VERSION} is required, you are currently using version {mistapi.__version__}.")

#####################################################################
##### ENTRY POINT ####
if __name__ == "__main__":
    #### LOGS ####
    logging.basicConfig(filename=log_file, filemode='w')
    logger.setLevel(logging.DEBUG)
    check_mistapi_version()

    ### START ###
    file_path = sys.argv[1]
    apisession = mistapi.APISession(env_file=env_file)
    apisession.login()

    org_id = mistapi.cli.select_org(apisession)[0]

    define_privileges(apisession, org_id)
    import_admins(apisession, file_path, org_id)

    admins = mistapi.api.v1.orgs.admins.listOrgAdmins(apisession, org_id).data
    

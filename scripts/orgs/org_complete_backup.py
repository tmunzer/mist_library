'''
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to backup a whole organization configuration and devices. 

IMPORTANT:
By default, the script will not migrade the devices. Please use the -u/--uclaim
option to migrate them (AP ONLY). 
Please use -u/--uclaim AND -a/--unclaim_all to also migrate the switches and
the gateways

-------
Requirements:
mistapi: https://pypi.org/project/mistapi/

This script requires the following scripts to be in the same folder:
- org_conf_backup.py
- org_inventory_backup.py

-------
Usage:
This script can be run as is (without parameters), or with the options below.
If no options are defined, or if options are missing, the missing options will
be asked by the script or the default values will be used.

It is recomended to use an environment file to store the required information
to request the Mist Cloud (see https://pypi.org/project/mistapi/ for more 
information about the available parameters).

-------
Script Parameters:
-h, --help              display this help

--org_id=           Optional, org_id of the org to clone
--org_name=         Optional, name of the org to clone, for validation 
                        purpose. Requires org_id to be defined

--src_env=              Optional, env file to use to access the src org (see
                        mistapi env file documentation here: 
                        https://pypi.org/project/mistapi/)
                        default is "~/.mist_env"

-l, --log_file=         define the filepath/filename where to write the logs
                        default is "./script.log"
-b, --backup_folder=    Path to the folder where to save the org backup (a 
                        subfolder will be created with the org name)
                        default is "./org_backup"

'''
#####################################################################
#### IMPORTS ####
import sys
import logging
import getopt

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

try:
    import org_conf_backup
    import org_inventory_backup
except:
    print("""
Critical: 
This script is using other scripts from the mist_library to perform all the
action. Please make sure the following python files are in the same folder
as the org_clone.py file:
    - org_conf_backup.py
    - org_inventory_backup.py
    """)
    sys.exit(2)

#####################################################################
#### PARAMETERS #####
backup_folder = "./org_backup"
log_file = "./script.log"
src_env_file =  "~/.mist_env"

#####################################################################
#### LOGS ####
logger = logging.getLogger(__name__)

#####################################################################
#### ORG FUNCTIONS ####
def _backup_org(source_mist_session:mistapi.APISession, org_id:str, backup_folder_param=str):
    try:
        _print_new_step("Backuping SOURCE Org Configuration")
        org_conf_backup.start(source_mist_session, org_id, backup_folder_param)
    except: 
        sys.exit(255)

#######
#######

def _backup_inventory(source_mist_session:mistapi.APISession, org_id:str, backup_folder_param:str):
    _print_new_step("Backuping SOURCE Org Inventory")
    org_inventory_backup.start(source_mist_session, org_id, backup_folder_param)   

#######
#######

def _print_new_step(message):
    print()
    print("".center(80,'*'))
    print(f" {message} ".center(80,'*'))
    print("".center(80,'*'))
    print()
    logger.info(f"{message}")

#######
#######
def _check_org_name(apisession:mistapi.APISession, dst_org_id:str, org_type:str, org_name:str=None):
    if not org_name:
        org_name = mistapi.api.v1.orgs.orgs.getOrgInfo(apisession, dst_org_id).data["name"]
    while True:
        print()
        resp = input(
            f"To avoid any error, please confirm the current {org_type} orgnization name: ")
        if resp == org_name:
            return True
        else:
            print()
            print("The orgnization names do not match... Please try again...")

#######
#######
def _select_org(org_type:str, mist_session=None):    
    org_id = mistapi.cli.select_org(mist_session)[0]
    org_name = mistapi.api.v1.orgs.orgs.getOrgInfo(mist_session, org_id).data["name"]
    _check_org_name(mist_session, org_id, org_type, org_name)
    return org_id, org_name

def _check_org_name_in_script_param(apisession:mistapi.APISession, org_id:str, org_name:str=None):
    response = mistapi.api.v1.orgs.orgs.getOrgInfo(apisession, org_id)
    if response.status_code != 200:
        console.critical(f"Unable to retrieve the org information: {response.data}")
        sys.exit(3)
    org_name_from_mist = response.data["name"]
    return org_name == org_name_from_mist
    

def _check_src_org(apisession:mistapi.APISession, org_id:str, org_name:str):
    _print_new_step("SOURCE Org")
    if org_id and org_name:
        if not _check_org_name_in_script_param(apisession, org_id, org_name):
            console.critical(f"Org name {org_name} does not match the org {org_id}")
            sys.exit(0)
    elif org_id and not org_name:
        return _check_org_name(apisession, org_id)
    elif not org_id and not org_name:
        return  _select_org("source", apisession)
    elif not org_id and org_name:
        console.critical(f"\"org_name\" cannot be defined without \"org_id\". Please remove \"org_name\" parameter or add \"org_id\"")
        sys.exit(0)
    else: #should not since we covered all the possibilities...
        sys.exit(0)


def start(apisession: mistapi.APISession, org_id:str=None, org_name:str=None, backup_folder_param:str=None,):    
    '''
    Start the process to clone the src org to the dst org

    PARAMS
    -------
    :param  mistapi.APISession  apisession      - mistapi session with `Super User` access the source Org, already logged in
    :param  str                 org_id          - Optional, org_id of the org to clone
    :param  str                 org_name        - Optional, name of the org to clone, for validation purpose. Requires org_id to be defined
    :param  str                 backup_folder_param - Path to the folder where to save the org backup (a subfolder will be created with the org name). default is "./org_backup"
    
    '''
    if not backup_folder_param: backup_folder_param = backup_folder
    org_id, org_name = _check_src_org(apisession, org_id, org_name)
    
    _backup_org(apisession, org_id, backup_folder_param)
    _backup_inventory(apisession, org_id, backup_folder_param)
    _print_new_step("Process finised")
    
###############################################################################
#### USAGE ####
def usage():
    print('''
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to backup a whole organization configuration and devices. 

IMPORTANT:
By default, the script will not migrade the devices. Please use the -u/--uclaim
option to migrate them (AP ONLY). 
Please use -u/--uclaim AND -a/--unclaim_all to also migrate the switches and
the gateways

-------
Requirements:
mistapi: https://pypi.org/project/mistapi/

This script requires the following scripts to be in the same folder:
- org_conf_backup.py
- org_inventory_backup.py

-------
Usage:
This script can be run as is (without parameters), or with the options below.
If no options are defined, or if options are missing, the missing options will
be asked by the script or the default values will be used.

It is recomended to use an environment file to store the required information
to request the Mist Cloud (see https://pypi.org/project/mistapi/ for more 
information about the available parameters).

-------
Script Parameters:
-h, --help              display this help

--org_id=           Optional, org_id of the org to clone
--org_name=         Optional, name of the org to clone, for validation 
                        purpose. Requires org_id to be defined

--src_env=              Optional, env file to use to access the src org (see
                        mistapi env file documentation here: 
                        https://pypi.org/project/mistapi/)
                        default is "~/.mist_env"

-l, --log_file=         define the filepath/filename where to write the logs
                        default is "./script.log"
-b, --backup_folder=    Path to the folder where to save the org backup (a 
                        subfolder will be created with the org name)
                        default is "./org_backup"

''')
    sys.exit(0)
    
###############################################################################
#### SCRIPT ENTRYPOINT ####
if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hl:b:", [
                                   "help", "org_id=", "org_name=",  "src_env=", "log_file=", "backup_folder="])
    except getopt.GetoptError as err:
        console.error(err)
        usage()

    org_id = None
    org_name = None
    backup_folder_param = None
    for o, a in opts:
        if o in ["-a", "--unclaim_all"]:
            unclaim_all = True
        elif o in ["-b", "--backup_folder"]:
            backup_folder_param = a
        elif o in ["-h", "--help"]:
            usage()
            sys.exit(0)
        elif o in ["-l", "--log_file"]:
            log_file = a
        elif o in ["--src_env"]:
            src_env_file = a
        elif o in ["--org_id"]:
            org_id = a
        elif o in ["--org_name"]:
            org_name = a
        else:
            assert False, "unhandled option"

    #### LOGS ####
    logging.basicConfig(filename=log_file, filemode='w')
    logger.setLevel(logging.DEBUG)
    ### MIST SESSION ###
    print(" API Session to access the Source Org ".center(80, "_"))
    apisession = mistapi.APISession(env_file=src_env_file)
    apisession.login()    

    ### START ###
    start(
        apisession,
        org_id=org_id,
        org_name=org_name,
        backup_folder_param=backup_folder_param, 
        )

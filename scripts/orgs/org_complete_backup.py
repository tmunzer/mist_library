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

--org_id=               Optional, org_id of the org to clone

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
def start(apisession: mistapi.APISession, org_id:str=None, backup_folder_param:str=None,):    
    '''
    Start the process to clone the src org to the dst org

    PARAMS
    -------
    :param  mistapi.APISession  apisession      - mistapi session with `Super User` access the source Org, already logged in
    :param  str                 org_id          - Optional, org_id of the org to clone
    :param  str                 backup_folder_param - Path to the folder where to save the org backup (a subfolder will be created with the org name). default is "./org_backup"
    
    '''
    if not backup_folder_param: backup_folder_param = backup_folder
    if not org_id: org_id = mistapi.cli.select_org(apisession)[0]
    
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

--org_id=               Optional, org_id of the org to clone

-e, --env=              Optional, env file to use to access the src org (see
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
        opts, args = getopt.getopt(sys.argv[1:], "hl:b:e:", [
                                   "help", "org_id=", "org_name=",  "env=", "src_env=", "log_file=", "backup_folder="])
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
        elif o in ["-e", "--env", "--src_env"]:
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
        backup_folder_param=backup_folder_param, 
        )

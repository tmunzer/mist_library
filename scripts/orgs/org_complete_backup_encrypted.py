"""
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to backup a whole organization configuration and devices in AES
encrypted files. 

This script will not change/create/delete/touch any existing objects. It will 
just retrieve every single object from the organization.

The backup is AES encrypted with a randomly generated key. The encryption key
is stored in a RSA encrypted file (encrypted with a RSA public key). The RSA
Private key is required to be able to decrypt AES encryption key. 

The encrypted backup can be decrypted with the following script:
https://github.com/tmunzer/mist_library/blob/master/scripts/utils/encryption.py

-------
Requirements:
mistapi: https://pypi.org/project/mistapi/
pycryptodome: https://pypi.org/project/pycryptodome/

This script requires the following scripts to be in the same folder:
- org_conf_backup_encrypted.py
- org_inventory_backup_encrypted.py

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

-o, --org_id=           Optional, org_id of the org to clone

--src_env=              Optional, env file to use to access the src org (see
                        mistapi env file documentation here: 
                        https://pypi.org/project/mistapi/)
                        default is "~/.mist_env"
-p, --puk=              path to the RSA public key

-l, --log_file=         define the filepath/filename where to write the logs
                        default is "./script.log"
-b, --backup_folder=    Path to the folder where to save the org backup (a 
                        subfolder will be created with the org name)
                        default is "./org_backup"

-d, --datetime          append the current date and time (ISO format) to the
                        backup name 
-t, --timestamp         append the current timestamp to the backup 

-------
Examples:
python3 ./org_complete_backup.py
python3 ./org_complete_backup.py \
    --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 \
    -p ./rsa.pub

"""
#####################################################################
#### IMPORTS ####
import sys
import logging
import getopt
import datetime

MISTAPI_MIN_VERSION = "0.52.0"
try:
    import mistapi
    from mistapi.__logger import console
except:
    print(
        """
Critical: 
\"mistapi\" package is missing. Please use the pip command to install it.

# Linux/macOS
python3 -m pip install mistapi

# Windows
py -m pip install mistapi
    """
    )
    sys.exit(2)

try:
    import org_conf_backup_encrypted
    import org_inventory_backup_encrypted
except:
    print(
        """
Critical: 
This script is using other scripts from the mist_library to perform all the
action. Please make sure the following python files are in the same folder
as the org_clone.py file:
    - org_conf_backup_encrypted.py
    - org_inventory_backup_encrypted.py
    """
    )
    sys.exit(2)

#####################################################################
#### PARAMETERS #####
DEFAULT_BACKUP_FOLDER = "./org_backup"
LOG_FILE = "./script.log"
SRC_ENV_FILE = "~/.mist_env"

#####################################################################
#### LOGS ####
LOGGER = logging.getLogger(__name__)

#####################################################################
#### ORG FUNCTIONS ####
def _backup_org(
    source_mist_session: mistapi.APISession,
    org_id: str,
    backup_folder_param:str,
    backup_name:str,
    puk_path:str

):
    LOGGER.debug(f"org_complete_backup:_backup_org")
    LOGGER.debug(f"org_complete_backup:_backup_org:parameter:org_id:{org_id}")
    LOGGER.debug(f"org_complete_backup:_backup_org:parameter:backup_folder_param:{backup_folder_param}")
    LOGGER.debug(f"org_complete_backup:_backup_org:parameter:backup_name:{backup_name}")

    try:
        _print_new_step("Backuping SOURCE Org Configuration")
        org_conf_backup_encrypted.start(
            mist_session=source_mist_session,
            org_id=org_id,
            backup_folder_param=backup_folder_param,
            backup_name=backup_name,
            puk_path=puk_path
            )
    except:
        sys.exit(255)


#######
#######


def _backup_inventory(
    source_mist_session: mistapi.APISession,
    org_id: str,
    backup_folder_param: str,
    backup_name:str,
    puk_path:str
):
    LOGGER.debug(f"org_complete_backup:_backup_inventory")
    LOGGER.debug(f"org_complete_backup:_backup_inventory:parameter:org_id:{org_id}")
    LOGGER.debug(f"org_complete_backup:_backup_inventory:parameter:backup_folder_param:{backup_folder_param}")
    LOGGER.debug(f"org_complete_backup:_backup_inventory:parameter:backup_name:{backup_name}")

    _print_new_step("Backuping SOURCE Org Inventory")
    org_inventory_backup_encrypted.start(
            mist_session=source_mist_session,
            org_id=org_id,
            backup_folder=backup_folder_param,
            backup_name=backup_name,
            puk_path=puk_path
        )


#######
#######


def _print_new_step(message):
    print()
    print("".center(80, "*"))
    print(f" {message} ".center(80, "*"))
    print("".center(80, "*"))
    print()
    LOGGER.info(f"{message}")


#######
#######
def start(
    apisession: mistapi.APISession,
    org_id: str = None,
    backup_folder_param: str = None,
    backup_name:str=None,
    backup_name_date:bool=False,
    backup_name_ts:bool=False,
    puk_path:str=None
):
    """
    Start the process to clone the src org to the dst org

    PARAMS
    -------
    apisession : mistapi.APISession
        mistapi session with `Super User` access the source Org, already logged in
    org_id : str
        Optional, org_id of the org to clone
    backup_folder_param : str
        Path to the folder where to save the org backup (a subfolder will be created
        with the org name). default is "./org_backup"
    backup_name : str
        Name of the subfolder where the the backup files will be saved
        default is the org name
    backup_name_date : bool, default = False
        if `backup_name_date`==`True`, append the current date and time (ISO 
        format) to the backup name 
    backup_name_ts : bool, default = False
        if `backup_name_ts`==`True`, append the current timestamp to the backup 
        name 
    puk_path : str, Default None
        file path to save the RSA Private key. If None, the backup will not be encrypted
    """
    LOGGER.debug(f"org_complete_backup:start")
    LOGGER.debug(f"org_complete_backup:start:parameter:org_id:{org_id}")
    LOGGER.debug(f"org_complete_backup:start:parameter:backup_folder_param:{backup_folder_param}")
    LOGGER.debug(f"org_complete_backup:start:parameter:backup_name:{backup_name}")
    LOGGER.debug(f"org_complete_backup:start:parameter:backup_name_date:{backup_name_date}")
    LOGGER.debug(f"org_complete_backup:start:parameter:backup_name_ts:{backup_name_ts}")
    LOGGER.debug(f"org_complete_backup:start:parameter:puk_path:{puk_path}")

    if not backup_folder_param:
        backup_folder_param = DEFAULT_BACKUP_FOLDER
    if not org_id:
        org_id = mistapi.cli.select_org(apisession)[0]
    org_name = mistapi.api.v1.orgs.orgs.getOrg(apisession, org_id).data["name"]

    if not backup_name:
        backup_name = org_name
    if backup_name_date:
        backup_name = f"{backup_name}_{datetime.datetime.isoformat(datetime.datetime.now()).split('.')[0].replace(':','.')}"
    elif backup_name_ts:
        backup_name = f"{backup_name}_{round(datetime.datetime.timestamp(datetime.datetime.now()))}"

    _backup_org(apisession, org_id, backup_folder_param, backup_name, puk_path)
    _backup_inventory(apisession, org_id, backup_folder_param, backup_name, puk_path)
    _print_new_step("Process finished")


###############################################################################
#### USAGE ####
def usage(error_message:str=None):
    """
    display script usage
    """
    print(
        """
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to backup a whole organization configuration and devices in AES
encrypted files. 

This script will not change/create/delete/touch any existing objects. It will 
just retrieve every single object from the organization.

The backup is AES encrypted with a randomly generated key. The encryption key
is stored in a RSA encrypted file (encrypted with a RSA public key). The RSA
Private key is required to be able to decrypt AES encryption key. 

The encrypted backup can be decrypted with the following script:
https://github.com/tmunzer/mist_library/blob/master/scripts/utils/encryption.py

-------
Requirements:
mistapi: https://pypi.org/project/mistapi/
pycryptodome: https://pypi.org/project/pycryptodome/

This script requires the following scripts to be in the same folder:
- org_conf_backup_encrypted.py
- org_inventory_backup_encrypted.py

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

-o, --org_id=           Optional, org_id of the org to clone

--src_env=              Optional, env file to use to access the src org (see
                        mistapi env file documentation here: 
                        https://pypi.org/project/mistapi/)
                        default is "~/.mist_env"
-p, --puk=              path to the RSA public key

-l, --log_file=         define the filepath/filename where to write the logs
                        default is "./script.log"
-b, --backup_folder=    Path to the folder where to save the org backup (a 
                        subfolder will be created with the org name)
                        default is "./org_backup"

-d, --datetime          append the current date and time (ISO format) to the
                        backup name 
-t, --timestamp         append the current timestamp to the backup 

-------
Examples:
python3 ./org_complete_backup.py
python3 ./org_complete_backup.py \
    --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 \
    -p ./rsa.pub

"""
    )
    if error_message:
        console.critical(error_message)
    sys.exit(0)


def check_mistapi_version():
    """
    Function to check the mistapi package version
    """
    if mistapi.__version__ < MISTAPI_MIN_VERSION:
        LOGGER.critical(
            f"\"mistapi\" package version {MISTAPI_MIN_VERSION} is required, "
            f"you are currently using version {mistapi.__version__}."
        )
        LOGGER.critical(f"Please use the pip command to updated it.")
        LOGGER.critical("")
        LOGGER.critical(f"    # Linux/macOS")
        LOGGER.critical(f"    python3 -m pip install --upgrade mistapi")
        LOGGER.critical("")
        LOGGER.critical(f"    # Windows")
        LOGGER.critical(f"    py -m pip install --upgrade mistapi")
        print(
            f"""
    Critical: 
    \"mistapi\" package version {MISTAPI_MIN_VERSION} is required, you are currently using version {mistapi.__version__}. 
    Please use the pip command to updated it.

    # Linux/macOS
    python3 -m pip install --upgrade mistapi

    # Windows
    py -m pip install --upgrade mistapi
        """
        )
        sys.exit(2)
    else:
        LOGGER.info(
            f"\"mistapi\" package version {MISTAPI_MIN_VERSION} is required, "
            f"you are currently using version {mistapi.__version__}."
        )


###############################################################################
#### SCRIPT ENTRYPOINT ####
if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(
            sys.argv[1:],
            "hl:o:b:e:tdp:",
            [
                "help",
                "org_id=",
                "env=",
                "src_env=",
                "log_file=",
                "backup_folder=",
                "datetime", 
                "timestamp",
                "puk="
            ],
        )
    except getopt.GetoptError as err:
        usage(err)

    ORG_ID = None
    BACKUP_FOLDER = DEFAULT_BACKUP_FOLDER
    BACKUP_NAME = False
    BACKUP_NAME_DATE = False
    BACKUP_NAME_TS = False
    PUK_PATH = None
    for o, a in opts:
        if o in ["-b", "--backup_folder"]:
            BACKUP_FOLDER = a
        elif o in ["-h", "--help"]:
            usage()
            sys.exit(0)
        elif o in ["-l", "--log_file"]:
            LOG_FILE = a
        elif o in ["-e", "--env", "--src_env"]:
            SRC_ENV_FILE = a
        elif o in ["-o", "--org_id"]:
            ORG_ID = a
        elif o in ["-d", "--datetime"]:
            if BACKUP_NAME_TS:
                usage("Inavlid Parameters: \"-d\"/\"--date\" and \"-t\"/\"--timestamp\" are exclusive")
            else:
                BACKUP_NAME_DATE = True
        elif o in ["-t", "--timestamp"]:
            if BACKUP_NAME_DATE:
                usage("Inavlid Parameters: \"-d\"/\"--date\" and \"-t\"/\"--timestamp\" are exclusive")
            else:
                BACKUP_NAME_TS = True
        elif o in ["-p", "--puk"]:
            PUK_PATH = a
        else:
            assert False, "unhandled option"

    #### LOGS ####
    logging.basicConfig(filename=LOG_FILE, filemode="w")
    LOGGER.setLevel(logging.DEBUG)
    check_mistapi_version()
    ### MIST SESSION ###
    print(" API Session to access the Source Org ".center(80, "_"))
    apisession = mistapi.APISession(env_file=SRC_ENV_FILE)
    apisession.login()

    ### START ###
    start(
        apisession,
        org_id=ORG_ID,
        backup_folder_param=BACKUP_FOLDER,
        backup_name=BACKUP_NAME,
        backup_name_date=BACKUP_NAME_DATE,
        backup_name_ts=BACKUP_NAME_TS,
        puk_path=PUK_PATH
    )

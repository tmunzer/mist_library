"""
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to backup a whole organization configuration and devices. 

This script will not change/create/delete/touch any existing objects. It will 
just retrieve every single object from the organization.

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

It is recommended to use an environment file to store the required information
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
    --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4

"""

#####################################################################
#### IMPORTS ####
import sys
import logging
import argparse
import datetime

MISTAPI_MIN_VERSION = "0.52.0"
try:
    import mistapi
    from mistapi.__logger import console
except ImportError:
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
    import org_conf_backup
    import org_inventory_backup
except ImportError:
    print(
        """
Critical: 
This script is using other scripts from the mist_library to perform all the
action. Please make sure the following python files are in the same folder
as the org_clone.py file:
    - org_conf_backup.py
    - org_inventory_backup.py
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
    backup_folder_param: str,
    backup_name: str,
) -> None:
    LOGGER.debug("org_complete_backup:_backup_org")
    LOGGER.debug("org_complete_backup:_backup_org:parameter:org_id: %s", org_id)
    LOGGER.debug(
        "org_complete_backup:_backup_org:parameter:backup_folder_param: %s",
        backup_folder_param,
    )
    LOGGER.debug(
        "org_complete_backup:_backup_org:parameter:backup_name: %s", backup_name
    )

    try:
        _print_new_step("Backing up SOURCE Org Configuration")
        org_conf_backup.start(
            mist_session=source_mist_session,
            org_id=org_id,
            backup_folder_param=backup_folder_param,
            backup_name=backup_name,
        )
    except Exception:
        sys.exit(255)


#######
#######


def _backup_inventory(
    source_mist_session: mistapi.APISession,
    org_id: str,
    backup_folder_param: str,
    backup_name: str,
) -> None:
    LOGGER.debug("org_complete_backup:_backup_inventory")
    LOGGER.debug("org_complete_backup:_backup_inventory:parameter:org_id: %s", org_id)
    LOGGER.debug(
        "org_complete_backup:_backup_inventory:parameter:backup_folder_param: %s",
        backup_folder_param,
    )
    LOGGER.debug(
        "org_complete_backup:_backup_inventory:parameter:backup_name: %s", backup_name
    )

    _print_new_step("Backing up SOURCE Org Inventory")
    org_inventory_backup.start(
        mist_session=source_mist_session,
        org_id=org_id,
        backup_folder=backup_folder_param,
        backup_name=backup_name,
    )


#######
#######


def _print_new_step(message) -> None:
    print()
    print("".center(80, "*"))
    print(f" {message} ".center(80, "*"))
    print("".center(80, "*"))
    print()
    LOGGER.info(message)


#######
#######
def start(
    apisession: mistapi.APISession,
    org_id: str = "",
    backup_folder_param: str = "",
    backup_name: str = "",
    backup_name_date: bool = False,
    backup_name_ts: bool = False,
) -> None:
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
    """
    LOGGER.debug("org_complete_backup:start")
    LOGGER.debug("org_complete_backup:start:parameter:org_id: %s", org_id)
    LOGGER.debug(
        "org_complete_backup:start:parameter:backup_folder_param: %s",
        backup_folder_param,
    )
    LOGGER.debug("org_complete_backup:start:parameter:backup_name: %s", backup_name)
    LOGGER.debug(
        "org_complete_backup:start:parameter:backup_name_date: %s", backup_name_date
    )
    LOGGER.debug(
        "org_complete_backup:start:parameter:backup_name_ts: %s", backup_name_ts
    )

    if not backup_folder_param:
        backup_folder_param = DEFAULT_BACKUP_FOLDER
    if not org_id:
        org_id = mistapi.cli.select_org(apisession)[0]
    org_name = mistapi.api.v1.orgs.orgs.getOrg(apisession, org_id).data["name"]

    if not backup_name:
        backup_name = org_name
    if backup_name_date:
        backup_name = f"{backup_name}_{datetime.datetime.isoformat(datetime.datetime.now()).split('.')[0].replace(':', '.')}"
    elif backup_name_ts:
        backup_name = f"{backup_name}_{round(datetime.datetime.timestamp(datetime.datetime.now()))}"

    _backup_org(apisession, org_id, backup_folder_param, backup_name)
    _backup_inventory(apisession, org_id, backup_folder_param, backup_name)
    _print_new_step("Process finished")


###############################################################################
#### USAGE ####
def usage(error_message: str = "") -> None:
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
Python script to backup a whole organization configuration and devices. 

This script will not change/create/delete/touch any existing objects. It will 
just retrieve every single object from the organization.

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

It is recommended to use an environment file to store the required information
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

-d, --datetime          append the current date and time (ISO format) to the
                        backup name 
-t, --timestamp         append the current timestamp to the backup 

-------
Examples:
python3 ./org_complete_backup.py
python3 ./org_complete_backup.py \
    --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4

"""
    )
    if error_message:
        console.critical(error_message)
    sys.exit(0)


def check_mistapi_version():
    """Check if the installed mistapi version meets the minimum requirement."""

    current_version = mistapi.__version__.split(".")
    required_version = MISTAPI_MIN_VERSION.split(".")

    try:
        for i, req in enumerate(required_version):
            if current_version[int(i)] > req:
                break
            if current_version[int(i)] < req:
                raise ImportError(
                    f'"mistapi" package version {MISTAPI_MIN_VERSION} is required '
                    f"but version {mistapi.__version__} is installed."
                )
    except ImportError as e:
        LOGGER.critical(str(e))
        LOGGER.critical("Please use the pip command to update it.")
        LOGGER.critical("")
        LOGGER.critical("    # Linux/macOS")
        LOGGER.critical("    python3 -m pip install --upgrade mistapi")
        LOGGER.critical("")
        LOGGER.critical("    # Windows")
        LOGGER.critical("    py -m pip install --upgrade mistapi")
        print(
            f"""
Critical:\r\n
{e}\r\n
Please use the pip command to update it.
# Linux/macOS
python3 -m pip install --upgrade mistapi
# Windows
py -m pip install --upgrade mistapi
            """
        )
        sys.exit(2)
    finally:
        LOGGER.info(
            '"mistapi" package version %s is required, '
            "you are currently using version %s.",
            MISTAPI_MIN_VERSION,
            mistapi.__version__,
        )


###############################################################################
#### SCRIPT ENTRYPOINT ####
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Backup a whole organization configuration and devices"
    )
    parser.add_argument("-o", "--org_id", help="Optional, org_id of the org to backup")
    parser.add_argument(
        "-e",
        "--env",
        "--src_env",
        dest="env",
        default=SRC_ENV_FILE,
        help="Optional, env file to use to access the src org",
    )
    parser.add_argument(
        "-l",
        "--log_file",
        default=LOG_FILE,
        help="define the filepath/filename where to write the logs",
    )
    parser.add_argument(
        "-b",
        "--backup_folder",
        default=DEFAULT_BACKUP_FOLDER,
        help="Path to the folder where to save the org backup",
    )

    time_group = parser.add_mutually_exclusive_group()
    time_group.add_argument(
        "-d",
        "--datetime",
        action="store_true",
        help="append the current date and time (ISO format) to the backup name",
    )
    time_group.add_argument(
        "-t",
        "--timestamp",
        action="store_true",
        help="append the current timestamp to the backup name",
    )

    args = parser.parse_args()

    ORG_ID = args.org_id
    BACKUP_FOLDER = args.backup_folder
    BACKUP_NAME = ""
    BACKUP_NAME_DATE = args.datetime
    BACKUP_NAME_TS = args.timestamp
    LOG_FILE = args.log_file
    SRC_ENV_FILE = args.env

    #### LOGS ####
    logging.basicConfig(filename=LOG_FILE, filemode="w")
    LOGGER.setLevel(logging.DEBUG)
    check_mistapi_version()
    ### MIST SESSION ###
    print(" API Session to access the Source Org ".center(80, "_"))
    APISESSION = mistapi.APISession(env_file=SRC_ENV_FILE)
    APISESSION.login()

    ### START ###
    start(
        APISESSION,
        org_id=ORG_ID,
        backup_folder_param=BACKUP_FOLDER,
        backup_name=BACKUP_NAME,
        backup_name_date=BACKUP_NAME_DATE,
        backup_name_ts=BACKUP_NAME_TS,
    )

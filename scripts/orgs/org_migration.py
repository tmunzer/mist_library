"""
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to migrate a whole organization and the devices to another one. 
The destination org can be an existing org, or it can be created during the 
process.

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
- org_conf_deploy.py
- org_inventory_backup.py
- org_inventory_deploy.py

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

--src_org_id=           Optional, org_id of the org to clone
--src_org_name=         Optional, name of the org to clone, for validation 
                        purpose. Requires src_org_id to be defined
--dst_org_id=           Optional, org_id of the org where to clone the src_org,
                        if the org already exists
--dst_org_name=         Optional, name of the org where to clone the src_org. 
                        If dst_org_id is defined (org already exists), will be 
                        used for validation, if dst_org_id is not defined, a
                        new org will be created

--src_env=              Optional, env file to use to access the src org (see
                        mistapi env file documentation here: 
                        https://pypi.org/project/mistapi/)
                        default is "~/.mist_env"
--dst_env=              Optional, env file to use to access the dst org (see
                        mistapi env file documentation here: 
                        https://pypi.org/project/mistapi/)
                        default is "~/.mist_env"

-u, --unclaim           if set the script will unclaim the devices from the 
                        source org (only for devices claimed in the source org,
                        not for adopted devices). Unclaim process will only be 
                        simulated if in Dry Run mode.
                        WARNING: this option will only unclaim Mist APs, use 
                        the -a option to also uncail switches and gatewys
-a, --unclaim_all       To be used with the -u option. Allows the script to
                        also migrate switches and gateways from the source
                        org to the destination org (works only for claimed
                        devices, not adopted ones).
                        WARNING: This process may reset and reboot the boxes.
                        Please make sure this will not impact users on site!

-l, --log_file=         define the filepath/filename where to write the logs
                        default is "./script.log"
-b, --backup_folder=    Path to the folder where to save the org backup (a 
                        subfolder will be created with the org name)
                        default is "./org_backup"

"""
#####################################################################
#### IMPORTS ####
import sys
import logging
import getopt

MISTAPI_MIN_VERSION = "0.44.1"

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
    import org_conf_backup
    import org_conf_deploy
    import org_inventory_backup
    import org_inventory_deploy
except:
    print(
        """
Critical: 
This script is using other scripts from the mist_library to perform all the
action. Please make sure the following python files are in the same folder
as the org_clone.py file:
    - org_conf_backup.py
    - org_conf_deploy.py
    - org_inventory_backup.py
    - org_inventory_deploy.py
    """
    )
    sys.exit(2)

#####################################################################
#### PARAMETERS #####
DEFAULT_BACKUP_FOLDER = "./org_backup"
LOG_FILE = "./script.log"
SRC_ENV_FILE = ""#"~/.mist_env"
DST_ENV_FILE = None

#####################################################################
#### LOGS ####
LOGGER = logging.getLogger(__name__)


#####################################################################
#### ORG FUNCTIONS ####
def _backup_org(
    source_mist_session: mistapi.APISession, src_org_id: str, backup_folder_param=str
):
    try:
        _print_new_step("Backuping SOURCE Org Configuration")
        org_conf_backup.start(source_mist_session, src_org_id, backup_folder_param)
    except:
        sys.exit(255)


def _deploy_org(
    dest_mist_session: mistapi.APISession,
    dst_org_id: str,
    dest_org_name: str,
    src_org_name: str,
    backup_folder_param: str,
):
    _print_new_step("Deploying Configuration to the DESTINATION Org")
    org_conf_deploy.start(
        dest_mist_session,
        dst_org_id,
        dest_org_name,
        source_backup=src_org_name,
        backup_folder_param=backup_folder_param,
    )


#######
#######


def _backup_inventory(
    source_mist_session: mistapi.APISession, src_org_id: str, backup_folder_param: str
):
    _print_new_step("Backuping SOURCE Org Inventory")
    org_inventory_backup.start(source_mist_session, src_org_id, backup_folder_param)


def _precheck_inventory(
    dst_mist_session: mistapi.APISession,
    dst_org_id: str,
    dst_org_name: str,
    src_org_name: str,
    backup_folder_param: str,
):
    _print_new_step("Pre-check for INVENTORY restoration")
    org_inventory_deploy.start(
        dst_mist_session,
        dst_org_id=dst_org_id,
        dst_org_name=dst_org_name,
        source_backup=src_org_name,
        backup_folder_param=backup_folder_param,
        proceed=False,
    )


def _deploy_inventory(
    dst_mist_session: mistapi.APISession,
    src_mist_session: mistapi.APISession,
    dst_org_id: str,
    dst_org_name: str,
    src_org_name: str,
    backup_folder_param: str,
    unclaim: bool = False,
    unclaim_all: bool = False,
):
    _print_new_step("Pre-check for INVENTORY restoration")
    org_inventory_deploy.start(
        dst_apisession=dst_mist_session,
        src_apisession=src_mist_session,
        dst_org_id=dst_org_id,
        dst_org_name=dst_org_name,
        source_backup=src_org_name,
        backup_folder_param=backup_folder_param,
        proceed=True,
        unclaim=unclaim,
        unclaim_all=unclaim_all,
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
def _create_org(mist_session: mistapi.APISession):
    while True:
        custom_dest_org_name = input("What is the new Organization name? ")
        if custom_dest_org_name:
            org = {"name": custom_dest_org_name}
            print()
            print(
                f'Creating the organisation "{custom_dest_org_name}"'
                f" in {mist_session.get_cloud()} ".ljust(79, "."),
                end="",
                flush=True,
            )
            try:
                org_id = mistapi.api.v1.orgs.orgs.createOrg(mist_session, org).data[
                    "id"
                ]
                print("\033[92m\u2714\033[0m")
                print()
            except:
                print("\033[31m\u2716\033[0m")
                sys.exit(10)
            return org_id, custom_dest_org_name


def select_or_create_org(mist_session: mistapi.APISession = None):
    while True:
        res = input(
            "Do you want to create a (n)ew organisation, (r)estore to an existing one, or (q)uit? "
        )
        if res.lower() == "r":
            return _select_org("destination", mist_session)
        elif res.lower() == "n":
            return _create_org(mist_session)
        elif res.lower() == "q":
            sys.exit(0)


def _check_org_name(
    apisession: mistapi.APISession, dst_org_id: str, org_type: str, org_name: str = None
):
    if not org_name:
        org_name = mistapi.api.v1.orgs.orgs.getOrg(apisession, dst_org_id).data["name"]
    while True:
        print()
        resp = input(
            f"To avoid any error, please confirm the current {org_type} orgnization name: "
        )
        if resp == org_name:
            return True
        else:
            print()
            print("The orgnization names do not match... Please try again...")


#######
#######
def _select_org(org_type: str, mist_session=None):
    org_id = mistapi.cli.select_org(mist_session)[0]
    org_name = mistapi.api.v1.orgs.orgs.getOrg(mist_session, org_id).data["name"]
    _check_org_name(mist_session, org_id, org_type, org_name)
    return org_id, org_name


def _check_org_name_in_script_param(
    apisession: mistapi.APISession, org_id: str, org_name: str = None
):
    response = mistapi.api.v1.orgs.orgs.getOrg(apisession, org_id)
    if response.status_code != 200:
        console.critical(f"Unable to retrieve the org information: {response.data}")
        sys.exit(3)
    org_name_from_mist = response.data["name"]
    return org_name == org_name_from_mist


def _check_src_org(
    src_apisession: mistapi.APISession, src_org_id: str, src_org_name: str
):
    _print_new_step("SOURCE Org")
    if src_org_id and src_org_name:
        if not _check_org_name_in_script_param(src_apisession, src_org_id, src_org_name):
            console.critical(f"Org name {src_org_name} does not match the org {src_org_id}")
            sys.exit(0)
        return src_org_id, src_org_name
    elif src_org_id and not src_org_name:
        return _check_org_name(src_apisession, src_org_id, "Source")
    elif not src_org_id and not src_org_name:
        return _select_org("source", src_apisession)
    elif not src_org_id and src_org_name:
        console.critical(
            f'"src_org_name" cannot be defined without "src_org_id". '
            f'Please remove "src_org_name" parameter or add "src_org_id"'
        )
        sys.exit(0)
    else:  # should not since we covered all the possibilities...
        sys.exit(0)


def _check_dst_org(
    dst_apisession: mistapi.APISession,
    dst_org_id: str,
    dst_org_name: str,
):
    if dst_org_id and dst_org_name:
        if not _check_org_name_in_script_param(dst_apisession, dst_org_id, dst_org_name):
            console.critical(f"Org name {dst_org_name} does not match the org {dst_org_id}")
            sys.exit(0)
        return dst_org_id, dst_org_name
    elif dst_org_id and not dst_org_name:
        return _check_org_name(dst_apisession, dst_org_id, "Destination")
    elif not dst_org_id and dst_org_name:
        response = mistapi.api.v1.orgs.orgs.createOrg(dst_apisession, {"name": dst_org_name})
        if response.status_code == 200:
            dst_org_id = response.data["id"]
            dst_org_name = response.data["name"]
            return dst_org_id, dst_org_name
        else:
            console.critical("Unable to create destination Org... Exiting")
            sys.exit(1)
    elif not dst_org_id and not dst_org_name:
        _print_new_step("DESTINATION Org")
        return select_or_create_org(dst_apisession)
    else:  # should not since we covered all the possibilities...
        sys.exit(0)


def start(
    src_apisession: mistapi.APISession,
    dst_apisession: mistapi.APISession = None,
    src_org_id: str = None,
    src_org_name: str = None,
    dst_org_id: str = None,
    dst_org_name=None,
    backup_folder_param: str = None,
    unclaim: bool = False,
    unclaim_all: bool = False,
):
    """
    Start the process to clone the src org to the dst org

    PARAMS
    -------
    src_apisession : mistapi.APISession
        mistapi session with `Super User` access the source Org, already logged in
    dst_apisession : mistapi.APISession
        Optional, mistapi session with `Super User` access the source Org, already logged in.
        If not defined, the src_apissession will be reused
    src_org_id : str
        Optional, org_id of the org to clone
    src_org_name : str
        Optional, name of the org to clone, for validation purpose. Requires src_org_id to
        be defined
    dst_org_id : str
        Optional, org_id of the org where to clone the src_org, if the org already exists
    dst_org_name : str
        Optional, name of the org where to clone the src_org. If dst_org_id is defined (org
        already exists), will be used for validation, if dst_org_id is not defined, a new org
        will be created
    backup_folder_param : str
        Path to the folder where to save the org backup (a subfolder will be created with the
        org name). default is "./org_backup"
    unclaim : bool
        If `unclaim`==`True`, the script will unclaim the devices from the source org. Unclaim
        process will only be simulated if in Dry Run mode. WARNING: this option will only
        unclaim Mist APs, set `unclaim_all` to True to also uncail switches and gatewys
    unclaim_all : bool
        If `unclaim_all`==`True`, the script will also migrate switches and gateways from the
        source org to the destination org (works only for claimed devices, not adopted ones).
        WARNING: This process may reset and reboot the boxes. Please make sure this will not
        impact users on site!

    """
    if not backup_folder_param:
        backup_folder_param = DEFAULT_BACKUP_FOLDER
    if not dst_apisession:
        dst_apisession = src_apisession
    src_org_id, src_org_name = _check_src_org(src_apisession, src_org_id, src_org_name)
    dst_org_id, dst_org_name = _check_dst_org(dst_apisession, dst_org_id, dst_org_name)

    _backup_org(src_apisession, src_org_id, backup_folder_param)
    _backup_inventory(src_apisession, src_org_id, backup_folder_param)
    _deploy_org(dst_apisession, dst_org_id, dst_org_name, src_org_name, backup_folder_param)
    _precheck_inventory(dst_apisession, dst_org_id, dst_org_name, src_org_name, backup_folder_param)
    if unclaim:
        _deploy_inventory(
            dst_mist_session=dst_apisession,
            src_mist_session=src_apisession,
            dst_org_id=dst_org_id,
            dst_org_name=dst_org_name,
            src_org_name=src_org_name,
            backup_folder_param=backup_folder_param,
            unclaim=unclaim,
            unclaim_all=unclaim_all,
        )

    _print_new_step("Process finished")
    console.info(
        f"The Org {src_org_name} ({src_apisession.get_cloud()}) has been cloned "
        f"into the Org {dst_org_name} ({dst_apisession.get_cloud()}) with success"
    )


###############################################################################
#### USAGE ####
def usage(error_message:str=None):
    """
    display usage
    """
    print(
        """
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to migrate a whole organization and the devices to another one. 
The destination org can be an existing org, or it can be created during the 
process.

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
- org_conf_deploy.py
- org_inventory_backup.py
- org_inventory_deploy.py
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

--src_org_id=           Optional, org_id of the org to clone
--src_org_name=         Optional, name of the org to clone, for validation 
                        purpose. Requires src_org_id to be defined
--dst_org_id=           Optional, org_id of the org where to clone the src_org,
                        if the org already exists
--dst_org_name=         Optional, name of the org where to clone the src_org. 
                        If dst_org_id is defined (org already exists), will be 
                        used for validation, if dst_org_id is not defined, a
                        new org will be created

--src_env=              Optional, env file to use to access the src org (see
                        mistapi env file documentation here: 
                        https://pypi.org/project/mistapi/)
                        default is "~/.mist_env"
--dst_env=              Optional, env file to use to access the dst org (see
                        mistapi env file documentation here: 
                        https://pypi.org/project/mistapi/)
                        default is "~/.mist_env"

-u, --unclaim           if set the script will unclaim the devices from the 
                        source org (only for devices claimed in the source org,
                        not for adopted devices). Unclaim process will only be 
                        simulated if in Dry Run mode.
                        WARNING: this option will only unclaim Mist APs, use 
                        the -a option to also uncail switches and gatewys
-a, --unclaim_all       To be used with the -u option. Allows the script to
                        also migrate switches and gateways from the source
                        org to the destination org (works only for claimed
                        devices, not adopted ones).
                        WARNING: This process may reset and reboot the boxes.
                        Please make sure this will not impact users on site!

-l, --log_file=         define the filepath/filename where to write the logs
                        default is "./script.log"
-b, --backup_folder=    Path to the folder where to save the org backup (a 
                        subfolder will be created with the org name)
                        default is "./org_backup"

"""
    )
    if error_message:
        console.critical(error_message)
    sys.exit(0)


def check_mistapi_version():
    if mistapi.__version__ < MISTAPI_MIN_VERSION:
        LOGGER.critical(
            f'"mistapi" package version {MISTAPI_MIN_VERSION} is required, you are currently using version {mistapi.__version__}.'
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
            f'"mistapi" package version {MISTAPI_MIN_VERSION} is required, '
            f"you are currently using version {mistapi.__version__}."
        )


###############################################################################
#### SCRIPT ENTRYPOINT ####
if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(
            sys.argv[1:],
            "hl:b:ua",
            [
                "help",
                "src_org_id=",
                "src_org_name=",
                "dst_org_id=",
                "dst_org_name=",
                "dst_env=",
                "src_env=",
                "log_file=",
                "backup_folder=",
                "unclaim",
                "unclaim_all",
            ],
        )
    except getopt.GetoptError as err:
        console.error(err)
        usage()

    SRC_ORG_ID = None
    SRC_ORG_NAME = None
    DST_ORG_ID = None
    DST_ORG_NAME = None
    BACKUP_FOLDER = DEFAULT_BACKUP_FOLDER
    UNCLAIM = False
    UNCLAIM_ALL = False
    for o, a in opts:
        if o in ["-a", "--unclaim_all"]:
            UNCLAIM_ALL = True
        elif o in ["-u", "--unclaim"]:
            UNCLAIM = True
        elif o in ["-b", "--backup_folder"]:
            BACKUP_FOLDER = a
        elif o in ["-h", "--help"]:
            usage()
            sys.exit(0)
        elif o in ["-l", "--log_file"]:
            LOG_FILE = a
        elif o in ["--src_env"]:
            SRC_ENV_FILE = a
        elif o in ["--src_org_id"]:
            SRC_ORG_ID = a
        elif o in ["--src_org_name"]:
            SRC_ORG_NAME = a
        elif o in ["--dst_env"]:
            DST_ENV_FILE = a
        elif o in ["--dst_org_id"]:
            DST_ORG_ID = a
        elif o in ["--dst_org_name"]:
            DST_ORG_NAME = a
        else:
            assert False, "unhandled option"

    #### LOGS ####
    logging.basicConfig(filename=LOG_FILE, filemode="w")
    LOGGER.setLevel(logging.DEBUG)
    check_mistapi_version()
    ### MIST SESSION ###
    print(" API Session to access the Source Org ".center(80, "_"))
    SRC_APISESSION = mistapi.APISession(env_file=SRC_ENV_FILE)
    SRC_APISESSION.login()
    print(" API Session to access the Destination Org ".center(80, "_"))
    DST_APISESSION = mistapi.APISession(env_file=DST_ENV_FILE)
    DST_APISESSION.login()

    ### START ###
    start(
        SRC_APISESSION,
        DST_APISESSION,
        src_org_id=SRC_ORG_ID,
        src_org_name=SRC_ORG_NAME,
        dst_org_id=DST_ORG_ID,
        dst_org_name=DST_ORG_NAME,
        backup_folder_param=BACKUP_FOLDER,
        unclaim=UNCLAIM,
        unclaim_all=UNCLAIM_ALL,
    )

"""
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to uninvite (remove) expired admin invites.

-------
Requirements:
mistapi: https://pypi.org/project/mistapi/

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

-o, --org_id=           ID of the Mist Org
-n, --org_name=         Name of the Mist Org (used for validation purpose)
-a, --apply             By default the script is running in dry run mode.
                        Use the -a/--apply to delete the flagged accounts.

-l, --log_file=         define the filepath/filename where to write the logs
                        default is "./script.log"
-e, --env=              define the env file to use (see mistapi env file 
                        documentation here: https://pypi.org/project/mistapi/)
                        default is "~/.mist_env"

-------
Examples:
python3 ./delete_expired_invites.py     
python3 ./delete_expired_invites.py -o 203d3d02-xxxx-xxxx-xxxx-76896a3330f4 -n "My Mist Org"

"""

#####################################################################
#### IMPORTS ####
import logging
import sys
import datetime
import getopt

MISTAPI_MIN_VERSION = "0.52.4"

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


#####################################################################
#### PARAMETERS #####
LOG_FILE = "./script.log"
ENV_FILE = "~/.mist_env"

#####################################################################
#### LOGS ####
LOGGER = logging.getLogger(__name__)


#####################################################################
# PROGRESS BAR AND DISPLAY
class ProgressBar:
    """Progress bar for long-running operations."""

    def __init__(self):
        self.steps_total = 0
        self.steps_count = 0

    def _pb_update(self, size: int = 80):
        if self.steps_count > self.steps_total:
            self.steps_count = self.steps_total

        percent = self.steps_count / self.steps_total
        delta = 17
        x = int((size - delta) * percent)
        print("Progress: ", end="")
        print(f"[{'█' * x}{'.' * (size - delta - x)}]", end="")
        print(f"{int(percent * 100)}%".rjust(5), end="")

    def _pb_new_step(
        self,
        message: str,
        result: str,
        inc: bool = False,
        size: int = 80,
        display_pbar: bool = True,
    ):
        if inc:
            self.steps_count += 1
        text = f"\033[A\033[F{message}"
        print(f"{text} ".ljust(size + 4, "."), result)
        print("".ljust(80))
        if display_pbar:
            self._pb_update(size)

    def _pb_title(
        self, text: str, size: int = 80, end: bool = False, display_pbar: bool = True
    ):
        print("\033[A")
        print(f" {text} ".center(size, "-"), "\n")
        if not end and display_pbar:
            print("".ljust(80))
            self._pb_update(size)

    def set_steps_total(self, steps_total: int):
        """Set the total number of steps for the progress bar."""
        self.steps_count = 0
        self.steps_total = steps_total

    def log_message(self, message, display_pbar: bool = True):
        """Log a message."""
        self._pb_new_step(message, " ", display_pbar=display_pbar)

    def log_success(self, message, inc: bool = False, display_pbar: bool = True):
        """Log a success message."""
        LOGGER.info("%s: Success", message)
        self._pb_new_step(
            message, "\033[92m\u2714\033[0m\n", inc=inc, display_pbar=display_pbar
        )

    def log_warning(self, message, inc: bool = False, display_pbar: bool = True):
        """Log a warning message."""
        LOGGER.warning("%s: Warning", message)
        self._pb_new_step(
            message, "\033[93m\u2b58\033[0m\n", inc=inc, display_pbar=display_pbar
        )

    def log_failure(self, message, inc: bool = False, display_pbar: bool = True):
        """Log a failure message."""
        LOGGER.error("%s: Failure", message)
        self._pb_new_step(
            message, "\033[31m\u2716\033[0m\n", inc=inc, display_pbar=display_pbar
        )

    def log_title(self, message, end: bool = False, display_pbar: bool = True):
        """Log a title message."""
        LOGGER.info("%s", message)
        self._pb_title(message, end=end, display_pbar=display_pbar)


PB = ProgressBar()


#####################################################################
#### FUNCTIONS ####

def _load_admins(apisession: mistapi.APISession, org_id: str) -> list:
    message = "Loading admins list"
    PB.log_message(message, display_pbar=False)
    try:
        resp = mistapi.api.v1.orgs.admins.listOrgAdmins(apisession, org_id)
        if resp and resp.status_code == 200:
            PB.log_success(message, inc=False, display_pbar=False)
            if isinstance(resp.data, list):
                return resp.data
        PB.log_failure(message, inc=False, display_pbar=False)
        return []    
    except Exception:
        PB.log_failure(message, inc=False, display_pbar=False)
        LOGGER.error("Exception occurred", exc_info=True)
        sys.exit(2)
    

def _unclaim_admins(apisession: mistapi.APISession, org_id: str, admins: list):
    for admin in admins:
        message = f"Removing admin {admin.get('email')}"
        PB.log_message(message, display_pbar=True)
        try:
            LOGGER.debug("Uninviting admin %s", admin)
            resp = mistapi.api.v1.orgs.invites.uninviteOrgAdmin(
                apisession, org_id, admin.get("invite_id")
            )
            if resp and resp.status_code == 200:
                PB.log_success(message, inc=True, display_pbar=True)
            else:
                PB.log_failure(message, inc=True, display_pbar=True)
        except Exception:
            PB.log_failure(message, inc=True, display_pbar=True)
            LOGGER.error("Exception occurred", exc_info=True)

def _process_admins(admins:list)->list:
    expired_invites = []
    now = datetime.datetime.now()
    message = "Processing admins list"
    PB.log_message(message, display_pbar=False)
    for admin in admins:
        if admin.get("expire_time") and admin.get("expire_time") > 0:
            expire_time = datetime.datetime.fromtimestamp(admin.get("expire_time"))
            if expire_time < now:
                expired_invites.append({
                    "invite_id": admin.get("invite_id"),
                    "email": admin.get("email"),
                    "first_name": admin.get("first_name"),
                    "last_name": admin.get("last_name"),
                    "expiration_timestamp": str(admin.get("expire_time")),
                    "expiration_date": expire_time,
                    
                })
    PB.log_success(message, display_pbar=False)
    sorted(expired_invites, key=lambda d: d['expiration_timestamp'], reverse=True)
    return expired_invites

def _check_org_name_in_script_param(
    apisession: mistapi.APISession, org_id: str, org_name: str = ""
):
    response = mistapi.api.v1.orgs.orgs.getOrg(apisession, org_id)
    if response.status_code != 200:
        console.critical(f"Unable to retrieve the org information: {response.data}")
        sys.exit(3)
    org_name_from_mist = response.data["name"]
    return org_name == org_name_from_mist


def _check_org_name(apisession: mistapi.APISession, org_id: str, org_name: str = ""):
    if not org_name:
        org_name = mistapi.api.v1.orgs.orgs.getOrg(apisession, org_id).data["name"]
    while True:
        print()
        resp = input(
            "To avoid any error, please confirm the current destination organization name: "
        )
        if resp == org_name:
            print()
            print()
            print()
            return org_id, org_name
        else:
            print()
            print("The organization names do not match... Please try again...")


def _check_confirmation()-> bool:
    while True:
        response = input("Do you want to delete the listed invitations (y/N) ? ")
        if response.lower() == "y":
            return True
        elif response.lower() == "n" or response == "":
            print("Deletion canceled... Exiting...")
            sys.exit(0)

def start(apisession: mistapi.APISession, org_id: str, org_name: str, dry_run: bool=True):
    """
    Start the process to rename the devices

    PARAMS
    -------
    apisession : mistapi.APISession
        mistapi session, already logged in
    org_id : str
        only if the destination org already exists. org_id where to deploy the
        configuration
    org_name : str
        Org name, used to validate the destination org
    csv_file : str
        Path to the csv_file where the information are stored.
        default: "./uninvite_admins.py"
    """
    LOGGER.debug("start")
    LOGGER.debug(f"start:parameter:org_id:{org_id}")
    LOGGER.debug(f"start:parameter:org_name:{org_name}")
    LOGGER.debug(f"start:parameter:dry_run:{dry_run}")

    if org_id and org_name:
        if not _check_org_name_in_script_param(apisession, org_id, org_name):
            console.critical(f"Org name {org_name} does not match the org {org_id}")
    elif org_id and not org_name:
        org_id, org_name = _check_org_name(apisession, org_id)
    elif not org_id and not org_name:
        org_id = mistapi.cli.select_org(apisession, allow_many=True)[0]
        org_id, org_name = _check_org_name(apisession, org_id)
    else:
        usage('Cannot set "org_name" without org_id.')
        sys.exit(0)

    admins = _load_admins(apisession, org_id)
    expired_invites = _process_admins(admins)
    mistapi.cli.display_list_of_json_as_table(expired_invites, ["invite_id", "email", "first_name", "last_name", "expiration_date"])
    print()
    print(f"{len(expired_invites)} expired invitation(s)")
    print()
    if dry_run:
        print("Script in Dry Run mode, please use the -a/--apply parameter to delete the accounts... Exiting...")
        sys.exit(0)
    elif len(expired_invites) == 0:
        print("No invites to delete... Exiting...")
        sys.exit(0)
    else:
        PB.set_steps_total(len(expired_invites))
        if _check_confirmation():
            _unclaim_admins(apisession, org_id, expired_invites)


#####################################################################
##### USAGE ####
def usage(error_message: str | None= None):
    """
    display usage

    PARAMS
    -------
    error_message : str
        if error_message is set, display it after the usage
    """
    print(
"""
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to uninvite (remove) expired admin invites.

-------
Requirements:
mistapi: https://pypi.org/project/mistapi/

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

-o, --org_id=           ID of the Mist Org
-n, --org_name=         Name of the Mist Org (used for validation purpose)
-a, --apply             By default the script is running in dry run mode.
                        Use the -a/--apply to delete the flagged accounts.

-l, --log_file=         define the filepath/filename where to write the logs
                        default is "./script.log"
-e, --env=              define the env file to use (see mistapi env file 
                        documentation here: https://pypi.org/project/mistapi/)
                        default is "~/.mist_env"

-------
Examples:
python3 ./delete_expired_invites.py     
python3 ./delete_expired_invites.py -o 203d3d02-xxxx-xxxx-xxxx-76896a3330f4 -n "My Mist Org"

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
            mistapi.__version__
        )


#####################################################################
##### ENTRY POINT ####
if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(
            sys.argv[1:],
            "ho:n:ae:l:",
            ["help", "org_id=", "org_name=", "apply", "env=", "log_file="],
        )
    except getopt.GetoptError as err:
        console.error(err.msg)
        usage()
        
    ORG_ID = ""
    ORG_NAME = ""
    DRY_RUN = True
    for o, a in opts:
        if o in ["-h", "--help"]:
            usage()
        elif o in ["-o", "--org_id"]:
            ORG_ID = a
        elif o in ["-n", "--org_name"]:
            ORG_NAME = a
        elif o in ["-a", "--apply"]:
            DRY_RUN = False
        elif o in ["-e", "--env"]:
            ENV_FILE = a
        elif o in ["-l", "--log_file"]:
            LOG_FILE = a
        else:
            assert False, "unhandled option"

    #### LOGS ####
    logging.basicConfig(filename=LOG_FILE, filemode="w")
    LOGGER.setLevel(logging.DEBUG)
    check_mistapi_version()
    ### START ###
    APISESSION = mistapi.APISession(env_file=ENV_FILE)
    APISESSION.login()
    start(APISESSION, ORG_ID, ORG_NAME, DRY_RUN)

"""
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to revoke (remove) administrator access from a Mist organization
using a CSV file containing administrator information. This script provides a
safe and efficient way to bulk remove multiple administrators from an organization.

Key features:
- Bulk removal of administrators using CSV input
- Organization validation to prevent accidental deletions
- Flexible CSV format

Use cases:
- Employee offboarding processes
- Periodic access reviews and cleanup
- Security incident response (removing compromised accounts)
- Organizational restructuring
- Compliance with access management policies

IMPORTANT: This script permanently removes administrator access. Ensure you have
the correct organization and administrator list before proceeding.

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
CSV Format:
The first line MUST start with a "#" and defines each columns of the CSV file.

-------
CSV Parameters:
Required:
- admin_id
- admin_email

-------
Example:
#admin_id, admin_email, admin_first_name, admin_last_name
bb2c2f47-xxxx-xxxx-xxxx-a0422beaff00, jdoe@mycorp.net, John, Doe

-------
Script Parameters:
-h, --help              display this help

-o, --org_id=           ID of the Mist Org
-n, --org_name=         Name of the Mist Org (used for validation purpose)
-c, --csv_file=         CSV File to use.
                        default is "./delete_admins.csv"

-l, --log_file=         define the filepath/filename where to write the logs
                        default is "./script.log"
-e, --env=              define the env file to use (see mistapi env file
                        documentation here: https://pypi.org/project/mistapi/)
                        default is "~/.mist_env"

-------
Examples:
python3 ./delete_admins.py
python3 ./delete_admins.py -o 203d3d02-xxxx-xxxx-xxxx-76896a3330f4 -n "My Mist Org"

"""

#####################################################################
#### IMPORTS ####
import logging
import sys
import csv
import argparse

MISTAPI_MIN_VERSION = "0.57.1"

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
CSV_FILE = "./delete_admins.csv"

#####################################################################
#### LOGS ####
LOGGER = logging.getLogger(__name__)


#####################################################################
# PROGRESS BAR AND DISPLAY
class ProgressBar:
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
        print(f" {text} ".center(size, "-"), "\n\n")
        if not end and display_pbar:
            print("".ljust(80))
            self._pb_update(size)

    def set_steps_total(self, steps_total: int):
        self.steps_total = steps_total

    def log_message(self, message, display_pbar: bool = True):
        self._pb_new_step(message, " ", display_pbar=display_pbar)

    def log_success(self, message, inc: bool = False, display_pbar: bool = True):
        LOGGER.info("%s: Success", message)
        self._pb_new_step(
            message, "\033[92m\u2714\033[0m\n", inc=inc, display_pbar=display_pbar
        )

    def log_warning(self, message, inc: bool = False, display_pbar: bool = True):
        LOGGER.warning("%s: Warning", message)
        self._pb_new_step(
            message, "\033[93m\u2b58\033[0m\n", inc=inc, display_pbar=display_pbar
        )

    def log_failure(self, message, inc: bool = False, display_pbar: bool = True):
        LOGGER.error("%s: Failure", message)
        self._pb_new_step(
            message, "\033[31m\u2716\033[0m\n", inc=inc, display_pbar=display_pbar
        )

    def log_title(self, message, end: bool = False, display_pbar: bool = True):
        LOGGER.info(message)
        self._pb_title(message, end=end, display_pbar=display_pbar)


PB = ProgressBar()


#####################################################################
#### FUNCTIONS ####
def _unclaim_admins(apisession: mistapi.APISession, org_id: str, admins: list):
    for admin in admins:
        message = f"Removing admin {admin.get('email')}"
        PB.log_message(message, display_pbar=True)
        try:
            resp = mistapi.api.v1.orgs.admins.revokeOrgAdmin(
                apisession, org_id, admin.get("id")
            )
            if resp and resp.status_code == 200:
                PB.log_success(message, inc=True, display_pbar=True)
            else:
                PB.log_failure(message, inc=True, display_pbar=True)
        except Exception:
            PB.log_failure(message, inc=True, display_pbar=True)
            LOGGER.error("Exception occurred", exc_info=True)


def _read_csv_file(csv_file: str):
    LOGGER.debug("_read_csv_file")
    LOGGER.debug("_read_csv_file:parameter:csv_file:%s", csv_file)
    admins = []
    PB.log_message("Processing CSV file", display_pbar=False)
    with open(csv_file, "r", encoding="utf-8") as f:
        admin_id_column = 0
        admin_email_column = 1
        data_from_csv = csv.reader(f, skipinitialspace=True, quotechar='"')
        data_from_csv = [
            [c.replace("\ufeff", "") for c in row] for row in data_from_csv
        ]
        for line in data_from_csv:
            LOGGER.debug("_read_csv_file:%s", line)
            if line[0].startswith("#"):
                for i, col in enumerate(line):
                    if col.replace("#", "") == "admin_id":
                        admin_id_column = i
                    if col.replace("#", "") == "admin_email":
                        admin_email_column = i
            else:
                admin_id = line[admin_id_column]
                admin_email = line[admin_email_column]
                admins.append({"id": admin_id, "email": admin_email})
                LOGGER.debug("_read_csv_file:new id:%s, email: %s", admin_id, admin_email)

    LOGGER.debug(
        "_read_csv_file:got %d devices to rename from %s", len(admins), csv_file
    )
    PB.log_success("Processing CSV file", display_pbar=False, inc=False)
    return admins


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


def start(apisession: mistapi.APISession, org_id: str, org_name: str, csv_file: str):
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
        default: "./delete_admins.py"
    """
    LOGGER.debug("start")
    LOGGER.debug("start:parameter:org_id:%s", org_id)
    LOGGER.debug("start:parameter:org_name:%s", org_name)
    LOGGER.debug("start:parameter:csv_file:%s", csv_file)

    if org_id and org_name:
        if not _check_org_name_in_script_param(apisession, org_id, org_name):
            console.critical(f"Org name {org_name} does not match the org {org_id}")
            sys.exit(0)
    elif org_id and not org_name:
        org_id, org_name = _check_org_name(apisession, org_id)
    elif not org_id and not org_name:
        org_id = mistapi.cli.select_org(apisession, allow_many=True)[0]
        org_id, org_name = _check_org_name(apisession, org_id)
    else:
        usage('Cannot set "org_name" without org_id.')
        sys.exit(0)

    if not csv_file:
        csv_file = CSV_FILE

    admins = _read_csv_file(csv_file)
    PB.set_steps_total(len(admins))
    _unclaim_admins(apisession, org_id, admins)


#####################################################################
##### USAGE ####
def usage(error_message: str | None = None):
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
Python script to revoke (remove) administrator access from a Mist organization
using a CSV file containing administrator information. This script provides a
safe and efficient way to bulk remove multiple administrators from an organization.

Key features:
- Bulk removal of administrators using CSV input
- Organization validation to prevent accidental deletions
- Flexible CSV format

Use cases:
- Employee offboarding processes
- Periodic access reviews and cleanup
- Security incident response (removing compromised accounts)
- Organizational restructuring
- Compliance with access management policies

IMPORTANT: This script permanently removes administrator access. Ensure you have
the correct organization and administrator list before proceeding.

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
CSV Format:
The CSV file MUST only contains admin information, without header line

-------
CSV Parameters:
Required:
- admin_id
- admin_email

-------
CSV Example:
Example 1:
bb2c2f47-xxxx-xxxx-xxxx-a0422beaff00, jdoe@mycorp.net, John, Doe

Example 2:
#admin_id, admin_email, admin_first_name, admin_last_name
bb2c2f47-xxxx-xxxx-xxxx-a0422beaff00, jdoe@mycorp.net, John, Doe


-------
Script Parameters:
-h, --help              display this help

-o, --org_id=           ID of the Mist Org
-n, --org_name=         Name of the Mist Org (used for validation purpose)
-c, --csv_file=         CSV File to use.
                        default is "./delete_admins.csv"

-l, --log_file=         define the filepath/filename where to write the logs
                        default is "./script.log"
-e, --env=              define the env file to use (see mistapi env file 
                        documentation here: https://pypi.org/project/mistapi/)
                        default is "~/.mist_env"

-------
Examples:
python3 ./delete_admins.py     
python3 ./delete_admins.py -o 203d3d02-xxxx-xxxx-xxxx-76896a3330f4 -n "My Mist Org"

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


#####################################################################
##### ENTRY POINT ####
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Uninvite (remove) a list of Mist administrators from an organization.",
        add_help=False,
    )
    parser.add_argument(
        "-h",
        "--help",
        action="store_true",
        help="Display this help message and exit",
    )
    parser.add_argument("-o", "--org_id", help="ID of the Mist Org", default=None)
    parser.add_argument(
        "-n",
        "--org_name",
        help="Name of the Mist Org (used for validation purpose)",
        default=None,
    )
    parser.add_argument(
        "-c",
        "--csv_file",
        help="CSV File to use. Default is './delete_admins.csv'",
        default=CSV_FILE,
    )
    parser.add_argument(
        "-l",
        "--log_file",
        help="Define the filepath/filename where to write the logs. Default is './script.log'",
        default=LOG_FILE,
    )
    parser.add_argument(
        "-e",
        "--env",
        help="Define the env file to use. Default is '~/.mist_env'",
        default=ENV_FILE,
    )

    args = parser.parse_args()

    if args.help:
        usage()
        
    ORG_ID = args.org_id
    ORG_NAME = args.org_name
    CSV_FILE = args.csv_file
    ENV_FILE = args.env
    LOG_FILE = args.log_file

    #### LOGS ####
    logging.basicConfig(filename=LOG_FILE, filemode="w")
    LOGGER.setLevel(logging.DEBUG)
    check_mistapi_version()
    ### START ###
    APISESSION = mistapi.APISession(env_file=ENV_FILE)
    APISESSION.login()
    start(APISESSION, ORG_ID, ORG_NAME, CSV_FILE)

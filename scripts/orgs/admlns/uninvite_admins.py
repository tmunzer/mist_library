"""
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to uninvite (remove) a list of Mist administrators from an 
organization.

-------
Requirements:
mistapi: https://pypi.org/project/mistapi/

-------
Usage:
This script can be run as is (without parameters), or with the options below.
If no options are defined, or if options are missing, the missing options will
be asked by the script or the default values will be used.

It is recomended to use an environment file to store the required information
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

Optional:
- admin_first_name admin_last_name 

-------
CSV Example:
Example 1:
bb2c2f47-xxxx-xxxx-xxxx-a0422beaff00, jdoe@mycorp.net, John Doe


-------
Script Parameters:
-h, --help              display this help

-o, --org_id=           ID of the Mist Org
-n, --org_name=         Name of the Mist Org (used for validation purpose)
-c, --csv_file=         CSV File to use.
                        default is "./uninvite_admins.csv"

-l, --log_file=         define the filepath/filename where to write the logs
                        default is "./script.log"
-e, --env=              define the env file to use (see mistapi env file 
                        documentation here: https://pypi.org/project/mistapi/)
                        default is "~/.mist_env"

-------
Examples:
python3 ./uninvite_admins.py     
python3 ./uninvite_admins.py -o 203d3d02-xxxx-xxxx-xxxx-76896a3330f4 -n "My Mist Org"

"""

#####################################################################
#### IMPORTS ####
import logging
import sys
import csv
import re
import getopt

MISTAPI_MIN_VERSION = "0.46.1"

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


#####################################################################
#### PARAMETERS #####
LOG_FILE = "./script.log"
ENV_FILE = "~/.mist_env"
CSV_FILE = "./uninvite_admins.csv"

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
        print(f"Progress: ", end="")
        print(f"[{'█'*x}{'.'*(size-delta-x)}]", end="")
        print(f"{int(percent*100)}%".rjust(5), end="")

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
        LOGGER.info(f"{message}: Success")
        self._pb_new_step(
            message, "\033[92m\u2714\033[0m\n", inc=inc, display_pbar=display_pbar
        )

    def log_warning(self, message, inc: bool = False, display_pbar: bool = True):
        LOGGER.warning(f"{message}: Warning")
        self._pb_new_step(
            message, "\033[93m\u2B58\033[0m\n", inc=inc, display_pbar=display_pbar
        )

    def log_failure(self, message, inc: bool = False, display_pbar: bool = True):
        LOGGER.error(f"{message}: Failure")
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
            resp = mistapi.api.v1.orgs.invites.uninviteOrgAdmin(
                apisession, org_id, admin.get("id")
            )
            if resp and resp.status_code == 200:
                PB.log_success(message, inc=True, display_pbar=True)
            else:
                PB.log_failure(message, inc=True, display_pbar=True)
        except:
            PB.log_failure(message, inc=True, display_pbar=True)
            LOGGER.error("Exception occurred", exc_info=True)


def _read_csv_file(csv_file: str):
    LOGGER.debug("_read_csv_file")
    LOGGER.debug(f"_read_csv_file:parameter:csv_file:{csv_file}")
    admins = []
    PB.log_message("Processing CSV file", display_pbar=False)
    with open(csv_file, "r") as f:
        data_from_csv = csv.reader(f, skipinitialspace=True, quotechar='"')
        data_from_csv = [[c.replace("\ufeff", "") for c in row] for row in data_from_csv]
        for line in data_from_csv:
            LOGGER.debug(f"_read_csv_file:{line}")
            # this is for the first line of the CSV file
            admin_id = line[0]
            admin_email = line[1]
            admins.append({"id": admin_id, "email": admin_email})
            LOGGER.debug(f"_read_csv_file:new id:{admin_id}, email: {admin_email}")

    LOGGER.debug(f"_read_csv_file:got {len(admins)} devices to rename from {csv_file}")
    PB.log_success("Processing CSV file", display_pbar=False, inc=False)
    return admins


def _check_org_name_in_script_param(
    apisession: mistapi.APISession, org_id: str, org_name: str = None
):
    response = mistapi.api.v1.orgs.orgs.getOrg(apisession, org_id)
    if response.status_code != 200:
        console.critical(f"Unable to retrieve the org information: {response.data}")
        sys.exit(3)
    org_name_from_mist = response.data["name"]
    return org_name == org_name_from_mist


def _check_org_name(apisession: mistapi.APISession, org_id: str, org_name: str = None):
    if not org_name:
        org_name = mistapi.api.v1.orgs.orgs.getOrg(apisession, org_id).data["name"]
    while True:
        print()
        resp = input(
            "To avoid any error, please confirm the current destination orgnization name: "
        )
        if resp == org_name:
            print()
            print()
            print()
            return org_id, org_name
        else:
            print()
            print("The orgnization names do not match... Please try again...")


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
        default: "./uninvite_admins.py"
    """
    LOGGER.debug("start")
    LOGGER.debug(f"start:parameter:org_id:{org_id}")
    LOGGER.debug(f"start:parameter:org_name:{org_name}")
    LOGGER.debug(f"start:parameter:csv_file:{csv_file}")

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
def usage(error_message: str = None):
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
Python script to uninvite (remove) a list of Mist administrators from an 
organization.

-------
Requirements:
mistapi: https://pypi.org/project/mistapi/

-------
Usage:
This script can be run as is (without parameters), or with the options below.
If no options are defined, or if options are missing, the missing options will
be asked by the script or the default values will be used.

It is recomended to use an environment file to store the required information
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

Optional:
- admin_first_name admin_last_name 

-------
CSV Example:
Example 1:
bb2c2f47-xxxx-xxxx-xxxx-a0422beaff00, jdoe@mycorp.net, John Doe


-------
Script Parameters:
-h, --help              display this help

-o, --org_id=           ID of the Mist Org
-n, --org_name=         Name of the Mist Org (used for validation purpose)
-c, --csv_file=         CSV File to use.
                        default is "./uninvite_admins.csv"

-l, --log_file=         define the filepath/filename where to write the logs
                        default is "./script.log"
-e, --env=              define the env file to use (see mistapi env file 
                        documentation here: https://pypi.org/project/mistapi/)
                        default is "~/.mist_env"

-------
Examples:
python3 ./rename_devices.py     
python3 ./uninvite_admins.py -o 203d3d02-xxxx-xxxx-xxxx-76896a3330f4 -n "My Mist Org"

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


#####################################################################
##### ENTRY POINT ####
if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(
            sys.argv[1:],
            "ho:n:c:e:l:",
            ["help", "org_id=", "org_name=", "csv_file=", "env=", "log_file="],
        )
    except getopt.GetoptError as err:
        console.error(err)
        usage()
    ORG_ID = None
    ORG_NAME = None
    for o, a in opts:
        if o in ["-h", "--help"]:
            usage()
        elif o in ["-o", "--org_id"]:
            ORG_ID = a
        elif o in ["-n", "--org_name"]:
            ORG_NAME = a
        elif o in ["-c", "--csv_file"]:
            CSV_FILE = a
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
    start(APISESSION, ORG_ID, ORG_NAME, CSV_FILE)

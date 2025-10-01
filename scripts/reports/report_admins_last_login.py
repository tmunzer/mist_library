"""
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to generate a CSV report of organization admins and their last 
login activity. The script analyzes audit logs within a configurable
time period (default: 365 days) to determine when each admin last accessed the
organization.

Key features:
- Lists all organization administrators with their contact information
- Shows last login timestamp (epoch format) for each admin
- Configurable time window for audit log analysis
- Flexible filtering options:
  * All admins (regardless of login activity)
  * Only admins who accessed the org within the specified period
  * Only admins who have NOT accessed the org within the specified period
- Export results to CSV format for further analysis

This tool can be used for security audits, compliance reporting, and identifying
inactive administrator accounts that may need attention.

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
-h, --help                  display this help

-o, --org_id=               organization id to use. If not set, the script will 
                            ask for it
                            
-d, --duration              duration of the access logs to look at
                            default: 365d
-f, --filter=               type of admins to include into the report. Options are
                            - all (default)
                            - accessed: only reports the admins who accessed the
                                org during the `duration` period
                            - not_accessed: only reports the admins who didn't
                                access the org during the `duration` period
                            
-c, --csv_file=             Path to the CSV file where to save the result
                            default: ./report_admins_last_login.csv

-l, --log_file=             define the filepath/filename where to write the logs
                            default is "./script.log"
-e, --env=                  define the env file to use (see mistapi env file documentation
                            here: https://pypi.org/project/mistapi/)
                            default is "~/.mist_env"

-------
Examples:
python3 ./report_admins_last_login.py
python3 ./report_admins_last_login.py \
        -e ~/.mist_env \
        -o 9777c1a0-xxxx-xxxx-xxxx-xxxxxxxxxxxx 

"""

#### IMPORTS ####
import sys
import argparse
import logging
import csv
import datetime

MISTAPI_MIN_VERSION = "0.57.0"

try:
    import mistapi
    from mistapi.__logger import console as CONSOLE
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

#### PARAMETERS #####
ENV_FILE = "~/.mist_env"
CSV_FILE = "./report_admins_last_login.csv"
LOG_FILE = "./script.log"

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
def _retrieve_audit_logs(
    mist_session: mistapi.APISession,
    org_id: str,
    duration: str = "365d"
) -> list:
    message = "Retrieving Access Logs"
    PB.log_message(message, display_pbar=False)
    try:
        resp = mistapi.api.v1.orgs.logs.listOrgAuditLogs(
            mist_session,
            org_id,
            message="Access Org",
            duration=duration,
            limit=1000,
        )
        if resp.status_code == 200:
            logs = mistapi.get_all(mist_session, resp)
            PB.log_success(message, inc=False, display_pbar=False)
            return logs
        else:
            PB.log_failure(message, inc=False, display_pbar=False)
            sys.exit(2)
    except Exception:
        PB.log_failure(message, inc=False, display_pbar=False)
        LOGGER.error("Exception occurred", exc_info=True)
        sys.exit(2)
        
def _retrieve_admins(
    mist_session: mistapi.APISession,
    org_id: str
) -> list:
    message = "Retrieving Admins"
    PB.log_message(message, display_pbar=False)
    try:
        resp = mistapi.api.v1.orgs.admins.listOrgAdmins(
            mist_session,
            org_id,
        )
        if resp.status_code == 200:
            admins = mistapi.get_all(mist_session, resp)
            PB.log_success(message, inc=False, display_pbar=False)
            return admins
        else:
            PB.log_failure(message, inc=False, display_pbar=False)
            sys.exit(2)
    except Exception:
        PB.log_failure(message, inc=False, display_pbar=False)
        LOGGER.error("Exception occurred", exc_info=True)
        sys.exit(2)

def _process_admins(admins: list) -> dict:
    admin_logins = {}
    PB.set_steps_total(len(admins))
    message = "Processing Admin"
    PB.log_message(message, display_pbar=False)
    for admin in admins:
        if admin.get('admin_id'):
            admin_logins[admin['admin_id']] = {
                'id': admin.get('admin_id'),
                'first_name': admin.get('first_name'),
                'last_name': admin.get('last_name'),
                'email': admin.get('email'),
                'last_login': 0
            }
    PB.log_success(message, inc=False, display_pbar=False)
    return admin_logins

def _process_logins(access_logs: list, admins: dict) -> dict:
    PB.set_steps_total(len(access_logs))
    message = "Processing Access Logs"
    PB.log_message(message, display_pbar=False)
    for log in access_logs:
        admin_id = log.get("admin_id")
        if admin_id in admins:
            timestamp = log.get("timestamp")
            if timestamp > admins[admin_id]['last_login']:
                admins[admin_id]['last_login'] = timestamp
    PB.log_success(message, inc=False, display_pbar=False)
    return admins

def _write_csv(
    admins: dict,
    csv_file: str = "./report_admins_last_login.csv"
):
    """
    Write the admin login data to a CSV file.
    
    PARAMS
    -------
    admins : dict
        Dictionary containing admin data with last login timestamps.
    csv_file : str, default "./report_admins_last_login.csv"
        Path to the CSV file where the admin login report will be saved.
    """
    message = f'Saving report to CSV file "{csv_file}"'
    PB.log_message(message, display_pbar=False)
    try:
        with open(csv_file, mode="w", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(
                [
                    "#admin_id",
                    "admin_email",
                    "admin_first_name",
                    "admin_last_name",
                    "last_login_epoch",
                    "last_login_date",
                ]
            )
            for _, admin in admins.items():
                writer.writerow(
                    [
                        admin.get("id", ""),
                        admin.get("email", ""),
                        admin.get("first_name", ""),
                        admin.get("last_name", ""),
                        admin.get("last_login", 0),
                        datetime.datetime.fromtimestamp(
                            admin.get("last_login", 0)
                        ).strftime("%Y-%m-%d %H:%M:%S"),
                    ]
                )
        PB.log_success(message, inc=False, display_pbar=False)
    except Exception:
        PB.log_failure(message, inc=False, display_pbar=False)
        LOGGER.error("Exception occurred", exc_info=True)
        sys.exit(2)


###################################################################################################
################################# START
def start(
    apisession: mistapi.APISession,
    org_id: str,
    duration: str = "365d",
    admin_filter: str = "all",
    csv_file: str = "./report_admins_last_login.csv",    
):
    """
    Generate a CSV report listing admins and their last login times.

    PARAMS
    -------
    apisession : mistapi.APISession
        mistapi session with `Super User` access to the Org, already logged in
    org_id : str
        organization id to generate the report for. If not provided, the script will
        show a menu to select the organization.
    duration : str, default "365d"
        duration of the access logs to look at (e.g., "365d", "30d", "7d")
        default is "365d"
    admin_filter : str, default "all"
        type of admins to include in the report. Options are:
            - "all": include all admins (default)
            - "accessed": only include admins who accessed the org during the duration period
            - "not_accessed": only include admins who didn't access the org during the duration period
    csv_file : str, default "./report_admins_last_login.csv"
        Path to the CSV file where the admin login report will be saved.
    """
    if not org_id:
        org_id = mistapi.cli.select_org(apisession)[0]
    print()
    print()
    print()
    admins = _retrieve_admins(apisession, org_id)
    audit_logs = _retrieve_audit_logs(apisession, org_id, duration)
    admins = _process_admins(admins)
    admins = _process_logins(audit_logs, admins)
    if admin_filter == "accessed":
        admins = {k: v for k, v in admins.items() if v['last_login'] > 0}
    elif admin_filter == "not_accessed":
        admins = {k: v for k, v in admins.items() if v['last_login'] == 0}
    _write_csv(admins, csv_file)
    
    print()
    print("Script completed")


def usage(error_message: str | None = None):
    """
    show script usage
    """
    print(
        """
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to generate a CSV report of organization admins and their last 
login activity. The script analyzes audit logs within a configurable
time period (default: 365 days) to determine when each admin last accessed the
organization.

Key features:
- Lists all organization administrators with their contact information
- Shows last login timestamp (epoch format) for each admin
- Configurable time window for audit log analysis
- Flexible filtering options:
  * All admins (regardless of login activity)
  * Only admins who accessed the org within the specified period
  * Only admins who have NOT accessed the org within the specified period
- Export results to CSV format for further analysis

This tool can be used for security audits, compliance reporting, and identifying
inactive administrator accounts that may need attention.

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
-h, --help                  display this help

-o, --org_id=               organization id to use. If not set, the script will 
                            ask for it
                            
-d, --duration              duration of the access logs to look at
                            default: 365d
-f, --filter=               type of admins to include into the report. Options are
                            - all (default)
                            - accessed: only reports the admins who accessed the
                                org during the `duration` period
                            - not_accessed: only reports the admins who didn't
                                access the org during the `duration` period
                            
-c, --csv_file=             Path to the CSV file where to save the result
                            default: ./report_admins_last_login.csv

-l, --log_file=             define the filepath/filename where to write the logs
                            default is "./script.log"
-e, --env=                  define the env file to use (see mistapi env file documentation
                            here: https://pypi.org/project/mistapi/)
                            default is "~/.mist_env"

-------
Examples:
python3 ./report_admins_last_login.py
python3 ./report_admins_last_login.py \
        -e ~/.mist_env \
        -o 9777c1a0-xxxx-xxxx-xxxx-xxxxxxxxxxxx 

"""
    )
    if error_message:
        CONSOLE.critical(error_message)
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
        description="Display list of open events/alarms that are not cleared",
        add_help=False,
    )
    parser.add_argument(
        "-h",
        "--help",
        action="store_true",
        help="Display this help message and exit",
    )
    parser.add_argument(
        "-e", "--env_file", help="define the env file to use", default=None
    )
    parser.add_argument(
        "-o",
        "--org_id",
        help="Set the org_id where the webhook must be create/delete/retrieved",
        default="",
    )
    parser.add_argument(
        "-d", "--duration", help="duration of the events to look at", default="365d"
    )
    parser.add_argument(
        "-f",
        "--filter",
        help="type of admins to include in the report",
        choices=["all", "accessed", "not_accessed"],
        default="all",
    )
    parser.add_argument(
        "-l",
        "--log_file",
        help="define the filepath/filename where to write the logs",
        default=LOG_FILE,
    )
    parser.add_argument(
        "-c",
        "--csv_file",
        help="Path to the CSV file where to save the result",
        default=CSV_FILE,
    )

    args = parser.parse_args()
    
    if args.help:
        usage()

    ENV_FILE = args.env_file
    ORG_ID = args.org_id
    DURATION = args.duration
    FILTER = args.filter
    CSV_FILE = args.csv_file
    LOG_FILE = args.log_file

    # Validate duration format
    if not DURATION.endswith(("m", "h", "d", "w")):
        usage(
            f'Invalid -d / --duration parameter value, should be something like "10m", "2h", "7d", "1w"... Got "{DURATION}".'
        )

    #### LOGS ####
    logging.basicConfig(filename=LOG_FILE, filemode="w")
    LOGGER.setLevel(logging.DEBUG)
    check_mistapi_version()
    ### START ###
    APISESSION = mistapi.APISession(env_file=ENV_FILE, show_cli_notif=False)
    APISESSION.login()
    start(
        APISESSION, ORG_ID, DURATION, FILTER, CSV_FILE
    )

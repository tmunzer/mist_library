"""
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to generates a list of all the switches for a specified org/site
with, for each FPC:
        - VC name
        - VC reported Version
        - FPC Serial Number
        - FPC MAC Address
        - FPC Version
        - FPC Snapshot version
        - FPC Backup version
        - FPC Pending version
        - FPC Compliance (if the snapshot/backup is up to date)

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
Options:
-h, --help          display this help
-o, --org_id=       Set the org_id (only one of the org_id or site_id can be defined)
-s, --site_id=      Set the site_id  (only one of the org_id or site_id can be defined)

-f, --out_file=     define the filepath/filename where to save the data
                    default is "./report_rogues.csv"
-d, --datetime      append the current date and time (ISO format) to the report name
-t, --timestamp     append the current timestamp to the report name

-l, --log_file=     define the filepath/filename where to write the logs
                    default is "./script.log"
-e, --env=          define the env file to use (see mistapi env file documentation
                    here: https://pypi.org/project/mistapi/)
                    default is "~/.mist_env"

-------
Examples:
python3 ./report_switch_firmware.py
python3 ./report_switch_firmware.py --site_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4

"""

#### IMPORTS #####
import sys
import csv
import datetime
import argparse
import logging

MISTAPI_MIN_VERSION = "0.44.1"

try:
    import mistapi
    from mistapi.__logger import console
except ImportError:
    print("""
        Critical:
        \"mistapi\" package is missing. Please use the pip command to install it.

        # Linux/macOS
        python3 -m pip install mistapi

        # Windows
        py -m pip install mistapi
        """)
    sys.exit(2)


#### LOGS ####
LOGGER = logging.getLogger(__name__)
out = sys.stdout

#### PARAMETERS #####
CSV_FILE = "./report_switch_firmware.csv"
LOG_FILE = "./script.log"
ENV_FILE = "~/.mist_env"


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


###############################################################################
#### FUNCTIONS ####
def _process_fpc(
    vc_name: str,
    vc_version: str,
    vc_device_id: str,
    vc_site_id: str,
    fpc: dict,
    data: list,
) -> None:
    LOGGER.debug("Processing FPC: %s", fpc)
    fpv_version = fpc.get("version")
    fpc_snapshot_version = fpc.get("recovery_version")
    fpc_backup_version = None
    if not fpc_snapshot_version:
        fpc_backup_version = fpc.get("backup_version")
    fpc_need_snapshot = False
    if fpc.get("vc_version"):
        if (
            (
                fpc_backup_version
                and fpv_version != fpc_backup_version
            )
            or (
                fpc_snapshot_version
                and fpv_version != fpc_snapshot_version
            )
            or (not fpc.get("backup_version") and not fpc.get("recovery_version"))
        ):
            fpc_need_snapshot = True
    module = {
        "vc_name": vc_name,
        "vc_version": vc_version,
        "vc_device_id": vc_device_id,
        "vc_site_id": vc_site_id,
        "fpc_serial": fpc.get("serial"),
        "fpc_mac": fpc.get("mac"),
        "fpc_model": fpc.get("model"),
        "fpc_version": fpv_version,
        "fpc_snapshot_version": fpc_snapshot_version,
        "fpc_backup_version": fpc_backup_version,
        "fpc_need_snapshot": fpc_need_snapshot,
        "fpc_pending_version": fpc.get("pending_version"),
        "fpc_need_reboot": fpc.get("pending_version", "") != "",
    }
    LOGGER.debug("Processed module data: %s", module)
    data.append(module)


def _process_switches(switches: list) -> list:
    message = "Processing Switches"
    PB.set_steps_total(len(switches))
    PB.log_message(message)
    data = []
    for vc in switches:
        vc_version = vc.get("version")
        vc_name = vc.get("name")
        vc_device_id = vc.get("id")
        vc_site_id = vc.get("site_id")
        for fpc in vc.get("module_stat", []):
            _process_fpc(vc_name, vc_version, vc_device_id, vc_site_id, fpc, data)
        PB.steps_count += 1
    PB.log_success(message, display_pbar=False)
    return data


def _get_org_switches(apisession, org_id: str) -> list:
    message = " Retrieving Switches "
    PB.log_message(message, display_pbar=False)
    try:
        response = mistapi.api.v1.orgs.stats.listOrgDevicesStats(
            apisession, org_id, type="switch", limit=1000
        )
        if isinstance(response.data, list):
            switches = response.data
            while response and response.next:
                response = mistapi.get_next(apisession, response)
                if response:
                    switches.extend(response.data)
    except Exception:
        PB.log_failure(message, display_pbar=False)
    return switches


def _get_site_switches(apisession, site_id: str) -> list:
    print(" Retrieving Switches ".center(80, "-"))
    response = mistapi.api.v1.sites.stats.listSiteDevicesStats(
        apisession, site_id, type="switch", limit=1000
    )
    if isinstance(response.data, list):
        switches = response.data
        while response and response.next:
            response = mistapi.get_next(apisession, response)
            if response:
                switches.extend(response.data)
    return switches


### SAVE REPORT
def _save_as_csv(
    data: list,
    scope: str,
    scope_id: str,
    csv_file: str,
    append_dt: bool,
    append_ts: bool,
):
    headers = []
    total = len(data)
    message = "Generating CSV Headers"
    PB.set_steps_total(total)
    PB.log_title("Saving Data", display_pbar=True)
    PB.log_message(message)
    if append_dt:
        dt = (
            datetime.datetime.isoformat(datetime.datetime.now())
            .split(".")[0]
            .replace(":", ".")
        )
        csv_file = f"{csv_file.replace('.csv', f'_{dt}')}.csv"
    elif append_ts:
        ts = round(datetime.datetime.timestamp(datetime.datetime.now()))
        csv_file = f"{csv_file.replace('.csv', f'_{ts}')}.csv"

    for entry in data:
        for key in entry:
            if key not in headers:
                headers.append(key)
        PB.steps_count += 1
    PB.log_success(message, display_pbar=True)

    message = "Saving to file"
    with open(csv_file, "w", encoding="UTF8", newline="") as f:
        csv_writer = csv.writer(f)
        csv_writer.writerow([f"#Switches snapshot/backup for {scope} {scope_id}"])
        csv_writer.writerow(headers)
        for entry in data:
            tmp = []
            for header in headers:
                tmp.append(entry.get(header, ""))
            csv_writer.writerow(tmp)
            PB.steps_count += 1
        PB.log_success(message, display_pbar=True)
        print()
    return headers


####################
## MENU


def _show_menu(header: str, menu: list) -> str:
    print()
    print("".center(80, "-"))
    resp = None
    while True:
        print(f"{header}")
        i = 0
        for entry in menu:
            print(f"{i}) {entry}")
            i += 1
        resp = input(f"Please select an option (0-{i - 1}, q to quit): ")
        if resp.lower() == "q":
            sys.exit(0)
        else:
            try:
                resp = int(resp)
                if resp < 0 or resp >= i:
                    console.error(f"Please enter a number between 0 and {i - 1}.")
                else:
                    return menu[resp]
            except ValueError:
                console.error("Please enter a number\r\n ")


###############################################################################
### START
def _start(
    apisession: mistapi.APISession,
    scope: str,
    scope_id: str,
    csv_file: str,
    append_dt: bool = False,
    append_ts: bool = False,
) -> None:
    """
    Start the backup process

    PARAMS
    -------
    apisession : mistapi.APISession
        mistapi session
    scope : str, enum: org, site
        At which level the devices must be retrieved
    scope_id : str
        ID of the scope (org_id or site_id) where the devices must be retrieved
    csv_file : str
        define the filepath/filename where to save the data
        default is "./report_switch_firmware.csv"
    append_dt : bool, default = False
        append the current date and time (ISO format) to the backup name
    append_ts : bool, default = False
        append the timestamp at the end of the report and summary files

    """
    if not scope:
        menu = ["org", "site"]
        scope = _show_menu("", menu)
        if scope == "org":
            scope_id = mistapi.cli.select_org(apisession)[0]
        elif scope == "site":
            scope_id = mistapi.cli.select_site(apisession)[0]

    switches = None
    data = None
    if scope == "org":
        switches = _get_org_switches(apisession, scope_id)
    elif scope == "site":
        switches = _get_site_switches(apisession, scope_id)
    if switches:
        data = _process_switches(switches)

    if data:
        headers = _save_as_csv(data, scope, scope_id, csv_file, append_dt, append_ts)
        print()
        mistapi.cli.display_list_of_json_as_table(data, headers)


###############################################################################
### USAGE
def usage(error_message: str = ""):
    """
    display usage
    """
    print("""
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to generates a list of all the switches for a specified org/site
with, for each FPC:
        - VC name
        - VC reported Version
        - FPC Serial Number
        - FPC MAC Address
        - FPC Version
        - FPC Snapshot version
        - FPC Backup version
        - FPC Pending version
        - FPC Compliance (if the snapshot/backup is up to date)

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
Options:
-h, --help          display this help
-o, --org_id=       Set the org_id (only one of the org_id or site_id can be defined)
-s, --site_id=      Set the site_id  (only one of the org_id or site_id can be defined)

-f, --out_file=     define the filepath/filename where to save the data
                    default is "./report_rogues.csv"
-d, --datetime      append the current date and time (ISO format) to the report name
-t, --timestamp     append the current timestamp to the report name

-l, --log_file=     define the filepath/filename where to write the logs
                    default is "./script.log"
-e, --env=          define the env file to use (see mistapi env file documentation
                    here: https://pypi.org/project/mistapi/)
                    default is "~/.mist_env"

-------
Examples:
python3 ./report_switch_firmware.py
python3 ./report_switch_firmware.py --site_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4

""")
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
### ENTRY POINT
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate a list of switches with firmware information",
        add_help=False,
    )

    # Add help manually to maintain control over usage function
    parser.add_argument("-h", "--help", action="store_true", help="display this help")

    # Scope arguments (mutually exclusive)
    scope_group = parser.add_mutually_exclusive_group()
    scope_group.add_argument("-o", "--org_id", help="Set the org_id")
    scope_group.add_argument("-s", "--site_id", help="Set the site_id")

    # Timestamp arguments (mutually exclusive)
    time_group = parser.add_mutually_exclusive_group()
    time_group.add_argument(
        "-d",
        "--datetime",
        action="store_true",
        help="append the current date and time (ISO format) to the report name",
    )
    time_group.add_argument(
        "-t",
        "--timestamp",
        action="store_true",
        help="append the current timestamp to the report name",
    )

    # File arguments
    parser.add_argument(
        "-f",
        "--out_file",
        default=CSV_FILE,
        help="define the filepath/filename where to save the data",
    )
    parser.add_argument(
        "-e", "--env", default=ENV_FILE, help="define the env file to use"
    )
    parser.add_argument(
        "-l",
        "--log_file",
        default=LOG_FILE,
        help="define the filepath/filename where to write the logs",
    )

    args = parser.parse_args()

    if args.help:
        usage()

    SCOPE = ""
    SCOPE_ID = ""
    if args.org_id:
        SCOPE = "org"
        SCOPE_ID = args.org_id
    elif args.site_id:
        SCOPE = "site"
        SCOPE_ID = args.site_id

    APPEND_DT = args.datetime
    APPEND_TS = args.timestamp
    CSV_FILE = args.out_file
    ENV_FILE = args.env
    LOG_FILE = args.log_file

    #### LOGS ####
    logging.basicConfig(filename=LOG_FILE, filemode="w")
    LOGGER.setLevel(logging.DEBUG)
    check_mistapi_version()
    ### MIST SESSION ###
    APISESSION = mistapi.APISession(env_file=ENV_FILE)
    APISESSION.login()
    ### START ###
    _start(APISESSION, SCOPE, SCOPE_ID, CSV_FILE, APPEND_DT, APPEND_TS)

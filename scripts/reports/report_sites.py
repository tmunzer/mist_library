"""
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to generate a report of the Mist Sites and resolving the site
group names

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
-s, --site_id=      Set the site_id
-f, --out_file=     define the filepath/filename where to save the data
                    default is "./report_rogues.csv"
-l, --log_file=     define the filepath/filename where to write the logs
                    default is "./script.log"
-e, --env=          define the env file to use (see mistapi env file documentation
                    here: https://pypi.org/project/mistapi/)
                    default is "~/.mist_env"

-------
Examples:
python3 ./report_sites.py
python3 ./report_sites.py --site_ids=203d3d02-xxxx-xxxx-xxxx-76896a3330f4

"""

#### IMPORTS #####
import sys
import csv
import argparse
import logging

MISTAPI_MIN_VERSION = "0.56.4"

try:
    import mistapi
    from mistapi.__logger import console as CONSOLE
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


#### PARAMETERS #####
ENV_FILE = "~/.mist_env"
CSV_FILE = "./report_sites.csv"
LOG_FILE = "./script.log"
CSV_DELIMITER = ","
REPORT_HEADERS = [
    "country_code",
    "timezone",
    "address",
    "sitegroup_names",
    "sitegroup_ids",
    "notes",
    "latlng",
    "id",
    "name",
    "org_id",
    "created_time",
    "modified_time",
    "rftemplate_id",
    "aptemplate_id",
    "secpolicy_id",
    "alarmtemplate_id",
    "networktemplate_id",
    "gatewaytemplate_id",
    "sitetemplate_id",
    "tzoffset",
    "engagementEnabled",
    "analyticEnabled",
    "lat",
    "lng",
]
#### LOGS ####
LOGGER = logging.getLogger(__name__)
out = sys.stdout


#####################################################################
# PROGRESS BAR AND DISPLAY
class ProgressBar:
    """
    PROGRESS BAR AND DISPLAY
    """

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
        LOGGER.info("%s", message)
        self._pb_title(message, end=end, display_pbar=display_pbar)


PB = ProgressBar()

###############################################################################
#### FUNCTIONS ####


def _get_sitegroups(apisession: mistapi.APISession, org_id: str) -> dict:
    sitegroups = {}
    message = "Retrieving site groups..."
    PB.log_message(message, display_pbar=False)
    try:
        response = mistapi.api.v1.orgs.sitegroups.listOrgSiteGroups(
            apisession, org_id, limit=1000
        )
        if response.status_code == 200:
            data = mistapi.get_all(apisession, response)
            for site in data:
                sitegroups[site["id"]] = site["name"]
            PB.log_success(message, inc=False, display_pbar=False)
        else:
            PB.log_failure(message, inc=False, display_pbar=False)
    except Exception:
        PB.log_failure(message, inc=False, display_pbar=False)
        LOGGER.error("Exception occurred", exc_info=True)
        sys.exit(2)
    return sitegroups


def _get_sites(
    apisession: mistapi.APISession,
    org_id: str,
) -> list:
    sites = []
    message = "Retrieving sites..."
    PB.log_message(message, display_pbar=False)
    try:
        response = mistapi.api.v1.orgs.sites.listOrgSites(
            apisession, org_id, limit=1000
        )
        if response.status_code == 200:
            sites = mistapi.get_all(apisession, response)
            PB.log_success(message, inc=False, display_pbar=False)
        else:
            PB.log_failure(message, inc=False, display_pbar=False)
    except Exception:
        PB.log_failure(message, inc=False, display_pbar=False)
        LOGGER.error("Exception occurred", exc_info=True)
        sys.exit(2)
    return sites


def _process_sites(
    api_session: mistapi.APISession,
    org_id: str,
    sitegroups: dict,
) -> list:
    sites = []
    results = _get_sites(api_session, org_id)
    for r in results:
        sitegroup_ids = r.get("sitegroup_ids", [])
        sitegroup_names = []
        for sg_id in sitegroup_ids:
            sitegroup_names.append(sitegroups.get(sg_id, ""))
        r["sitegroup_names"] = sitegroup_names
        sites.append(r)
    return sites


### SAVE REPORT
def _format_data(data: list) -> list:
    formatted = []
    message = "Formatting results..."
    PB.log_message(message, display_pbar=False)
    formatted.append(REPORT_HEADERS)
    for site_data in data:
        tmp = []
        for header in REPORT_HEADERS:
            tmp.append(site_data.get(header, ""))
        formatted.append(tmp)
    return formatted


def _save_as_csv(data: list, csv_file: str):
    PB.log_title(f"Saving report to {csv_file}", display_pbar=False)
    with open(csv_file, "w", encoding="UTF8", newline="") as f:
        csv_writer = csv.writer(f, delimiter=CSV_DELIMITER)
        csv_writer.writerows(data)
    PB.log_success("Saving to file ", display_pbar=False)


def _display_report(data: list):
    PB.log_title("Displaying report", display_pbar=False)
    print(mistapi.cli.tabulate(data[1:], headers=data[0], tablefmt="rounded_grid"))


def start(
    api_session: mistapi.APISession,
    org_id: str,
    csv_file: str = CSV_FILE,
):
    """
    Start the report generation process.

    PARAMS
    ------
    apisession : mistapi.APISession
        mistapi session with `Observer` access the Org, already logged in
    org_id : str
        Mist Organization ID
    csv_file : str
        path to the CSV file to save the report
    """
    if not org_id:
        org_id = mistapi.cli.select_org(api_session)[0]

    sitegroups_map = _get_sitegroups(api_session, org_id)
    sites = _process_sites(api_session, org_id, sitegroups_map)
    formatted_data = _format_data(sites)
    _save_as_csv(formatted_data, csv_file)
    _display_report(formatted_data)


###############################################################################
### USAGE


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
Python script to generate a report of the Mist Sites and resolving the site
group names

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
-s, --site_id=      Set the site_id
-f, --out_file=     define the filepath/filename where to save the data
                    default is "./report_rogues.csv"
-l, --log_file=     define the filepath/filename where to write the logs
                    default is "./script.log"
-e, --env=          define the env file to use (see mistapi env file documentation
                    here: https://pypi.org/project/mistapi/)
                    default is "~/.mist_env"

-------
Examples:
python3 ./report_sites.py
python3 ./report_sites.py --site_ids=203d3d02-xxxx-xxxx-xxxx-76896a3330f4
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
### ENTRY POINT
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Display list of open events/alarms that are not cleared"
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

    ENV_FILE = args.env_file
    ORG_ID = args.org_id

    #### LOGS ####
    logging.basicConfig(filename=LOG_FILE, filemode="w")
    LOGGER.setLevel(logging.DEBUG)
    check_mistapi_version()
    ### MIST SESSION ###
    API_SESSION = mistapi.APISession(env_file=ENV_FILE)
    API_SESSION.login()
    ### START ###
    start(API_SESSION, ORG_ID, CSV_FILE)

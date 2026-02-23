"""
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to update the vars of existing sites in a Mist Org from a CSV file.

-------
Requirements:
mistapi: https://pypi.org/project/mistapi/

-------
Usage:
This script requires a parameter to locate the csv file. Other parameters listed below
are optional. If the optional parameters are not defined, the script will ask for the
additional required settings.

It is recommended to use an environment file to store the required information
to request the Mist Cloud (see https://pypi.org/project/mistapi/ for more
information about the available parameters).

-------
CSV Format:
The first line MUST start with a "#" and defines each columns of the CSV file. The allowed
values are listed below.

When defining the templates, the policies and the sitegroups, it is possible to use the
object name OR the object id (this must be defined in the first line, by appending "_name" or
"_id"). In case both name and id are defined, the name will be used.

-------
CSV Example with Site Name:
#site_name,var_name_1,var_name_2
Juniper France,3,1.2.3.4

CSV Example with Site ID:
#site_id,var_name_1,var_name_2
203d3d02-xxxx-xxxx-xxxx-76896a3330f4,3,1.2.3.4

-------
CSV Parameters:
Required:
- site_name or site_id
- vars


-------
Script Parameters:
-h, --help          display this help

-f, --file=         path to the CSV file (default: ./update_sites_vars.csv)

-o, --org_id=       Set the org_id (only one of the org_id or site_id can be defined)

-l, --log_file=     define the filepath/filename where to write the logs
                    default is "./script.log"
-e, --env=          define the env file to use (see mistapi env file documentation
                    here: https://pypi.org/project/mistapi/)
                    default is "~/.mist_env"

-------
Examples:
python3 ./update_sites_vars.py -f ./my_new_sites.csv
python3 ./update_sites_vars.py -f ./my_new_sites.csv --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4

"""

#### IMPORTS #####
import sys
import csv
import argparse
import logging
from typing import Tuple

MISTAPI_MIN_VERSION = "0.60.1"

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

#####################################################################
#### PARAMETERS #####
LOG_FILE = "./script.log"
ENV_FILE = "~/.mist_env"

#####################################################################
#### LOGS ####
LOGGER = logging.getLogger(__name__)



#####################################################################
# PROGRESS BAR
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
        print("\033[A")
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
        print()
        print("\033[A")
        print(f" {text} ".center(size, "-"), "\n")
        if not end and display_pbar:
            print("".ljust(80))
            self._pb_update(size)

    def inc(self, size: int = 80):
        self.steps_count += 1
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
# Functions
#####################################################################

def _update_sites_vars(apisession: mistapi.APISession, sites: list):
    for site in sites:
        message = f"Updating vars for site {site.get('site_name', site.get('site_id', 'unknown'))}"
        PB.log_message(message)
        if site.get("site_id"):
            res = mistapi.api.v1.sites.setting.updateSiteSettings(
                apisession, site["site_id"], body={
                    "vars": site["vars"]}
            )
            if res.status_code == 200:
                PB.log_success(message, inc=True)
            else:
                PB.log_failure(message, inc=True)
        else:
            PB.log_failure(message, inc=True)
            PB.log_failure(
                f"Unable to update vars for site {site.get('site_name', site.get('site_id', 'unknown'))} as the site ID is missing",
                inc=True,
            )


def _retrieve_site_ids(apisession: mistapi.APISession, org_id: str, sites: list) -> list:
    message = "Retrieving source site IDs"
    PB.log_message(message, display_pbar=False)
    try:
        res = mistapi.api.v1.orgs.sites.listOrgSites(
            apisession, org_id, limit=1000
        )
        sites_from_mist = mistapi.get_all(apisession, res)
        LOGGER.debug(sites_from_mist[0])
        site_mapping = {site["name"].lower(): site["id"]
                        for site in sites_from_mist}
    except Exception as e:
        PB.log_failure(message, display_pbar=False)
        LOGGER.error("retrieve_site_ids: An error occurred while retrieving the Mist Sites: %s", str(e))
        LOGGER.error("Exception occurred", exc_info=True)
        sys.exit(2)
    try:
        for site in sites:
            if site_mapping.get(site["site_name"].lower()):
                site["site_id"] = site_mapping[site["site_name"].lower()]
                LOGGER.info(
                    "retrieve_site_ids: Site %s ID retrieved: %s",
                    site["site_name"],
                    site["site_id"],
                )
            else:
                LOGGER.warning(
                    "retrieve_site_ids: Unable to retrieve the site ID for site %s. Site vars won't be updated...",
                    site["site_name"],
                )
        PB.log_success(message, display_pbar=False)
        return sites
    except Exception as e:
        PB.log_failure(message, display_pbar=False)
        LOGGER.error("retrieve_site_ids: An error occurred while retrieving the site IDs: %s", str(e))
        LOGGER.error("Exception occurred", exc_info=True)
        sys.exit(2)



def _read_csv_file(file_path: str) -> Tuple[list, bool]:
    
    with open(file_path, "r", encoding="utf-8") as f:
        data = csv.reader(f, skipinitialspace=True, quotechar='"')
        data = [[c.replace("\ufeff", "") for c in row] for row in data]
        fields = []
        sites = []
        need_to_retrieve_site_ids = False
        
        for line in data:
            if not fields:
                for column in line:
                    column_name = column.strip().lower().replace("#", "")
                    fields.append(column_name)
                    if column_name == "site_name":
                        need_to_retrieve_site_ids = True
            elif len(line) > 1 and line[0].strip() != "":
                site = {
                    "site_name": None,
                    "site_id": None,
                    "vars": {},
                }
                i = 0
                for column in line:
                    field = fields[i]
                    if field in ["site_name", "site_id"]:
                        site[field] = column
                    else:
                        site["vars"][field] = column
                    i += 1
                sites.append(site)
            else:
                LOGGER.info("Skipping empty line")
        if not "site_name" in fields and not "site_id" in fields:
            LOGGER.critical(
                "CSV file must contain either 'site_name' or 'site_id' column"
            )
            sys.exit(2)
        return sites, need_to_retrieve_site_ids


def start(
    apisession: mistapi.APISession,
    org_id: str = "",
    file_path: str = "./update_sites_vars.csv",
):
    """
    Start the process to update the sites

    PARAMS
    -------
    :param  mistapi.APISession  apisession      mistapi session with `Super User` access the source
                                                Org, already logged in
    :param  str                 org_id          Optional, org_id of the org where to process the sites
    :param  str                 file_path       path to the CSV file with all the sites to update
    """

    if not org_id:
        org_id = mistapi.cli.select_org(apisession)[0]

    sites, need_to_retrieve_site_ids = _read_csv_file(file_path)
    if need_to_retrieve_site_ids:
        sites = _retrieve_site_ids(apisession, org_id, sites)
    # 4 = IDs +  geocoding + site creation + clone site settings + site settings update
    PB.set_steps_total(len(sites))

    _update_sites_vars(apisession, sites)

    PB.log_title("Sites update Done", end=True)


###############################################################################
# USAGE
def usage(error: str | None = None):
    """
    display script usage
    """
    print("""
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to update the vars of existing sites in a Mist Org from a CSV file.

-------
Requirements:
mistapi: https://pypi.org/project/mistapi/

-------
Usage:
This script requires a parameter to locate the csv file. Other parameters listed below
are optional. If the optional parameters are not defined, the script will ask for the
additional required settings.

It is recommended to use an environment file to store the required information
to request the Mist Cloud (see https://pypi.org/project/mistapi/ for more
information about the available parameters).

-------
CSV Format:
The first line MUST start with a "#" and defines each columns of the CSV file. The allowed
values are listed below.

When defining the templates, the policies and the sitegroups, it is possible to use the
object name OR the object id (this must be defined in the first line, by appending "_name" or
"_id"). In case both name and id are defined, the name will be used.

-------
CSV Example with Site Name:
#site_name,var_name_1,var_name_2
Juniper France,3,1.2.3.4

CSV Example with Site ID:
#site_id,var_name_1,var_name_2
203d3d02-xxxx-xxxx-xxxx-76896a3330f4,3,1.2.3.4

-------
CSV Parameters:
Required:
- site_name or site_id
- vars


-------
Script Parameters:
-h, --help          display this help

-f, --file=         path to the CSV file (default: ./update_sites_vars.csv)

-o, --org_id=       Set the org_id (only one of the org_id or site_id can be defined)


-l, --log_file=     define the filepath/filename where to write the logs
                    default is "./script.log"
-e, --env=          define the env file to use (see mistapi env file documentation
                    here: https://pypi.org/project/mistapi/)
                    default is "~/.mist_env"

-------
Examples:
python3 ./update_sites_vars.py -f ./my_new_sites.csv
python3 ./update_sites_vars.py -f ./my_new_sites.csv --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4

""")
    if error:
        console.error(error)
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
# ENTRY POINT
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Automate the sites creation in a Mist Org from a CSV file.",
        add_help=False,
    )
    parser.add_argument("-f", "--file", dest="csv_file",
                        help="Path to the CSV file")
    parser.add_argument("-o", "--org_id", dest="org_id",
                        default="", help="Org ID")
    
    parser.add_argument("-l", "--log_file", dest="log_file",
                        default="./script.log", help="Log file path")
    parser.add_argument("-e", "--env", dest="env_file",
                        default="~/.mist_env", help="Env file to use")
    parser.add_argument("-h", "--help", action="store_true",
                        help="Show this help message and exit")

    args = parser.parse_args()

    if args.help:
        usage()

    CSV_FILE = args.csv_file if args.csv_file else "./update_sites_vars.csv"
    ORG_ID = args.org_id
    LOG_FILE = args.log_file
    ENV_FILE = args.env_file

    PARAMS = {
        "-f": CSV_FILE,
        "-o": ORG_ID,
        "-l": LOG_FILE,
        "-e": ENV_FILE,
    }

    #### LOGS ####
    logging.basicConfig(filename=LOG_FILE, filemode="w")
    LOGGER.setLevel(logging.DEBUG)
    check_mistapi_version()
    #### LOG SCRIPT PARAMETERS ####
    for param, value in PARAMS.items():
        LOGGER.debug("opts: %s is %s", param, value)
    ### MIST SESSION ###
    APISESSION = mistapi.APISession(env_file=ENV_FILE)
    APISESSION.login()

    ### START ###
    start(APISESSION, ORG_ID, CSV_FILE)

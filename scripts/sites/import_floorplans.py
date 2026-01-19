"""
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to import multiple Ekahau/iBwave project into Mist Organization.

To automatically assign the APs to the floorplans:
    
    - set the AP name in the project with the AP MAC Address
    If the AP names in the project is matching the MAC Address of AP in the 
    Org inventory, the AP will be automatically assigned to the site and 
    placed on the floorplan. 
    This method only requires the Ekahau/iBwave project files
    
    - use a CSV file to map AP names in the project with AP MAC addresses
    For each project, create a CSV file (example below) to map the AP name
    in the project with the AP MAC address from the Org inventory. This 
    will automatically assign the AP to the site, place it on the floorplan
    and name it with the name used in the project

IMPORTANT: 
Each proect files/CSV files must be named with the name of the site where 
you want to deploy the floorplans.

-------
Requirements:
mistapi: https://pypi.org/project/mistapi/

-------
Usage:
This script requires a parameter to locate folder where the Ekahau/iBwave 
project files are located. Other parameters listed below
are optional. If the optional parameters are not defined, the script will ask 
for the additional required settings.

It is recommended to use an environment file to store the required information
to request the Mist Cloud (see https://pypi.org/project/mistapi/ for more 
information about the available parameters).

-------
CSV Format:
The CSV Header Row "Vendor AP Name, Mist AP MAC Address" must be the first row 
in the line.
Each line must contains 2 columns:
- the name of the AP in the project
- the MAC address of the AP in the Mist Org Inventory

-------
CSV Example:
Vendor AP name,Mist AP Mac
AP01,d4:20:b0:c0:ff:ee

-------
CSV Parameters:


-------
Script Parameters:
-h, --help                  display this help

-o, --org_id=               Set the org_id (only one of the org_id or site_id 
                            can be defined)
-n, --org_name=             Org name where to deploy the floorplans, used to
                            validate the destination org

-f, --folder=               path to the folder where the Ekahau/Ibwave/CSV
                            files are located
                            default: ./floorplans/

--format=                   format of the files to import 
                            values: ekahau, ibwave
                            default: ekahau

--import_all_floorplans=    Include floorplans with unmatched APs
                            values: true, false
                            default: true
--import_height=            Import AP height
                            values: true, false
                            default: true       
import_orientation          Import AP orientation
                            values: true, false
                            default: true                         

-l, --log_file=     define the filepath/filename where to write the logs
                    default is "./script.log"
-e, --env=          define the env file to use (see mistapi env file documentation 
                    here: https://pypi.org/project/mistapi/)
                    default is "~/.mist_env"

-------
Examples:
python3 ./import_floorplans.py -f ./my_project_folder/
python3 ./import_floorplans.py \
        -f ./my_project_folder/ \
        --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 \
        --org_name="My Test Org" \
        --import_all_floorplans=true

"""

#### IMPORTS #####
import sys
import os
import argparse
import logging

MISTAPI_MIN_VERSION = "0.44.1"

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

#####################################################################
#### PARAMETERS #####
LOG_FILE = "./script.log"
ENV_FILE = "~/.mist_env"
FLOORPLANS_FOLDER = "./floorplans/"

#####################################################################
#### LOGS ####
LOGGER = logging.getLogger(__name__)
out = sys.stdout

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
        print()


pb = ProgressBar()


#####################################################################
def _result(errors: list):
    pb.log_title("Result", display_pbar=False)
    print("\033[A\033[A\033[F")
    if not errors:
        CONSOLE.info("All floorplans imported successfully and devices assigned")
    else:
        for error in errors:
            if error.get("level") == "warning":
                CONSOLE.warning(error["message"])
                LOGGER.warning(error["message"])
            else:
                CONSOLE.error(error["message"])
                LOGGER.error(error["message"])
    print()


###############################################################################
# IMPORT


def import_projects(
    apisession: mistapi.APISession,
    org_id: str,
    sites: dict,
    import_format: str = "ekahau",
    import_all_floorplans: bool = True,
    import_height: bool = True,
    import_orientation: bool = True,
) -> list:
    pb.log_title("Starting Import Process", display_pbar=False)
    errors = []
    for site_name in sites:
        csv_file = None
        project_file = None
        message = f"Importing maps for site {site_name}"
        pb.log_message(message)
        site_id = sites[site_name].get("id")
        if sites[site_name].get("project"):
            project_file = os.path.join(
                FLOORPLANS_FOLDER, sites[site_name].get("project")
            )
        if sites[site_name].get("csv"):
            csv_file = os.path.join(FLOORPLANS_FOLDER, sites[site_name].get("csv"))
        if not site_id:
            pb.log_failure(message, inc=True)
            errors.append({"site_name": site_name, "error": "Site ID missing"})
        elif not project_file:
            pb.log_failure(message, inc=True)
            errors.append({"site_name": site_name, "error": "Ekahau File missing"})
        else:
            try:
                json_dict = {
                    "import_all_floorplans": import_all_floorplans,
                    "import_height": import_height,
                    "import_orientation": import_orientation,
                    "vendor_name": import_format,
                    "site_id": site_id,
                }
                resp = mistapi.api.v1.orgs.maps.importOrgMapsFile(
                    apisession,
                    org_id,
                    auto_deviceprofile_assignment=True,
                    csv=csv_file,
                    file=project_file,
                    json=json_dict,
                )
                if resp.status_code == 200:
                    ignored_aps = {}
                    if resp.data:
                        for ap in resp.data.get("aps", []):
                            if ap.get("action") == "ignored":
                                ignored_aps[ap.get("name")] = ap.get("reason")
                        LOGGER.debug(resp.data)
                    if len(ignored_aps) == 0:
                        pb.log_success(message, inc=True)
                    else:
                        for mac, reason in ignored_aps.items():
                            errors.append(
                                {
                                    "level": "warning",
                                    "message": f"site {site_name} - device {mac} not assigned: {reason}",
                                }
                            )
                        pb.log_warning(message, inc=True)
                else:
                    pb.log_failure(message, inc=True)
                    errors.append(
                        {
                            "level": "error",
                            "error": f"site {site_name} - Got HTTP{resp.status_code} from Mist. Please check the script logs.",
                        }
                    )
            except Exception:
                pb.log_failure(message, inc=True)
                errors.append(
                    {
                        "level": "error",
                        "error": f"site {site_name} - Error when importing esx file. Please check the script logs.",
                    }
                )
                LOGGER.error("Exception occurred", exc_info=True)
    return errors


def _retrieve_site_ids(apisession: mistapi.APISession, org_id: str, sites: dict):
    pb.log_title("Retrieving Site IDs", display_pbar=False)

    try:
        message = "Retrieving Site IDs from Mist"
        pb.log_message(message, display_pbar=False)
        resp = mistapi.api.v1.orgs.sites.listOrgSites(apisession, org_id, limit=1000)
        sites_from_mist = mistapi.get_all(apisession, resp)
        pb.log_success(message, display_pbar=False)
        for site_name, _ in sites.items():
            message = f"Site {site_name}"
            pb.log_message(message, display_pbar=False)
            site = [s for s in sites_from_mist if s["name"] == site_name]
            if not site:
                pb.log_failure(
                    f"{message}: Unable to find site in the dest org",
                    display_pbar=False,
                )
            else:
                sites[site_name]["id"] = site[0]["id"]
                pb.log_success(f"{message}: {site[0]['id']}", display_pbar=False)
    except Exception:
        pb.log_failure(message, display_pbar=False)
        sys.exit(0)


###############################################################################
# CHECK EKAHAU/CSV FILES
def _list_files_to_process() -> dict:
    pb.log_title(f"Checking Files in {FLOORPLANS_FOLDER}", display_pbar=False)
    files_in_folder = os.listdir(FLOORPLANS_FOLDER)
    sites_to_process = {}
    for file in files_in_folder:
        message = f"File {file}"
        pb.log_message(message, display_pbar=False)
        if file.endswith(".csv"):
            site_name = file.replace(".csv", "")
            if site_name not in sites_to_process:
                sites_to_process[site_name] = {}
            sites_to_process[site_name]["csv"] = file
            pb.log_success(message, display_pbar=False)
        elif file.endswith(".esx"):
            site_name = file.replace(".esx", "")
            if site_name not in sites_to_process:
                sites_to_process[site_name] = {}
            sites_to_process[site_name]["project"] = file
            pb.log_success(message, display_pbar=False)
        elif file.endswith(".ibwc"):
            site_name = file.replace(".ibwc", "")
            if site_name not in sites_to_process:
                sites_to_process[site_name] = {}
            sites_to_process[site_name]["project"] = file
            pb.log_success(message, display_pbar=False)
        else:
            pb.log_warning(
                f"{message}: not a CSV, ESX or IBWC file. Skipping it",
                display_pbar=False,
            )
    return sites_to_process


###############################################################################
# ORG SELECTION
def _check_org_name_in_script_param(
    apisession: mistapi.APISession, org_id: str, org_name: str = ","
) -> bool:
    response = mistapi.api.v1.orgs.orgs.getOrg(apisession, org_id)
    if response.status_code != 200:
        CONSOLE.critical(f"Unable to retrieve the org information: {response.data}")
        sys.exit(3)
    org_name_from_mist = response.data["name"]
    return org_name == org_name_from_mist


def _check_org_name(
    apisession: mistapi.APISession,
    org_id: str,
    org_name: str = "",
) -> tuple[str, str]:
    if not org_name:
        org_name = mistapi.api.v1.orgs.orgs.getOrg(apisession, org_id).data["name"]
    while True:
        print()
        resp = input(
            "To avoid any error, please confirm the current destination organization name: "
        )
        if resp == org_name:
            return org_id, org_name
        else:
            print()
            print("The organization names do not match... Please try again...")


def _select_dest_org(apisession: mistapi.APISession) -> tuple[str, str]:
    print()
    print(" Destination Org ".center(80, "-"))
    print()
    org_id = mistapi.cli.select_org(apisession)[0]
    org_name = mistapi.api.v1.orgs.orgs.getOrg(apisession, org_id).data["name"]
    return _check_org_name(apisession, org_id, org_name)


def start(
    apisession: mistapi.APISession,
    org_id: str = "",
    org_name: str = "",
    import_format: str = "ekahau",
    import_all_floorplans: bool = True,
    import_height: bool = True,
    import_orientation: bool = True,
) -> None:
    """
    Main function to start the import process

    :param apisession: Mist APISession object
    :param org_id: Org ID where to import the floorplans
    :param org_name: Org name where to import the floorplans
    :param import_format: Format of the files to import (ekahau or ibwave)
    :param import_all_floorplans: Include floorplans with unmatched APs
    :param import_height: Import AP height
    :param import_orientation: Import AP orientation
    :return: None
    """
    if org_id and org_name:
        if not _check_org_name_in_script_param(apisession, org_id, org_name):
            CONSOLE.critical(f"Org name {org_name} does not match the org {org_id}")
            sys.exit(0)
    elif org_id and not org_name:
        org_id, org_name = _check_org_name(apisession, org_id)
    elif not org_id and not org_name:
        org_id, org_name = _select_dest_org(apisession)
    else:
        usage()
        sys.exit(0)

    global FLOORPLANS_FOLDER
    if not FLOORPLANS_FOLDER.endswith("/"):
        FLOORPLANS_FOLDER += "/"

    sites = _list_files_to_process()
    pb.set_steps_total(len(sites))

    _retrieve_site_ids(apisession, org_id, sites)

    errors = import_projects(
        apisession,
        org_id,
        sites,
        import_format,
        import_all_floorplans,
        import_height,
        import_orientation,
    )
    _result(errors)
    pb.log_title("Site Import Done", end=True)


###############################################################################
# USAGE
def usage(message: str | None = None):
    print(
        """
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to import multiple Ekahau/iBwave project into Mist Organization.

To automatically assign the APs to the floorplans:
    
    - set the AP name in the project with the AP MAC Address
    If the AP names in the project is matching the MAC Address of AP in the 
    Org inventory, the AP will be automatically assigned to the site and 
    placed on the floorplan. 
    This method only requires the Ekahau/iBwave project files
    
    - use a CSV file to map AP names in the project with AP MAC addresses
    For each project, create a CSV file (example below) to map the AP name
    in the project with the AP MAC address from the Org inventory. This 
    will automatically assign the AP to the site, place it on the floorplan
    and name it with the name used in the project

IMPORTANT: 
Each project files/CSV files must be named with the name of the site where 
you want to deploy the floorplans.

-------
Requirements:
mistapi: https://pypi.org/project/mistapi/

-------
Usage:
This script requires a parameter to locate folder where the Ekahau/iBwave 
project files are located. Other parameters listed below
are optional. If the optional parameters are not defined, the script will ask 
for the additional required settings.

It is recommended to use an environment file to store the required information
to request the Mist Cloud (see https://pypi.org/project/mistapi/ for more 
information about the available parameters).

-------
CSV Format:
The CSV Header Row "Vendor AP Name, Mist AP MAC Address" must be the first row 
in the line.
Each line must contains 2 columns:
- the name of the AP in the project
- the MAC address of the AP in the Mist Org Inventory

-------
CSV Example:
Vendor AP name,Mist AP Mac
AP01,d4:20:b0:c0:ff:ee

-------
CSV Parameters:


-------
Script Parameters:
-h, --help                  display this help

-o, --org_id=               Set the org_id (only one of the org_id or site_id 
                            can be defined)
-n, --org_name=             Org name where to deploy the floorplans, used to
                            validate the destination org

-f, --folder=               path to the folder where the Ekahau/Ibwave/CSV
                            files are located
                            default: ./floorplans/

--format=                   format of the files to import 
                            values: ekahau, ibwave
                            default: ekahau

--import_all_floorplans=    Include floorplans with unmatched APs
                            values: true, false
                            default: true
--import_height=            Import AP height
                            values: true, false
                            default: true       
import_orientation          Import AP orientation
                            values: true, false
                            default: true                         

-l, --log_file=     define the filepath/filename where to write the logs
                    default is "./script.log"
-e, --env=          define the env file to use (see mistapi env file documentation 
                    here: https://pypi.org/project/mistapi/)
                    default is "~/.mist_env"

-------
Examples:
python3 ./import_floorplans.py -f ./my_project_folder/
python3 ./import_floorplans.py \\
        -f ./my_project_folder/ \\
        --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 \\
        --org_name="My Test Org" \\
        --import_all_floorplans=true

"""
    )
    if message:
        CONSOLE.error(message)
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
        description="Import multiple Ekahau/iBwave project into Mist Organization.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Examples:
python3 ./import_floorplans.py -f ./my_project_folder/
python3 ./import_floorplans.py \\
        -f ./my_project_folder/ \\
        --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 \\
        --org_name="My Test Org" \\
        --import_all_floorplans=true
""",
        add_help=False,
    )
    parser.add_argument("-h", "--help", action="store_true", help="display this help")
    parser.add_argument(
        "-o",
        "--org_id",
        type=str,
        help="Set the org_id (only one of the org_id or site_id can be defined)",
    )
    parser.add_argument(
        "-n",
        "--org_name",
        type=str,
        help="Org name where to deploy the floorplans, used to validate the destination org",
    )
    parser.add_argument(
        "-f",
        "--folder",
        type=str,
        help="path to the folder where the Ekahau/Ibwave/CSV files are located",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["ekahau", "ibwave"],
        help="format of the files to import (ekahau or ibwave)",
    )
    parser.add_argument(
        "--import_all_floorplans",
        type=str,
        choices=["true", "false"],
        help="Include floorplans with unmatched APs (true or false, default false)",
    )
    parser.add_argument(
        "--import_height",
        type=str,
        choices=["true", "false"],
        help="Import AP height (true or false, default true)",
    )
    parser.add_argument(
        "--import_orientation",
        type=str,
        choices=["true", "false"],
        help="Import AP orientation (true or false, default true)",
    )
    parser.add_argument(
        "-e",
        "--env",
        type=str,
        help="define the env file to use (see mistapi env file documentation here: https://pypi.org/project/mistapi/)",
    )
    parser.add_argument(
        "-l",
        "--log_file",
        type=str,
        help="define the filepath/filename where to write the logs",
    )

    args = parser.parse_args()

    if args.help:
        usage()

    ORG_ID = args.org_id if args.org_id else ""
    ORG_NAME = args.org_name if args.org_name else ""
    FLOORPLANS_FOLDER = args.folder if args.folder else FLOORPLANS_FOLDER
    IMPORT_FORMAT = args.format if args.format else "ekahau"
    IMPORT_ALL_FLOORPLANS = False if args.import_all_floorplans == "false" else True
    IMPORT_HEIGHT = False if args.import_height == "false" else True
    IMPORT_ORIENTATION = False if args.import_orientation == "false" else True
    ENV_FILE = args.env if args.env else ENV_FILE
    LOG_FILE = args.log_file if args.log_file else LOG_FILE

    #### LOGS ####
    logging.basicConfig(filename=LOG_FILE, filemode="w")
    LOGGER.setLevel(logging.DEBUG)
    check_mistapi_version()
    ### MIST SESSION ###
    APISESSION = mistapi.APISession(env_file=ENV_FILE)
    APISESSION.login()

    ### START ###
    start(
        APISESSION,
        ORG_ID,
        ORG_NAME,
        IMPORT_FORMAT,
        IMPORT_ALL_FLOORPLANS,
        IMPORT_HEIGHT,
        IMPORT_ORIENTATION,
    )

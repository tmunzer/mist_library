"""
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to import multiple Ekahau/iBwave project into Mist Organisation.

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
This script requires a parameter to locate foldar where the Ekahau/iBwave 
project files are located. Other parameters listed below
are optional. If the optional parameters are not defined, the script will ask 
for the additional required settings.

It is recomended to use an environment file to store the required information
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
import getopt
import logging

MISTAPI_MIN_VERSION = "0.44.1"

try:
    import mistapi
    from mistapi.__logger import console
except:
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
log_file = "./script.log"
env_file = "~/.mist_env"
floorplans_folder = "./floorplans/"

#####################################################################
#### LOGS ####
logger = logging.getLogger(__name__)
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
        logger.info(f"{message}: Success")
        self._pb_new_step(
            message, "\033[92m\u2714\033[0m\n", inc=inc, display_pbar=display_pbar
        )

    def log_warning(self, message, inc: bool = False, display_pbar: bool = True):
        logger.warning(f"{message}: Warning")
        self._pb_new_step(
            message, "\033[93m\u2B58\033[0m\n", inc=inc, display_pbar=display_pbar
        )

    def log_failure(self, message, inc: bool = False, display_pbar: bool = True):
        logger.error(f"{message}: Failure")
        self._pb_new_step(
            message, "\033[31m\u2716\033[0m\n", inc=inc, display_pbar=display_pbar
        )

    def log_title(self, message, end: bool = False, display_pbar: bool = True):
        logger.info(message)
        self._pb_title(message, end=end, display_pbar=display_pbar)
        print()


pb = ProgressBar()

#####################################################################
def _result(errors:list):
    pb.log_title("Result", display_pbar=False)    
    print("\033[A\033[A\033[F")
    if not errors:
        console.info("All floorplans imported succesfully and devices assigned")
    else:
        for error in errors:
            if error.get("level") == "warning":
                console.warning(error['message'])
                logger.warning(error['message'])
            else:
                console.error(error["message"])
                logger.error(error["message"])
    print()

###############################################################################
# IMPORT

def import_projects(apisession: mistapi.APISession, org_id: str, sites: dict, format:str="ekahau", import_all_floorplans:bool=True, import_height:bool=True, import_orientation:bool=True) -> list:
    pb.log_title("Starting Import Process", display_pbar=False)
    errors = []
    for site_name in sites:
        csv_file = None
        project_file = None
        message = f"Importing maps for site {site_name}"
        pb.log_message(message)
        site_id = sites[site_name].get("id")
        if sites[site_name].get("project"):
            project_file = os.path.join(floorplans_folder, sites[site_name].get("project"))
        if sites[site_name].get("csv"):
            csv_file = os.path.join(floorplans_folder, sites[site_name].get("csv"))
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
                        "import_orientation":import_orientation,
                        "vendor_name": format,
                        "site_id": site_id
                }
                resp = mistapi.api.v1.orgs.maps.importOrgMapsFile(
                    apisession,
                    org_id,
                    auto_deviceprofile_assignment=True,
                    csv=csv_file,
                    file=  project_file,
                    json=json_dict,
                )
                if resp.status_code == 200:
                    ignored_aps = {}
                    if resp.data:
                        for ap in resp.data.get("aps", []):
                            if ap.get("action") == "ignored":
                                ignored_aps[ap.get("name")] = ap.get("reason")
                        logger.debug(resp.data)
                    if len(ignored_aps) == 0:
                        pb.log_success(message, inc=True)
                    else:
                        for mac in ignored_aps:
                            errors.append({
                                "level": "warning",
                                "message": f"site {site_name} - device {mac} not assigned: {ignored_aps[mac]}"
                            })
                        pb.log_warning(message, inc=True)
                else:
                    pb.log_failure(message, inc=True)
                    errors.append(
                        {
                            "level": "error",
                            "error": f"site {site_name} - Got HTTP{resp.status_code} from Mist. Please check the script logs.",
                        }
                    )
            except:
                pb.log_failure(message, inc=True)
                errors.append(
                    {
                        "level": "error",
                        "error": f"site {site_name} - Error when importing esx file. Please check the script logs.",
                    }
                )
                logger.error("Exception occurred", exc_info=True)
    return errors


def _retrieve_site_ids(apisession: mistapi.APISession, org_id: str, sites: list):
    pb.log_title(f"Retrieving Site IDs", display_pbar=False)

    try:
        message = "Retrieving Site IDs from Mist"
        pb.log_message(message, display_pbar=False)
        resp = mistapi.api.v1.orgs.sites.listOrgSites(apisession, org_id, limit=1000)
        sites_from_mist = mistapi.get_all(apisession, resp)
        pb.log_success(message, display_pbar=False)
        for site_name in sites:
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
    except:
        pb.log_failure(message, display_pbar=False)
        sys.exit(0)


###############################################################################
# CHECK EKAHAU/CSV FILES
def _list_files_to_process() -> dict:
    pb.log_title(f"Checking Files in {floorplans_folder}", display_pbar=False)
    files_in_folder = os.listdir(floorplans_folder)
    sites_to_process = {}
    for file in files_in_folder:
        message = f"File {file}"
        pb.log_message(message, display_pbar=False)
        if file.endswith(".csv"):
            site_name = file.replace(".csv", "")
            if not site_name in sites_to_process:
                sites_to_process[site_name] = {}
            sites_to_process[site_name]["csv"] = file
            pb.log_success(message, display_pbar=False)
        elif file.endswith(".esx"):
            site_name = file.replace(".esx", "")
            if not site_name in sites_to_process:
                sites_to_process[site_name] = {}
            sites_to_process[site_name]["project"] = file
            pb.log_success(message, display_pbar=False)
        elif file.endswith(".ibwc"):
            site_name = file.replace(".ibwc", "")
            if not site_name in sites_to_process:
                sites_to_process[site_name] = {}
            sites_to_process[site_name]["project"] = file
            pb.log_success(message, display_pbar=False)
        else:
            pb.log_warning(
                f"{message}: not a CSV, ESX or IBWC file. Skipping it", display_pbar=False
            )
    return sites_to_process


###############################################################################
# ORG SELECTION
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
            return org_id, org_name
        else:
            print()
            print("The orgnization names do not match... Please try again...")


def _select_dest_org(apisession: mistapi.APISession):
    print()
    print(" Destination Org ".center(80, "-"))
    print()
    org_id = mistapi.cli.select_org(apisession)[0]
    org_name = mistapi.api.v1.orgs.orgs.getOrg(apisession, org_id).data["name"]
    if _check_org_name(apisession, org_id, org_name):
        return org_id, org_name


def start(apisession: mistapi.APISession, org_id: str = None, org_name: str = None, format:str="ekahau", import_all_floorplans:bool=True, import_height:bool=True, import_orientation:bool=True):
    if org_id and org_name:
        if not _check_org_name_in_script_param(apisession, org_id, org_name):
            console.critical(f"Org name {org_name} does not match the org {org_id}")
            sys.exit(0)
    elif org_id and not org_name:
        org_id, org_name = _check_org_name(apisession, org_id)
    elif not org_id and not org_name:
        org_id, org_name = _select_dest_org(apisession)
    else:
        usage()
        sys.exit(0)

    global floorplans_folder
    if not floorplans_folder.endswith("/"):
        floorplans_folder += "/"

    sites = _list_files_to_process()
    pb.set_steps_total(len(sites))

    _retrieve_site_ids(apisession, org_id, sites)

    errors = import_projects(apisession, org_id, sites, format, import_all_floorplans, import_height, import_orientation)
    _result(errors)
    pb.log_title("Site Import Done", end=True)


###############################################################################
# USAGE
def usage():
    print(
"""
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to import multiple Ekahau/iBwave project into Mist Organisation.

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
This script requires a parameter to locate foldar where the Ekahau/iBwave 
project files are located. Other parameters listed below
are optional. If the optional parameters are not defined, the script will ask 
for the additional required settings.

It is recomended to use an environment file to store the required information
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
    sys.exit(0)

def check_mistapi_version():
    if mistapi.__version__ < MISTAPI_MIN_VERSION:
        logger.critical(f"\"mistapi\" package version {MISTAPI_MIN_VERSION} is required, you are currently using version {mistapi.__version__}.")
        logger.critical(f"Please use the pip command to updated it.")
        logger.critical("")
        logger.critical(f"    # Linux/macOS")
        logger.critical(f"    python3 -m pip install --upgrade mistapi")
        logger.critical("")
        logger.critical(f"    # Windows")
        logger.critical(f"    py -m pip install --upgrade mistapi")
        print(f"""
    Critical: 
    \"mistapi\" package version {MISTAPI_MIN_VERSION} is required, you are currently using version {mistapi.__version__}. 
    Please use the pip command to updated it.

    # Linux/macOS
    python3 -m pip install --upgrade mistapi

    # Windows
    py -m pip install --upgrade mistapi
        """)
        sys.exit(2)
    else: 
        logger.info(f"\"mistapi\" package version {MISTAPI_MIN_VERSION} is required, you are currently using version {mistapi.__version__}.")


###############################################################################
# ENTRY POINT
if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(
            sys.argv[1:],
            "ho:n:f:e:l:",
            [
                "help",
                "org_id=",
                "--org_name=",
                "google_api_key=",
                "folder=",
                "env=",
                "log_file=",
                "format=",
                "import_all_floorplans=",
                "import_height=",
                "import_orientation=",
            ],
        )
    except getopt.GetoptError as err:
        console.error(err)
        usage()

    org_id = None
    org_name = None
    format = None
    import_all_floorplans = None
    import_height = None
    import_orientation = None
    for o, a in opts:
        if o in ["-h", "--help"]:
            usage()
        elif o in ["-o", "--org_id"]:
            org_id = a
        elif o in ["-n", "--org_name"]:
            org_name = a
        elif o in ["-f", "--folder"]:
            floorplans_folder = a
        elif o == "--format":
            if a in ["ekahau", "ibwave"]:
                format = a
            else:
                console.error("invalid --format value. Only \"ekahau\" or \"ibwave\" are supported...")
        elif o == "--import_all_floorplans":
            if a.lower() == "true":
                import_all_floorplans = True
            elif a.lower() == "false":
                import_all_floorplans = False
            else:
                console.error("invalid --import_all_floorplans value. Only \"true\" or \"false\" are supported...")
        elif o == "--import_height":
            if a.lower() == "true":
                import_height = True
            elif a.lower() == "false":
                import_height = False
            else:
                console.error("invalid --import_height value. Only \"true\" or \"false\" are supported...")
        elif o == "--import_orientation":
            if a.lower() == "true":
                import_orientation = True
            elif a.lower() == "false":
                import_orientation = False
            else:
                console.error("invalid --import_orientation value. Only \"true\" or \"false\" are supported...")
        elif o in ["-e", "--env"]:
            env_file = a
        elif o in ["-l", "--log_file"]:
            log_file = a
        else:
            assert False, "unhandled option"

    #### LOGS ####
    logging.basicConfig(filename=log_file, filemode="w")
    logger.setLevel(logging.DEBUG)
    check_mistapi_version()
    ### MIST SESSION ###
    apisession = mistapi.APISession(env_file=env_file)
    apisession.login()

    ### START ###
    start(apisession, org_id, org_name)

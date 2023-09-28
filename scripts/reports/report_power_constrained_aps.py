"""
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to list APs with power contraints (with limited power supply).
The result is displayed on the console and saved in a CSV file.

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
Script Parameters:
-h, --help              display this help
-o, --org_id=           Set the org_id
-c, --csv_file=         Path to the CSV file where to save the output
                        default is "./validate_site_variables.csv"
-l, --log_file=         define the filepath/filename where to write the logs
                        default is "./script.log"
-e, --env=              define the env file to use (see mistapi env file 
                        documentation here: https://pypi.org/project/mistapi/)
                        default is "~/.mist_env"

-------
Examples:
python3 ./report_power_constrained_aps.py     
python3 ./report_power_constrained_aps.py --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 

"""

#### IMPORTS ####
import sys
import csv
import os
import logging
import getopt

MISTAPI_MIN_VERSION = "0.45.1"

try:
    import mistapi
    from mistapi.__api_response import APIResponse
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


#### PARAMETERS #####

LOG_FILE = "./script.log"
ENV_FILE = os.path.join(os.path.expanduser('~'), ".mist_env")
OUT_FILE_PATH="./report_power_constrained_aps.csv"

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
        print(f" {text} ".center(size, "-"), "\n")
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

    def log_warning(self, message, inc:bool=False, display_pbar:bool=True):
        LOGGER.warning(f"{message}")
        self._pb_new_step(message, "\033[93m\u2B58\033[0m\n", inc=inc, display_pbar=display_pbar)

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
def _process_data(sites:list, csv_file:str) -> None:
    '''
    function to process the sites, display the result and save it into a 
    CSV file

    PARAMS
    -------
    sites : list
        list of sites. Each site has the generic site info plus the list 
        of devices in `site["devices"]`

    csv_file : str
        path to the CSV file used to save the results

    '''
    header = [
        "#org_id",
        "site_name", 
        "site_id", 
        "device_name", 
        "device_id",
        "model", 
        "power_constrained",
        "power_budget",
        "power_src",
        "system_name", 
        #"system_desc",
        "port_desc", 
        "port_id", 
        "lldp_med_supported",
        "power_request_count",
        "power_allocated",
        "power_requested",
        "power_draw"
        ]
    result = []
    for site in sites:
        org_id = site["org_id"]
        site_name = site["name"]
        site_id = site["id"]
        for device in site.get("devices", []):
            if device.get("power_constrained"):
                data=[
                    org_id,
                    site_name,
                    site_id,
                    device.get("name"),
                    device.get("id"),
                    device.get("model"),
                    device.get("power_constrained"),
                    device.get("power_budget"),
                    device.get("power_src"),
                    device.get("lldp_stat", {}).get("system_name"),
                    #device.get("lldp_stat", {}).get("system_desc"),
                    device.get("lldp_stat", {}).get("port_desc"),
                    device.get("lldp_stat", {}).get("port_id"),
                    device.get("lldp_stat", {}).get("lldp_med_supported"),
                    device.get("lldp_stat", {}).get("power_request_count"),
                    device.get("lldp_stat", {}).get("power_allocated"),
                    device.get("lldp_stat", {}).get("power_requested"),
                    device.get("lldp_stat", {}).get("power_draw")
                ]
                LOGGER.debug(data)
                result.append(data)
    mistapi.cli.pretty_print(result, header)

    if csv_file:
        result.insert(0, header)
        with open(csv_file, 'w') as f:
            writer = csv.writer(f)
            writer.writerows(result)

def _get_org_devices(apisession: mistapi.APISession, org_id: str) -> list:
    '''
    function to retrieve the devices stats from the org.

    PARAMS
    -------
    apisession : mistapi.APISession
        mistapi session with access the source or the Site, already logged in
    org_id : str
        org_id to use

    RETURN
    -----------
    list
        list of devices stats from the site
    '''
    message = f"Retrieving devices stats"
    try:
        PB.log_message(message, display_pbar=False)
        response = mistapi.api.v1.orgs.stats.listOrgDevicesStats(apisession, org_id, limit=1000, type="ap", fields="power_constrained,power_budget,power_src,lldp_stat")
        devices = mistapi.get_all(apisession, response)
        PB.log_success(message, display_pbar=False)
        return devices
    except Exception as error:
        PB.log_failure(message, display_pbar=False)
        LOGGER.error("Unable to retrieve the list of devices stats from the Org")
        LOGGER.error("Exception occurred", exc_info=True)
        return []

def _get_sites(apisession: mistapi.APISession, org_id:str) -> list:
    '''
    function to retrieve the list of sites from the org.

    PARAMS
    -------
    apisession : mistapi.APISession
        mistapi session with access the source or the Site, already logged in
    org_id : str
        org_id to use

    RETURN
    -----------
    list
        list sites
    '''
    message = f"Retrieving list of sites"
    try:
        PB.log_message(message, display_pbar=False)
        response = mistapi.api.v1.orgs.sites.listOrgSites(apisession, org_id, limit=1000)
        sites = mistapi.get_all(apisession, response)
        PB.log_success(message, display_pbar=False)
        return sites
    except Exception as error:
        PB.log_failure(message, display_pbar=False)
        LOGGER.error("Unable to retrieve the list of sites")
        LOGGER.error("Exception occurred", exc_info=True)
        return []


def start(apisession: mistapi.APISession,  org_id:str, csv_file:str=None) -> list:
    '''
    Start the process to clone the src org to the dst org

    PARAMS
    -------
    apisession : mistapi.APISession
        mistapi session with access the source or the Site, already logged in
    org_id : str
        org_id, depending on the `scope` value
    csv_file : str
        Optional, place where to save the result (csv format)

    RETURN
    -----------
    list
        list of sites. Each site has the generic site info plus the list 
        of devices in `site["devices"]`
    '''

    PB.log_title("Preparation steps", display_pbar=False)
    devices = []
    sites = _get_sites(apisession, org_id)
    devices = _get_org_devices(apisession, org_id)
    for site in sites:
        site_devices = [d for d in devices if d.get("site_id") == site["id"]]
        site["devices"] = site_devices

    PB.log_title("Result", display_pbar=False)
    _process_data(sites, csv_file)

    return sites

###############################################################################
#### USAGE ####

def usage():
    """
    print script usage and exit
    """
    print("""
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to list APs with power contraints (with limited power supply).
The result is displayed on the console and saved in a CSV file.

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
Script Parameters:
-h, --help              display this help
-o, --org_id=           Set the org_id
-c, --csv_file=         Path to the CSV file where to save the output
                        default is "./validate_site_variables.csv"
-l, --log_file=         define the filepath/filename where to write the logs
                        default is "./script.log"
-e, --env=              define the env file to use (see mistapi env file 
                        documentation here: https://pypi.org/project/mistapi/)
                        default is "~/.mist_env"

-------
Examples:
python3 ./report_power_constrained_aps.py     
python3 ./report_power_constrained_aps.py --org_id=203d3d02-xxxx-xxxx-xxxx-76896a3330f4 

""")
    sys.exit(0)

def check_mistapi_version():
    '''
    Check the mistapi package version in use, and compare it to MISTAPI_MIN_VERSION
    '''
    if mistapi.__version__ < MISTAPI_MIN_VERSION:
        LOGGER.critical(f"\"mistapi\" package version {MISTAPI_MIN_VERSION} is required, you are currently using version {mistapi.__version__}.")
        LOGGER.critical(f"Please use the pip command to updated it.")
        LOGGER.critical("")
        LOGGER.critical(f"    # Linux/macOS")
        LOGGER.critical(f"    python3 -m pip install --upgrade mistapi")
        LOGGER.critical("")
        LOGGER.critical(f"    # Windows")
        LOGGER.critical(f"    py -m pip install --upgrade mistapi")
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
        LOGGER.info(f"\"mistapi\" package version {MISTAPI_MIN_VERSION} is required, you are currently using version {mistapi.__version__}.")

#####################################################################
#### SCRIPT ENTRYPOINT ####
if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(sys.argv[1:], "ho:f:e:l:", [
            "help", 
            "org_id=", 
            "file=",
            "env=", 
            "log_file="
            ])
    except getopt.GetoptError as err:
        console.error(err)
        usage()

    ORG_ID=None
    CSF_FILE=OUT_FILE_PATH
    for o, a in opts: # type: ignore
        if o in ["-h", "--help"]:
            usage()
        elif o in ["-o", "--org_id"]:
            ORG_ID = a
        elif o in ["-f", "--file"]:
            CSF_FILE = a
        elif o in ["-e", "--env"]:
            ENV_FILE=a
        elif o in ["-l", "--log_file"]:
            LOG_FILE = a
        else:
            assert False, "unhandled option"

    #### LOGS ####
    logging.basicConfig(filename=LOG_FILE, filemode='w')
    LOGGER.setLevel(logging.DEBUG)
    check_mistapi_version()
    ### START ###
    apisession = mistapi.APISession(env_file=ENV_FILE)
    apisession.login()
    if not ORG_ID:
        ORG_ID = mistapi.cli.select_org(apisession)[0]
    start(apisession, ORG_ID, CSF_FILE)

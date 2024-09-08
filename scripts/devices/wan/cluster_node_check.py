"""
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to retrieve the role of each Gateway Cluster nodes accross a 
whole Organization.

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

-o, --org_id=           Mist Org ID 
-c, --csv_file=         output file (csv)
                        default: ./cluster_node_check.csv
-d, --datetime          append the current date and time (ISO format) to the
                        backup name 
-t, --timestamp         append the timestamp at the end of the report and summary files

-l, --log_file=         define the filepath/filename where to write the logs
                        default is "./script.log"
-e, --env=              define the env file to use (see mistapi env file 
                        documentation here: https://pypi.org/project/mistapi/)
                        default is "~/.mist_env"

-------
Examples:
python3 ./cluster_node_check.py     
python3 ./cluster_node_check.py -o 203d3d02-xxxx-xxxx-xxxx-76896a3330f4
"""

#####################################################################
#### IMPORTS ####
import logging
import sys
import getopt
import datetime
import tabulate

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
CSV_FILE = "./cluster_node_check.csv"

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


def get_device_stats(
    apisession: mistapi.APISession,
    org_id: str
):
    message = "retrieving gateway stats"
    PB.log_message(message, display_pbar=False)
    try:
        resp = mistapi.api.v1.orgs.stats.listOrgDevicesStats(apisession, org_id, "gateway", fields="*")
        if resp.status_code == 200:
            data = mistapi.get_all(apisession, resp)
            PB.log_success(message, inc=False, display_pbar=False)
            return data
        else:
            PB.log_failure(message, inc=False, display_pbar=False)
            sys.exit(1)
    except:
        PB.log_failure(message, inc=False, display_pbar=False)
        LOGGER.error("Exception occurred", exc_info=True)
        sys.exit(1)
        

def process_device_stats(data: list):
    message = f"processing {len(data)} gateways"
    PB.log_message(message, display_pbar=False)
    clusters = []
    for device in data:
        if device.get("is_ha"):
            cluster_mac = device.get("id").split("-")[4]
            cluster_device_id = device.get("id")
            cluster_hostname = device.get("hostname")
            cluster_site_id = device.get("site_id")            
            node0_mac =  device.get("module_stat", {})[0].get("mac")
            node0_role = device.get("module_stat", {})[0].get("vc_role")
            node1_mac =  device.get("module2_stat", {})[0].get("mac")
            node1_role = device.get("module2_stat", {})[0].get("vc_role")
            if cluster_mac == node0_mac:
                clusters.append({
                    "site_id": cluster_site_id,
                    "hostname": cluster_hostname,
                    "device_id": cluster_device_id,
                    "node0_mac":node0_mac,
                    "node0_role":node0_role,
                    "node1_mac":node1_mac,
                    "node1_role":node1_role,
                })
            else:
                clusters.append({
                    "site_id": cluster_site_id,
                    "hostname": cluster_hostname,
                    "device_id": cluster_device_id,
                    "node0_mac":node1_mac,
                    "node0_role":node1_role,
                    "node1_mac":node0_mac,
                    "node1_role":node0_role,
                })
    PB.log_success(message, inc=False, display_pbar=False)
    return clusters

def save_result(clusters: list, csv_file: str, append_dt:bool, append_ts:bool):
    message=f"saving result to {csv_file}"
    PB.log_message(message, display_pbar=False)
    try:
        if append_dt:
            dt = datetime.datetime.isoformat(datetime.datetime.now()).split('.')[0].replace(':','.')
            csv_file = f"{csv_file.replace('.csv', f'_{dt}')}.csv"
        elif append_ts:
            ts = round(datetime.datetime.timestamp(datetime.datetime.now()))
            csv_file = f"{csv_file.replace('.csv', f'_{ts}')}.csv"
        with open(csv_file, "w") as f:
            f.write("site_id,hostname,device_id,node0_mac,node0_role,node1_mac,node1_role\n")
            for c in clusters:
                f.write(f"{c.get('site_id')},{c.get('hostname')},{c.get('device_id')},{c.get('node0_mac')},{c.get('node0_role')},{c.get('node1_mac')},{c.get('node1_role')}\n")
        PB.log_success(message, inc=False, display_pbar=False)
    except:
        PB.log_failure(message, inc=False, display_pbar=False)
        LOGGER.error("Exception occurred", exc_info=True)


def start(
    apisession: mistapi.APISession, org_id: str, csv_file: str="./cluster_node_check.csv", append_dt:bool=False, append_ts:bool=False):
    """
    Start the process to rename the devices

    PARAMS
    -------
    apisession : mistapi.APISession
        mistapi session, already logged in
    org_id : str
    csv_file : str, defailt: ./cluster_node_check.csv
        output file (csv)
    append_dt : bool
        append the current date and time (ISO format) to the backup name 
    append_ts : bool
        append the timestamp at the end of the report and summary files
    """
    LOGGER.debug("start")
    LOGGER.debug(f"start:parameter:org_id:{org_id}")
    print()
    print()

    if not org_id:
        org_id = mistapi.cli.select_org(apisession)[0]
    if not csv_file:
        csv_file = CSV_FILE

    data = get_device_stats(apisession, org_id)
    clusters = process_device_stats(data)
    save_result(clusters, csv_file, append_dt, append_ts)

    print(tabulate.tabulate(clusters, headers={
        "site_id":"site_id",
        "hostname":"hostname",
        "device_id":"device_id",
        "node0_mac":"node0_mac",
        "node0_role":"node0_role",
        "node1_mac":"node1_mac",
        "node1_role":"node1_role"
        }))
    print()
    print(f"{len(clusters)} clusters detected accrosse the whole organization ({len(data)} gateways)")
    print(f"results saved to {csv_file}")


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
Python script to retrieve the role of each Gateway Cluster nodes accross a 
whole Organization.

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

-o, --org_id=           Mist Org ID 
-c, --csv_file=         output file (csv)
                        default: ./cluster_node_check.csv
-d, --datetime          append the current date and time (ISO format) to the
                        backup name 
-t, --timestamp         append the timestamp at the end of the report and summary files

-l, --log_file=         define the filepath/filename where to write the logs
                        default is "./script.log"
-e, --env=              define the env file to use (see mistapi env file 
                        documentation here: https://pypi.org/project/mistapi/)
                        default is "~/.mist_env"

-------
Examples:
python3 ./cluster_node_check.py     
python3 ./cluster_node_check.py -o 203d3d02-xxxx-xxxx-xxxx-76896a3330f4
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
            "ho:c:e:l:dt",
            ["help", "org_id=", "csv_file=", "env=", "log_file=","timestamp","datetime"],
        )
    except getopt.GetoptError as err:
        console.error(err)
        usage()

    ORG_ID = None
    APPEND_DT = False
    APPEND_TS = False

    for o, a in opts:
        if o in ["-h", "--help"]:
            usage()
        elif o in ["-o", "--org_id"]:
            ORG_ID = a
        elif o in ["-c", "--csv_file"]:
            CSV_FILE = a
        elif o in ["-d", "--datetime"]:
            if APPEND_TS:
                usage("Inavlid Parameters: \"-d\"/\"--date\" and \"-t\"/\"--timestamp\" are exclusive")
            else:
                APPEND_DT = True
        elif o in ["-t", "--timestamp"]:
            if APPEND_DT:
                usage("Inavlid Parameters: \"-d\"/\"--date\" and \"-t\"/\"--timestamp\" are exclusive")
            else:
                APPEND_TS = True
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
    APISESSION = mistapi.APISession(env_file=ENV_FILE, show_cli_notif=False)
    APISESSION.login()
    start(APISESSION, ORG_ID, CSV_FILE, APPEND_DT, APPEND_TS)

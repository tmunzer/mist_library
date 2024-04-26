"""
-------------------------------------------------------------------------------

    Written by Thomas Munzer (tmunzer@juniper.net)
    Github repository: https://github.com/tmunzer/Mist_library/

    This script is licensed under the MIT License.

-------------------------------------------------------------------------------
Python script to retrieve VPN Peers statistics for gateways assigned to a site

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

-o, --org_id=           Mist Org ID where the devices are claimed to
-s, --site_id=          Mist Site ID where the devices are claimed to
-d, --duration=         Duration (default: 1w)

-l, --log_file=         define the filepath/filename where to write the logs
                        default is "./script.log"
-e, --env=              define the env file to use (see mistapi env file 
                        documentation here: https://pypi.org/project/mistapi/)
                        default is "~/.mist_env"

-------
Examples:
python3 ./rename_devices.py     
python3 ./rename_devices.py -o 203d3d02-xxxx-xxxx-xxxx-76896a3330f4 -s 03d3d02-xxxx-xxxx-xxxx-76896a3330f4

"""

#####################################################################
#### IMPORTS ####
import logging
import sys
import getopt
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
CSV_FILE = "./rename_devices.csv"

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


def get_vpn_peer_metrics(
    apisession: mistapi.APISession,
    site_id: str,
    device_mac: str,
    node_id: str,
    peer_mac: str,
    port_id: str,
    peer_port_id: str,
    duration: str,
):
    try:
        url = f"/api/v1/sites/{site_id}/insights/device/{device_mac}/vpn_peer-metrics"
        query_params = {
            "node": node_id,
            "interval": 600,
            "peer_mac": peer_mac,
            "port_id": port_id,
            "peer_port_id": peer_port_id,
            "duration": duration,
        }
        res = apisession.mist_get(url, query_params)
        return res.data
    except:
        print("error")


def get_vpn_peer_peak(
    apisession: mistapi.APISession,
    site_id: str,
    device_mac: str,
    node_id: str,
    peer_mac: str,
    port_id: str,
    peer_port_id: str,
    duration: str,
):

    max_latency = 0
    max_latency_datetime = -1
    max_jitter = 0
    max_jitter_datetime = -1
    max_loss = 0
    max_loss_datetime = -1

    try:
        message = f"Retrieving VPN Stats - {device_mac}:{node_id}:{port_id}<->{peer_mac}:{peer_port_id}"
        PB.log_message(message, display_pbar=True)
        data = get_vpn_peer_metrics(
            apisession,
            site_id,
            device_mac,
            node_id,
            peer_mac,
            port_id,
            peer_port_id,
            duration,
        )
        for i in range(0, len(data.get("rt", []))):
            latency = data["avg_latency"][i]
            jitter = data["avg_jitter"][i]
            loss = data["avg_loss"][i]
            if latency and latency > max_latency:
                max_latency = latency
                max_latency_datetime = data["rt"][i]
            if jitter and jitter > max_jitter:
                max_jitter = jitter
                max_jitter_datetime = data["rt"][i]
            if loss and loss > max_loss:
                max_loss = loss
                max_loss_datetime = data["rt"][i]
        PB.log_success(message, display_pbar=True, inc=True)
    except:
        PB.log_failure(message, display_pbar=True, inc=True)

    return {
        "jitter": {"max": max_jitter, "at": max_jitter_datetime},
        "latency": {"max": max_latency, "at": max_latency_datetime},
        "loss": {"max": max_loss, "at": max_loss_datetime},
    }


def get_vpn_peers(
    apisession: mistapi.APISession, org_id: str, device_mac: str, duration: str
):
    try:
        message = f"Retrieving VPN Peers for {device_mac}"
        PB.log_message(message, display_pbar=False)
        url = f"/api/v1/orgs/{org_id}/stats/vpn_peers/search"
        query_params = {"mac": device_mac, "duration": duration, "limit": 1000}
        vpn_peers = apisession.mist_get(url, query_params).data.get("results")
        PB.log_success(f"{message}: {len(vpn_peers)}", display_pbar=False)
        return vpn_peers
    except:
        PB.log_failure(message, display_pbar=False)


def get_site_name(apisession: mistapi.APISession, site_id: str):
    try:
        message = f"Retrieving Site info"
        data = mistapi.api.v1.sites.sites.getSiteInfo(apisession, site_id).data
        PB.log_success(f"{message}: {len(data)}", display_pbar=False)
        return data["name"]
    except:
        PB.log_failure(message, display_pbar=False)


def get_device_name(apisession: mistapi.APISession, org_id: str, device_mac: str):
    try:
        message = f"Retrieving Gateways info for {device_mac}"
        data = mistapi.api.v1.orgs.inventory.getOrgInventory(
            apisession, org_id, mac=device_mac, type="gateway", vc=True
        ).data
        PB.log_success(f"{message}: {len(data)}", display_pbar=True, inc=False)
        return data[0]["name"]
    except:
        PB.log_failure(message, display_pbar=True, inc=False)
        return device_mac


def get_site_gateways(apisession: mistapi.APISession, org_id: str, site_id: str):
    try:
        message = f"Retrieving Gateways for site {site_id}"
        data = mistapi.api.v1.orgs.inventory.getOrgInventory(
            apisession, org_id, site_id=site_id, type="gateway"
        ).data
        PB.log_success(f"{message}: {len(data)}", display_pbar=False)
        return data
    except:
        PB.log_failure(message, display_pbar=False)


def start(
    apisession: mistapi.APISession, org_id: str, site_id: str, duration: str = "1w"
):
    """
    Start the process to rename the devices

    PARAMS
    -------
    apisession : mistapi.APISession
        mistapi session, already logged in
    org_id : str
    site_id : str
    duration : str
        e.g. 1w, 1d, 1h, ...
    """
    LOGGER.debug("start")
    LOGGER.debug(f"start:parameter:org_id:{org_id}")
    print()
    print()

    if not org_id:
        org_id = mistapi.cli.select_org(apisession)[0]
    if not site_id:
        site_id = mistapi.cli.select_site(apisession, org_id)[0]

    site_name = get_site_name(apisession, site_id)
    site_gateways = get_site_gateways(apisession, org_id, site_id)
    device_names = {}
    result = [
        [
            "Site Name",
            "Device Name",
            "Node ID",
            "Interface Name",
            "Neighborhood",
            "Peer Name",
            "Status",
            "Max Jitter",
            "Max Latency",
            "Max Loss",
        ]
    ]

    for device in site_gateways:
        device_mac = device["mac"]
        device_name = device["name"]
        vpn_peers = get_vpn_peers(apisession, org_id, device_mac, duration)
        PB.set_steps_total(len(vpn_peers))
        for vpn_peer in vpn_peers:
            node_id = vpn_peer["node"]
            peer_mac = vpn_peer["peer_mac"]
            port_id = vpn_peer["port_id"]
            peer_port_id = vpn_peer["peer_port_id"]
            vpn_name = vpn_peer["vpn_name"]
            if peer_mac in device_names:
                peer_name = device_names[peer_mac]
            else:
                peer_name = get_device_name(apisession, org_id, peer_mac)
                device_names[peer_mac] = peer_name
            if vpn_peer["up"]:
                status = "Up"
                data = get_vpn_peer_peak(
                    apisession,
                    site_id,
                    device_mac,
                    node_id,
                    peer_mac,
                    port_id,
                    peer_port_id,
                    duration,
                )
            else:
                message = f"VPN Down - {device_mac}:{node_id}:{port_id}<->{peer_mac}:{peer_port_id}"
                PB.log_message(message)
                PB.log_success(message, inc=True)
                status = "Standby"
                data = {
                    "jitter": {"max": 0, "at": -1},
                    "latency": {"max": 0, "at": -1},
                    "loss": {"max": 0, "at": -1},
                }
            result.append(
                [
                    site_name,
                    device_name,
                    node_id,
                    port_id,
                    vpn_name,
                    peer_name,
                    status,
                    f"{data['jitter']['max']} at {data['jitter']['at']}",
                    f"{data['latency']['max']} at {data['latency']['at']}",
                    f"{data['loss']['max']} at {data['loss']['at']}",
                ]
            )

    PB.log_title("Results", end=True)
    print(f"Statistics for the last {duration}")
    print(tabulate.tabulate(result))


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
Python script to retrieve VPN Peers statistics for gateways assigned to a site

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

-o, --org_id=           Mist Org ID where the devices are claimed to
-s, --site_id=          Mist Site ID where the devices are claimed to
-d, --duration=         Duration (default: 1w)

-l, --log_file=         define the filepath/filename where to write the logs
                        default is "./script.log"
-e, --env=              define the env file to use (see mistapi env file 
                        documentation here: https://pypi.org/project/mistapi/)
                        default is "~/.mist_env"

-------
Examples:
python3 ./rename_devices.py     
python3 ./rename_devices.py -o 203d3d02-xxxx-xxxx-xxxx-76896a3330f4 -s 03d3d02-xxxx-xxxx-xxxx-76896a3330f4
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
            "ho:s:d:e:l:",
            ["help", "org_id=", "site_id=", "duration=", "env=", "log_file="],
        )
    except getopt.GetoptError as err:
        console.error(err)
        usage()
    ORG_ID = None
    SITE_ID = None
    DURATION = "1w"
    for o, a in opts:
        if o in ["-h", "--help"]:
            usage()
        elif o in ["-o", "--org_id"]:
            ORG_ID = a
        elif o in ["-s", "--site_id"]:
            SITE_ID = a
        elif o in ["-d", "--duration"]:
            DURATION = a
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
    APISESSION = mistapi.APISession(env_file=ENV_FILE, show_cli_notif=False)
    APISESSION.login()
    start(APISESSION, ORG_ID, SITE_ID, DURATION)
